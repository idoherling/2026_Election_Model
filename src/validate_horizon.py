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
from validate_bayes import (CACHE_DIR, CYCLE_THRESHOLD, ORDER, OUT_DIR,
                            PAST_PAIRS, VAL_BLOC_OVERRIDES, _decomp_map,
                            apply_decomp, harness_frame, harness_prepare,
                            load_or_fit, project_cycle, StaleArmCache)

warnings.filterwarnings("ignore")
import os as _os0
HORIZONS = [int(x) for x in _os0.environ.get("HORIZONS", "56,21").split(",")]   # e.g. HORIZONS=56,21,7
CACHE = CACHE_DIR   # HARNESS_CACHE_DIR (research caches live apart; a name or a path)
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
        res = apply_decomp(results[results["cycle"] == cycle], cycle)
        params = decompose(exclude_cycle=cycle)
        from validate_bayes import (new_lists_for_cycle, new_straddler_params,
                                    trailing_likud_params)
        # 2026-10-10 (dossier s.41): the trailing-Likud parameters were never
        # passed here, so TRAIL was OFF in every horizon run - including the
        # shipped "calendar" baseline. Horizon numbers recorded before this
        # date are TRAIL-off numbers.
        params["trail"] = trailing_likud_params(polls, results, exclude_cycle=cycle)
        params["new_lists"] = new_lists_for_cycle(polls, cycle)
        params["nstrad"] = new_straddler_params(exclude_cycle=cycle)
        params["pair_alias"] = _decomp_map(cycle)   # dossier s.40
        from validate_bayes import arab_turnout_params, add_calibration_params
        params["arab_tab"] = arab_turnout_params(cycle)   # dossier s.43
        params["arab_lineage"] = bm.arab_lineage_share(exclude_cycle=cycle)   # s.51
        from validate_model import REGISTERED_PAIRS
        params["registered_pairs"] = REGISTERED_PAIRS[cycle]   # dossier s.47
        params["cycle"] = cycle
        add_calibration_params(params, cycle)              # dossier s.48
        for h in HORIZONS:
            asof = eday - pd.Timedelta(days=h)
            try:
                # as-of frame: DECOMP + (HARNESS_FIDELITY) ballot fidelity
                cyc = harness_frame(polls, cycle, eday, asof)
                data = harness_prepare(cyc, asof)
                if data["n_polls"] < 8:
                    print(f"[{cycle} D-{h}] only {data['n_polls']} polls, skipped")
                    continue
                idata = load_or_fit(CACHE / f"{cycle}_D{h}.nc", data, 400, 400)
            except Exception as e:
                print(f"[{cycle} D-{h}] FAILED: {e}")
                continue
            # "calendar" = the shipped configuration (production layer defaults).
            # calendar first: its list mask grades every config in the
            # *_fixed columns (each config draws from its own fresh rng)
            configs = [("calendar", calendar_weeks(h), 1.0, 1.0), ("plain", h / 7.0, 1.0, 1.0)]
            fixed = None
            import os as _os, json as _json
            if not _os.environ.get("HORIZON_SKIP_GRID"):
                configs += [(f"cal_s{st}_rw{rw}", calendar_weeks(h) * rw, st, rw)
                            for st in STACK_GRID for rw in RW_GRID if not (st == 1.0 and rw == 1.0)]
            # HORIZON_LAYERS='name1:{"flag":true};name2:{...}' adds layer configs
            # (candidate tests) at the calendar horizon.
            extra = {}
            for spec in filter(None, _os.environ.get("HORIZON_LAYERS", "").split(";")):
                nm_, js_ = spec.split(":", 1)
                extra[nm_] = _json.loads(js_)
                configs.append((nm_, calendar_weeks(h), 1.0, 1.0))
            project_cycle.job = f"{cycle}_D{h}"   # layer 'posterior' (refit arms)
            for mode, wk, st, rw in configs:
                try:
                    seats, blocs, base, comp_of = project_cycle(
                        data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                        PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                        np.random.default_rng(SEED + h + int(_os.environ.get("HARNESS_SEED_OFFSET", 0))),
                        resid_scale=bm.RESID_SCALE * st,
                        weeks_override=wk,
                        layers=dict({"shock_scale": st}, **extra.get(mode, {})))
                except (FileNotFoundError, StaleArmCache) as e:   # a refit arm's cache is missing / stale
                    print(f"[{cycle} D-{h} {mode}] skipped: {e}")
                    continue
                actual = np.zeros(seats.shape[1])
                for r in res.itertuples():
                    hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
                    if len(hit) == 1:
                        actual[hit.pop()] += r.seats
                active = (base >= 0.005) | (actual > 0)
                if mode == "calendar":
                    fixed = active
                lo, hi = np.percentile(seats, 5, axis=0), np.percentile(seats, 95, axis=0)
                pp = (seats >= 1).mean(axis=0)
                a = 0.10
                isc = (hi - lo) + (2/a) * np.maximum(lo - actual, 0) + (2/a) * np.maximum(actual - hi, 0)
                nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
                rows.append({"cycle": cycle, "horizon": h, "mode": mode,
                             "n_polls": int(data["n_polls"]),
                             "seat_mae": float(np.abs(seats.mean(axis=0) - actual)[active].mean()),
                             "seat_mae_median": float(np.abs(np.median(seats, axis=0) - actual)[active].mean()),
                             "seat_mae_central": float(np.abs(project_cycle.last_central - actual)[active].mean()),
                             "trail_frac": project_cycle.last_trail["frac"],
                             "coverage_90": float(((actual >= lo) & (actual <= hi))[active].mean()),
                             "threshold_brier": float(np.mean((pp[active] - (actual[active] > 0)) ** 2)),
                             "interval_score": float(isc[active].mean()),
                             "seat_mae_fixed": float(np.abs(seats.mean(axis=0) - actual)[fixed].mean()),
                             "seat_mae_median_fixed": float(np.abs(np.median(seats, axis=0) - actual)[fixed].mean()),
                             "coverage_90_fixed": float(((actual >= lo) & (actual <= hi))[fixed].mean()),
                             "threshold_brier_fixed": float(np.mean((pp[fixed] - (actual[fixed] > 0)) ** 2)),
                             "interval_score_fixed": float(isc[fixed].mean()),
                             "seat_mae_central_fixed": float(np.abs(project_cycle.last_central - actual)[fixed].mean()),
                             "n_pairs": len(project_cycle.last_pairs["applied"]),
                             "mean_width": float((hi - lo)[active].mean()),
                             "arab_fam_err": float(seats[:, project_cycle.last_fams == "arab"].sum(axis=1).mean()
                                                   - actual[project_cycle.last_fams == "arab"].sum()),
                             "p_nb61": float((nb >= 61).mean()),
                             "nb_actual": int(actual[blocs == "netanyahu_bloc"].sum())})
                print(f"[{cycle} D-{h} {mode}] MAE {rows[-1]['seat_mae']:.2f} | cov {rows[-1]['coverage_90']:.0%} | "
                      f"width {rows[-1]['mean_width']:.1f} | iscore {rows[-1]['interval_score']:.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "model_validation_horizon.csv", index=False)
    print("\nHorizon harness (pooled over cycles):")
    tab = df.groupby(["horizon", "mode"]).agg(mae=("seat_mae", "mean"), coverage=("coverage_90", "mean"),
                                              brier=("threshold_brier", "mean"), width=("mean_width", "mean"),
                                              iscore=("interval_score", "mean"), cycles=("cycle", "nunique"))
    # arms scored in fewer cycles than the calendar baseline at the same
    # horizon are not comparable when pooled: flag and drop them
    full = tab.groupby(level=0)["cycles"].transform("max")
    partial = tab[tab["cycles"] < full]
    if len(partial):
        print("  arms scored in fewer cycles than the baseline, left out: "
              + ", ".join(f"D-{hz} {m} ({int(n)})" for (hz, m), n in partial["cycles"].items()))
    print(tab[tab["cycles"] == full].round(3).to_string())
    print("\nwrote model_validation_horizon.csv")


if __name__ == "__main__":
    main()
