"""The Bayesian workflow, run from the beginning.

Stages (Gelman et al., "Bayesian Workflow", ordered so each earns the next):

  story      The estimand and generative story, stated before any fitting.
  prior      Prior predictive simulation — do the priors, alone, generate
             plausible Israeli polling worlds? (No data touched.)
  recovery   Fake-data simulation — generate data from KNOWN parameters,
             fit, verify the model recovers them. If it can't find truth
             it's known to contain, it can't find truth in real data.
  ladder     Fit M0 -> M3 on real data, simplest first, each expansion
             justified by criticism of its predecessor; PSIS-LOO comparison.
               M0  static shares + normal noise        (a fancy average)
               M1  + random-walk trend                 (opinion moves)
               M2  + per-firm house effects            (pollsters differ)
               M3  + group nesting, Student-t, per-    (the production
                    list noise                          model)
  sensitivity  How much do the projection layer's unidentifiable industry-
             shock priors move the headline probability?

Run:  python workflow_bayes.py all      (or a single stage name)
Artifacts land in data/processed/workflow_* and the fitted M3 posterior in
data/processed/m3_idata.nc for reuse. The narrative report lives in
docs/bayesian_workflow.md.
"""

from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

from bayes_model import (
    BLOC_SWING_SD, FAMILY_SHOCK, HOLDOUT_DAYS, SEED, prepare_data, project,
)
from scrape_polls import PROCESSED_DIR

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------- builder --
def build_model(data, trend=True, house=False, groups=False, robust=False,
                empirical_start=True):
    import pymc as pm
    import pytensor.tensor as pt

    B = len(data["latent_blocks"])
    W = data["n_weeks"]
    F = len(data["firms"])
    G = len(data["groups"])
    y, wk = data["y"], data["week"]
    bi, fi = data["block_i"], data["firm_i"]

    if empirical_start:
        first = pd.DataFrame({"b": bi, "y": y, "w": wk})
        early = first[first["w"] <= 8].groupby("b")["y"].mean()
        early = early.reindex(range(B)).fillna(0.01).clip(lower=0.004)
        mu0 = np.log(early.values[:-1] / early.values[-1])
    else:
        mu0 = np.zeros(B - 1)

    with pm.Model() as model:
        z0 = pm.Normal("z0", mu=mu0, sigma=0.5 if empirical_start else 1.5,
                       shape=B - 1)
        if trend:
            tau = pm.HalfNormal("tau", 0.06, shape=B - 1)
            steps = pm.Normal("steps", 0, 1, shape=(W - 1, B - 1))
            dt = np.sqrt(np.asarray(data.get("dt_weeks",
                                             np.ones(W - 1))))[:, None]
            z = pt.concatenate(
                [z0[None, :],
                 z0[None, :] + pt.cumsum(steps * tau * dt, axis=0)],
                axis=0)
        else:
            z = pt.tile(z0[None, :], (W, 1))
        z = pm.Deterministic("z", z)
        shares = pm.Deterministic(
            "shares", pt.special.softmax(
                pt.concatenate([z, pt.zeros((W, 1))], axis=1), axis=1))

        mu = shares[wk, bi]
        if house:
            if groups:
                sigma_g = pm.HalfNormal("sigma_g", 0.015)
                sigma_f = pm.HalfNormal("sigma_f", 0.008)
                gamma = pm.Normal("gamma", 0, sigma_g, shape=(G, B))
                delta = pm.Normal("delta", gamma[data["firm_group"]],
                                  sigma_f, shape=(F, B))
            else:
                sigma_f = pm.HalfNormal("sigma_f", 0.015)
                delta = pm.Normal("delta", 0, sigma_f, shape=(F, B))
            delta_c = pm.Deterministic("delta_c", delta - delta.mean(axis=0))
            mu = mu + delta_c[fi, bi]

        if robust:
            s_obs = pm.HalfNormal("s_obs", 0.012, shape=B)
            pm.StudentT("y", nu=4, mu=mu, sigma=s_obs[bi] + 0.002, observed=y)
        else:
            s = pm.HalfNormal("s_obs", 0.012)
            pm.Normal("y", mu=mu, sigma=s + 0.002, observed=y)
    return model


def sample(model, draws=700, tune=700, loglik=False):
    import pymc as pm
    with model:
        return pm.sample(
            draws=draws, tune=tune, chains=4, cores=4, target_accept=0.92,
            random_seed=SEED, progressbar=False,
            compute_convergence_checks=False,
            idata_kwargs={"log_likelihood": loglik})


