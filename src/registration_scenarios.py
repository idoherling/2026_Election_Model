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
                            -> RESOLVED True 2026-09-04 (withdrew)
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
    # 2026-09-16: disqualification petitions (section 7A) filed by the
    # Sept 15 deadline - Ra'am (Likud, Otzma, a voters' forum), the Joint
    # List (Likud), Otzma Yehudit (the Democrats, Zulat), RZP-Zehut
    # (Zulat), the Democrats (Otzma). The CEC hears them next week; a
    # list disqualification is appealable to the Supreme Court, which has
    # reinstated every Arab list the committee barred since 2003 (Tibi/
    # Bishara 2003, Balad and Ra'am-Ta'al 2009, Ra'am-Balad 2019) and has
    # barred no Jewish list since Kach in 1988. Priors are the residual
    # after that record; candidate-level petitions (Kasif, Abu Shahada) do
    # not remove a list's seats and are not modeled.
    "raam_disqualified": 0.02,
    "joint_list_disqualified": 0.015,
    "otzma_disqualified": 0.01,
    "rzp_disqualified": 0.005,
    "democrats_disqualified": 0.005,
}
# Where a disqualified list's voters go (share of its vote; the remainder
# abstains): Arab-list voters mostly stay in the family, right-wing lists
# flow to Likud and the sister list.
DISQUALIFY_TRANSFER = {
    "raam": ("raam_disqualified", [("balad", 0.50)]),
    "balad": ("joint_list_disqualified", [("raam", 0.40)]),
    "otzma": ("otzma_disqualified", [("likud", 0.50), ("rzp", 0.35), ("amcha_yisrael", 0.10)]),
    "rzp": ("rzp_disqualified", [("otzma", 0.55), ("likud", 0.35)]),
    "democrats": ("democrats_disqualified", [("yashar", 0.45), ("bennett_2026", 0.35), ("balad", 0.10)]),
}
MERGE_RETENTION = 0.90
# Fold redistribution vectors (centre desk, Aug 30): named absorbers get
# explicit shares; the remainder scatters proportionally (renormalization).
# Unity's voters are ex-Likud but have LEFT the Likud orbit - only ~20%
# return; Erdan/Edelstein/Shaked voters split toward Together and YB.
# Fold transfers (2026-09-03, audit #4): structure from the measured
# Kolot Nodedim 2021->2022 matrix for ABSORBED lists - their voters land
# ~90-100% on heir lists, split across several: Yamina -> RZP 45 / Jewish
# Home 24 / Likud 14 / National Unity 11 / Shas 6; New Hope -> National
# Unity 58 / Likud 42; Blue and White -> National Unity 70 / Yesh Atid 30.
# Analogs: ZH-Reservists ~ New Hope + B&W (Hendel ex-New Hope, Tropper
# ex-B&W); Blue and White ~ its own 2022 pattern; Unity ~ Likud alumni.
FOLD_TRANSFER = {
    "zionist_home": [("yashar", 0.55), ("bennett_2026", 0.15), ("likud", 0.20)],
    # 2026-10-20 OWNER RULING ("Gantz voters lean unity"): Blue and White
    # withdrew on 19 Oct with no endorsement and a closing message against
    # "only not Bibi"; no poll has measured where its remaining voters go
    # (Israel Hayom 19 Oct: "estimates only"). Commentary points to Hendel's
    # unity pitch (Ynet, Srugim, Israel Hayom), to Eisenkot (JDN Barometer)
    # and, per Filber's unpublished internal polls, to Netanyahu as PM. The
    # owner set the vector below; the 2022 measured pattern (BW_TRANSFER_2022)
    # stays as an alternative in the model explorer. Replace both with a
    # measured flow as soon as a pollster publishes one.
    "blue_white": [("yashar", 0.35), ("bennett_2026", 0.10),
                   ("zionist_home", 0.25), ("likud", 0.15)],
    "unity": [("likud", 0.45), ("yashar", 0.25), ("yisrael_beytenu", 0.10),
              ("bennett_2026", 0.10)],
    # 2026-10-23 (dossier s.72): Ahi withdrew four days out after a deal with
    # Likud (a deputy minister in the PM's office); Rabbi Abergel told his
    # followers to vote Likud (INN 709199, Israel Hayom 21693463, Kore
    # 223826). No poll measured its voters: the endorsement routes .60 to
    # Likud, .15 to Shas (the movement's Sephardi-traditional orbit), the
    # rest stay home - a stated judgment, as s.64.
    "ahi": [("likud", 0.60), ("shas", 0.15)],
}
# Blue and White's measured 2021->2022 absorbed-list pattern (National
# Unity 70 / Yesh Atid 30 -> Yashar .60 / Together .25, rest abstain): the
# official vector until the 20 Oct owner ruling; kept for the explorer.
BW_TRANSFER_2022 = [("yashar", 0.60), ("bennett_2026", 0.25)]
# Set on filing day to collapse the mixture, e.g.
# RESOLVED = {"balad_splits": False, "rzp_fate": "merge_otzma", ...}
# 2026-09-01: Segalovitz-Ra'am deal announced as OFFICIAL — the event is
# resolved True. 2026-09-03: the +0.4 scenario boost ZEROED — the Sept 2
# poll wave prices the joint slate directly (see apply function).
# 2026-09-02: Smotrich-Feiglin (RZP-Zehut) technical bloc announced
# OFFICIAL — rzp_fate resolved to merge_zehut. 2026-09-03: the
# MERGE_RETENTION transfer is RETIRED — pollsters now publish a single
# "RZP - Zehut" column (Sept 2 wave, 5-6 seats), so the zehut micro-list
# was removed from MICRO_POLLED in bayes_model and the merge branch
# no-ops (no zehut component exists to transfer).
# 2026-09-02 (owner): Balad staying in the Joint List is to be treated
# as certain — balad_splits resolved False.
RESOLVED: dict = {"segalovitz_joins_raam": True,
                  "rzp_fate": "merge_zehut",
                  "balad_splits": False,
                  # 2026-09-04: Erdan announced Unity will not run (Ynet,
                  # Israel Hayom, N12) after the Blue & White merger talks
                  # collapsed the same day; no endorsement given. The fold
                  # vector (Likud .45 / Yashar .25 / YB .10 / ...) applies
                  # in every draw; the Erdan-Gantz union can no longer file.
                  "unity_folds": True,
                  "centre_union_files": False,
                  # FILING DAY 2026-09-08/09 (38 lists filed; CEC approval
                  # Sept 27): Blue and White FILED (Gantz #1, letters כן),
                  # so it does not fold; the Reservists FILED as
                  # "Reservists - Economic Party" (Hendel + Zelekha + Wilf)
                  # after Tropper left for Yashar on Sept 6 - the
                  # zionist_home series continues as that list and does
                  # not fold. Every registration event is now resolved:
                  # the mixture is a single configuration.
                  "zionist_home_folds": False,
                  # 2026-10-08: the disqualification petitions are closed -
                  # the CEC barred Ra'am (18-5-1), the Joint List and Kasif
                  # and rejected the petitions against Otzma, RZP-Zehut and
                  # the Democrats; the Supreme Court unanimously reinstated
                  # Ra'am, the Joint List and Kasif (early Oct); Abu Shahada
                  # withdrew his candidacy (no seat effect). All resolved.
                  "raam_disqualified": False, "joint_list_disqualified": False,
                  "otzma_disqualified": False, "rzp_disqualified": False,
                  "democrats_disqualified": False}
