"""Horizon-aware harness (accuracy round 3, #2).

The standard harness grades election-eve forecasts. The published forecast
is made weeks out, and nothing had graded the layers that carry that
horizon's uncertainty: the random-walk forward variance, and the campaign
volatility calendar that scales it. This script fits each graded cycle
AS OF D-h for h in HORIZONS, projects to election day two ways - plain
weeks (sqrt(h/7) x tau) and calendar-effective weeks (production's
campaign_vol_weight integration) - and scores both against the result.

Output: data/processed/model_validation_horizon.csv
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import bayes_model as bm
from bayes_model import SEED, fit, prepare_data
from error_decomposition import decompose
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
from simulate import THRESHOLD
from validate_bayes import (CYCLE_THRESHOLD, ORDER, PAST_PAIRS,
                            VAL_BLOC_OVERRIDES, apply_decomp, project_cycle)

warnings.filterwarnings("ignore")
HORIZONS = [56, 21]
CACHE = PROCESSED_DIR / "harness_cache"
# Joint calibration grid for the next run: scale on the shock stack
# (swing, family sd, residual) x scale on the forward random-walk variance.
STACK_GRID = [0.7, 0.85, 1.0]
RW_GRID = [1.0, 1.25, 1.5]


def calendar_weeks(h: int) -> float:
    eff, d, step = 0.0, h, 7
    while d > 0:
        st = min(step, d)
        eff += bm.campaign_vol_weight(d) ** 2 * (st / 7.0)
        d -= st
    return eff


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    rng = np.random.default_rng(SEED)
    rows = []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        cyc = apply_decomp(polls[(polls["cycle"] == cycle) & polls["sums_ok"]], cycle)
        res = apply_decomp(results[results["cycle"] == cycle], cycle)
        params = decompose(exclude_cycle=cycle)
        for h in HORIZONS:
            asof = eday - pd.Timedelta(days=h)
            try:
                data = prepare_data(cyc, asof, modern_remaps=False)
                if data["n_polls"] < 8:
                    print(f"[{cycle} D-{h}] only {data['n_polls']} polls, skipped")
                    continue
                import arviz as az
                CACHE.mkdir(exist_ok=True)
                nc = CACHE / f"{cycle}_D{h}.nc"
                if nc.exists():
                    idata = az.from_netcdf(nc)
                else:
                    _, idata = fit(data, draws=400, tune=400)
                    az.to_netcdf(idata, nc)
            except Exception as e:
                print(f"[{cycle} D-{h}] FAILED: {e}")
                continue
            configs = [("plain", h / 7.0, 1.0, 1.0), ("calendar", calendar_weeks(h), 1.0, 1.0)]
            configs += [(f"cal_s{st}_rw{rw}", calendar_weeks(h) * rw, st, rw)
                        for st in STACK_GRID for rw in RW_GRID if not (st == 1.0 and rw == 1.0)]
            for mode, wk, st, rw in configs:
                seats, blocs, base, comp_of = project_cycle(
                    data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                    PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                    np.random.default_rng(SEED + h), resid_scale=bm.RESID_SCALE * st,
                    weeks_override=wk, layers={"shock_scale": st})
                actual = np.zeros(seats.shape[1])
                for r in res.itertuples():
                    hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
                    if len(hit) == 1:
                        actual[hit.pop()] += r.seats
                active = (base >= 0.005) | (actual > 0)
                lo, hi = np.percentile(seats, 5, axis=0), np.percentile(seats, 95, axis=0)
                pp = (seats >= 1).mean(axis=0)
                a = 0.10
                isc = (hi - lo) + (2/a) * np.maximum(lo - actual, 0) + (2/a) * np.maximum(actual - hi, 0)
                nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
                rows.append({"cycle": cycle, "horizon": h, "mode": mode,
                             "n_polls": int(data["n_polls"]),
                             "seat_mae": float(np.abs(seats.mean(axis=0) - actual)[active].mean()),
                             "coverage_90": float(((actual >= lo) & (actual <= hi))[active].mean()),
                             "threshold_brier": float(np.mean((pp[active] - (actual[active] > 0)) ** 2)),
                             "interval_score": float(isc[active].mean()),
                             "mean_width": float((hi - lo)[active].mean()),
                             "p_nb61": float((nb >= 61).mean()),
                             "nb_actual": int(actual[blocs == "netanyahu_bloc"].sum())})
                print(f"[{cycle} D-{h} {mode}] MAE {rows[-1]['seat_mae']:.2f} | cov {rows[-1]['coverage_90']:.0%} | "
                      f"width {rows[-1]['mean_width']:.1f} | iscore {rows[-1]['interval_score']:.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(PROCESSED_DIR / "model_validation_horizon.csv", index=False)
    print("\nHorizon harness (pooled over cycles):")
    print(df.groupby(["horizon", "mode"]).agg(mae=("seat_mae", "mean"), coverage=("coverage_90", "mean"),
                                              brier=("threshold_brier", "mean"), width=("mean_width", "mean"),
                                              iscore=("interval_score", "mean")).round(3).to_string())
    print("\nwrote model_validation_horizon.csv")


if __name__ == "__main__":
    main()
