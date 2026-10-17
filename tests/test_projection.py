"""The production projection (bayes_model.project) on a synthetic posterior.

No MCMC: a small CLR-shaped posterior (zc, tau) over the 2026 list set is
pushed through the full shock stack - random walk forward, residual shock,
bloc swing, certainty layer, family shocks, new-straddler and trailing-Likud
layers, gevalt and centre churn, loyal-list shrinkage, kalpi caps - and the
seat law, in both the "current" configuration and the registration mixture
the site publishes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import bayes_model as bm

COMPONENTS = ["likud", "yashar", "bennett_2026+yesh_atid", "democrats", "yisrael_beytenu",
              "shas", "utj", "otzma", "rzp", "raam", "balad+hadash_taal", "amcha_yisrael",
              "zionist_home", "blue_white", "haredi_public", "noam"]
SHARES = np.array([.215, .19, .095, .075, .068, .066, .07, .05, .034, .04, .072, .02,
                   .016, .01, .005, .004])


class _Idata:
    def __init__(self, posterior):
        self.posterior = posterior


def synthetic_posterior(chains=2, draws=150, weeks=6, seed=1):
    rng = np.random.default_rng(seed)
    b = len(COMPONENTS)
    mu = np.log(SHARES / SHARES.sum())
    z = mu[None, None, None, :] + rng.normal(0, 0.05, size=(chains, draws, weeks, b))
    z = z - z.mean(axis=-1, keepdims=True)
    tau = np.abs(rng.normal(0.03, 0.01, size=(chains, draws, b)))
    return _Idata(xr.Dataset({"zc": (("chain", "draw", "week", "list"), z),
                              "tau": (("chain", "draw", "list"), tau)}))


def synthetic_data(asof="2026-10-15"):
    return {"asof": pd.Timestamp(asof), "components": list(COMPONENTS),
            "last_obs_day": np.full(len(COMPONENTS), -1),
            "on_ballot": np.ones(len(COMPONENTS), dtype=bool)}


@pytest.mark.parametrize("config", ["current", "mixture"])
def test_projection_seats_sum_to_120(monkeypatch, capsys, config):
    monkeypatch.setattr(bm, "N_PROJ", 1200)
    rng = np.random.default_rng(bm.SEED)
    seats, labels, blocs = bm.project(synthetic_data(), synthetic_posterior(), rng, config=config)
    out = capsys.readouterr().out
    assert seats.shape == (1200, len(labels))
    assert (seats.sum(axis=1) == 120).all()
    assert (seats >= 0).all()
    # a list that passes the threshold carries at least d'Hondt's lower quota
    assert (seats[seats > 0] >= 3).all()
    # every signed 2026 surplus pair resolves on the 2026 list set (s.40)
    assert "WARNING surplus pairs not resolved" not in out
    assert len(bm.project.last_pairs) == 5
    # last_pairs holds list names; a working copy carrying the targeting
    # project's uncommitted hook overwrites it with column indices, so map
    # those back through the labels
    pairs = [tuple(labels[i] if isinstance(i, (int, np.integer)) else i for i in p)
             for p in bm.project.last_pairs]
    assert ("Likud", "Religious Zionist Party") in pairs
    # the projected share vector is a distribution over the lists
    assert np.isclose(bm.project.last_share_mean.sum(), 1.0)
    assert set(np.unique(blocs)) <= {"netanyahu_bloc", "opposition_bloc", "other", "unaligned"}


def test_projection_is_seeded(monkeypatch):
    """Same posterior, same seed -> identical seat draws (the build is
    reproducible; harness comparisons rely on it)."""
    monkeypatch.setattr(bm, "N_PROJ", 1200)
    a = bm.project(synthetic_data(), synthetic_posterior(), np.random.default_rng(7))[0]
    b = bm.project(synthetic_data(), synthetic_posterior(), np.random.default_rng(7))[0]
    assert (a == b).all()
