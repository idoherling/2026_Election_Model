"""Threshold calibration on the graded record (accuracy round four, #1).

Uses the horizon harness's cached posteriors (data/processed/harness_cache/
<cycle>_D<h>.nc) to project every cycle as of D-56 and D-21 under the shipped
layer configuration, then grades PASS PROBABILITIES for the lists that
mattered: those whose projected share sat within a band around the
threshold. Outputs a reliability table (predicted pass probability bins vs
realised pass rate), the straddler Brier score, and the realised drift of
straddlers between the projection date and the result, by horizon.

Writes data/processed/model_validation_threshold.csv (one row per
cycle x horizon x straddling list).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import bayes_model as bm
from validate_bayes import (ORDER, ELECTION_DAY, CYCLE_THRESHOLD, PAST_PAIRS,
                            VAL_BLOC_OVERRIDES, apply_decomp, decompose,
                            project_cycle, trailing_likud_params, SEED,
                            new_lists_for_cycle, new_straddler_params)
from validate_horizon import HORIZONS, CACHE, calendar_weeks
from scrape_polls import PROCESSED_DIR
from simulate import THRESHOLD

BAND_LO, BAND_HI = -0.75, 1.50     # percentage points around the threshold


def main(layers: dict | None = None) -> pd.DataFrame:
    import arviz as az
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    rows = []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        thr = CYCLE_THRESHOLD.get(cycle, THRESHOLD)
        cyc = apply_decomp(polls[(polls["cycle"] == cycle) & polls["sums_ok"]], cycle)
        res = apply_decomp(results[results["cycle"] == cycle], cycle)
        params = decompose(exclude_cycle=cycle)
        params["trail"] = trailing_likud_params(polls, results, exclude_cycle=cycle)
        params["new_lists"] = new_lists_for_cycle(polls, cycle)
        params["nstrad"] = new_straddler_params(exclude_cycle=cycle)
        for h in HORIZONS:
            nc = CACHE / f"{cycle}_D{h}.nc"
            if not nc.exists():
                continue
            asof = eday - pd.Timedelta(days=h)
            data = bm.prepare_data(cyc, asof, modern_remaps=False)
            idata = az.from_netcdf(nc)
            L = dict({"anchors": False}, **(layers or {}))
            seats, blocs, base, comp_of = project_cycle(
                data, idata, eday, thr, PAST_PAIRS[cycle], params,
                VAL_BLOC_OVERRIDES.get(cycle), np.random.default_rng(SEED + h),
                resid_scale=bm.RESID_SCALE, weeks_override=calendar_weeks(h), layers=L)
            actual_share = np.zeros(seats.shape[1])
            for r in res.itertuples():
                hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
                if len(hit) == 1:
                    v = r.vote_pct if pd.notna(r.vote_pct) else r.seats / 120 * 100
                    actual_share[hit.pop()] += float(v)
            pp = (seats >= 1).mean(axis=0)
            for i, comp in enumerate(data["components"]):
                proj = base[i] * 100
                if (proj - thr * 100) < BAND_LO or (proj - thr * 100) > BAND_HI:
                    continue
                rows.append({"cycle": cycle, "horizon": h, "list": comp,
                             "new": bool(set(comp.split("+")) <= params["new_lists"]),
                             "threshold": thr * 100, "proj_share": proj,
                             "p_pass": float(pp[i]), "actual_share": actual_share[i],
                             "passed": bool(actual_share[i] >= thr * 100),
                             "drift": actual_share[i] - proj})
    df = pd.DataFrame(rows)
    if not (layers or {}).get("new_straddler"):
        df.to_csv(PROCESSED_DIR / "model_validation_threshold.csv", index=False)
    if df.empty:
        print("no cached horizon posteriors yet - run validate_horizon first")
        return df
    print(df.round(3).to_string(index=False))
    for h, g in df.groupby("horizon"):
        brier = np.mean((g["p_pass"] - g["passed"]) ** 2)
        print(f"\nD-{h}: {len(g)} straddlers | Brier {brier:.3f} | realised pass {g['passed'].mean():.2f} "
              f"vs mean p_pass {g['p_pass'].mean():.2f} | mean drift {g['drift'].mean():+.2f} pp "
              f"(sd {g['drift'].std():.2f})")
        bins = pd.cut(g["p_pass"], [0, 0.25, 0.5, 0.75, 1.0], include_lowest=True)
        print(g.groupby(bins, observed=True).agg(n=("passed", "size"), p_pred=("p_pass", "mean"),
                                                 p_real=("passed", "mean")).round(2).to_string())
    return df


if __name__ == "__main__":
    base = main()
    if not base.empty and base["new"].any():
        print("\n=== with the new-straddler layer (LOO parameters) ===")
        lay = main(layers={"new_straddler": True})
        for h in sorted(base["horizon"].unique()):
            b = base[base.horizon == h]; l = lay[lay.horizon == h]
            print(f"D-{h}: Brier all {np.mean((b.p_pass-b.passed)**2):.3f} -> {np.mean((l.p_pass-l.passed)**2):.3f} | "
                  f"new only {np.mean((b[b.new].p_pass-b[b.new].passed)**2):.3f} -> {np.mean((l[l.new].p_pass-l[l.new].passed)**2):.3f} | "
                  f"established {np.mean((b[~b.new].p_pass-b[~b.new].passed)**2):.3f} -> {np.mean((l[~l.new].p_pass-l[~l.new].passed)**2):.3f}")
