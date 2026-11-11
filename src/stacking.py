"""Bayesian stacking of error-stack variants (dossier s.62).

Stacking (Yao, Vehtari, Simpson & Gelman 2018, Bayesian Analysis 13(3))
chooses weights on the simplex over candidate predictive distributions to
maximise the leave-one-out log score. Here the candidates are five variants
of the election-day error stack (bayes_model.ERROR_STACK_ARMS): shipped,
cal_A (t-scale fix), cal_B (vote-share residual), resid_hybrid and Bfix.
The harness projections are leave-one-cycle-out in every parameter, so each
cycle's predictive is a LOO predictive.

    python src/stacking.py run OUT_DIR [--horizons eve,7,21]
                                       [--seeds 0,100,200] [--cycles 2009,...]
    python src/stacking.py fit OUT_DIR
    python src/stacking.py run_stack OUT_DIR [--cycles ...]
    python src/stacking.py grade OUT_DIR

run:       every arm x cycle x horizon x seed projected once on the cached
           posteriors (read only) with validate_bayes.project_cycle; seat
           draws stored as int8 in OUT_DIR/draws_<horizon>_<cycle>.npz.
           Eve uses the ablation stream SEED + 11 + offset and the eve
           forward weeks; D-h uses SEED + h + offset and the calendar-
           effective weeks (validate_horizon's "calendar" config).
fit:       stacking weights on the five-arm simplex maximising the summed
           per-list log score (floor EPS on each arm's pmf), the three
           horizons averaged with equal weight and the seeds averaged: on
           all eight cycles (production) and on the seven training cycles
           of each held-out cycle (nested LOO). OUT_DIR/weights.json.
run_stack: the held-out stacked forecast of each fold: one project_cycle
           pass with layer error_stack = that fold's weights (the harness
           mirror of bayes_model.ERROR_STACK); OUT_DIR/stack_<h>_<c>.npz.
grade:     reproduction gate, every arm's rule metrics, log score and CRPS,
           the weights and their stability, the nested-LOO stacked
           forecast under the s.53 / s.55 rule, the fold table.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ARMS = ["shipped", "cal_A", "cal_B", "resid_hybrid", "Bfix"]   # s.62.1, fixed
EPS = 1e-4            # log-score floor on each arm's pmf (below 1 draw in 4000)
HORIZONS = ["eve", "7", "21"]
SEEDS = [0, 100, 200]
MAX_SEATS = 120
RULE = {"seat_mae": 0.010, "threshold_brier": 0.0010, "interval_score": 0.05}
FOLD_TIE = 0.1
METRICS = ["seat_mae_median", "seat_mae", "coverage_90", "threshold_brier", "interval_score"]


# ---------------------------------------------------------------------------
# the stacking optimiser
# ---------------------------------------------------------------------------
def _softmax(theta):
    e = np.exp(theta - theta.max())
    return e / e.sum()


def stack_objective(w, P, a=None) -> float:
    """sum_i a_i log(P_i . w): the (weighted) log score of the mixture."""
    P = np.asarray(P, float)
    a = np.ones(len(P)) if a is None else np.asarray(a, float)
    return float((a * np.log(P @ np.asarray(w, float))).sum())


def stack_weights(P, a=None, em_check: bool = True) -> np.ndarray:
    """Weights w on the simplex maximising sum_i a_i log(sum_k w_k P_ik).

    P (n, K): each candidate's (floored, so positive) predictive probability
    of the realised outcome i; a (n,): non-negative observation weights.
    BFGS on a softmax parametrisation (all K logits; the gradient is
    orthogonal to the non-identified direction, so it never moves) with the
    analytic gradient, from equal weights. The objective is concave in w,
    so a stationary point is the global optimum; em_check also runs the EM
    fixed point for mixture weights and keeps whichever scores higher."""
    from scipy.optimize import minimize
    P = np.asarray(P, float)
    if P.ndim != 2 or (P <= 0).any():
        raise ValueError("P must be a 2-d array of positive probabilities")
    n, K = P.shape
    a = np.ones(n) if a is None else np.asarray(a, float)
    scale = a.sum()

    def f(theta):
        w = _softmax(theta)
        m = P @ w
        val = -(a * np.log(m)).sum() / scale
        gw = -(a[:, None] * P / m[:, None]).sum(axis=0) / scale     # d(-obj)/dw
        return val, w * (gw - (w * gw).sum())                        # chain rule through softmax

    res = minimize(f, np.zeros(K), jac=True, method="BFGS",
                   options={"gtol": 1e-10, "maxiter": 20000})
    w = _softmax(res.x)
    if em_check:
        w_em = stack_weights_em(P, a)
        if stack_objective(w_em, P, a) > stack_objective(w, P, a):
            w = w_em
    return w / w.sum()


def stack_weights_em(P, a=None, iters: int = 200000, tol: float = 1e-13) -> np.ndarray:
    """EM for mixture weights with fixed components: w_k <- sum_i a_i r_ik /
    sum_i a_i, r_ik = w_k P_ik / sum_j w_j P_ij. Monotone in the objective."""
    P = np.asarray(P, float)
    n, K = P.shape
    a = np.ones(n) if a is None else np.asarray(a, float)
    w = np.full(K, 1.0 / K)
    for _ in range(iters):
        r = P * w / (P @ w)[:, None]
        w_new = (a[:, None] * r).sum(axis=0) / a.sum()
        if np.abs(w_new - w).max() < tol:
            return w_new
        w = w_new
    return w


def round_weights(w, names, decimals: int = 3) -> dict:
    """Production form (s.62.1): rounded to three decimals, renormalised on
    the largest weight, arms that round to zero dropped."""
    r = np.round(np.asarray(w, float), decimals)
    r[int(np.argmax(r))] += round(1.0 - r.sum(), decimals)
    return {n: round(float(x), decimals) for n, x in zip(names, r) if x > 0}


# ---------------------------------------------------------------------------
# scores
# ---------------------------------------------------------------------------
def pmf_at(seats, actual) -> np.ndarray:
    """Per list, the fraction of draws giving exactly the realised seats."""
    return (np.asarray(seats) == np.asarray(actual)[None, :]).mean(axis=0)


def log_score(seats, actual, mask, eps: float = EPS) -> float:
    return float(np.log(np.maximum(pmf_at(seats, actual), eps))[mask].sum())


def cdf_matrix(seats) -> np.ndarray:
    """(B, 121): each list's CDF at 0..120 seats."""
    seats = np.asarray(seats)
    out = np.empty((seats.shape[1], MAX_SEATS + 1))
    for j in range(seats.shape[1]):
        out[j] = np.bincount(seats[:, j].astype(int), minlength=MAX_SEATS + 1)[:MAX_SEATS + 1].cumsum()
    return out / seats.shape[0]


