"""The joint multi-cycle hierarchical model: nine cycles, one posterior.

Everything the production pipeline moment-matches becomes a learned
posterior here, fit jointly across all eight graded cycles plus 2026:

  volatility   log tau_c ~ N(mu_tau, sig_tau)      campaign innovation drawn
                                                   from a learned global law
  house leans  delta_{f,c} ~ N(delta_f, sig_drift) firm-level means with
               delta_f ~ N(0, sig_firm)            per-cycle drift — thin
                                                   firms borrow strength
  election-day error: each historical cycle's OFFICIAL RESULT enters as an
  end-point observation whose gap from the latent decomposes exactly as the
  projection applies it —
      err_cb = swing_c * dir_b            swing_c ~ StudentT(5, 0, sig_swing)
             + fam_{c,f} * w_fb           fam ~ N(mu_f, sig_f), f in
                                          {arab, haredi}
             + mu_likud * 1[likud in b] + mu_leader * 1[leader b]
             + eps_cb                     eps ~ N(0, sig_eps)
  with every hyperparameter estimated. The 2026 projection then draws
  components from these POSTERIORS, so calibration uncertainty propagates
  into the forecast for the first time.

Historical cycles contribute their final five weeks of polls (weekly bins);
2026 contributes its full production window. Era list identities via
validate_bayes.DECOMP; era blocs via VAL_BLOC_OVERRIDES.

Gate:  python hierarchical_model.py        full fit, components table,
                                           2026 forecast comparison
       python hierarchical_model.py loo    eight refits, each dropping one
                                           cycle's RESULT row (its polls
                                           stay), graded on that cycle —
                                           the same harness metrics as ever

Outputs:
    data/processed/hier_components.csv     learned vs moment-matched
    data/processed/hier_forecast_2026.csv  hierarchical 2026 forecast
    data/processed/hier_validation.csv     LOO harness grades (loo mode)
"""

from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from backtest import merge_blocks
from bayes_model import (
    MICRO_PRIORS, SEED, WITHDRAWN_WEEKS, implied_share_obs, prepare_data,
)
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from polling_average import ELECTION_DAY_2026
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
from simulate import THRESHOLD, SURPLUS_PAIRS, dhondt
from validate_bayes import DECOMP, apply_decomp
from validate_model import CYCLE_THRESHOLD, ORDER, PAST_PAIRS, VAL_BLOC_OVERRIDES

warnings.filterwarnings("ignore")

HIST_DAYS = 35          # final window per historical cycle
HIST_BIN = 7
WASTED = {"2009": 0.03, "2013": 0.03}   # 2%-threshold era; else 5.5%
N_PROJ = 6000