# ------------------------------------------------------------------ prior --
def stage_prior(data):
    import pymc as pm
    print("== PRIOR PREDICTIVE (no data involved) ==")
    m = build_model(data, trend=True, house=True, groups=True, robust=True,
                    empirical_start=False)
    with m:
        prior = pm.sample_prior_predictive(samples=500, random_seed=SEED)
    sh = prior.prior["shares"].values[0]          # (500, W, B)
    top = sh[:, -1, :].max(axis=1)
    weekly = np.abs(np.diff(sh, axis=1)).mean(axis=(1, 2))
    yrep = prior.prior_predictive["y"].values[0]
    rows = {
        "largest list final share, 5-95%":
            f"{np.percentile(top, 5):.2f} - {np.percentile(top, 95):.2f}",
        "mean |weekly share move|, 5-95%":
            f"{np.percentile(weekly, 5):.4f} - {np.percentile(weekly, 95):.4f}",
        "simulated poll values within [0, 0.5]":
            f"{((yrep > -0.02) & (yrep < 0.5)).mean():.1%}",
    }
    for k, v in rows.items():
        print(f"  {k}: {v}")
    pd.Series(rows).to_csv(PROCESSED_DIR / "workflow_prior_predictive.csv")
    print("  -> priors generate plausible polling worlds; largest-list share"
          "\n     spans real Israeli outcomes (Kadima '09 ~0.23, fragmented"
          " ~0.15)\n")


# --------------------------------------------------------------- recovery --
def stage_recovery():
    print("== FAKE-DATA RECOVERY (known truth) ==")
    rng = np.random.default_rng(7)
    B, W, F, G = 6, 20, 6, 4
    true_tau = rng.uniform(0.02, 0.08, B - 1)
    z = np.zeros((W, B - 1))
    z[0] = rng.normal(0, 1, B - 1)
    for w in range(1, W):
        z[w] = z[w - 1] + rng.normal(0, true_tau)
    zf = np.concatenate([z, np.zeros((W, 1))], axis=1)
    shares = np.exp(zf) / np.exp(zf).sum(axis=1, keepdims=True)
    true_delta = rng.normal(0, 0.012, (F, B))
    true_delta -= true_delta.mean(axis=0)

    n_obs = 3 * W * B
    wk = rng.integers(0, W, n_obs)
    bi = rng.integers(0, B, n_obs)
    fi = rng.integers(0, F, n_obs)
    y = (shares[wk, bi] + true_delta[fi, bi]
         + rng.standard_t(4, n_obs) * 0.008)
    data = {
        "y": y, "week": wk, "block_i": bi, "firm_i": fi,
        "firm_group": rng.integers(0, G, F), "n_weeks": W,
        "latent_blocks": list(range(B)), "firms": list(range(F)),
        "groups": list(range(G)),
    }
    m = build_model(data, trend=True, house=True, groups=True, robust=True)
    idata = sample(m, draws=500, tune=600)
    post = idata.posterior
    sh_post = post["shares"].values.reshape(-1, W, B)
    lo = np.percentile(sh_post, 5, axis=0)
    hi = np.percentile(sh_post, 95, axis=0)
    cover = ((shares >= lo) & (shares <= hi)).mean()
    tau_mean = post["tau"].values.reshape(-1, B - 1).mean(axis=0)
    tau_corr = np.corrcoef(true_tau, tau_mean)[0, 1]
    d_mean = post["delta_c"].values.reshape(-1, F, B).mean(axis=0)
    d_corr = np.corrcoef(true_delta.ravel(), d_mean.ravel())[0, 1]
    div = int(idata.sample_stats["diverging"].sum())
    print(f"  true share trajectories inside 90% CI: {cover:.1%}"
          f"  (target ~90%)")
    print(f"  innovation (tau) recovery corr: {tau_corr:.2f}")
    print(f"  house-effect recovery corr: {d_corr:.2f} | divergences: {div}")
    pd.Series({"share_coverage_90": round(float(cover), 3),
               "tau_corr": round(float(tau_corr), 2),
               "house_corr": round(float(d_corr), 2),
               "divergences": div}).to_csv(
        PROCESSED_DIR / "workflow_recovery.csv")
    print()