def crps_from_cdf(F, actual, mask) -> float:
    """Discrete CRPS sum_x (F(x) - 1{x >= y})^2, summed over the masked lists."""
    x = np.arange(MAX_SEATS + 1)
    step = (x[None, :] >= np.asarray(actual)[:, None]).astype(float)
    return float(((F - step) ** 2).sum(axis=1)[mask].sum())


def rule_metrics(seats, actual, mask, nb=None) -> dict:
    """The harness metrics (validate_bayes / validate_horizon, *_fixed mask)."""
    seats = np.asarray(seats, float)
    lo, hi = np.percentile(seats, 5, axis=0), np.percentile(seats, 95, axis=0)
    pp = (seats >= 1).mean(axis=0)
    isc = (hi - lo) + 20 * np.maximum(lo - actual, 0) + 20 * np.maximum(actual - hi, 0)
    m = mask
    out = {"seat_mae_median": float(np.abs(np.median(seats, axis=0) - actual)[m].mean()),
           "seat_mae": float(np.abs(seats.mean(axis=0) - actual)[m].mean()),
           "coverage_90": float(((actual >= lo) & (actual <= hi))[m].mean()),
           "threshold_brier": float(np.mean((pp[m] - (actual[m] > 0)) ** 2)),
           "interval_score": float(isc[m].mean()),
           "mean_width": float((hi - lo)[m].mean())}
    if nb is not None:
        out["p_nb61"] = float((seats[:, nb].sum(axis=1) >= 61).mean())
        out["nb_actual"] = int(actual[nb].sum())
    return out


