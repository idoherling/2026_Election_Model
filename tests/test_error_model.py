"""The hierarchical error model (src/error_model.py, dossier s.61).

Shapes and identities of the record, the posterior-predictive draws the
projection takes, the production projection with the flag on (synthetic
hyperparameters, no MCMC), and one small NUTS fit on SIMULATED data: the
model must recover the generating parameters and the simulated record's
moments roughly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import error_model as em


def _hyper(n=400, seed=3, nu=8.0, gaussian=False):
    rng = np.random.default_rng(seed)
    return {"mu_beta": rng.normal(1.0, 0.5, n), "sigma_beta": np.abs(rng.normal(2.0, 0.3, n)),
            "mu_h": rng.normal(-1.0, 0.3, n), "sigma_h": np.abs(rng.normal(0.8, 0.2, n)),
            "a": rng.normal(np.log(1.2), 0.05, n), "b": rng.normal(0.6, 0.05, n),
            "gamma": rng.normal(0.3, 0.05, n),
            "nu": np.full(n, np.inf) if gaussian else np.full(n, nu)}


def test_record_shapes_and_loadings():
    rec = em.record(None)
    assert len(rec) == 95 and rec["cycle"].nunique() == 8
    for col in ("l_bloc", "l_haredi", "l_arab", "l_common", "size", "new", "error"):
        assert rec[col].notna().all()
    g = rec.groupby("cycle")
    # the projection's zero-sum allocations: bloc and family loadings sum to
    # zero within a cycle, the common term to one
    assert np.allclose(g["l_bloc"].sum(), 0.0)
    assert np.allclose(g["l_haredi"].sum(), 0.0)
    assert np.allclose(g["l_arab"].sum(), 0.0)
    assert np.allclose(g["l_common"].sum(), 1.0)
    assert np.allclose(rec.loc[rec["nb"]].groupby("cycle")["l_bloc"].sum(), 1.0)
    assert (rec["size"] >= em.SIZE_FLOOR).all()
    # the leave-one-cycle-out record drops exactly the cycle
    r13 = em.record("2013")
    assert "2013" not in set(r13["cycle"]) and len(r13) == 95 - (rec["cycle"] == "2013").sum()


def test_first_cycle_rule():
    rec = em.record(None)
    new = set(map(tuple, rec.loc[rec["new"], ["cycle", "components"]].values))
    assert ("2013", "yesh_atid") in new and ("2021", "new_hope") in new
    assert not rec.loc[rec["cycle"] == "2009", "new"].any()
    # lineage: RZP 2021 and Yamina / the Joint List 2019s are not debutants
    assert ("2021", "rzp") not in new and ("2019s", "yamina") not in new
    assert ("2019s", "joint_list") not in new
    comps = ["likud", "yashar", "democrats", "bennett_2026+yesh_atid", "amcha_yisrael",
             "zionist_home", "noam", "balad+hadash_taal"]
    m = dict(zip(comps, em.first_cycle_mask(comps, "2026")))
    assert m["yashar"] and m["amcha_yisrael"] and m["zionist_home"]
    assert not (m["likud"] or m["democrats"] or m["bennett_2026+yesh_atid"] or m["noam"]
                or m["balad+hadash_taal"])


@pytest.mark.parametrize("gaussian", [False, True])
def test_predictive_draw_shapes(gaussian):
    hy = _hyper(gaussian=gaussian)
    rng = np.random.default_rng(0)
    idx = em.draw_index(hy, 5000, rng)
    sizes = np.array([0.1, 4.0, 25.0])
    eps = em.resid_draws(hy, idx, sizes, np.array([False, False, True]), rng)
    assert eps.shape == (5000, 3) and np.isfinite(eps).all()
    sc = em.resid_scale(hy, idx, sizes, np.zeros(3))
    # sizes below the floor take the floor's scale; the scale rises with size
    assert np.allclose(sc[:, 0], em.resid_scale(hy, idx, [em.SIZE_FLOOR], [0])[:, 0])
    assert (sc[:, 2] > sc[:, 1]).all()
    beta = em.bloc_draws(hy, idx, rng.standard_normal(5000))
    phi = em.haredi_draws(hy, idx, rng.standard_normal(5000))
    assert beta.shape == phi.shape == (5000,)
    s = em.predictive_summary(hy, n=20000)
    assert s["bloc"]["sd"] > hy["sigma_beta"].mean() * 0.95   # parameter uncertainty adds
    assert s["resid_25"]["sd"] > s["resid_4"]["sd"]


def test_production_projection_with_the_flag_on(monkeypatch):
    import bayes_model as bm
    from test_projection import synthetic_data, synthetic_posterior
    assert bm.ERROR_MODEL == "moments"            # shipped value
    monkeypatch.setattr(bm, "N_PROJ", 1000)
    monkeypatch.setattr(bm, "ERROR_MODEL", "hierarchical")
    monkeypatch.setattr(em, "production_hyper", lambda: _hyper())
    seats, labels, blocs = bm.project(synthetic_data(), synthetic_posterior(),
                                      np.random.default_rng(bm.SEED))
    assert seats.shape == (1000, len(labels)) and (seats.sum(axis=1) == 120).all()
    assert "yashar" in bm.project.last_hier_new and "likud" not in bm.project.last_hier_new


def _simulate(true, design: pd.DataFrame, reps: int, seed: int) -> pd.DataFrame:
    """A record with the real design (loadings, sizes, first-cycle flags)
    replicated `reps` times, errors drawn from the model at `true`."""
    rng = np.random.default_rng(seed)
    out = []
    for r in range(reps):
        for c, g in design.groupby("cycle", sort=False):
            g = g.copy()
            g["cycle"] = f"{c}_{r}"
            beta = true["mu_beta"] + true["sigma_beta"] * rng.standard_normal()
            ph = true["mu_h"] + true["sigma_h"] * rng.standard_normal()
            pa = true["mu_a"] + true["sigma_a"] * rng.standard_normal()
            kp = true["mu_k"] + true["sigma_k"] * rng.standard_normal()
            sig = np.exp(true["a"] + true["b"] * np.log(g["size"] / em.SIZE_REF)
                         + true["gamma"] * g["new"])
            g["error"] = (beta * g["l_bloc"] + ph * g["l_haredi"] + pa * g["l_arab"]
                          + kp * g["l_common"] + sig * rng.standard_t(true["nu"], len(g)))
            out.append(g)
    return pd.concat(out, ignore_index=True)


def test_fit_recovers_simulated_moments():
    true = {"mu_beta": 1.0, "sigma_beta": 3.0, "mu_h": -1.0, "sigma_h": 1.0, "mu_a": 0.0,
            "sigma_a": 1.0, "mu_k": 1.4, "sigma_k": 0.5, "a": np.log(1.2), "b": 0.6,
            "gamma": 0.3, "nu": 8.0}
    sim = _simulate(true, em.record(None), reps=3, seed=11)
    idata = em.sample(sim, "full", draws=400, tune=500, chains=2, cores=1, random_seed=5,
                      log_likelihood=False)
    post = idata.posterior
    m = {k: float(post[k].mean()) for k in ("mu_beta", "sigma_beta", "mu_h", "a", "b")}
    assert abs(m["b"] - true["b"]) < 0.3
    assert abs(m["a"] - true["a"]) < 0.3
    assert 1.5 < m["sigma_beta"] < 5.5
    assert abs(m["mu_h"] - true["mu_h"]) < 1.0
    assert em.diagnostics(idata)["divergences"] <= 5
    # the fitted residual reproduces the simulated record's second moment:
    # the posterior-predictive residual sd of the small lists (<= 8 u) is
    # about the generating sd (scale x sqrt(nu / (nu - 2)))
    hy = {k: post[k].values.reshape(-1) for k in ("a", "b", "gamma", "nu")}
    sim_small = sim[sim["size"] <= 8]
    sc_true = np.exp(true["a"] + true["b"] * np.log(sim_small["size"] / em.SIZE_REF)
                     + true["gamma"] * sim_small["new"])
    sd_true = np.sqrt((sc_true ** 2).mean() * true["nu"] / (true["nu"] - 2))
    rng = np.random.default_rng(2)
    idx = em.draw_index(hy, 4000, rng)
    eps = em.resid_draws(hy, idx, sim_small["size"].values, sim_small["new"].values, rng)
    assert 0.7 < eps.std() / sd_true < 1.4