# blue_white_folds is REOPENED (2026-10-08) with a new meaning: Blue and
# White withdrawing before election day. It polls 0.7-1.3% in every
# post-approval filing; opposition leaders are reported to be offering
# Gantz a "withdrawal with honour" (Ch13, Israel Hayom), he is in talks
# with Eisenkot, and his list is also negotiating a surplus pact with
# the Reservists (a signal of staying). A withdrawal routes its voters by
# the measured 2022 pattern (Yashar 0.60 / Together 0.25, rest abstain).
# 2026-10-10 review, vector KEPT: a "late halt, no endorsement" re-spec
# (Yashar .35 / Together .15 / Likud .10) has no voter-level source, and
# Gantz's own framing ("no votes will be wasted", ToI 20 Sept) does not
# imply a larger loss. CAUTION: any change here moves Yashar's mean share
# and with it the GLOBAL trailing-Likud switch in bayes_model.project
# (TRAIL fires on mean shares): on the 10 Oct posterior the half-step
# .45/.20 turns TRAIL off and moves P(NB>=61) 21.7 -> 14.1. Re-check on
# 20 Oct (last pre-blackout polls); collapse via RESOLVED on 23 Oct.
PRIORS["blue_white_folds"] = 0.40
# 2026-10-13: Gantz, publicly, ~2.5 weeks out: "I am not withdrawing -
# whoever says I am burning votes is lying" (Kan live blog,
# https://www.kan.org.il/content/kan-news/politic/live-1107821/); his camp
# told Walla (1 Oct) withdrawal is "not on the table"; Israel Hayom
# (https://www.israelhayom.co.il/news/politics/article/21557821) reports a
# possible exit only in the final days if the threshold is out of reach.
# Lowered to 0.25: a late exit stays live but is no longer the base case.
PRIORS["blue_white_folds"] = 0.25
# 2026-10-19: RESOLVED True. Gantz announced Blue and White's withdrawal
# ("I will not run in the coming elections"), endorsed no candidate and
# called for a unity government (Kan 1110686; mako 02450f13...; Walla
# 383958100). Its voters route by the list's measured 2022 vector (Yashar
# .60 / Together .25, rest abstain): no endorsement, so the vector stands.
RESOLVED["blue_white_folds"] = True
# 2026-10-23: Ahi withdrew (see FOLD_TRANSFER["ahi"]; dossier s.72).
RESOLVED["ahi_folds"] = True


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
    # 2026-09-03: boost RETIRED (set to 0). Four post-announcement polls
    # (fieldwork Sept 2: Lazar, Direct Polls, Maagar, Midgam Project) price
    # the joint Ra'am-Segalovitz slate directly at 4-5 seats; keeping the
    # scenario boost on top would count his voters twice.
    boost = 0.0
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

    # Disqualification petitions (open until the CEC and the Supreme Court
    # rule): the list's column is zeroed and its voters redistributed.
    for pid, (event, dests) in DISQUALIFY_TRANSFER.items():
        src = _col(comps, pid)
        if src is None:
            continue
        on = bern(event)
        for absorber, transfer in dests:
            dst = _col(comps, absorber)
            if dst is None or dst == src:
                continue
            shares[on, dst] += transfer * shares[on, src]
        shares[on, src] = 0.0
        events[event] = on

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
    # Owner ruling 2026-09-09: "without Arab seats" = the opposition lists
    # alone (Segalovitz's Ra'am seat is NOT added); "with Ra'am" = the
    # opposition lists plus Ra'am as a whole.
    anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
    _ri = next((i for i, l in enumerate(labels) if l == "Ra'am"), None)
    raam_seats = seats[:, _ri] if _ri is not None else np.zeros(len(seats))
    anti_raam = anti + raam_seats

    dist = pd.DataFrame({
        "list": labels,
        "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
    }).sort_values("mean", ascending=False)
    dist.to_csv(PROCESSED_DIR / "bayes_forecast_mixture.csv", index=False)
    pd.DataFrame({"list": project.last_labels,
                  "components": project.last_components,
                  "share_mean": np.round(project.last_share_mean, 5),
                  "share_median": np.round(project.last_share_median, 5)}).to_csv(
        PROCESSED_DIR / "mixture_shares.csv", index=False)
    # Feed the formation layer the same mixture draws, so registration
    # events (RZP-Zehut pass/fail, centre folds) flow into coalition math.
    pd.DataFrame(seats, columns=labels).to_parquet(
        PROCESSED_DIR / "mixture_draws.parquet")
    # the share draws behind those seats, row-aligned (market blend, s.71)
    pd.DataFrame(project.last_share_draws, columns=project.last_labels).to_parquet(
        PROCESSED_DIR / "mixture_share_draws.parquet")

    summary = pd.DataFrame([{
        "p_nb_61": round(float((nb >= 61).mean()), 3),
        "p_anti_61": round(float((anti >= 61).mean()), 3),
        "p_anti_raam_61": round(float((anti_raam >= 61).mean()), 3),
        # deadlock counts Ra'am with the change bloc (owner definition)
        "p_neither": round(float(((nb < 61) & (anti_raam < 61)).mean()), 3),
        "nb_mean": round(float(nb.mean()), 1),
        "nb_p05": int(np.percentile(nb, 5)),
        "nb_p95": int(np.percentile(nb, 95)),
    }])
    summary.to_csv(PROCESSED_DIR / "mixture_blocs.csv", index=False)
    # Persist the conditional layers' state from THIS (published) run into
    # fit_summary.json for the site annex: whether the trailing-Likud
    # conditional fired and on what margin, and which lists the
    # new-straddler desertion hit. (bayes_model.main writes the file before
    # its own 'current' projection, so it cannot record the mixture's.)
    import json
    fs = PROCESSED_DIR / "fit_summary.json"
    try:
        fsum = json.loads(fs.read_text())
    except (FileNotFoundError, ValueError):
        fsum = {}
    from bayes_model import TRAIL_SAT_SOURCE
    margin = getattr(project, "last_trail_margin", None)
    fsum.update({
        "trail_on": bool(getattr(project, "last_trail_on", False)),
        "trail_margin_seats": None if margin is None else round(float(margin), 2),
        "trail_source": "satellites" if TRAIL_SAT_SOURCE else "field",
        # trail_ramp (merged 15 Oct, held off; dossier s.46): the layer's
        # weight (mean over draws, 0..1) when bm.TRAIL_RAMP_ON; None under
        # the cliff, where trail_on says whether it fired
        "trail_weight": getattr(project, "last_trail_weight", None),
        "new_straddlers": [labels[i] for i, c in enumerate(project.last_components)
                           if c in set(getattr(project, "last_new_straddlers", []))],
    })
    fs.write_text(json.dumps(fsum, indent=1))

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