def seed_int(hz: str, offset: int) -> int:
    from bayes_model import SEED
    return (SEED + 11 + offset) if hz == "eve" else (SEED + int(hz) + offset)


# ---------------------------------------------------------------------------
# harness windows
# ---------------------------------------------------------------------------
def _windows(cycles, horizons):
    """(hz, cycle, data, idata, params, eday, weeks, job, actual-resolver)
    for every cached window, with the same parameters validate_bayes.main /
    validate_horizon.main build (all leave-one-cycle-out)."""
    import bayes_model as bm
    from error_decomposition import decompose
    from scrape_polls import ELECTION_DAY, PROCESSED_DIR
    import validate_bayes as vb
    from validate_horizon import calendar_weeks

    import record
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = record.results()
    for cycle in cycles:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        res = vb.apply_decomp(results[results["cycle"] == cycle], cycle)
        params = decompose(exclude_cycle=cycle)
        params["trail"] = vb.trailing_likud_params(polls, results, exclude_cycle=cycle)
        params["new_lists"] = vb.new_lists_for_cycle(polls, cycle)
        params["nstrad"] = vb.new_straddler_params(exclude_cycle=cycle)
        params["pair_alias"] = vb._decomp_map(cycle)
        params["arab_tab"] = vb.arab_turnout_params(cycle)
        params["arab_lineage"] = bm.arab_lineage_share(exclude_cycle=cycle)
        params["haredi_lineage"] = bm.haredi_lineage_share(exclude_cycle=cycle)
        params["registered_pairs"] = vb.REGISTERED_PAIRS[cycle]
        params["cycle"] = cycle
        vb.add_calibration_params(params, cycle)
        vb.add_threshold_params(params, cycle)
        for hz in horizons:
            if hz == "eve":
                asof, nc, dr, job, wk = eday - pd.Timedelta(days=1), f"{cycle}_eve.nc", 600, f"{cycle}_eve", None
            else:
                h = int(hz)
                asof, nc, dr, job = eday - pd.Timedelta(days=h), f"{cycle}_D{h}.nc", 400, f"{cycle}_D{h}"
                wk = calendar_weeks(h)
            path = vb.CACHE_DIR / nc
            if not path.exists():
                raise SystemExit(f"[{job}] no cached posterior {path} (the run reads the cache only)")
            cyc = vb.harness_frame(polls, cycle, eday, asof, verbose=False)
            data = vb.harness_prepare(cyc, asof)
            if hz != "eve" and data["n_polls"] < 8:
                print(f"[{job}] only {data['n_polls']} polls: skipped (as validate_horizon)")
                continue
            idata = vb.load_or_fit(path, data, dr, dr)
            yield hz, cycle, data, idata, params, eday, wk, job, res


def _project(vb, data, idata, params, eday, wk, cycle, seed, layers):
    from simulate import THRESHOLD
    return vb.project_cycle(data, idata, eday, vb.CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                            vb.PAST_PAIRS[cycle], params, vb.VAL_BLOC_OVERRIDES.get(cycle),
                            np.random.default_rng(seed), weeks_override=wk, layers=layers)


def _actual(res, comp_of, B):
    actual = np.zeros(B)
    for r in res.itertuples():
        hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
        if len(hit) == 1:
            actual[hit.pop()] += r.seats
    return actual


def run(out: Path, horizons, seeds, cycles) -> None:
    import bayes_model as bm
    import validate_bayes as vb
    out.mkdir(parents=True, exist_ok=True)
    for hz, cycle, data, idata, params, eday, wk, job, res in _windows(cycles, horizons):
        vb.project_cycle.job = job
        draws, masks, actual, nb = [], [], None, None
        for arm in ARMS:
            per_seed = []
            for k, off in enumerate(seeds):
                seats, blocs, base, comp_of = _project(vb, data, idata, params, eday, wk, cycle,
                                                       seed_int(hz, off), dict(bm.ERROR_STACK_ARMS[arm]))
                if arm == "shipped":
                    act = _actual(res, comp_of, seats.shape[1])
                    actual = act if actual is None else actual
                    assert (act == actual).all()
                    masks.append((base >= 0.005) | (act > 0))
                    nb = blocs == "netanyahu_bloc"
                per_seed.append(seats.astype(np.int8))
            draws.append(np.stack(per_seed))
        np.savez_compressed(out / f"draws_{hz}_{cycle}.npz", seats=np.stack(draws), actual=actual,
                            mask=np.stack(masks), nb=nb, arms=np.array(ARMS), seeds=np.array(seeds),
                            components=np.array(data["components"]))
        print(f"[{job}] stored {len(ARMS)} arms x {len(seeds)} seeds", flush=True)


