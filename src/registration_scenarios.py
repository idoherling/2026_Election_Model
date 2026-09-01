"""Registration-deadline scenario module: the forecast as a MIXTURE.

Final lists are filed with the CEC on September 9, 2026 (CONFIRMED);
surplus-vote agreements register separately by October 16. Until then, a forecast conditional on today's list
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
  rzp_fate                  RZP polls ~3.3%. Aug 30 deep dive: two live,
                            mutually exclusive rescue tracks:
    alone             0.12  post-primaries purity posture, both tracks die
    merge_otzma       0.08  "final and absolute" refusal — but Netanyahu
                            forced this exact merger in 2021 and 2022
    merge_likud       0.36  technical absorption, Ynet's "most likely"
    merge_zehut       0.31  Smotrich-Feiglin technical bloc, advanced talks
                            (Feiglin #2 + slots 8,10); combined list faces
                            the threshold itself (~75% pass rate in draws)
    withdraws         0.13  Feiglin-2019-style paid exit
  zionist_home_folds  0.45  ZH-Reservists is the strongest micro; Tropper's
                            pre-agreed fallback is folding into Yashar
  blue_white_folds    0.65  Gantz MK ultimatum vs his slot-#1 demand
  unity_folds         0.85  Erdan won't run to the end at 0.8%
  centre_union_files  0.12  Erdan-Gantz(-Zelicha) union files as one list
                            instead of folding (usually still sub-threshold)
  segalovitz_joins_raam 0.80  agreement in principle signed Aug 5 (Maariv);
                            slot #2 reserved at Ra'am's primaries; both
                            sides burned their boats. Effect: Ra'am gains
                            the pairwise-measured scenario-poll boost,
                            carved from the centre bloc, NOT a new list.

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
    # Aug 30 deep dive: Smotrich-Feiglin technical bloc CONFIRMED in
    # advanced talks (Feiglin #2, Zehut slots 8+10; Amit Segal/Ch12, both
    # parties confirm; Netanyahu blessing "in principle") — a live branch,
    # not a rumor lane. Likud technical absorption remains Ynet's "most
    # likely". The two tracks are substitutes. Otzma merger "final and
    # absolute" dead.
    # merge_otzma nudged up from 0.02: the institutions desk warns never
    # to fully trust a "final and absolute" refusal before the deadline —
    # Netanyahu personally forced this exact merger in 2021 AND 2022 —
    # though this cycle Ben Gvir is above threshold and bleeding to
    # Winter, so the historical enforcement mechanism (mutual threshold
    # fear) is absent.
    "rzp_alone": 0.12, "rzp_merge_otzma": 0.08,
    "rzp_merge_likud": 0.36, "rzp_merge_zehut": 0.31,
    "rzp_withdraws": 0.13,
    # Centre desk (Aug 30): ZH-Reservists is the strongest micro (2.0-2.9%,
    # crossed once) with a pre-agreed Tropper fallback of folding into
    # Yashar (Kan 11 via Maariv Jul 7) -> files ~0.55.
    "zionist_home_folds": 0.45,
    # Gantz's MKs threaten to walk rather than "burn votes"; 48% of the
    # public says retire; but his #1 demand blocks the mergers.
    "blue_white_folds": 0.65,
    # Correspondent consensus: Erdan won't run to the end at 0.8% (Kipa
    # Aug 29).
    "unity_folds": 0.85,
    # Erdan-Gantz working teams + Erdan-Zelicha "one political force"
    # track (Israel Hayom Aug 29): a union FILES instead of folding.
    # Ch13 (Aug 26) tested even Gantz+Erdan+Shaked merged and it still
    # missed 3.25% - the union mostly burns votes anyway.
    "centre_union_files": 0.12,
    # Maariv (Aug 5): agreement in principle SIGNED; slot #2 structurally
    # reserved at Ra'am's Aug 22 primaries; both sides burned their boats
    # (he resigned the Knesset; Abbas ran primaries with #2 vacated).
    # Residual: the recognition-formula double-speak spiral (Abbas's
    # Aug 26 Arabic post).
    "segalovitz_joins_raam": 0.80,
}
MERGE_RETENTION = 0.90
# Fold redistribution vectors (centre desk, Aug 30): named absorbers get
# explicit shares; the remainder scatters proportionally (renormalization).
# Unity's voters are ex-Likud but have LEFT the Likud orbit - only ~20%
# return; Erdan/Edelstein/Shaked voters split toward Together and YB.
FOLD_TRANSFER = {
    "zionist_home": [("yashar", 0.75)],
    "blue_white": [("yashar", 0.45), ("bennett_2026", 0.15)],
    "unity": [("bennett_2026", 0.25), ("yisrael_beytenu", 0.20),
              ("likud", 0.20), ("yashar", 0.15)],
}
# Set on filing day to collapse the mixture, e.g.
# RESOLVED = {"balad_splits": False, "rzp_fate": "merge_otzma", ...}
# 2026-09-01: Segalovitz-Ra'am deal announced as OFFICIAL — the event is
# resolved True. The +0.4-seat scenario boost stays for now because the
# poll stream predates the announcement; ZERO IT at the Sept 9 refit,
# when post-announcement polls price the joint slate directly (keeping
# both would double-count).
# 2026-09-02: Smotrich-Feiglin (RZP-Zehut) technical bloc announced
# OFFICIAL — rzp_fate resolves to merge_zehut: RZP absorbs Zehut's
# share at MERGE_RETENTION and the combined list faces the 3.25%
# threshold on its own in every draw. Post-announcement polls of the
# joint list will absorb this directly; at that point the retention
# transfer should be retired the same way as the Segalovitz boost.
# 2026-09-02 (owner): Balad staying in the Joint List is to be treated
# as certain — balad_splits resolved False.
RESOLVED: dict = {"segalovitz_joins_raam": True,
                  "rzp_fate": "merge_zehut",
                  "balad_splits": False}


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

    # RZP's fate (categorical). merge_zehut = the Smotrich-Feiglin
    # technical bloc: RZP absorbs Zehut's share and the combined list
    # faces the threshold on its own (~4.3-5.0% nominal, retention
    # haircut applied -> passes in roughly three-quarters of draws).
    rzp = _col(comps, "rzp")
    otzma = _col(comps, "otzma")
    likud = _col(comps, "likud")
    zehut = _col(comps, "zehut")
    if "rzp_fate" in RESOLVED:
        fate = np.full(n, RESOLVED["rzp_fate"], dtype=object)
    else:
        u = rng.random(n)
        cut1 = p["rzp_alone"]
        cut2 = cut1 + p["rzp_merge_otzma"]
        cut3 = cut2 + p["rzp_merge_likud"]
        cut4 = cut3 + p["rzp_merge_zehut"]
        fate = np.select([u < cut1, u < cut2, u < cut3, u < cut4],
                         ["alone", "merge_otzma", "merge_likud",
                          "merge_zehut"],
                         default="withdraws")
    if rzp is not None:
        m_o = fate == "merge_otzma"
        shares[m_o, otzma] += MERGE_RETENTION * shares[m_o, rzp]
        m_l = fate == "merge_likud"
        shares[m_l, likud] += MERGE_RETENTION * shares[m_l, rzp]
        if zehut is not None:
            m_z = fate == "merge_zehut"
            shares[m_z, rzp] += MERGE_RETENTION * shares[m_z, zehut]
            shares[m_z, zehut] = 0.0
        gone = m_o | m_l | (fate == "withdraws")
        shares[gone, rzp] = 0.0
    events["rzp_fate"] = fate

    # Centre union (Erdan-Gantz[-Zelicha] "one political force"): B&W and
    # Unity file as ONE list under the B&W line instead of folding.
    # Retention haircut per merger norm; the combined ~2.6-3.1% still
    # usually misses 3.25% (Ch13 tested the merger and it failed).
    union_on = bern("centre_union_files")
    bw = _col(comps, "blue_white")
    un = _col(comps, "unity")
    if bw is not None and un is not None:
        shares[union_on, bw] = MERGE_RETENTION * (
            shares[union_on, bw] + shares[union_on, un])
        shares[union_on, un] = 0.0
    events["centre_union_files"] = union_on

    # Sub-threshold centre lists folding into absorbers (suppressed for
    # B&W/Unity in union draws — the union already consumed them).
    for pid, dests in FOLD_TRANSFER.items():
        src = _col(comps, pid)
        if src is None:
            continue
        on = bern(f"{pid}_folds")
        if pid in ("blue_white", "unity"):
            on = on & ~union_on
        for absorber, transfer in dests:
            dst = _col(comps, absorber)
            if dst is None:
                continue
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
    # Feed the formation layer the same mixture draws, so registration
    # events (RZP-Zehut pass/fail, centre folds) flow into coalition math.
    pd.DataFrame(seats, columns=labels).to_parquet(
        PROCESSED_DIR / "mixture_draws.parquet")

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
