"""Registration-deadline scenario module: the forecast as a MIXTURE.

Final lists are filed with the CEC at the beginning of September
(~47 days before the October 27 vote). Until then, a forecast conditional on today's list
structure understates uncertainty in exactly the dimension that decides
Israeli elections. This module samples registration events PER DRAW, so the
published forecast is a mixture over configurations, and every event's
marginal effect is read off the same simulations.

Events, priors, and precedents (all priors are stated judgment):

  balad_splits        0.10  The three-way Joint List deal was SIGNED on
                            2026-08-19 (Tibi accepted the framework after the
                            Aug 9 collapse; ToI/Haaretz) — residual risk of a
                            pre-filing fracture only. Standalone share 2.2%
                            (18 scenario polls) if it does fracture.
                            KNOWN LIMIT: a Ta'al-alone split is not
                            representable while hadash_taal is one registry
                            unit; this event covers the Balad dimension only.
  rzp_fate                  RZP polls ~3.3%, the classic forced-merge zone:
    alone             0.30
    merge_otzma       0.45  the 2022 Netanyahu-brokered RZP-OY precedent
    merge_likud       0.15  the New-Hope-into-Likud 2026 precedent
    withdraws         0.10
  zionist_home_folds  0.55  2-3% lists usually fold by the deadline (The
                            Israelis 2021, Derekh Eretz); absorber Yashar
                            (ex-military centre-right affinity)
  blue_white_folds    0.65  ~1% list; absorber Yashar (Gantz-legacy voters)
  unity_folds         0.70  Erdan/Edelstein are Likud provenance — their
                            voters transfer RIGHT (absorber Likud)
  segalovitz_joins_raam 0.55  Yoav Segalovitz (ex-Yesh Atid) negotiating the
                            No. 2 slot on Ra'am's slate — he has already left
                            Yesh Atid and talks are public (ToI/i24, Aug
                            2026). Effect: Ra'am gains the pairwise-measured
                            scenario-poll boost, carved from the centre bloc
                            (his crossover voters), NOT a new list.

Transfer rules: a bloc-internal merge retains 90% of combined support
(URWP/RZP-OY pattern); a fold-and-endorse transfers 55-65% to the absorber
with the rest scattering proportionally (renormalization). All rates are
assumptions made visible, not measurements.

On filing day: set RESOLVED to the realized events and the mixture
collapses to the true configuration — that day is a scheduled refit.

Outputs:
    data/processed/registration_priors.csv
    data/processed/bayes_forecast_mixture.csv    per-list, mixture forecast
    data/processed/mixture_blocs.csv             bloc probabilities
    data/processed/registration_effects.csv      per-event marginal effects
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR

warnings.filterwarnings("ignore")

SEED = 20261027

PRIORS = {
    "balad_splits": 0.10,
    "rzp_alone": 0.30, "rzp_merge_otzma": 0.45,
    "rzp_merge_likud": 0.15, "rzp_withdraws": 0.10,
    "zionist_home_folds": 0.55,
    "blue_white_folds": 0.65,
    "unity_folds": 0.70,
    "segalovitz_joins_raam": 0.55,
}
MERGE_RETENTION = 0.90
FOLD_TRANSFER = {"zionist_home": ("yashar", 0.60),
                 "blue_white": ("yashar", 0.50),
                 "unity": ("likud", 0.55)}
# Set on filing day to collapse the mixture, e.g.
# RESOLVED = {"balad_splits": False, "rzp_fate": "merge_otzma", ...}
RESOLVED: dict = {}


def _col(comps, component):
    return next((i for i, c in enumerate(comps) if component in c), None)


def apply_registration_events(shares, comps, labels, blocs, fams, rng,
                              params=None):
    """Sample registration events per draw and reshape shares accordingly.

    Returns (shares, comps, labels, blocs, fams, events) — events is a
    DataFrame of per-draw indicators for the marginal-effects readout.
    """
    n = shares.shape[0]
    p = dict(PRIORS)
    cp = params or {}

    def bern(name):
        if name in RESOLVED:
            return np.full(n, bool(RESOLVED[name]))
        return rng.random(n) < p[name]

    events = {}

    # Segalovitz joins Ra'am's slate: Ra'am gains his crossover voters,
    # carved proportionally from the centre bloc. No new list is created.
    seg_on = bern("segalovitz_joins_raam")
    boost = cp.get("segalovitz_boost_seats", 1.3) / 120.0
    raam = _col(comps, "raam")
    centre = blocs == "opposition_bloc"
    w = np.where(centre, shares.mean(axis=0), 0.0)
    if raam is not None:
        shares = shares - seg_on[:, None] * boost * (w / w.sum())
        shares[:, raam] += np.where(seg_on, boost, 0.0)
    events["segalovitz_joins_raam"] = seg_on

    # Balad splits from the Joint List.
    jl = _col(comps, "hadash_taal")
    split_on = bern("balad_splits")
    balad_share = cp.get("balad_alone_pct", 2.2) / 100.0
    take = np.where(split_on, np.minimum(shares[:, jl], balad_share), 0.0)
    shares = np.concatenate([shares, take[:, None]], axis=1)
    shares[:, jl] -= take
    comps.append({"balad"})
    labels.append("Balad (alone)")
    blocs = np.append(blocs, "other")
    fams = np.append(fams, "arab")
    events["balad_splits"] = split_on

    # RZP's fate (categorical).
    rzp = _col(comps, "rzp")
    otzma = _col(comps, "otzma")
    likud = _col(comps, "likud")
    if "rzp_fate" in RESOLVED:
        fate = np.full(n, RESOLVED["rzp_fate"], dtype=object)
    else:
        u = rng.random(n)
        cut1 = p["rzp_alone"]
        cut2 = cut1 + p["rzp_merge_otzma"]
        cut3 = cut2 + p["rzp_merge_likud"]
        fate = np.select([u < cut1, u < cut2, u < cut3],
                         ["alone", "merge_otzma", "merge_likud"],
                         default="withdraws")
    if rzp is not None:
        m_o = fate == "merge_otzma"
        shares[m_o, otzma] += MERGE_RETENTION * shares[m_o, rzp]
        m_l = fate == "merge_likud"
        shares[m_l, likud] += MERGE_RETENTION * shares[m_l, rzp]
        gone = m_o | m_l | (fate == "withdraws")
        shares[gone, rzp] = 0.0
    events["rzp_fate"] = fate

    # Sub-threshold centre lists folding into absorbers.
    for pid, (absorber, transfer) in FOLD_TRANSFER.items():
        src = _col(comps, pid)
        dst = _col(comps, absorber)
        if src is None or dst is None:
            continue
        on = bern(f"{pid}_folds")
        shares[on, dst] += transfer * shares[on, src]
        shares[on, src] = 0.0
        events[f"{pid}_folds"] = on

    shares = np.clip(shares, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)
    return shares, comps, labels, blocs, fams, pd.DataFrame(events)


def main() -> None:
    import arviz as az
    from bayes_model import fit, prepare_data, project

    try:
        scen = pd.read_csv(PROCESSED_DIR / "arab_scenarios.csv")
        balad = scen[scen["list"].str.fullmatch("Balad")
                     & scen["below_pct"].notna()]["below_pct"].mean()
        joint = scen[(scen["list"] == "Ra'am+Segalovitz")
                     & scen["seats"].notna()]
        base = scen[(scen["scenario"] == "baseline")
                    & (scen["list"] == "Ra'am") & scen["seats"].notna()]
        base_map = base.groupby(["pollster", "fieldwork_end"])["seats"].mean()
        boosts = [r.seats - base_map[(r.pollster, r.fieldwork_end)]
                  for r in joint.itertuples()
                  if (r.pollster, r.fieldwork_end) in base_map.index]
        params = {"balad_alone_pct": float(balad),
                  "segalovitz_boost_seats": (float(np.mean(boosts))
                                             if boosts else 1.3)}
        print(f"scenario params: balad alone {params['balad_alone_pct']:.1f}%"
              f" | Ra'am+Segalovitz boost {params['segalovitz_boost_seats']:+.1f}"
              f" seats ({len(boosts)} poll pairs)")
    except FileNotFoundError:
        params = {}

    nc = PROCESSED_DIR / "m3_idata.nc"
    data = prepare_data()
    if nc.exists():
        idata = az.from_netcdf(nc)
    else:
        _, idata = fit(data, draws=600, tune=600)
        az.to_netcdf(idata, nc)

    rng = np.random.default_rng(SEED)
    seats, labels, blocs = project(data, idata, rng, config="mixture",
                                   config_params=params)
    blocs = np.array(blocs)
    events = project.last_events  # attached by the mixture branch

    nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
    anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)

    dist = pd.DataFrame({
        "list": labels,
        "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
    }).sort_values("mean", ascending=False)
    dist.to_csv(PROCESSED_DIR / "bayes_forecast_mixture.csv", index=False)

    summary = pd.DataFrame([{
        "p_nb_61": round(float((nb >= 61).mean()), 3),
        "p_anti_61": round(float((anti >= 61).mean()), 3),
        "p_neither": round(float(((nb < 61) & (anti < 61)).mean()), 3),
        "nb_mean": round(float(nb.mean()), 1),
        "nb_p05": int(np.percentile(nb, 5)),
        "nb_p95": int(np.percentile(nb, 95)),
    }])
    summary.to_csv(PROCESSED_DIR / "mixture_blocs.csv", index=False)

    effects = []
    for col in events.columns:
        vals = events[col]
        cats = vals.unique() if vals.dtype == object else [True, False]
        for cat in cats:
            m = (vals == cat).values
            if m.sum() < 50:
                continue
            effects.append({
                "event": col, "outcome": str(cat),
                "probability": round(float(m.mean()), 3),
                "p_nb_61": round(float((nb[m] >= 61).mean()), 3),
                "p_neither": round(float(((nb[m] < 61)
                                          & (anti[m] < 61)).mean()), 3),
                "nb_mean": round(float(nb[m].mean()), 1),
            })
    eff = pd.DataFrame(effects)
    eff.to_csv(PROCESSED_DIR / "registration_effects.csv", index=False)
    pd.Series(PRIORS).to_csv(PROCESSED_DIR / "registration_priors.csv")

    s = summary.iloc[0]
    print("MIXTURE forecast (over registration scenarios):")
    print(f"  P(NB>=61) = {s['p_nb_61']:.1%} | P(anti>=61) = "
          f"{s['p_anti_61']:.1%} | P(neither) = {s['p_neither']:.1%}")
    print(f"  NB mean {s['nb_mean']}, 90% interval "
          f"[{s['nb_p05']}, {s['nb_p95']}]\n")
    print(dist.head(16).to_string(index=False))
    print("\nPer-event marginal effects (same draws, conditioned):")
    print(eff.to_string(index=False))


if __name__ == "__main__":
    main()