def load(out: Path, prefix: str = "draws") -> dict:
    W = {}
    for f in sorted(out.glob(f"{prefix}_*.npz")):
        _, hz, cycle = f.stem.split("_", 2)
        z = np.load(f, allow_pickle=False)
        W[(hz, cycle)] = {k: z[k] for k in z.files}
    return W


# ---------------------------------------------------------------------------
# fitting the weights
# ---------------------------------------------------------------------------
def stack_rows(W, cycles, horizons=HORIZONS, arms=ARMS):
    """The stacking design: one row per (cycle, horizon, seed, masked list),
    columns the arms' floored pmf at the realised seats; observation weight
    1 / (n_horizons x n_seeds), so the objective is
    sum_c mean_h mean_s S_{c,h,s}(w)."""
    rows, wts, keys = [], [], []
    for (hz, cycle), z in W.items():
        if cycle not in cycles or hz not in horizons:
            continue
        ai = [list(z["arms"]).index(a) for a in arms]
        S = z["seats"].shape[1]
        for s in range(S):
            m = z["mask"][s]
            p = np.stack([pmf_at(z["seats"][a, s], z["actual"]) for a in ai], axis=1)[m]
            rows.append(np.maximum(p, EPS))
            wts.append(np.full(m.sum(), 1.0 / (len(horizons) * S)))
            keys += [(cycle, hz, s)] * int(m.sum())
    return np.concatenate(rows), np.concatenate(wts), keys


