"""The prediction-market blend (src/market_blend.py, dossier s.71)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import market_blend as mb


def test_bracket_labels():
    assert mb._seat_range("<20") == (0, 19)
    assert mb._seat_range("20-24") == (20, 24)
    assert mb._seat_range("35+") == (35, 10 ** 6)
    assert mb._below_threshold("<3.25%") and mb._below_threshold("2.75-3.25%")
    assert mb._below_threshold("<2.75%") and not mb._below_threshold("3.25-4%")
    assert not mb._below_threshold("4.25%+")


def test_rake_matches_targets_with_least_change():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 10, 4000)
    y = rng.integers(0, 3, 4000)
    Mx = np.stack([(x < 4), (x >= 4) & (x < 7), (x >= 7)], axis=1).astype(float)
    My = np.stack([y == k for k in range(3)], axis=1).astype(float)
    tx, ty = np.array([.2, .3, .5]), np.array([.5, .25, .25])
    w = mb.rake([Mx, My], [tx, ty])
    assert np.allclose(w @ Mx, tx, atol=1e-6) and np.allclose(w @ My, ty, atol=1e-6)
    assert mb.ess(w) > 2000            # a modest tilt keeps most of the sample
    # targets equal to the model's own probabilities leave the draws untouched
    w0 = mb.rake([Mx], [Mx.mean(axis=0)])
    assert np.allclose(w0, 1 / len(x))


def test_apply_resamples_seats_and_shares_together(tmp_path, monkeypatch):
    n = 2000
    rng = np.random.default_rng(2)
    likud = rng.integers(15, 35, n)
    seats = pd.DataFrame({"Likud": likud, "Yashar": 120 - likud})
    shares = pd.DataFrame({"Likud": likud / 120.0 + 1e-4 * np.arange(n), "Yashar": (120 - likud) / 120.0})
    seats.to_parquet(tmp_path / "mixture_draws.parquet")
    shares.to_parquet(tmp_path / "mixture_share_draws.parquet")
    pd.DataFrame({"list": ["Likud", "Yashar"], "components": ["likud", "yashar"],
                  "share_mean": [0, 0], "share_median": [0, 0]}).to_csv(tmp_path / "mixture_shares.csv", index=False)
    pd.DataFrame({"list": ["Likud", "Yashar"], "bloc": ["Netanyahu bloc", "Anti-Netanyahu bloc"]}).to_csv(
        tmp_path / "bayes_forecast_2026.csv", index=False)
    raw = tmp_path / "raw"; raw.mkdir()
    mk = [{"groupItemTitle": lab, "outcomePrices": json.dumps([str(p), str(1 - p)]),
           "bestBid": p - .01, "bestAsk": p + .01} for lab, p in (("<20", .4), ("20-24", .3), ("25-29", .2), ("30+", .1))]
    (raw / "likud.json").write_text(json.dumps([{"volume": 1e6, "markets": mk}]))
    monkeypatch.setattr(mb, "QUESTIONS", [("likud", "seats", "Likud", None)])
    rep = mb.apply(tmp_path, raw)
    b = pd.read_parquet(tmp_path / "mixture_draws.parquet")
    s = pd.read_parquet(tmp_path / "mixture_share_draws.parquet")
    # every resampled row keeps its own share vector
    assert np.allclose(np.round((s["Likud"] - b["Likud"] / 120.0) / 1e-4) % 1, 0)
    q = rep["questions"][0]
    assert np.allclose(q["blend"], q["target"], atol=1e-6)            # w 0.5 pool reproduced
    got = np.array([(b["Likud"] < 20).mean(), b["Likud"].between(20, 24).mean()])
    assert np.allclose(got, np.array(q["target"][:2]), atol=0.02)     # after resampling
    assert (tmp_path / "mixture_draws_model.parquet").exists()
