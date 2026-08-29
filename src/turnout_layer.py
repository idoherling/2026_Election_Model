"""Turnout-and-undecided layer: what the disclosure data adds to the model.

Two components, both from data already in the repo:

  1. UNDECIDED (in the fit): each CEC filing's reported undecided share
     widens that poll's observation noise by an ESTIMATED factor (beta_u in
     bayes_model.fit — the data decides whether undecided-heavy polls are
     less informative; a useless signal shrinks the coefficient to zero).
     25 of 37 filings report an undecided share.

  2. TURNOUT (at projection): a differential Arab-turnout dial. Calibration:
     the 2021 -> 2022 sector turnout swing (44.6% -> 53.2%) moved the Arab
     lists' combined national share from ~8.6% to ~10.7% (~+24%), so
     factors 0.88 / 1.00 / 1.12 span a plausible low/central/high range.
     Context for the central setting: the StatNet/KAP engagement series is
     near record levels (77% support participation in government) and the
     Segalovitz-on-Ra'am development points the same way — the LOW scenario
     is the tail risk, not the base case.

  Dropped after inspection: sector-sample-composition adjustments — the
  filings' demographic tables collide with age-bracket rows under line-based
  parsing (Tatika's "18" is the 18-29 bracket). Needs table-structure
  parsing; documented as future work rather than shipped wrong.

Outputs:
    data/processed/turnout_scenarios.csv
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR

warnings.filterwarnings("ignore")

SEED = 20261027
FACTORS = {"low_turnout": 0.88, "central": 1.00, "high_turnout": 1.12}


def main() -> None:
    import arviz as az
    from bayes_model import fit, prepare_data, project

    fil = pd.read_csv(PROCESSED_DIR / "cec_filings.csv", dtype={"ref": str})
    u = fil.dropna(subset=["undecided_pct"])
    print(f"undecided shares: {len(u)}/{len(fil)} filings, "
          f"mean {u['undecided_pct'].mean():.1f}%, "
          f"range {u['undecided_pct'].min():.0f}-"
          f"{u['undecided_pct'].max():.0f}%")
    print(u.groupby("pollster")["undecided_pct"].mean().round(1)
          .sort_values().to_string(), "\n")

    nc = PROCESSED_DIR / "m3_idata.nc"
    data = prepare_data()
    if nc.exists():
        idata = az.from_netcdf(nc)
    else:
        _, idata = fit(data, draws=600, tune=600)
        az.to_netcdf(idata, nc)
    if "beta_u" in idata.posterior:
        bu = idata.posterior["beta_u"].values.ravel()
        print(f"beta_u posterior: mean {bu.mean():.2f} "
              f"[{np.percentile(bu, 5):.2f}, {np.percentile(bu, 95):.2f}]\n")

    rows = []
    for name, fct in FACTORS.items():
        rng = np.random.default_rng(SEED)
        seats, labels, blocs = project(data, idata, rng,
                                       config="arab_turnout",
                                       config_params={"factor": fct})
        blocs = np.array(blocs)
        nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
        anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
        arab = seats[:, blocs == "other"].sum(axis=1)
        jl = next((i for i, l in enumerate(labels) if "Hadash" in l), None)
        ra = next((i for i, l in enumerate(labels) if l == "Ra'am"), None)
        rows.append({
            "scenario": name, "factor": fct,
            "arab_seats_mean": round(float(arab.mean()), 1),
            "p_jl_passes": round(float((seats[:, jl] >= 4).mean()), 3),
            "p_raam_passes": round(float((seats[:, ra] >= 4).mean()), 3),
            "p_nb_61": round(float((nb >= 61).mean()), 3),
            "p_anti_61": round(float((anti >= 61).mean()), 3),
            "p_neither": round(float(((nb < 61) & (anti < 61)).mean()), 3),
        })
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "turnout_scenarios.csv", index=False)
    print("Arab-turnout scenarios (posterior projections):")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