def fit(out: Path) -> dict:
    W = load(out)
    cycles = sorted({c for _, c in W})
    P, a, _ = stack_rows(W, cycles)
    w_all = stack_weights(P, a)
    res = {"arms": ARMS, "eps": EPS, "all_raw": w_all.tolist(),
           "all": round_weights(w_all, ARMS),
           "em_all": stack_weights_em(P, a).tolist(),
           "objective_all": stack_objective(w_all, P, a), "folds": {}, "folds_raw": {},
           "select": {}}
    for c in cycles:
        Pc, ac, _ = stack_rows(W, [x for x in cycles if x != c])
        wc = stack_weights(Pc, ac)
        res["folds_raw"][c] = wc.tolist()
        res["folds"][c] = round_weights(wc, ARMS)
        # single-arm selection by the same training objective
        res["select"][c] = ARMS[int(np.argmax([stack_objective(np.eye(len(ARMS))[k], Pc, ac)
                                                for k in range(len(ARMS))]))]
    (out / "weights.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"all": res["all"], "folds": res["folds"], "select": res["select"]}, indent=1))
    return res


def run_stack(out: Path, cycles, horizons=HORIZONS, seeds=SEEDS) -> None:
    import validate_bayes as vb
    wt = json.loads((out / "weights.json").read_text())
    for hz, cycle, data, idata, params, eday, wk, job, res in _windows(cycles, horizons):
        vb.project_cycle.job = job
        w = wt["folds"][cycle]
        per_seed, frac = [], []
        for off in seeds:
            seats, _, _, _ = _project(vb, data, idata, params, eday, wk, cycle,
                                      seed_int(hz, off), {"error_stack": w})
            per_seed.append(seats.astype(np.int8))
            frac.append([vb.project_cycle.last_error_stack.get(a, 0.0) for a in ARMS])
        np.savez_compressed(out / f"stack_{hz}_{cycle}.npz", seats=np.stack(per_seed),
                            weights=np.array([w.get(a, 0.0) for a in ARMS]), frac=np.array(frac),
                            seeds=np.array(seeds))
        print(f"[{job}] stacked forecast with {w}", flush=True)


# ---------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------
def crn_mixture(z, s, hz, offset, w: dict) -> np.ndarray:
    """The exact mixture sampled from the stored draws with common random
    numbers: simulation i takes arm a_i's draw i, a_i from the same child
    generator the mirror uses."""
    import bayes_model as bm
    names, arm = bm.error_stack_assign(np.random.default_rng(seed_int(hz, offset)), w,
                                       z["seats"].shape[2])
    ai = np.array([list(z["arms"]).index(n) for n in names])[arm]
    return z["seats"][ai, s, np.arange(len(arm))]


def score_table(W, S_draws, wt) -> pd.DataFrame:
    rows = []
    for (hz, cycle), z in sorted(W.items()):
        actual, nb = z["actual"], z["nb"]
        arms = list(z["arms"])
        for s, off in enumerate(z["seeds"]):
            m = z["mask"][s]
            pm = {a: np.maximum(pmf_at(z["seats"][k, s], actual), EPS) for k, a in enumerate(arms)}
            Fm = {a: cdf_matrix(z["seats"][k, s]) for k, a in enumerate(arms)}

            def add(label, seats=None, ls=None, crps=None):
                r = {"horizon": hz, "cycle": cycle, "seed": int(off), "label": label,
                     "n_lists": int(m.sum())}
                if seats is not None:
                    r.update(rule_metrics(seats, actual, m, nb))
                    r["bloc_sq"] = (r["p_nb61"] - float(r["nb_actual"] >= 61)) ** 2
                    r["log_score"] = log_score(seats, actual, m) if ls is None else ls
                    r["crps"] = crps_from_cdf(cdf_matrix(seats), actual, m) if crps is None else crps
                else:
                    r["log_score"], r["crps"] = ls, crps
                rows.append(r)

            for a in arms:
                add(a, z["seats"][arms.index(a), s])

            def exact(w):   # the pmf mixture's own log score and CRPS
                ls = float(np.log(sum(w.get(a, 0.0) * pm[a] for a in arms))[m].sum())
                F = sum(w.get(a, 0.0) * Fm[a] for a in arms)
                return ls, crps_from_cdf(F, actual, m)

            wf = wt["folds"][cycle]
            ls, cr = exact(wf)
            add("stack_exact", crn_mixture(z, s, hz, off, wf), ls, cr)
            ls, cr = exact(wt["all"])
            add("stack_insample", crn_mixture(z, s, hz, off, wt["all"]), ls, cr)
            sel = wt["select"][cycle]
            add("select", z["seats"][arms.index(sel), s])
            if (hz, cycle) in S_draws:
                add("stack", S_draws[(hz, cycle)]["seats"][s])
    return pd.DataFrame(rows)


def pooled(d: pd.DataFrame, cols) -> pd.Series:
    """Per seed the mean over cycles, then the mean over seeds."""
    return d.groupby("seed")[cols].mean().mean()


def rule_check(T: pd.DataFrame, arm: str, base: str = "shipped") -> tuple:
    ok, why, rows = True, [], []
    for hz in HORIZONS:
        b, x = T[(T.label == base) & (T.horizon == hz)], T[(T.label == arm) & (T.horizon == hz)]
        if x.empty:
            return False, [f"{hz} missing"], rows
        pb, px = pooled(b, METRICS), pooled(x, METRICS)
        fb = b.groupby("cycle")["seat_mae_median"].mean()
        fx = x.groupby("cycle")["seat_mae_median"].mean()
        dd = (fx - fb).reindex(fb.index)
        lost = dd[dd >= FOLD_TIE]
        if len(lost):
            ok = False
            why.append(f"{hz}: median fold(s) " + ", ".join(f"{c} {v:+.3f}" for c, v in lost.items()))
        for k, fl in RULE.items():
            if px[k] - pb[k] > fl:
                ok = False
                why.append(f"{hz}: {k} {px[k] - pb[k]:+.4f} > {fl}")
        if abs(px["coverage_90"] - 0.9) > abs(pb["coverage_90"] - 0.9) + 1e-12:
            ok = False
            why.append(f"{hz}: coverage {px['coverage_90']:.4f} further from .90 than {pb['coverage_90']:.4f}")
        rows.append({"horizon": hz, "W": int((dd <= -FOLD_TIE).sum()),
                     "T": int((dd.abs() < FOLD_TIE).sum()), "L": int((dd >= FOLD_TIE).sum())})
    return ok, why, rows


def grade(out: Path) -> None:
    W = load(out)
    S_draws = load(out, "stack")
    wt = json.loads((out / "weights.json").read_text())
    T = score_table(W, S_draws, wt)
    T.to_csv(out / "scores.csv", index=False)
    cycles = sorted(T.cycle.unique())
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    labels = ARMS + ["stack", "stack_exact", "stack_insample", "select"]

    print("=== pooled rule metrics (3 seeds; per seed mean over cycles) ===")
    for hz in HORIZONS:
        tab = []
        for lab in labels:
            x = T[(T.label == lab) & (T.horizon == hz)]
            if x.empty:
                continue
            p = pooled(x, METRICS + ["mean_width"])
            p["log_score"] = x.groupby("seed")["log_score"].sum().mean()
            p["crps"] = x.groupby("seed")["crps"].sum().mean()
            p["bloc_brier"] = pooled(x, ["bloc_sq"])["bloc_sq"]
            tab.append(p.rename(lab))
        print(f"\n--- {hz} ---")
        print(pd.DataFrame(tab).round(4).to_string())

    print("\n=== log score / CRPS by cycle (seed mean; sum over lists) ===")
    for hz in HORIZONS:
        x = T[T.horizon == hz].groupby(["label", "cycle"])[["log_score", "crps"]].mean()
        print(f"\n--- {hz} log score ---")
        print(x["log_score"].unstack("cycle").reindex(labels).round(2).to_string())
        print(f"--- {hz} CRPS ---")
        print(x["crps"].unstack("cycle").reindex(labels).round(2).to_string())

    print("\n=== weights ===")
    fr = pd.DataFrame(wt["folds_raw"], index=ARMS).T
    fr.loc["ALL"] = wt["all_raw"]
    print(fr.round(4).to_string())
    print("rounded production weights:", wt["all"])
    print("rounded fold weights:", wt["folds"])
    st = pd.DataFrame(wt["folds_raw"], index=ARMS).T
    print("fold stability: min / max / sd\n" + pd.DataFrame(
        {"min": st.min(), "max": st.max(), "sd": st.std(ddof=1)}).round(4).to_string())
    print("single-arm selection per fold:", wt["select"])

    print("\n=== fold table: median MAE (three-seed mean), stack - shipped ===")
    for hz in HORIZONS:
        b = T[(T.label == "shipped") & (T.horizon == hz)].groupby("cycle")["seat_mae_median"].mean()
        rows = {"shipped": b}
        for lab in ["stack", "stack_exact"] + ARMS[1:]:
            x = T[(T.label == lab) & (T.horizon == hz)]
            if not x.empty:
                rows[lab] = x.groupby("cycle")["seat_mae_median"].mean() - b
        print(f"\n--- {hz} ---")
        print(pd.DataFrame(rows).round(3).T.to_string())

    print("\n=== rule (s.53 / s.55) vs shipped ===")
    for lab in ["stack"] + ARMS[1:] + ["stack_exact"]:
        ok, why, rows = rule_check(T, lab)
        wtl = " ".join(f"{r['horizon']} {r['W']}/{r['T']}/{r['L']}" for r in rows)
        print(f"  {lab:14s} {'PASS' if ok else 'FAIL'}  folds W/T/L {wtl}  " + "; ".join(why))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    cmd, out = sys.argv[1], Path(sys.argv[2])
    opts = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    from validate_bayes import ORDER
    cyc = opts.get("--cycles", ",".join(ORDER)).split(",")
    if cmd == "run":
        run(out, horizons=opts.get("--horizons", ",".join(HORIZONS)).split(","),
            seeds=[int(s) for s in opts.get("--seeds", ",".join(map(str, SEEDS))).split(",")],
            cycles=cyc)
    elif cmd == "fit":
        fit(out)
    elif cmd == "run_stack":
        run_stack(out, cyc)
    elif cmd == "grade":
        grade(out)
    else:
        raise SystemExit(f"unknown command {cmd!r}")
