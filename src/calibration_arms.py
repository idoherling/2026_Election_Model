"""Uncertainty calibration arms (dossier s.48).

Grades the shock-stack candidates of s.48 together with a residual-width
grid, at election eve and at D-7 / D-21 / D-56, on the cached harness
posteriors (read only), and chooses the width by nested leave-one-cycle-out.

    python src/calibration_arms.py run OUT_DIR [--horizons eve,7,21,56]
                                       [--seeds 0,1,2] [--cycles 2009,...]
    python src/calibration_arms.py grade OUT_DIR

run: for every (horizon, cycle) window it loads the window's posterior, the
cycle's leave-one-cycle-out parameters (the same calls validate_bayes.main
and validate_horizon.main make) and projects every arm x width x seed with
the harness's own project_cycle. Eve uses the eve ablation stream
(SEED + 11 + seed) and the eve forward weeks; D-h uses SEED + h + seed and
the calendar-effective weeks, as validate_horizon does. Every row is scored
on the shipped list mask: the base arm at the shipped width, same seed.
Writes OUT_DIR/rows_<horizon>_<cycle>.csv.

grade: pooled metrics per arm and horizon (cycles first, then the seed
mean), per-fold interval-score wins, the bloc Brier for P(NB >= 61), and
the nested leave-one-cycle-out width arms: for each held-out cycle the width
with the lowest mean interval score over the other seven cycles, averaged
with equal weight over eve / D-7 / D-21, graded on the held-out cycle at
every horizon (pre-registered, s.48.1).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ARMS = {
    "base": {},
    "A": {"t_unit": True},
    "B": {"resid_space": "vote"},
    "Bfix": {"resid_space": "seat_fix"},
    "AB": {"t_unit": True, "resid_space": "vote"},
    "D": {"resid_df": "loo"},
    "ABD": {"t_unit": True, "resid_space": "vote", "resid_df": "loo"},
    # hierarchical error model (dossier s.61): its residual width multiplier
    # is the layer hier_width (the fixed arm at bm.HIER_RESID_SCALE, 1.0)
    "H1": {"error_model": "hierarchical"},
}
# nested width arms (CBfix added by amendment 3, s.48.1: the width re-chosen
# after the decompose() index fix; H2 = H1 with the nested width, s.61.1)
GRID_ARMS = {"C0": "base", "CA": "A", "CAB": "AB", "CABD": "ABD", "CBfix": "Bfix", "H2": "H1"}
WIDTHS = [round(0.4 + 0.1 * i, 1) for i in range(13)]               # 0.4 .. 1.6
CHOICE_HORIZONS = ["eve", "7", "21"]                                  # D-56 never chooses
METRICS = ["seat_mae_median", "seat_mae", "coverage_90", "threshold_brier", "interval_score"]


def _jobs(arm_widths):
    for arm, flags in ARMS.items():
        for w in arm_widths(arm):
            yield arm, w, flags


def _is_hier(flags) -> bool:
    return flags.get("error_model") == "hierarchical"


def fixed_width(arm: str, shipped_w: float) -> float:
    """The width a fixed (non-nested) arm is graded at: the shipped
    RESID_SCALE, or bm.HIER_RESID_SCALE on a hierarchical arm (s.61)."""
    import bayes_model as bm
    return float(bm.HIER_RESID_SCALE) if _is_hier(ARMS.get(arm, {})) else shipped_w


def run(out: Path, horizons, seeds, cycles, tag: str = "") -> None:
    import bayes_model as bm
    from bayes_model import SEED
    from error_decomposition import decompose
    from scrape_polls import ELECTION_DAY, PROCESSED_DIR
    from simulate import THRESHOLD
    import validate_bayes as vb
    from validate_horizon import calendar_weeks

    shipped_w = float(bm.RESID_SCALE)
    grid_bases = set(GRID_ARMS.values())

    def arm_widths(arm):
        return WIDTHS if arm in grid_bases else [fixed_width(arm, shipped_w)]

    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    out.mkdir(parents=True, exist_ok=True)
    for cycle in cycles:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        res = vb.apply_decomp(results[results["cycle"] == cycle], cycle)
        params = decompose(exclude_cycle=cycle)
        params["trail"] = vb.trailing_likud_params(polls, results, exclude_cycle=cycle)
        params["new_lists"] = vb.new_lists_for_cycle(polls, cycle)
        params["nstrad"] = vb.new_straddler_params(exclude_cycle=cycle)
        params["pair_alias"] = vb._decomp_map(cycle)
        params["arab_tab"] = vb.arab_turnout_params(cycle)
        params["arab_lineage"] = bm.arab_lineage_share(exclude_cycle=cycle)   # s.51
        params["haredi_lineage"] = bm.haredi_lineage_share(exclude_cycle=cycle)   # s.54
        vb.add_calibration_params(params, cycle)
        for hz in horizons:
            if hz == "eve":
                asof, nc, dr, job = eday - pd.Timedelta(days=1), f"{cycle}_eve.nc", 600, f"{cycle}_eve"
                wk = None
            else:
                h = int(hz)
                asof, nc, dr, job = eday - pd.Timedelta(days=h), f"{cycle}_D{h}.nc", 400, f"{cycle}_D{h}"
                wk = calendar_weeks(h)
            path = vb.CACHE_DIR / nc
            if not path.exists():
                print(f"[{job}] no cached posterior {path}: skipped (never fitted here)")
                continue
            cyc = vb.harness_frame(polls, cycle, eday, asof, verbose=False)
            data = vb.harness_prepare(cyc, asof)
            idata = vb.load_or_fit(path, data, dr, dr)
            vb.project_cycle.job = job
            rows = []
            for s in seeds:
                seed = (SEED + 11 + s) if hz == "eve" else (SEED + int(hz) + s)
                fixed = None
                order = [("base", shipped_w, {})] + [j for j in _jobs(arm_widths)
                                                     if not (j[0] == "base" and j[1] == shipped_w)]
                for arm, w, flags in order:
                    # a hierarchical arm's width is its hier_width layer (s.61)
                    lay = dict(flags, hier_width=w) if _is_hier(flags) else flags
                    seats, blocs, base, comp_of = vb.project_cycle(
                        data, idata, eday, vb.CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                        vb.PAST_PAIRS[cycle], params, vb.VAL_BLOC_OVERRIDES.get(cycle),
                        np.random.default_rng(seed), resid_scale=w,
                        weeks_override=wk, layers=lay)
                    actual = np.zeros(seats.shape[1])
                    for r in res.itertuples():
                        hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
                        if len(hit) == 1:
                            actual[hit.pop()] += r.seats
                    active = (base >= 0.005) | (actual > 0)
                    if fixed is None:
                        fixed = active
                    m = fixed
                    lo, hi = np.percentile(seats, 5, axis=0), np.percentile(seats, 95, axis=0)
                    pp = (seats >= 1).mean(axis=0)
                    isc = (hi - lo) + 20 * np.maximum(lo - actual, 0) + 20 * np.maximum(actual - hi, 0)
                    nbm = blocs == "netanyahu_bloc"
                    rows.append({
                        "horizon": hz, "cycle": cycle, "seed": s, "arm": arm, "width": w,
                        "n_lists": int(m.sum()),
                        "seat_mae_median": float(np.abs(np.median(seats, axis=0) - actual)[m].mean()),
                        "seat_mae": float(np.abs(seats.mean(axis=0) - actual)[m].mean()),
                        "coverage_90": float(((actual >= lo) & (actual <= hi))[m].mean()),
                        "threshold_brier": float(np.mean((pp[m] - (actual[m] > 0)) ** 2)),
                        "interval_score": float(isc[m].mean()),
                        "mean_width": float((hi - lo)[m].mean()),
                        "p_nb61": float((seats[:, nbm].sum(axis=1) >= 61).mean()),
                        "nb_actual": int(actual[nbm].sum()),
                        "trail_frac": float(vb.project_cycle.last_trail.get("frac", 0.0)),
                    })
            df = pd.DataFrame(rows)
            df.to_csv(out / f"rows_{hz}_{cycle}{tag}.csv", index=False)
            b = df[(df.arm == "base") & (df.width == shipped_w)][METRICS].mean()
            print(f"[{job}] {len(df)} rows | base: " + " ".join(f"{k} {v:.3f}" for k, v in b.items()), flush=True)


# ---------------------------------------------------------------------------
def load_rows(out: Path) -> pd.DataFrame:
    fs = sorted(out.glob("rows_*.csv"))
    d = pd.concat([pd.read_csv(f, dtype={"horizon": str, "cycle": str}) for f in fs], ignore_index=True)
    # a supplementary pass repeats base / its own arm at the shipped width;
    # every projection uses a fresh rng(seed), so the repeats are identical
    d = d.drop_duplicates(["horizon", "cycle", "seed", "arm", "width"])
    d["bloc_hit"] = (d["nb_actual"] >= 61).astype(float)
    d["bloc_sq"] = (d["p_nb61"] - d["bloc_hit"]) ** 2
    return d


def pooled(d: pd.DataFrame) -> pd.Series:
    """Cycles pooled (mean of per-cycle means), then the mean over seeds."""
    by_seed = d.groupby("seed")[METRICS + ["bloc_sq", "mean_width"]].mean()
    out = by_seed.mean()
    out["ce"] = abs(out["coverage_90"] - 0.90)
    out["n_cycles"] = d["cycle"].nunique()
    out["n_seeds"] = d["seed"].nunique()
    return out


def nested_choice(d: pd.DataFrame, arm: str, held: str | None) -> float:
    """The width minimising the training interval score: cycles other than
    `held`, per horizon in CHOICE_HORIZONS the seed-mean per-cycle IS
    averaged over cycles, then the equal-weight mean over horizons."""
    x = d[(d.arm == arm) & d.horizon.isin(CHOICE_HORIZONS)]
    if held is not None:
        x = x[x.cycle != held]
    per = (x.groupby(["horizon", "cycle", "width"])["interval_score"].mean()
           .groupby(["horizon", "width"]).mean().unstack(0))
    per = per[[h for h in CHOICE_HORIZONS if h in per.columns]]
    return float(per.mean(axis=1).idxmin())


def grade(out: Path) -> None:
    import bayes_model as bm
    shipped_w = float(bm.RESID_SCALE)
    d = load_rows(out)
    cycles = sorted(d.cycle.unique())
    horizons = [h for h in ["eve", "7", "21", "56"] if h in set(d.horizon)]
    # assemble every arm's graded rows: fixed-width arms at the shipped width,
    # nested arms at their held-out choice
    graded, picks = [], {}
    have = set(d.arm)          # a subset run (--arms) grades only its arms
    for arm in [a for a in ARMS if a in have]:
        x = d[(d.arm == arm) & (d.width == fixed_width(arm, shipped_w))]
        graded.append(x.assign(label=arm))
    for lab, arm in [(l, a) for l, a in GRID_ARMS.items() if a in have]:
        picks[lab] = {c: nested_choice(d, arm, c) for c in cycles}
        x = pd.concat([d[(d.arm == arm) & (d.cycle == c) & (d.width == picks[lab][c])]
                       for c in cycles])
        graded.append(x.assign(label=lab))
        picks[lab]["ALL"] = nested_choice(d, arm, None)
    g = pd.concat(graded, ignore_index=True)
    g.to_csv(out / "graded_rows.csv", index=False)

    print(f"cycles {cycles}; horizons {horizons}; widths {WIDTHS}; shipped width {shipped_w}")
    print("\nnested width picks (held-out cycle -> width; ALL = production choice):")
    for lab, p in picks.items():
        print(f"  {lab:5s} {GRID_ARMS[lab]:4s}: " + ", ".join(f"{k} {v:.1f}" for k, v in p.items()))
    summ = []
    for hz in horizons:
        base = g[(g.label == "base") & (g.horizon == hz)]
        pb = pooled(base)
        bfold = base.groupby("cycle")[["interval_score", "seat_mae_median"]].mean()
        for lab in g.label.unique():
            x = g[(g.label == lab) & (g.horizon == hz)]
            if x.empty:
                continue
            px = pooled(x)
            xf = x.groupby("cycle")[["interval_score", "seat_mae_median"]].mean()
            dis = (xf["interval_score"] - bfold["interval_score"]).dropna()
            dmm = (xf["seat_mae_median"] - bfold["seat_mae_median"]).dropna()
            row = {"horizon": hz, "arm": lab, **px.to_dict(),
                   "is_w": int((dis < -0.05).sum()), "is_t": int((dis.abs() <= 0.05).sum()),
                   "is_l": int((dis > 0.05).sum()),
                   "mm_w": int((dmm < -0.1).sum()), "mm_t": int((dmm.abs() <= 0.1).sum()),
                   "mm_l": int((dmm > 0.1).sum())}
            # seed noise of the paired difference (eve only: 3 seeds)
            if x.seed.nunique() > 1:
                xs = x.groupby("seed")[METRICS].mean()
                bs = base.groupby("seed")[METRICS].mean()
                dd = (xs - bs).std(ddof=1)
                for k in METRICS:
                    row["sd_" + k] = float(dd[k])
            summ.append(row)
    S = pd.DataFrame(summ)
    S.to_csv(out / "summary.csv", index=False)
    show = ["horizon", "arm", "seat_mae_median", "seat_mae", "coverage_90", "threshold_brier",
            "interval_score", "ce", "bloc_sq", "mean_width", "is_w", "is_t", "is_l",
            "mm_w", "mm_t", "mm_l", "n_cycles", "n_seeds"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        for hz in horizons:
            print(f"\n=== {hz} ===")
            print(S[S.horizon == hz][show].round(4).to_string(index=False))
    # decision rule (s.48.1)
    print("\n=== decision rule (vs base) ===")
    eve = S[S.horizon == "eve"].set_index("arm")
    b = eve.loc["base"]
    res = []
    for lab in eve.index:
        if lab == "base":
            continue
        a = eve.loc[lab]
        why = []
        if not a["interval_score"] < b["interval_score"]:
            why.append(f"eve IS {a['interval_score']:.3f} >= {b['interval_score']:.3f}")
        if a["ce"] > b["ce"] + 0.005:
            why.append(f"eve CE {a['ce']:.3f} > {b['ce']:.3f}+.005")
        for k, floor in (("seat_mae_median", 0.010), ("seat_mae", 0.010), ("threshold_brier", 0.0010)):
            nf = max(2 * float(a.get("sd_" + k, 0.0) or 0.0), floor)
            if a[k] - b[k] > nf:
                why.append(f"eve {k} +{a[k] - b[k]:.4f} > floor {nf:.4f}")
        for hz in ("7", "21"):
            hh = S[(S.horizon == hz)].set_index("arm")
            if lab not in hh.index:
                why.append(f"D-{hz} missing")
                continue
            if hh.loc[lab, "interval_score"] - hh.loc["base", "interval_score"] > 0.05:
                why.append(f"D-{hz} IS +{hh.loc[lab, 'interval_score'] - hh.loc['base', 'interval_score']:.3f}")
            if hh.loc[lab, "ce"] - hh.loc["base", "ce"] > 0.010:
                why.append(f"D-{hz} CE +{hh.loc[lab, 'ce'] - hh.loc['base', 'ce']:.3f}")
        res.append((lab, not why, a["interval_score"], a["ce"], "; ".join(why) or "PASS"))
    for lab, ok, isc, ce, why in res:
        print(f"  {lab:5s} IS {isc:.3f} CE {ce:.3f}  {why}")
    passing = [(isc, ce, lab) for lab, ok, isc, ce, _ in res if ok]
    if passing:
        best = min(passing)[0]
        near = [p for p in passing if p[0] - best <= 0.02]

        def hmean(lab):
            hh = S[S.horizon.isin(["7", "21"]) & (S.arm == lab)]
            return float(hh["interval_score"].mean())
        near.sort(key=lambda p: (round(p[1], 3), hmean(p[2])))
        print(f"\nrecommended (lowest eve IS, within .02 -> lower CE, then D-7/D-21 IS): {near[0][2]}")
    else:
        print("\nno arm passes")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    cmd, out = sys.argv[1], Path(sys.argv[2])
    opts = dict(zip(sys.argv[3::2], sys.argv[4::2]))
    if cmd == "run":
        from validate_bayes import ORDER
        if "--arms" in opts:   # a subset pass (base always kept for the list mask)
            keep = set(opts["--arms"].split(",")) | {"base"}
            ARMS = {k: v for k, v in ARMS.items() if k in keep}
            GRID_ARMS = {k: v for k, v in GRID_ARMS.items() if v in keep and (v != "base" or "base" in opts["--arms"].split(","))}
        run(out,
            horizons=opts.get("--horizons", "eve,7,21,56").split(","),
            seeds=[int(s) for s in opts.get("--seeds", "0").split(",")],
            cycles=opts.get("--cycles", ",".join(ORDER)).split(","),
            tag=opts.get("--tag", ""))
    else:
        grade(out)
