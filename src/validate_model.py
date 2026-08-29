"""Retro-validation: run the full forecast pipeline as-of each past election.

For every graded cycle, the pipeline (house effects -> trend adjustment ->
quality/group-weighted average -> correlated-error simulation -> threshold ->
Bader-Ofer) is rebuilt using only that cycle's polls, as of the day before
the election, and its stated probabilities are graded against the official
result:

  * 90% interval coverage — do per-list [p05, p95] intervals contain the
    actual seats ~90% of the time?
  * threshold Brier score — quality of P(list wins seats);
  * seat MAE of the simulated mean;
  * P(right/Netanyahu bloc >= 61) vs what happened.

Calibration constants (bloc swing sd, family shocks) are re-estimated
leave-one-cycle-out, so no cycle is graded with numbers that saw its own
outcome. Debut widening is off here (per-cycle debut sets are not tracked),
which makes stated intervals slightly conservative. Historical surplus pairs
are approximations of the registered agreements.

Outputs:
    data/processed/model_validation.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from house_effects import CYCLE_BLOC_OVERRIDES
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
from simulate import build_inputs, simulate_core

N_SIMS = 10_000
ORDER = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
CYCLE_THRESHOLD = {"2009": 0.02, "2013": 0.02}  # 3.25% from 2015 on
# Era-correct bloc fixes beyond the shared overrides: New Hope in 2021 ran
# explicitly never-Netanyahu (it merged into Likud only in 2026).
VAL_BLOC_OVERRIDES = dict(CYCLE_BLOC_OVERRIDES)
VAL_BLOC_OVERRIDES["2021"] = {"new_hope": "opposition_bloc"}
PAST_PAIRS = {  # approximations of the registered agreements
    "2009": [("likud", "yisrael_beytenu"), ("shas", "utj")],
    "2013": [("likud", "jewish_home"), ("shas", "utj")],
    "2015": [("likud", "jewish_home"), ("shas", "utj"),
             ("meretz", "zionist_union")],
    "2019a": [("likud", "urwp"), ("shas", "utj"), ("blue_white", "labor")],
    "2019s": [("likud", "yamina"), ("shas", "utj"), ("blue_white", "labor_gesher")],
    "2020": [("likud", "yamina"), ("shas", "utj"),
             ("blue_white", "labor_gesher_meretz")],
    "2021": [("likud", "rzp"), ("shas", "utj"), ("yesh_atid", "blue_white")],
    "2022": [("likud", "rzp"), ("shas", "utj"), ("yesh_atid", "blue_white")],
}


def loo_calibration(fam: pd.DataFrame, test_cycle: str):
    """Bloc swing sd and family shocks from all cycles except the tested one."""
    others = [c for c in ORDER if c != test_cycle and c in fam.columns]
    bloc_err = fam.loc["right", others] + fam.loc["haredi", others]
    shocks = {}
    for f in ("arab", "haredi"):
        vals = fam.loc[f, others].astype(float)
        shocks[f] = (float(vals.mean()), float(vals.std(ddof=1)))
    return float(bloc_err.astype(float).std(ddof=1)), shocks


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    fam = pd.read_csv(PROCESSED_DIR / "bias_family.csv", index_col=0)

    rows, matched_all, list_rows = [], [], []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        asof = eday - pd.Timedelta(days=1)
        cyc_polls = polls[(polls["cycle"] == cycle) & polls["sums_ok"]]
        from error_decomposition import decompose
        params = decompose(exclude_cycle=cycle)

        avg, _ = build_inputs(cyc_polls, asof, eday=eday,
                              bloc_overrides=VAL_BLOC_OVERRIDES.get(cycle),
                              debut=set())
        seats = simulate_core(
            avg, PAST_PAIRS[cycle],
            threshold=CYCLE_THRESHOLD.get(cycle, 0.0325),
            scale=1.0, bloc_swing_sd=params["bloc_sd"],
            family_shock=params["family"], anchors=None,
            n_sims=N_SIMS,
        )

        # Actual seats per simulated block.
        comp_of = {c: i for i, cs in enumerate(avg["components"])
                   for c in cs.split("+")}
        res = results[results["cycle"] == cycle]
        actual = np.zeros(len(avg))
        unmatched = 0
        for r in res.itertuples():
            hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
            if len(hit) == 1:
                actual[hit.pop()] += r.seats
            else:
                unmatched += r.seats

        p05 = np.percentile(seats, 5, axis=0)
        p95 = np.percentile(seats, 95, axis=0)
        active = (avg["share"].values >= 0.005) | (actual > 0)
        covered = ((actual >= p05) & (actual <= p95))[active]
        p_pass = (seats >= 1).mean(axis=0)
        brier = float(np.mean((p_pass[active] - (actual[active] > 0)) ** 2))
        mae = float(np.abs(seats.mean(axis=0) - actual)[active].mean())

        nb_mask = (avg["bloc"] == "netanyahu_bloc").values
        nb_sim = seats[:, nb_mask].sum(axis=1)
        nb_actual = int(actual[nb_mask].sum())
        for i in np.nonzero(active)[0]:
            list_rows.append({
                "cycle": cycle, "components": avg["components"].iloc[i],
                "pred": float(seats.mean(axis=0)[i]),
                "actual": int(actual[i]),
            })
        rows.append({
            "cycle": cycle, "n_lists": int(active.sum()),
            "coverage_90": round(float(covered.mean()), 2),
            "threshold_brier": round(brier, 3),
            "seat_mae": round(mae, 2),
            "p_bloc_61": round(float((nb_sim >= 61).mean()), 3),
            "bloc_actual": nb_actual,
            "bloc_61_happened": nb_actual >= 61,
            "unmatched_actual_seats": unmatched,
        })
        matched_all.append(covered)

    out = pd.DataFrame(rows).set_index("cycle")
    out.to_csv(PROCESSED_DIR / "model_validation.csv")
    pd.DataFrame(list_rows).to_csv(
        PROCESSED_DIR / "model_validation_lists.csv", index=False)
    print("Model retro-validation, final-eve forecasts "
          f"({N_SIMS:,} sims/cycle, leave-one-cycle-out calibration):\n")
    print(out.to_string())
    pooled = np.concatenate(matched_all)
    print(f"\npooled 90% interval coverage: {pooled.mean():.1%} "
          f"({int(pooled.sum())}/{len(pooled)} lists)")
    p61 = out["p_bloc_61"]
    hap = out["bloc_61_happened"].astype(float)
    print(f"bloc>=61 probabilities vs outcomes: "
          f"mean stated {p61.mean():.1%}, realized {hap.mean():.1%}, "
          f"Brier {((p61 - hap) ** 2).mean():.3f}")
    print(f"pooled seat MAE of simulation means: "
          f"{out['seat_mae'].mean():.2f}")
    print("\nwrote model_validation.csv")


if __name__ == "__main__":
    main()