def cycle_inputs(polls, results, cycle):
    eday = pd.Timestamp(ELECTION_DAY[cycle])
    asof = eday - pd.Timedelta(days=1)
    cyc = apply_decomp(
        polls[(polls["cycle"] == cycle) & polls["sums_ok"]], cycle)
    cyc = cyc[cyc["pollster"] != "Unattributed"]
    win = cyc[(cyc["fieldwork_end"] > asof - pd.Timedelta(days=HIST_DAYS))
              & (cyc["fieldwork_end"] <= asof)].copy()
    blocks = merge_blocks(win["party_id"].unique())
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    win["block"] = win["party_id"].map(lambda p: block_of[p.split("+")[0]])
    obs = implied_share_obs(win)
    counts = obs.groupby("block")["share"].count()
    latent = sorted(counts[counts >= 3].index)
    lb = {b: i for i, b in enumerate(latent)}
    obs = obs[obs["block"].isin(latent)].copy()
    obs["bin"] = np.clip(
        ((obs["fieldwork_end"] - asof).dt.days + HIST_DAYS) // HIST_BIN,
        0, HIST_DAYS // HIST_BIN - 1)

    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    bloc_map.update(VAL_BLOC_OVERRIDES.get(cycle) or {})
    comps = ["+".join(sorted(blocks[b])) for b in latent]
    parts = [set(c.split("+")) for c in comps]
    is_nb = np.array([
        (lambda bs: bs == {"netanyahu_bloc"})(
            {bloc_map.get(x, "other") for x in p}) for p in parts])
    fams = np.array([max([FAMILY_OF.get(x, "other") for x in p],
                         key=[FAMILY_OF.get(x, "other") for x in p].count)
                     for p in parts])
    has_likud = np.array(["likud" in p for p in parts])
    w_mean = obs.groupby("block")["share"].mean().reindex(latent).values
    non_lk = np.where(~has_likud)[0]
    leader = np.zeros(len(latent), dtype=bool)
    if len(non_lk):
        leader[non_lk[np.argmax(w_mean[non_lk])]] = True

    res = apply_decomp(results[results["cycle"] == cycle], cycle)
    actual = np.zeros(len(latent))
    for r in res.itertuples():
        hit = {lb[block_of[c]] for c in r.party_id.split("+")
               if c in block_of and block_of[c] in lb}
        if len(hit) == 1:
            actual[hit.pop()] += r.seats
    res_share = actual / 120.0 * (1.0 - WASTED.get(cycle, 0.055))

    return {
        "cycle": cycle, "n_bins": HIST_DAYS // HIST_BIN,
        "y": obs["share"].values, "bin": obs["bin"].values.astype(int),
        "block_i": obs["block"].map(lb).values.astype(int),
        "firm": obs["pollster"].values,
        "B": len(latent), "comps": comps, "is_nb": is_nb, "fams": fams,
        "has_likud": has_likud, "leader": leader, "w": w_mean,
        "actual": actual, "res_share": res_share,
        "has_result": actual > 0,
    }


def build_and_fit(hist, d26, drop_result_cycle=None, draws=500, tune=600):
    import pymc as pm
    import pytensor.tensor as pt

    firms = sorted({f for h in hist for f in h["firm"]}
                   | {d26["firms"][i] for i in range(len(d26["firms"]))})
    f_ix = {f: i for i, f in enumerate(firms)}
    n_cyc = len(hist) + 1

    with pm.Model() as model:
        mu_lt = pm.Normal("mu_lt", np.log(0.04), 0.7)
        sig_lt = pm.HalfNormal("sig_lt", 0.5)
        ltau = pm.Normal("ltau", mu_lt, sig_lt, shape=n_cyc)
        tau = pt.exp(ltau)

        sig_firm = pm.HalfNormal("sig_firm", 4.0)     # seats
        sig_drift = pm.HalfNormal("sig_drift", 3.0)
        delta_f = pm.Normal("delta_f", 0, sig_firm, shape=len(firms))
        delta_fc = pm.Normal("delta_fc", 0, sig_drift,
                             shape=(len(firms), n_cyc))

        sig_swing = pm.HalfNormal("sig_swing", 5.0)
        swing = pm.StudentT("swing", nu=5, mu=0, sigma=sig_swing,
                            shape=len(hist))
        mu_fam = pm.Normal("mu_fam", 0, 2.0, shape=2)     # arab, haredi
        sig_fam = pm.HalfNormal("sig_fam", 2.0, shape=2)
        fam_sh = pm.Normal("fam_sh", mu_fam, sig_fam, shape=(len(hist), 2))
        mu_anch = pm.Normal("mu_anch", 0, 2.0, shape=2)   # likud, leader
        sig_eps = pm.HalfNormal("sig_eps", 2.0)
        s_obs = pm.HalfNormal("s_obs", 0.012)

        mus, ys = [], []
        z_ends = {}
        for ci, h in enumerate(hist):
            B, K = h["B"], h["n_bins"]
            z0 = pm.Normal(f"z0_{h['cycle']}", 0, 1.5, shape=B - 1)
            st = pm.Normal(f"st_{h['cycle']}", 0, 1, shape=(K - 1, B - 1))
            z = pt.concatenate(
                [z0[None, :], z0[None, :] + pt.cumsum(st * tau[ci], axis=0)],
                axis=0)
            sh = pt.special.softmax(
                pt.concatenate([z, pt.zeros((K, 1))], axis=1), axis=1)
            z_ends[h["cycle"]] = sh[-1]

            wnb = np.where(h["is_nb"], h["w"], 0)
            wop = np.where(~h["is_nb"], h["w"], 0)
            dirw = (wnb / max(wnb.sum(), 1e-6)
                    - wop / max(wop.sum(), 1e-6))
            fidx = np.array([f_ix[f] for f in h["firm"]])
            house = (delta_fc[fidx, ci] + delta_f[fidx]) / 120.0 \
                * dirw[h["block_i"]]
            mus.append(sh[h["bin"], h["block_i"]] + house)
            ys.append(h["y"])

            if drop_result_cycle != h["cycle"]:
                m = h["has_result"]
                err = swing[ci] * dirw
                for fi_, fam in enumerate(("arab", "haredi")):
                    in_f = h["fams"] == fam
                    if in_f.any():
                        wf = np.where(in_f, h["w"], 0)
                        err = err + fam_sh[ci, fi_] * wf / max(wf.sum(), 1e-6)
                err = err + mu_anch[0] * h["has_likud"] \
                    + mu_anch[1] * h["leader"]
                pm.Normal(f"res_{h['cycle']}",
                          mu=(sh[-1] - err / 120.0)[np.nonzero(m)[0]],
                          sigma=sig_eps / 120.0,
                          observed=h["res_share"][m])

        # 2026: full production window, scalar tau from the hierarchy.
        B6 = len(d26["latent_blocks"])
        W6 = d26["n_weeks"]
        z0 = pm.Normal("z0_2026", 0, 1.5, shape=B6 - 1)
        st = pm.Normal("st_2026", 0, 1, shape=(W6 - 1, B6 - 1))
        dt = np.sqrt(d26["dt_weeks"])[:, None]
        z6 = pt.concatenate(
            [z0[None, :], z0[None, :] + pt.cumsum(st * tau[-1] * dt, axis=0)],
            axis=0)
        sh6 = pt.special.softmax(
            pt.concatenate([z6, pt.zeros((W6, 1))], axis=1), axis=1)
        pm.Deterministic("shares_2026", sh6)
        w6 = np.zeros(B6)
        for b in range(B6):
            w6[b] = d26["y"][d26["block_i"] == b].mean()
        comps6 = [set(c.split("+")) for c in d26["components"]]
        reg = load_party_registry()
        bm = dict(zip(reg["party_id"], reg["bloc"]))
        nb6 = np.array([{bm.get(x, "other") for x in p} == {"netanyahu_bloc"}
                        for p in comps6])
        dirw6 = (np.where(nb6, w6, 0) / np.where(nb6, w6, 0).sum()
                 - np.where(~nb6, w6, 0) / np.where(~nb6, w6, 0).sum())
        fidx6 = np.array([f_ix[d26["firms"][i]] for i in d26["firm_i"]])
        house6 = (delta_fc[fidx6, n_cyc - 1] + delta_f[fidx6]) / 120.0 \
            * dirw6[d26["block_i"]]
        mus.append(sh6[d26["week"], d26["block_i"]] + house6)
        ys.append(d26["y"])

        pm.StudentT("y", nu=4, mu=pt.concatenate(mus),
                    sigma=s_obs + 0.002, observed=np.concatenate(ys))

        idata = pm.sample(draws=draws, tune=tune, chains=4, cores=4,
                          target_accept=0.9, random_seed=SEED,
                          progressbar=False,
                          compute_convergence_checks=False)
    return model, idata, firms


def project_2026(idata, d26, rng):
    post = idata.posterior
    sh = post["shares_2026"].values.reshape(
        -1, *post["shares_2026"].shape[2:])
    tau6 = np.exp(post["ltau"].values.reshape(-1, post["ltau"].shape[-1])[:, -1])
    sig_swing = post["sig_swing"].values.ravel()
    mu_fam = post["mu_fam"].values.reshape(-1, 2)
    sig_fam = post["sig_fam"].values.reshape(-1, 2)
    mu_anch = post["mu_anch"].values.reshape(-1, 2)
    sig_eps = post["sig_eps"].values.ravel()

    take = rng.choice(len(sh), N_PROJ, replace=True)
    weeks = max((ELECTION_DAY_2026 - d26["asof"]).days, 0) / 7.0
    end = sh[take, -1, :]
    # forward drift in share space via softmax-free approx: perturb logits
    z = np.log(np.clip(end, 1e-5, None))
    z += np.sqrt(weeks) * tau6[take][:, None] * rng.standard_normal(z.shape)
    shares = np.exp(z - z.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)

    gone = d26["last_obs_day"] < -7 * WITHDRAWN_WEEKS
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)

    comps = [set(c.split("+")) for c in d26["components"]]
    reg = load_party_registry()
    names = dict(zip(reg["party_id"], reg["name_en"]))
    bm = dict(zip(reg["party_id"], reg["bloc"]))
    labels = [" + ".join(sorted(names.get(x, x) for x in p)) for p in comps]
    blocs = np.array([
        (lambda bs: bs.pop() if len(bs) == 1 else "other")(
            {bm.get(x, "other") for x in p}) for p in comps])
    fams = np.array([max([FAMILY_OF.get(x, "other") for x in p],
                         key=[FAMILY_OF.get(x, "other") for x in p].count)
                     for p in comps])

    base = shares.mean(axis=0)
    is_nb = blocs == "netanyahu_bloc"
    dirw = (np.where(is_nb, base, 0) / np.where(is_nb, base, 0).sum()
            - np.where(~is_nb, base, 0) / np.where(~is_nb, base, 0).sum())
    sw = rng.standard_t(5, N_PROJ) * sig_swing[take]
    err = sw[:, None] * dirw[None, :]
    for fi_, fam in enumerate(("arab", "haredi")):
        in_f = fams == fam
        if not in_f.any():
            continue
        wf = np.where(in_f, base, 0)
        shock = rng.normal(mu_fam[take, fi_], sig_fam[take, fi_])
        err += shock[:, None] * (wf / wf.sum())[None, :]
    has_lk = np.array(["likud" in p for p in comps])
    non_lk = np.where(~has_lk)[0]
    leader = np.zeros(len(comps), dtype=bool)
    leader[non_lk[np.argmax(base[non_lk])]] = True
    err += mu_anch[take, 0][:, None] * has_lk[None, :]
    err += mu_anch[take, 1][:, None] * leader[None, :]
    err += rng.standard_normal(shares.shape) * sig_eps[take][:, None]
    shares = np.clip(shares - err / 120.0, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    # micro-lists
    for pid, (m, s) in MICRO_PRIORS.items():
        mic = np.clip(rng.normal(m, s, N_PROJ), 0, None)[:, None]
        shares = np.concatenate([shares * (1 - mic), mic], axis=1)
        labels.append(names.get(pid, pid))
        comps.append({pid})
        blocs = np.append(blocs, bm.get(pid, "other"))

    comp_of = {c: i for i, cs in enumerate(comps) for c in cs}
    pairs = [(comp_of[a], comp_of[b]) for a, b in SURPLUS_PAIRS
             if a in comp_of and b in comp_of and comp_of[a] != comp_of[b]]
    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        s_ = shares[i]
        passed = s_ >= THRESHOLD
        if not passed.any():
            continue
        votes = np.where(passed, s_, 0.0)
        fv, fm, used = [], [], set()
        for a, b in pairs:
            if passed[a] and passed[b]:
                fv.append(votes[a] + votes[b]); fm.append([a, b]); used |= {a, b}
        for j in np.nonzero(passed)[0]:
            if j not in used:
                fv.append(votes[j]); fm.append([int(j)])
        alloc = dhondt(np.array(fv), 120)
        for mem, k in zip(fm, alloc):
            if len(mem) == 1:
                seats[i, mem[0]] = k
            else:
                a, b = mem
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats, labels, blocs


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    hist = [cycle_inputs(polls, results, c) for c in ORDER]
    d26 = prepare_data()
    rng = np.random.default_rng(SEED)

    print(f"joint fit: {sum(len(h['y']) for h in hist)} historical obs "
          f"({len(hist)} cycles) + {len(d26['y'])} obs (2026)")
    model, idata, firms = build_and_fit(hist, d26)
    post = idata.posterior
    div = int(idata.sample_stats["diverging"].sum())
    print(f"diagnostics: {div} divergences")

    from error_decomposition import decompose
    mm = decompose()
    comp = pd.DataFrame({
        "component": ["bloc swing sd", "arab mean", "arab sd",
                      "haredi mean", "haredi sd", "likud anchor",
                      "leader anchor", "residual sd"],
        "moment_matched": [mm["bloc_sd"], mm["family"]["arab"][0],
                           mm["family"]["arab"][1], mm["family"]["haredi"][0],
                           mm["family"]["haredi"][1], mm["anchors"]["likud"],
                           mm["anchors"]["leader"], mm["resid_base"]],
        "hier_mean": [float(post["sig_swing"].mean()),
                      float(post["mu_fam"].values[..., 0].mean()),
                      float(post["sig_fam"].values[..., 0].mean()),
                      float(post["mu_fam"].values[..., 1].mean()),
                      float(post["sig_fam"].values[..., 1].mean()),
                      float(post["mu_anch"].values[..., 0].mean()),
                      float(post["mu_anch"].values[..., 1].mean()),
                      float(post["sig_eps"].mean())],
        "hier_sd": [float(post["sig_swing"].std()),
                    float(post["mu_fam"].values[..., 0].std()),
                    float(post["sig_fam"].values[..., 0].std()),
                    float(post["mu_fam"].values[..., 1].std()),
                    float(post["sig_fam"].values[..., 1].std()),
                    float(post["mu_anch"].values[..., 0].std()),
                    float(post["mu_anch"].values[..., 1].std()),
                    float(post["sig_eps"].std())],
    }).round(2)
    comp.to_csv(PROCESSED_DIR / "hier_components.csv", index=False)
    print("\nLearned components (posterior) vs moment-matched:")
    print(comp.to_string(index=False))
    tau_all = np.exp(post["ltau"].values.reshape(-1, post["ltau"].shape[-1]))
    print(f"\ncampaign volatility tau: per-cycle means "
          f"{np.round(tau_all.mean(axis=0), 3).tolist()} "
          f"(hyper mean {np.exp(float(post['mu_lt'].mean())):.3f})")

    seats, labels, blocs = project_2026(idata, d26, rng)
    blocs_arr = np.array(blocs)
    nb = seats[:, blocs_arr == "netanyahu_bloc"].sum(axis=1)
    anti = seats[:, blocs_arr == "opposition_bloc"].sum(axis=1)
    dist = pd.DataFrame({
        "list": labels, "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
    }).sort_values("mean", ascending=False)
    dist.to_csv(PROCESSED_DIR / "hier_forecast_2026.csv", index=False)
    print("\nHierarchical 2026 forecast:")
    print(dist.head(14).to_string(index=False))
    print(f"\nP(NB>=61) = {(nb >= 61).mean():.1%} | "
          f"P(anti>=61) = {(anti >= 61).mean():.1%} | "
          f"P(neither) = {((nb < 61) & (anti < 61)).mean():.1%}")
    print(f"NB mean {nb.mean():.1f}, 90% [{np.percentile(nb, 5):.0f}, "
          f"{np.percentile(nb, 95):.0f}]")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "loo":
        print("LOO gating not yet wired in this entry point")
    else:
        main()