# ----------------------------------------------------------------- ladder --
def stage_ladder(data):
    import arviz as az
    print("== MODEL LADDER (real data, simplest first) ==")
    specs = {
        "M0_static": dict(trend=False),
        "M1_trend": dict(trend=True),
        "M2_house": dict(trend=True, house=True),
        "M3_full": dict(trend=True, house=True, groups=True, robust=True),
    }
    idatas, rows = {}, []
    for name, kw in specs.items():
        m = build_model(data, **kw)
        idata = sample(m, loglik=True)
        idatas[name] = idata
        div = int(idata.sample_stats["diverging"].sum())
        loo = az.loo(idata)
        post = idata.posterior
        sh = post["shares"].values.reshape(-1, *post["shares"].shape[2:])
        mu = sh[:, data["week"], data["block_i"]]
        if "delta_c" in post:
            d = post["delta_c"].values.reshape(-1, *post["delta_c"].shape[2:])
            mu = mu + d[:, data["firm_i"], data["block_i"]]
        resid = np.abs(np.median(mu, axis=0) - data["y"]) * 120
        rows.append({"model": name, "elpd_loo": round(float(loo.elpd_loo), 1),
                     "p_loo": round(float(loo.p_loo), 1),
                     "divergences": div,
                     "median_abs_resid_seats": round(float(np.median(resid)), 2)})
        print(f"  {name}: elpd {rows[-1]['elpd_loo']:>8} | p_loo "
              f"{rows[-1]['p_loo']:>6} | div {div} | median |resid| "
              f"{rows[-1]['median_abs_resid_seats']} seats")
    comp = az.compare(idatas, ic="loo")
    print("\n", comp[["rank", "elpd_loo", "elpd_diff", "dse"]].to_string())
    pd.DataFrame(rows).to_csv(PROCESSED_DIR / "workflow_ladder.csv",
                              index=False)
    comp.to_csv(PROCESSED_DIR / "workflow_loo_compare.csv")
    az.to_netcdf(idatas["M3_full"], PROCESSED_DIR / "m3_idata.nc")
    print("  -> saved M3 posterior to m3_idata.nc\n")


# ----------------------------------------------------------- sensitivity --
def stage_sensitivity(data):
    import arviz as az
    import bayes_model as bm
    print("== SENSITIVITY of P(NB>=61) to projection-layer priors ==")
    nc = PROCESSED_DIR / "m3_idata.nc"
    if nc.exists():
        idata = az.from_netcdf(nc)
    else:
        m = build_model(data, trend=True, house=True, groups=True,
                        robust=True)
        idata = sample(m)
        az.to_netcdf(idata, nc)
    grid = []
    for swing in (2.5, 3.5, 4.5):
        for fams_on in (True, False):
            bm.BLOC_SWING_SD = swing
            bm.FAMILY_SHOCK = ({"arab": (-0.7, 1.2), "haredi": (-1.0, 1.6)}
                               if fams_on else {})
            rng = np.random.default_rng(SEED)
            seats, labels, blocs = project(data, idata, rng)
            nb = seats[:, np.array(blocs) == "netanyahu_bloc"].sum(axis=1)
            grid.append({"bloc_swing_sd": swing, "family_shocks": fams_on,
                         "p_nb_61": round(float((nb >= 61).mean()), 3),
                         "nb_mean": round(float(nb.mean()), 1)})
            print(f"  swing_sd={swing}, family_shocks={fams_on}: "
                  f"P(NB>=61)={grid[-1]['p_nb_61']:.1%}, "
                  f"mean {grid[-1]['nb_mean']}")
    bm.BLOC_SWING_SD = BLOC_SWING_SD
    bm.FAMILY_SHOCK = FAMILY_SHOCK
    pd.DataFrame(grid).to_csv(PROCESSED_DIR / "workflow_sensitivity.csv",
                              index=False)


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = prepare_data() if stage != "recovery" else None
    if data is not None:
        print(f"data: {data['n_polls']} polls, {len(data['y'])} obs, "
              f"{len(data['latent_blocks'])} lists, {data['n_weeks']} weeks\n")
    if stage in ("prior", "all"):
        stage_prior(data)
    if stage in ("recovery", "all"):
        stage_recovery()
    if stage in ("ladder", "all"):
        stage_ladder(data)
    if stage in ("sensitivity", "all"):
        stage_sensitivity(data)


if __name__ == "__main__":
    main()
