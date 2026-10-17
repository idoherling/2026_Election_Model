"""Retro-validation of the Bayesian model on the eight graded cycles.

Same protocol as validate_model.py graded the simple pipeline with: for each
past election, the state-space model is refit using only that cycle's polls
as of the day before the vote, projected through that cycle's threshold and
(approximate) surplus pairs with LEAVE-ONE-CYCLE-OUT industry shocks, and
graded on 90% interval coverage, threshold Brier, seat MAE, and the stated
bloc-majority probability. Ends with the head-to-head against the simple
pipeline's model_validation.csv.

The projection code deliberately mirrors bayes_model.project() in
validation-parameterized form rather than sharing it — the production path
stays untouched by validation needs.

Outputs:
    data/processed/model_validation_bayes.csv
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import bayes_model as bm
from bayes_model import SEED, T_DF, WITHDRAWN_WEEKS, fit, prepare_data
from error_decomposition import decompose
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
import simulate as _sim
from simulate import THRESHOLD, dhondt
from validate_model import (
    CYCLE_THRESHOLD, ORDER, PAST_PAIRS, REGISTERED_PAIRS, VAL_BLOC_OVERRIDES,
)

warnings.filterwarnings("ignore")

N_PROJ = 4000
WIDTH_GRID = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1]
# the trailing-Likud gate before round three: the 0.5-seat cliff on the
# mean margin, calibrated on the cliff's record
_CLIFF = {"trail_mode": "mean", "trail_lo": 0.5, "trail_wcal": False}
ABLATIONS = [
    ("shipped", {}),
    ("no_resid", {"resid": False}), ("no_swing", {"swing": False}),
    ("no_family", {"family": False}), ("no_gevalt", {"gevalt": False}),
    ("no_loyal", {"loyal": False}),
    ("no_trail", {"gevalt_cond": False}), ("trail_full", {"trail_scale": 1.0}),
    ("no_nstrad", {"new_straddler": False}),
    ("anchors_on", {"anchors": True}),
    ("pair_fix", {"pair_fix": True}), ("pair_alias", {"pair_alias": True}),
    # candidate gone14 (2026-10-10, dossier s.41): withdrawn-list rule at 14
    # days inside the final four weeks; gone_zero keeps dropped lists at
    # zero through the residual shock (the stats/build skeptic fix).
    ("gone14", {"gone_days": 14}), ("gone10", {"gone_days": 10}),
    ("gone_zero", {"gone_zero": True}),
    ("gone14_zero", {"gone_days": 14, "gone_zero": True}),
    # candidate trail_geometry (2026-10-10, dossier s.41). PRIMARY,
    # pre-registered: trail_sat = same draw, same gate, same half strength,
    # sourced from the bloc's own non-haredi satellites (the gevalt
    # coupling's rule mask). The rest are sensitivity runs, not choices.
    # Since the round-three ramp was merged (15 Oct), these arms spell out
    # the cliff they were graded with (_CLIFF), so they keep their meaning
    # whichever gate ALL_LAYERS mirrors.
    ("trail_sat", dict(_CLIFF, trail_source="sat")),
    ("trail_sat_era", dict(_CLIFF, trail_source="era")),
    ("trail_draw_sat", dict(_CLIFF, trail_source="sat", trail_mode="draw")),
    ("trail_draw_sat_full", dict(_CLIFF, trail_source="sat", trail_mode="draw", trail_scale=1.0)),
    ("trail_ramp_sat", dict(_CLIFF, trail_source="sat", trail_mode="ramp", trail_hi=2.0)),
    # 2026-10-13 combine: the ship set together
    ("combined", dict(_CLIFF, pair_fix=True, gone_days=14, gone_zero=True, trail_source="sat")),
    ("latent_only", {k: False for k in ["resid", "swing", "family", "gevalt", "loyal",
                                        "gevalt_cond", "new_straddler"]}),
    # candidate resid_relcap (dossier s.42)
    ("relcap075", {"resid_relcap": 0.75}), ("relcap100", {"resid_relcap": 1.0}),
    ("relcap150", {"resid_relcap": 1.5}),
    # candidate arab_turnout_regime (2026-10-13, dossier s.43): the
    # production turnout mechanism graded against the additive family
    # shock. arab_add_e0 = the raw-e0 additive control; turnA/turnB =
    # production's form (k = 1) on regime tables A/B; _k50/_k25/_kloo =
    # partial pass-through of the expected ratio; regB = the LOO regression
    # (intercept + slope); oracle = realised turnout (diagnostic).
    ("arab_e1_prev", {"arab_mode": None}),   # the pre-15-Oct harness default
    ("arab_add_e0", {"arab_mode": "add_e0"}),
    # 15 Oct: every arm spells out k and the intercept. Once the ALL_LAYERS
    # default became regB (k "loo", intercept on), bare turnA/turnB/_kNN/
    # oracle entries would silently inherit both and stop being the arms
    # s.43 graded (found by the round-three share-space candidate).
    ("arab_turnA", {"arab_mode": "turnout", "arab_regime": "A", "arab_k": 1.0,
                    "arab_intercept": False}),
    ("arab_turnB", {"arab_mode": "turnout", "arab_regime": "B", "arab_k": 1.0,
                    "arab_intercept": False}),
    ("arab_turnA_k50", {"arab_mode": "turnout", "arab_regime": "A", "arab_k": 0.5,
                        "arab_intercept": False}),
    ("arab_turnB_k50", {"arab_mode": "turnout", "arab_regime": "B", "arab_k": 0.5,
                        "arab_intercept": False}),
    ("arab_turnB_k25", {"arab_mode": "turnout", "arab_regime": "B", "arab_k": 0.25,
                        "arab_intercept": False}),
    ("arab_turnB_kloo", {"arab_mode": "turnout", "arab_regime": "B", "arab_k": "loo",
                         "arab_intercept": False}),
    ("arab_regB", {"arab_mode": "turnout", "arab_regime": "B", "arab_k": "loo",
                   "arab_intercept": True}),
    ("arab_oracle", {"arab_mode": "turnout", "arab_T": "oracle", "arab_k": 1.0,
                     "arab_intercept": False}),
    # Latent arms (round three, 2026-10-15, dossier s.46): the projection on
    # another cache's refit of the same window, graded inside the run so
    # *_fixed uses the run's shipped list mask. alr_latent = the pre-round-
    # three additive-log-ratio latent on the ballot-fidelity windows
    # (harness_cache_alr_fidelity) - the comparator on the shipped harness.
    # clr_latent = the round-three arm on the s.43 windows
    # (harness_cache_clr; use with HARNESS_FIDELITY=0 BAYES_CLR=0
    # HARNESS_CACHE_DIR=harness_cache_alr, the legacy ALR cache). An arm
    # whose cache is missing or does not match the window is skipped.
    ("alr_latent", {"posterior": "harness_cache_alr_fidelity"}),
    ("clr_latent", {"posterior": "harness_cache_clr"}),
    # trail_ramp (2026-10-15, dossier s.46). PRE-REGISTERED primary tramp_m
    # (merged, HELD OFF by the fidelity gate G2): weight 1 at margin <= -1.0, 0 at
    # >= +2.0 seats, calibrated with the same weight (w-weighted LOO
    # record). The rest are the round-three sensitivity arms (not shipped).
    ("tramp_m", {"trail_mode": "ramp", "trail_lo": -1.0, "trail_hi": 2.0, "trail_wcal": True}),
    ("tramp_d", {"trail_mode": "ramp_draw", "trail_lo": -1.0, "trail_hi": 2.0, "trail_wcal": True}),
    ("tramp05_m", {"trail_mode": "ramp", "trail_lo": 0.5, "trail_hi": 2.0, "trail_wcal": True}),
    ("tramp05_d", {"trail_mode": "ramp_draw", "trail_lo": 0.5, "trail_hi": 2.0, "trail_wcal": True}),
    ("tramp_m_cliffcal", {"trail_mode": "ramp", "trail_lo": -1.0, "trail_hi": 2.0}),
    # the pre-round-three trail gate (the 0.5-seat cliff on the mean margin)
    ("trail_cliff", dict(_CLIFF)),
    # round-three combine (G1): CLR posterior + the ramp
    ("clr_tramp_m", {"posterior": "harness_cache_clr", "trail_mode": "ramp",
                     "trail_lo": -1.0, "trail_hi": 2.0, "trail_wcal": True}),
    # Sector family terms (2026-10-15, dossier s.51; pre-registered there).
    # hared_e0: haredi family mean = LOO raw (e0) total, e1 sd kept.
    # arab_raam_split: the regB intercept allocated by the lineages' LOO
    # under-count shares (s_raam = 1.0 in every fold on today's record).
    ("hared_e0", {"haredi_mean": "e0"}),
    ("arab_raam_split", {"arab_icpt_alloc": "lineage"}),
    ("sector_both", {"haredi_mean": "e0", "arab_icpt_alloc": "lineage"}),
    # seat_law_fidelity (2026-10-15, dossier s.47). Part A, the instrument
    # (ADOPTED 15 Oct: the harness default, HARNESS_REG_PAIRS=1): the
    # surplus pairs registered with the CEC (validate_model.
    # REGISTERED_PAIRS, resolved through the cycle's DECOMP map); past_pairs
    # = the PAST_PAIRS approximations as the harness ran them before.
    # Part B, the threshold denominator (graded, NOT shipped): s.81(a) tests
    # 3.25% of ALL valid votes, so the draws test sh x (1 - u) and the
    # central count tests the UN-renormalised median (thr_u, central_raw).
    # Pre-registered primary: u = 0.01 with central_raw on the registered
    # pairs (reg_thr). The rest are decompositions/sensitivity: thr_u
    # "oracle" = the window's realised unmodelled CEC share (diagnostic);
    # "loo" = the mean of the other cycles' record.
    ("reg_pairs", {"pairs": "registered"}),
    ("past_pairs", {"pairs": "past"}),
    ("thr_valid", {"pairs": "past", "thr_u": 0.01, "central_raw": True}),
    ("reg_thr", {"pairs": "registered", "thr_u": 0.01, "central_raw": True}),
    ("reg_thr_draws", {"pairs": "registered", "thr_u": 0.01}),
    ("reg_central_raw", {"pairs": "registered", "central_raw": True}),
    ("reg_thr_u005", {"pairs": "registered", "thr_u": 0.005, "central_raw": True}),
    ("reg_thr_loo", {"pairs": "registered", "thr_u": "loo", "central_raw": True}),
    ("reg_thr_oracle", {"pairs": "registered", "thr_u": "oracle", "central_raw": True}),
    # uncertainty calibration (2026-10-15, dossier s.48), at the shipped
    # width; the nested width arms (C0/CA/CAB/CABD) run in calibration_arms.py
    # house-effect centring on operations (2026-10-16, dossier s.53)
    ("house_group", {"house_centre": "operation"}),
    # haredi family mean by each lineage's own record (dossier s.54)
    ("hared_alloc", {"haredi_alloc": "record"}),
    ("cal_A", {"t_unit": True}),
    ("cal_B", {"resid_space": "vote"}),
    ("cal_Bfix", {"resid_space": "seat_fix"}),
    ("cal_AB", {"t_unit": True, "resid_space": "vote"}),
    ("cal_D", {"resid_df": "loo"}),
    # near-threshold calibration (2026-10-17, dossier s.57; pre-registered
    # there): the new-straddler layer with its drift measured on CEC vote
    # shares (the layer-off base is no_nstrad); cal_B above is the second
    # registered arm; nstrad_ran_B = the pair
    ("nstrad_ran", {"nstrad_record": "ran"}),
    ("nstrad_ran_B", {"nstrad_record": "ran", "resid_space": "vote"}),
]
# HORIZON_LAYERS string for the same arms (validate_horizon.py):
ARAB_HORIZON_LAYERS = ";".join(
    f"{n}:{__import__('json').dumps(f)}" for n, f in ABLATIONS if n.startswith("arab_"))
# and for the round-three arms (CLR needs the CLR horizon caches,
# build_harness_cache.py):
CLR_HORIZON_LAYERS = 'clr_latent:{"posterior": "harness_cache_clr"}'
# Quick runs (candidate testing): HARNESS_ABLATIONS=shipped,my_layer limits the
# ablation list by name; HARNESS_SKIP_WIDTH=1 skips the width grid.
import os as _os
if _os.environ.get("HARNESS_ABLATIONS"):
    _keep = set(_os.environ["HARNESS_ABLATIONS"].split(","))
    ABLATIONS = [a for a in ABLATIONS if a[0] in _keep]

# Era-specific alliance identities: which composite each historical id was.
# Applied component-wise before block-building, so pre-merger component
# polls and post-merger joint polls share one entity — the same treatment
# 2026 gets (Together = Bennett + Yesh Atid), without which past windows
# carry phantom lists that poll early, vanish, and get graded as misses.
DECOMP = {
    "2015": {"joint_list": "balad+hadash_taal+raam_taal",
             "zionist_union": "hatnuah+labor"},
    "2019a": {"hosen_telem": "hosen+telem",
              "blue_white": "hosen+telem+yesh_atid",
              "urwp": "jewish_home+national_union",
              "raam_balad": "balad+raam"},
    "2019s": {"hosen_telem": "hosen+telem",
              "blue_white": "hosen+telem+yesh_atid",
              "urwp": "jewish_home+national_union",
              "dem_union": "idp+meretz",
              "labor_gesher": "gesher+labor",
              "raam_balad": "balad+raam"},
    "2020": {"blue_white": "hosen+telem+yesh_atid",
             "dem_union": "idp+meretz",
             "labor_gesher": "gesher+labor",
             "labor_gesher_meretz": "gesher+labor+meretz",
             "yesh_atid_telem": "telem+yesh_atid"},
    "2021": {"labor_meretz": "labor+meretz",
             "otzma_noam": "noam+otzma"},
    "2022": {"otzma_noam": "noam+otzma"},
}


from pathlib import Path as _Path

# ---------------------------------------------------------------------------
# Harness ballot fidelity (candidate harness_ballot_fidelity, 2026-10-15,
# dossier s.46). ON by default since the round-three restatement:
# the historical windows are the ballot each cycle actually had. It changes
# the fitted data, so the shared harness_cache holds fidelity windows
# (CLR-on-fidelity); HARNESS_FIDELITY=0 needs the legacy cache.
#   (1) drop_unfiled: after the filing deadline (+3 days), with the ballot
#       read from the lists polled after the deadline (+2 days, as-of window
#       only), drop (a) composites spanning two ballot lists - 2021 Joint
#       List + Ra'am from five 1-3 Feb polls, 2015 Likud + Yisrael Beytenu,
#       2020 Jewish Home + Otzma - together with the rest of that poll's
#       observation of the blocks they fed (no partial sums), and (b)
#       phantom lists not linked to any ballot list (2019a Joint List, 2019s
#       New Right, 2022 Yamina).
#   (2) DECOMP_FIDELITY: 2021 Yesh Atid-Telem = telem + yesh_atid; 2020
#       Yamina = jewish_home + national_union + new_right and URWP =
#       jewish_home + national_union (the five-party composite then folds).
#   (3) ABSORBED_IDS (Zehut, NEP) are 2026 identities: kept in 2019a/2021,
#       with Zehut's dated withdrawal in September 2019 (WITHDRAWALS).
#   (4) cache safety: each posterior carries its component list,
#       observation count and latent; a mismatch on load is an error, not
#       a silent misalignment (check_signature).
# ---------------------------------------------------------------------------
# Round three (2026-10-15): DEFAULT ON - the grading harness is the
# ballot-fidelity one; HARNESS_FIDELITY=0 reproduces the s.43 windows (the
# legacy ALR cache, harness_cache_alr, is built on those).
FIDELITY = _os.environ.get("HARNESS_FIDELITY", "1") == "1"


def resolve_cache(name) -> _Path:
    """A harness cache: a directory name under data/processed
    (harness_cache_clr) or a path (anything with a separator)."""
    name = str(name)
    if _os.sep in name or "/" in name:
        return _Path(name)
    return PROCESSED_DIR / name


# The shared posterior cache and the latent its posteriors are fitted with.
# Round three (2026-10-15, dossier s.46): the shared cache holds CLR fits;
# the pre-CLR ALR fits are kept as harness_cache_alr. A fit with any other
# latent may never write into the shared cache (harness_cache_dir).
SHARED_CACHE = PROCESSED_DIR / "harness_cache"
SHARED_CACHE_LATENT = "clr"


def current_latent() -> str:
    return "clr" if bm.CLR_LATENT else "alr"


def harness_cache_dir(write: bool = False) -> _Path:
    """Posterior cache of the refit harnesses. HARNESS_CACHE_DIR (a name
    under data/processed, or a path) points a run at a research cache
    (harness_cache_clr, harness_cache_fidelity). write=True refuses a fit
    whose latent differs from the shared cache's into the shared cache."""
    d = resolve_cache(_os.environ.get("HARNESS_CACHE_DIR", "harness_cache"))
    if write and current_latent() != SHARED_CACHE_LATENT and \
            d.resolve() == SHARED_CACHE.resolve():
        raise SystemExit(f"a {current_latent()} refit may not write into the shared "
                         f"{SHARED_CACHE_LATENT} cache {SHARED_CACHE}: set HARNESS_CACHE_DIR "
                         "to a separate cache directory")
    return d


CACHE_DIR = harness_cache_dir()
OUT_DIR = _Path(_os.environ.get("HARNESS_OUT_DIR", str(PROCESSED_DIR)))
FILING_DAYS = 47          # lists are filed on D-47 (Knesset Elections Law s.57(i))
DECOMP_FIDELITY = {
    "2020": {"yamina": "jewish_home+national_union+new_right",
             "urwp": "jewish_home+national_union"},
    "2021": {"yesh_atid_telem": "telem+yesh_atid"},
}
# Post-filing withdrawals: the list stops being on the ballot from this date.
WITHDRAWALS = {"2019s": {"zehut": "2019-08-29"}}   # Feiglin withdrew for Likud


def _decomp_map(cycle: str) -> dict:
    m = dict(DECOMP.get(cycle, {}))
    if FIDELITY:
        m.update(DECOMP_FIDELITY.get(cycle, {}))
    return m


def drop_unfiled(cyc: pd.DataFrame, cycle: str, eday: pd.Timestamp,
                 asof: pd.Timestamp, verbose: bool = True):
    """Ballot fidelity (1): rows of lists not on the ballot, as seen from the
    as-of date. Uses only polls with fieldwork_end <= asof (no look-ahead).
    Returns (frame, dropped ids, n observations removed)."""
    deadline = eday - pd.Timedelta(days=FILING_DAYS)
    win = cyc[cyc["fieldwork_end"] <= asof]
    out = cyc
    dropped_ids: list = []
    for pid, since in WITHDRAWALS.get(cycle, {}).items():
        if asof >= pd.Timestamp(since):
            hit = out["party_id"].str.split("+").map(lambda cs: pid in cs)
            if hit.any():
                dropped_ids.append(f"{pid}(withdrawn {since})")
                out = out[~hit]
                win = win[~win["party_id"].str.split("+").map(lambda cs: pid in cs)]
    if asof < deadline + pd.Timedelta(days=3):
        return out, dropped_ids, 0
    from backtest import merge_blocks
    post = win[win["fieldwork_end"] > deadline + pd.Timedelta(days=2)]
    # ballot entities: the lists polled after the deadline (merged where
    # post-deadline ids themselves overlap)
    ents = merge_blocks(post["party_id"].unique())
    ent_of = {c: i for i, e in enumerate(ents) for c in e}
    ids = list(win["party_id"].unique())
    # (a) straddlers: an id spanning two or more ballot lists is a composite
    # that did not run (2021 Joint List + Ra'am, 2015 Likud + YB, 2020
    # Jewish Home + Otzma, 2021 Labor + Meretz)
    strad = {p for p in ids if len({ent_of[c] for c in p.split("+") if c in ent_of}) >= 2}
    # (b) phantoms: after removing straddlers, a block of ids with no
    # component on the ballot (2019a Joint List, 2019s New Right, 2022
    # Yamina). Pre-merger components linked to a ballot list through a
    # composite poll stay (2021 Otzma/Noam inside RZP, 2020 Democratic
    # Union inside Labor-Gesher-Meretz).
    rest = [p for p in ids if p not in strad]
    blocks = merge_blocks(rest)
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    live = {i for i, b in enumerate(blocks) if b & set(ent_of)}
    multi = [sorted(b) for b in blocks if len({ent_of[c] for c in b if c in ent_of}) >= 2]
    if multi and verbose:
        print(f"[{cycle} asof {asof.date()}] WARNING: blocks spanning two ballot lists: {multi}")
    phantom = {p for p in rest if block_of[p.split("+")[0]] not in live}
    bad = strad | phantom
    if not bad:
        return out, dropped_ids, 0
    # observation-level removal: every row of the same poll that feeds a
    # block a straddler touched goes too (no poll left as a partial sum)
    row_block = out["party_id"].map(lambda p: block_of.get(p.split("+")[0]))
    is_bad = out["party_id"].isin(bad)
    kill = set()
    for r in out[out["party_id"].isin(strad)].itertuples():
        for c in r.party_id.split("+"):
            if c in block_of:
                kill.add((r.poll_id, block_of[c]))
    extra = pd.Series([(pid, b) in kill for pid, b in zip(out["poll_id"], row_block)],
                      index=out.index) & ~is_bad
    n_extra = int(extra.sum())
    dropped_ids += sorted(bad)
    if verbose:
        print(f"[{cycle} asof {asof.date()}] ballot fidelity: straddlers {sorted(strad)}, "
              f"phantoms {sorted(phantom)} ({int(is_bad.sum())} rows) + {n_extra} same-poll "
              f"rows of the blocks the straddlers fed")
    return out[~(is_bad | extra)], dropped_ids, n_extra


def harness_frame(polls: pd.DataFrame, cycle: str, eday: pd.Timestamp,
                  asof: pd.Timestamp, verbose: bool = True) -> pd.DataFrame:
    """The cycle's poll frame for an as-of fit: DECOMP, plus (FIDELITY) the
    ballot-fidelity drops."""
    cyc = apply_decomp(polls[(polls["cycle"] == cycle) & polls["sums_ok"]], cycle)
    if FIDELITY:
        cyc, _, _ = drop_unfiled(cyc, cycle, eday, asof, verbose=verbose)
    return cyc


def harness_prepare(cyc: pd.DataFrame, asof: pd.Timestamp) -> dict:
    data = prepare_data(cyc, asof, modern_remaps=False, drop_absorbed=not FIDELITY)
    cycles = sorted(set(cyc["cycle"].astype(str)))
    if len(cycles) != 1:
        raise ValueError(f"a harness window holds one cycle, got {cycles}")
    data["cycle"] = cycles[0]   # the graded cycle: its leave-one-out scorecard
    return data


# ---------------------------------------------------------------------------
# Leave-one-cycle-out pollster scorecard (2026-10-16, dossier s.50).
# fit() gives each firm a precision prior lam ~ LogNormal(log 1/q^2, 0.20)
# with q from the results-graded scorecard of final-poll errors. The full
# scorecard grades all eight cycles 2009-2022, so a harness refit of cycle c
# had c's own final-poll errors in its prior. Harness fits now use the
# scorecard rebuilt without c (polling_average.quality_map(exclude_cycle)).
# Production 2026 keeps the full scorecard (all eight cycles are its past).
#   HARNESS_SCORECARD=loo   (default) harness fits and caches are LOO
#   HARNESS_SCORECARD=full  the pre-s.50 prior, to grade the legacy caches
# Each posterior load_or_fit writes carries its scorecard ("loo:<cycle>" or
# "full") and check_signature refuses a cache fitted under the other one;
# caches written before s.50 carry none and are "full".
# ---------------------------------------------------------------------------
SCORECARD = _os.environ.get("HARNESS_SCORECARD", "loo")
if SCORECARD not in ("loo", "full"):
    raise SystemExit(f"HARNESS_SCORECARD={SCORECARD!r}: 'loo' or 'full'")


def scorecard_exclude(data: dict) -> str | None:
    """The cycle left out of the lam-prior scorecard for this window's fit."""
    if SCORECARD == "full":
        return None
    if "cycle" not in data:
        raise KeyError("harness data carry no 'cycle' (build them with harness_prepare)")
    return data["cycle"]


def scorecard_tag(data: dict) -> str:
    ex = scorecard_exclude(data)
    return "full" if ex is None else f"loo:{ex}"


def posterior_latent(post) -> str:
    """"clr" for a centred-log-ratio posterior ("zc", weeks x B), "alr" for
    the additive log-ratio one ("z", weeks x B-1)."""
    return "clr" if "zc" in post else "alr"


def check_signature(idata, data: dict, nc, latent: str | None = None) -> None:
    """Cache safety: the cached posterior must be a fit of these data. Caches
    written by load_or_fit carry the component list, observation count and
    latent in attrs; legacy caches are checked on the latent's dimension
    (ALR: B-1 columns of "z"; CLR: B columns of "zc"). latent: the latent
    the caller expects (None = either). The lam-prior scorecard must be the
    run's (HARNESS_SCORECARD; a cache without the attr predates s.50 and was
    fitted on the full scorecard)."""
    post = idata.posterior
    lat = posterior_latent(post)
    B = len(data["components"])
    at = dict(post.attrs)
    want = scorecard_tag(data)
    if at.get("scorecard", "full") != want:
        raise RuntimeError(f"cache {nc}: lam prior fitted on scorecard "
                           f"{at.get('scorecard', 'full (pre-s.50 cache)')}, this run "
                           f"grades with {want} (HARNESS_SCORECARD / HARNESS_CACHE_DIR)")
    if "components" in at:
        if at["components"] != "|".join(data["components"]) or int(at["n_obs"]) != len(data["y"]):
            raise RuntimeError(f"stale cache {nc}: cached {at['components']} n_obs {at['n_obs']} "
                               f"vs data {'|'.join(data['components'])} n_obs {len(data['y'])}")
        if at.get("latent", lat) != lat:
            raise RuntimeError(f"cache {nc}: attrs say {at['latent']}, posterior is {lat}")
    width = post["zc" if lat == "clr" else "z"].shape[-1]
    if width != (B if lat == "clr" else B - 1):
        raise RuntimeError(f"stale cache {nc}: {lat} latent width {width} vs {B} lists")
    if latent is not None and lat != latent:
        raise RuntimeError(f"cache {nc} holds {lat} posteriors; this run fits {latent} "
                           f"(BAYES_CLR / HARNESS_CACHE_DIR)")


def load_or_fit(nc, data: dict, draws: int, tune: int):
    """Cached posterior with a signature check (components, observation count,
    latent, lam-prior scorecard); a missing one is fitted with the current
    latent and the run's scorecard (leave-one-cycle-out by default, s.50)
    and written with its signature (never a non-shared latent into the
    shared cache)."""
    import arviz as az
    import json
    nc = _Path(nc)
    if nc.exists():
        idata = az.from_netcdf(nc)
        check_signature(idata, data, nc, latent=current_latent())
        return idata
    if current_latent() != SHARED_CACHE_LATENT and \
            nc.parent.resolve() == SHARED_CACHE.resolve():
        raise SystemExit(f"a {current_latent()} refit may not write {nc.name} into the "
                         f"shared {SHARED_CACHE_LATENT} cache")
    excl = scorecard_exclude(data)
    _, idata = fit(data, draws=draws, tune=tune, scorecard_exclude=excl)
    q = bm.lam_prior_q(data["firms"], exclude_cycle=excl)
    idata.posterior.attrs.update({"components": "|".join(data["components"]),
                                  "n_obs": int(len(data["y"])),
                                  "latent": current_latent(),
                                  "scorecard": scorecard_tag(data),
                                  "nuts_seed": int(bm.SEED),   # FIT_SEED reseeds
                                  # the q behind each firm's lam prior (audit)
                                  "lam_prior_q": json.dumps(
                                      {f: round(float(v), 3) for f, v in zip(data["firms"], q)})})
    nc.parent.mkdir(parents=True, exist_ok=True)
    az.to_netcdf(idata, nc)
    return idata


_ALT_POST = {}


class StaleArmCache(LookupError):
    """A refit arm's cached posterior is not a fit of this window."""


def alt_posterior(cache_name: str, job: str, data: dict):
    """The posterior of the same cycle/horizon window from another cache (a
    refit arm graded inside the run, so its *_fixed columns use the run's
    shipped list mask; layer 'posterior'). Signature-checked against the
    window's data; its latent may differ from the run's."""
    import arviz as az
    key = (cache_name, job)
    if key not in _ALT_POST:
        nc = resolve_cache(cache_name) / f"{job}.nc"
        if not nc.exists():
            raise FileNotFoundError(f"{nc} missing: fit it with build_harness_cache.py")
        idata = az.from_netcdf(nc)
        try:
            check_signature(idata, data, nc)
        except RuntimeError as e:
            raise StaleArmCache(str(e)) from None
        _ALT_POST.clear()
        _ALT_POST[key] = idata
    return _ALT_POST[key]


def latent_draws(post):
    """(last-week latent, tau) draws as the projection uses them: ALR "z"
    (B-1 columns against a zero reference) or CLR "zc" (all B lists, a tau
    per list). Returns (z_last, tau, is_clr)."""
    clr = "zc" in post
    zname = "zc" if clr else "z"
    z_last = post[zname].values[:, :, -1, :].reshape(-1, post[zname].shape[-1])
    tau = post["tau"].values.reshape(-1, post["tau"].shape[-1])
    return z_last, tau, clr


def apply_decomp(polls: pd.DataFrame, cycle: str) -> pd.DataFrame:
    mapping = _decomp_map(cycle)
    if not mapping:
        return polls
    polls = polls.copy()
    polls["party_id"] = polls["party_id"].map(
        lambda pid: "+".join(sorted({
            part for c in pid.split("+")
            for part in mapping.get(c, c).split("+")})))
    return polls


# seat_law_fidelity part A (dossier s.47): grade with the surplus pairs
# registered with the CEC. ADOPTED 15 Oct as the harness instrument (default
# ON); HARNESS_REG_PAIRS=0 grades with the PAST_PAIRS approximations as the
# harness ran them before (the s.46 baseline).
REG_PAIRS = _os.environ.get("HARNESS_REG_PAIRS", "1") == "1"
# Realised vote share of the lists OUTSIDE each cycle's modelled set (the
# eve window's components), from the CEC final counts
# (data/cec_final_counts.csv; computed and checked by validate_seat_law.py).
# thr_u "oracle" uses the cycle's own value (diagnostic: it is the outcome);
# "loo" the mean of the other seven. (2009/2013 are 2%-era fields with many
# unpolled lists; 3.25%-era mean 0.98%.)
UNMODELLED_REC = {"2009": 0.0219, "2013": 0.0412, "2015": 0.0153, "2019a": 0.008,
                  "2019s": 0.0097, "2020": 0.0038, "2021": 0.0068, "2022": 0.0149}


def unmodelled_u(spec, cycle: str) -> float:
    if spec == "oracle":
        return UNMODELLED_REC[cycle]
    if spec == "loo":
        return float(np.mean([v for c, v in UNMODELLED_REC.items() if c != cycle]))
    return float(spec or 0.0)


# Defaults MIRROR PRODUCTION (bayes_model): anchors retired, the
# trailing-Likud conditional at half strength sourced from the bloc's
# satellites, new-straddler desertion on, the surplus-pair resolver fix,
# the 14-day withdrawn-list rule with dropped lists held at zero
# (2026-10-13 ship set, dossier s.41).
# An ablation turns one layer off (or an alternative on) relative to this.
ALL_LAYERS = {"resid": True, "swing": True, "family": True, "anchors": False,
              "gevalt": True, "loyal": True,
              "anchor_likud": True, "anchor_leader": True, "anchor_scale": 1.0,
              "shock_scale": 1.0,
              # accuracy round four #4: Likud's poll beat conditional on
              # TRAILING (or tying) the largest non-bloc list at the
              # projection date - the successor to the retired fixed anchor
              "gevalt_cond": True, "trail_scale": 0.5,
              # accuracy round four #1: first-cycle lists projected at the
              # threshold band lose votes to strategic desertion (measured on
              # the D-56/D-21 straddler record: 2 of 11 passed, drift -1.6 pp)
              "new_straddler": True,
              # dossier s.40: surplus-pair resolver fix (simulate.
              # PAIR_RESOLVER_FIX); pair_alias also resolves DECOMP-renamed
              # PAST_PAIRS ids
              "pair_fix": True, "pair_alias": False,
              # candidate gone14 (OFF): unpolled-days cutoff that replaces
              # 7 x WITHDRAWN_WEEKS when the projection date is within
              # gone_gate days of the election; gone_zero holds dropped
              # lists at zero (no residual shock resurrects them).
              "gone_days": 14, "gone_gate": 28, "gone_zero": True,
              # candidate trail_geometry (defaults = shipped geometry):
              # source 'field' | 'sat' (NB non-haredi non-Likud rule mask,
              # the gevalt coupling's) | 'era' (hand list, sensitivity only);
              # gate 'mean' (0.5-seat cliff on the mean projection) | 'draw'
              # (same test per pre-shock latent draw) | 'ramp' (weight falls
              # linearly from margin trail_lo to trail_hi seats)
              "trail_source": "sat", "trail_mode": "mean", "trail_hi": 2.0,
              # trail_ramp (2026-10-15, dossier s.46): the ramp's lower end
              # (weight 1 at margin <= trail_lo), mode 'ramp_draw' (the ramp
              # per pre-shock latent draw), and trail_wcal = re-estimate the
              # LOO mu/sd as the w-weighted record under the same ramp
              # (False = the cliff's record). trail_lo 0.5 + 'ramp' is the
              # round-five ramp (trail_ramp_sat).
              # Round three (15 Oct): the ramp tramp_m is merged but HELD
              # OFF in production (bm.TRAIL_RAMP_ON False), so the mirror
              # stays the cliff; the arm tramp_m grades the ramp.
              "trail_lo": 0.5, "trail_wcal": False,
              # candidate resid_relcap (2026-10-13, dossier s.42): cap each
              # list's residual sd at c x its own projected share, so a list
              # polling 0.3% is not given a 1.4 pp additive shock that the
              # zero clip turns into a ~0.7% mean (None = shipped, uncapped)
              "resid_relcap": None,
              # candidate arab_turnout_regime (2026-10-13, dossier s.43).
              # arab_mode None = shipped harness (additive e1 LOO family
              # mean) | "add_e0" (additive RAW-e0 LOO mean, e1 sd) |
              # "turnout" (production's ARAB_TURNOUT branch mirrored: base =
              # the previous election's Arab turnout, T ~ mean + 0.05 x the
              # family's t draw x shock_scale, r = T/base, Arab lists scaled
              # jointly, mass from the rest). arab_regime "A" | "B" picks the
              # LOO regime mean (ARAB_REGIMES); arab_T "oracle" uses the
              # cycle's REALISED turnout (diagnostic only). arab_k: pass-
              # through of the expected ratio (1.0 = production; "loo" = the
              # LOO slope of family e0 on the ratio-implied error);
              # arab_intercept adds that regression's LOO intercept.
              # SHIPPED 15 Oct (s.43): the regression form arab_regB.
              "arab_mode": "turnout", "arab_regime": "B", "arab_T": "regime",
              "arab_k": "loo", "arab_intercept": True,
              # sector family terms (2026-10-15, dossier s.51; shipped =
              # "e0" since 16 Oct / "base"): haredi_mean "e0" = the LOO raw family mean
              # with the e1 sd (hared_e0); arab_icpt_alloc "lineage" = the
              # LOO intercept allocated by the Ra'am / other-Arab lineages'
              # LOO under-count shares, family total kept (arab_raam_split)
              "haredi_mean": "e0", "arab_icpt_alloc": "base",
              # clr_latent (2026-10-15, dossier s.46): None = this run's
              # posterior; a cache (name under data/processed, or a path) =
              # the same window's posterior from that cache (a refit arm)
              "posterior": None,
              # seat_law_fidelity (2026-10-15, dossier s.47). pairs
              # "registered" = REGISTERED_PAIRS[cycle] resolved through the
              # DECOMP map (the harness default since 15 Oct, REG_PAIRS: an
              # instrument change - production has no historical pairs) |
              # "past" = PAST_PAIRS as passed (ids DECOMP renamed are
              # dropped unless pair_alias). thr_u: the unmodelled vote share
              # in the s.81(a) denominator, mirrored from production
              # (simulate.THRESHOLD_ALL_VALID / UNMODELLED_SHARE; OFF); a
              # float, "loo" or "oracle" (UNMODELLED_REC). central_raw: the
              # central count tests the un-renormalised median
              # (official_forecast.allocate_central under the same flag).
              "pairs": "registered" if REG_PAIRS else "past",
              "thr_u": _sim.UNMODELLED_SHARE if _sim.THRESHOLD_ALL_VALID else 0.0,
              "central_raw": bool(_sim.THRESHOLD_ALL_VALID),
              # uncertainty calibration (2026-10-15, dossier s.48), all OFF
              # = shipped. t_unit: every Student-t shock (bloc swing, family
              # t draw incl. the Arab turnout draw) scaled to unit variance,
              # so its sd is the measured one (bm.T_UNIT_VAR). resid_space:
              # the residual line from "seat" (shipped decompose()),
              # "seat_fix" (decompose(index_fix=True)) or "vote"
              # (decompose_vote: vote-share errors of lists that ran), all
              # LOO (bm.RESID_SPACE). resid_df: None = Gaussian residual;
              # "loo" = Student t, sd matched, df from the LOO kurtosis of
              # the record resid_space reads (bm.RESID_T_DF); a number =
              # that df.
              "t_unit": False, "resid_space": "seat", "resid_df": None,
              # house-effect centring (dossier s.53): "firm" = shipped;
              # "operation" = re-centred on operations (bm.HOUSE_CENTRE)
              "house_centre": bm.HOUSE_CENTRE,
              # haredi family mean allocation (dossier s.54): "base" =
              # shipped; "record" = by the lineages' LOO under-count share
              "haredi_alloc": bm.HAREDI_ALLOC,
              # new-straddler record (dossier s.57): "seat" = shipped
              # (model_validation_threshold.csv, seat-implied shares);
              # "ran" = CEC vote shares of the first-cycle straddlers that
              # ran (NSTRAD_RAN_RECORD), LOO (bm.NEW_STRADDLER_RECORD)
              "nstrad_record": bm.NEW_STRADDLER_RECORD}

# Arab-sector turnout by election (share of eligible Arab citizens voting).
# Series as compiled in the dossier (s.4, s.24) and the production comment
# on ARAB_TURNOUT (IDI / Dayan Center figures); 2019a 49.2 / 2019s 59.2
# corroborated by the IDI slide reproduced by the ACI Task Force
# (acitaskforce.org resource-1774-1.pdf). 2022 = 0.538, the kalpi layer's
# own Arab-locality measure (kalpi_sectors.csv, 0.5376) - the value
# production uses as ARAB_TURNOUT["base"] and sector_stream converts with
# (IDI reports 53.2%); one source for both the harness and production.
ARAB_TURNOUT_REC = {"2006": 0.563, "2009": 0.534, "2013": 0.565, "2015": 0.635,
                    "2019a": 0.492, "2019s": 0.592, "2020": 0.648, "2021": 0.446,
                    "2022": 0.538}
# Regime tables. A = production's (a Joint List of ALL Arab parties);
# B = structural (Hadash-Ta'al and Balad on one list, so it adds 2021 - the
# structure 2026 has: the Joint List without Ra'am).
ARAB_REGIMES = {"A": {"2015", "2019s", "2020"},
                "B": {"2015", "2019s", "2020", "2021"}}


def arab_turnout_params(cycle: str) -> dict:
    """Per-cycle inputs of the harness turnout layer, leave-one-cycle-out:
    base (previous election's turnout), realised turnout, the LOO mean of
    realised turnout in the cycle's own regime under tables A and B, and
    the LOO regression of the family's raw error on the error the realised
    turnout ratio implies (e0 = a + k x imp, imp = -(T/base - 1) x polled)."""
    from error_decomposition import _frames
    prev = dict(zip(ORDER, ["2006"] + list(ORDER[:-1])))
    out = {"base": ARAB_TURNOUT_REC[prev[cycle]], "realised": ARAB_TURNOUT_REC[cycle]}
    others = [c for c in ORDER if c != cycle]
    for nm, uni in ARAB_REGIMES.items():
        same = [c for c in others if (c in uni) == (cycle in uni)]
        out["mean_" + nm] = float(np.mean([ARAB_TURNOUT_REC[c] for c in same]))
    fr = _frames()
    e0, imp = [], []
    for c in ORDER:
        # strict leave-one-cycle-out (15 Oct verification): drop every row
        # whose ratio T_c / T_prev(c) reads the graded cycle's turnout
        if c == cycle or prev[c] == cycle or c not in fr:
            continue
        a = fr[c][fr[c]["family"] == "arab"]
        if a.empty:
            continue
        r = ARAB_TURNOUT_REC[c] / ARAB_TURNOUT_REC[prev[c]]
        e0.append(float(a["error"].sum())); imp.append(-(r - 1.0) * float(a["polled"].sum()))
    X = np.c_[np.ones(len(imp)), imp]
    a_, k_ = np.linalg.lstsq(X, np.array(e0), rcond=None)[0]
    out["a_loo"], out["k_loo"] = float(a_), float(k_)
    return out
# Hand-picked right-flank ids per era (sensitivity run only: its case was
# argued from outcomes - it drops Yisrael Beytenu from the 2015 pool).
GEVALT_ERA_IDS = {"jewish_home", "national_union", "otzma", "yachad_yishai",
                  "zehut", "new_right", "urwp", "yamina", "rzp", "noam",
                  "amcha_yisrael"}
NSTRAD_BAND = (-0.75, 1.5)   # pp around the threshold (projected share)


def new_lists_for_cycle(polls: pd.DataFrame, cycle: str) -> set:
    """Component ids first polled in this cycle (no polls in any earlier one)."""
    seen = set()
    for cyc in ORDER:
        if cyc == cycle:
            break
        seen |= set(polls[polls["cycle"] == cyc]["party_id"].str.split("+").explode())
    now = set(polls[polls["cycle"] == cycle]["party_id"].str.split("+").explode())
    return {c for c in now if c not in seen}


# Candidate nstrad_ran (2026-10-17, dossier s.57): the first-cycle
# straddler record on CEC VOTE SHARES. validate_threshold.py with
# HARNESS_FIDELITY=1 and the layer OFF (an explicit layer-off base), on the
# s.50 leave-one-out-scorecard caches, D-56/D-21; the rows new & ran
# (actual = the list's CEC share, data/ran_vote_shares.csv). Non-runners
# (Joint List 2019a, IDP 2019s, the Israelis 2021) are not desertion and
# are left out. (cycle, horizon, list, projected %, CEC %, drift pp)
NSTRAD_RAN_RECORD = [
    ("2009", 56, "greens", 2.395803, 0.37, -2.025803),
    ("2009", 21, "gil", 1.260910, 0.52, -0.740910),
    ("2009", 21, "greens", 1.877859, 0.37, -1.507859),
    ("2013", 21, "am_shalem", 1.841427, 1.20, -0.641427),
    ("2013", 21, "otzma", 1.635630, 1.76, 0.124370),
    ("2019a", 56, "gesher", 3.412323, 1.73, -1.682323),
    ("2019a", 21, "zehut", 3.403746, 2.74, -0.663746),
    ("2021", 56, "nep", 2.741321, 0.79, -1.951321),
    ("2021", 56, "rzp", 3.084791, 5.12, 2.035209),
    ("2021", 21, "raam", 2.909468, 3.79, 0.880532),
]


def new_straddler_params(exclude_cycle: str | None = None, record: str = "seat") -> dict:
    """LOO mean/sd of the realised drift (result - projected share, pp) of
    FIRST-CYCLE lists projected within NSTRAD_BAND at D-56/D-21, from
    model_validation_threshold.csv (validate_threshold.py; record "seat",
    shipped) or from NSTRAD_RAN_RECORD (record "ran", dossier s.57)."""
    if record == "ran":
        x = np.array([r[5] for r in NSTRAD_RAN_RECORD if r[0] != str(exclude_cycle)])
        if len(x) < 3:
            return {"mu": 0.0, "sd": 0.0, "n": int(len(x))}
        return {"mu": float(x.mean()), "sd": float(x.std(ddof=1)), "n": int(len(x))}
    try:
        d = pd.read_csv(PROCESSED_DIR / "model_validation_threshold.csv")
    except FileNotFoundError:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    if "new" not in d.columns:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    d = d[d["new"] & (d["cycle"].astype(str) != str(exclude_cycle))]
    if len(d) < 3:
        return {"mu": 0.0, "sd": 0.0, "n": int(len(d))}
    return {"mu": float(d["drift"].mean()), "sd": float(d["drift"].std(ddof=1)), "n": int(len(d))}
TRAIL_MARGIN = 0.5   # seats: "trailing or tied" = Likud <= leader + margin


def trailing_likud_params(polls: pd.DataFrame, results: pd.DataFrame,
                          exclude_cycle: str | None = None) -> dict:
    """Leave-one-cycle-out measurement of Likud's final-week poll miss in
    cycles where it trailed (or tied) the largest non-Netanyahu-bloc list
    in the final week. Returns {"mu", "sd", "n", "cycles"}."""
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    misses, record = {}, {}
    for cyc in ORDER:
        if cyc == exclude_cycle:
            continue
        eday = pd.Timestamp(ELECTION_DAY[cyc])
        p = polls[(polls["cycle"] == cyc) & (polls["fieldwork_end"] < eday)
                  & (polls["fieldwork_end"] >= eday - pd.Timedelta(days=7))]
        r = results[results["cycle"] == cyc]
        if p.empty or r.empty:
            continue
        bm_c = dict(bloc_map, **VAL_BLOC_OVERRIDES.get(cyc, {}))
        avg = p.groupby("party_id")["seats"].mean()
        lk = [pid for pid in avg.index if "likud" in pid.split("+")]
        if not lk:
            continue
        lk = lk[0]
        others = [pid for pid in avg.index
                  if pid != lk and bm_c.get(pid.split("+")[0], "other") != "netanyahu_bloc"]
        if not others:
            continue
        leader = avg[others].max()
        act = r[r["party_id"] == lk]["seats"]
        if len(act):
            # every non-excluded cycle's (final-week margin, miss): the
            # trail_ramp candidate re-weights the record by its own ramp
            record[cyc] = (float(avg[lk] - leader), float(act.iloc[0]) - float(avg[lk]))
        if avg[lk] <= leader + TRAIL_MARGIN:
            if len(act):
                misses[cyc] = float(act.iloc[0]) - float(avg[lk])
    vals = np.array(list(misses.values()))
    if len(vals) == 0:
        return {"mu": 0.0, "sd": 0.0, "n": 0, "cycles": {}, "record": record}
    return {"mu": float(vals.mean()), "sd": float(vals.std(ddof=1)) if len(vals) > 1 else 3.0,
            "n": int(len(vals)), "cycles": misses, "record": record}


def trail_ramp_weight(margin, lo, hi):
    """Candidate trail_ramp (2026-10-15, dossier s.46): weight 1 at
    margin <= lo seats, 0 at margin >= hi, linear in between (bm.trail_weight)."""
    return bm.trail_weight(margin, lo, hi)


def trail_ramp_params(tp: dict, lo: float, hi: float) -> dict:
    """w-weighted mean/sd of Likud's final-week miss over the (LOO) record,
    w = the same ramp the projection applies, so calibration and
    application agree (a cycle at w=0.5 counts half). sd uses reliability
    weights (V1 - V2/V1 denominator); 3.0 seats when fewer than two
    cycles carry weight, as trailing_likud_params does for n=1."""
    rec = tp.get("record", {})
    if not rec:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    m = np.array([v[0] for v in rec.values()])
    x = np.array([v[1] for v in rec.values()])
    w = trail_ramp_weight(m, lo, hi)
    v1, v2 = w.sum(), (w ** 2).sum()
    if v1 <= 0:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    mu = float((w * x).sum() / v1)
    n_w = int((w > 0).sum())
    sd = float(np.sqrt((w * (x - mu) ** 2).sum() / (v1 - v2 / v1))) if n_w > 1 else 3.0
    return {"mu": mu, "sd": sd, "n": n_w, "n_eff": float(v1 ** 2 / v2)}


def add_calibration_params(params: dict, cycle: str) -> dict:
    """Leave-one-cycle-out inputs of the s.48 calibration layers: the
    residual lines of the unique-label seat record and of the vote-share
    record, and the arm-D tail df of each record."""
    from error_decomposition import decompose as _dec, decompose_vote, seat_tail
    fx = _dec(exclude_cycle=cycle, index_fix=True)
    vt = decompose_vote(exclude_cycle=cycle)
    params["resid_lines"] = {"seat_fix": (fx["resid_base"], fx["resid_slope"]),
                             "vote": (vt["resid_base"], vt["resid_slope"])}
    params["resid_tail"] = {"seat": seat_tail(exclude_cycle=cycle)["df"],
                            "vote": vt["tail"]["df"]}
    return params


def add_threshold_params(params: dict, cycle: str) -> dict:
    """Leave-one-cycle-out inputs of the s.57 near-threshold candidates: the
    new-straddler drift on the CEC-vote-share record (layer nstrad_record)."""
    params["nstrad_ran"] = new_straddler_params(exclude_cycle=cycle, record="ran")
    return params


def allocate_vector(v, threshold, pair_idx, raw: bool = False, u: float = 0.0):
    """Threshold + surplus pairs + d'Hondt (Bader-Ofer) on one share vector.
    raw (seat_law_fidelity, s.47): test the vector as given (a median share
    vector, not additive) x (1 - u) against the threshold instead of
    renormalising it; the division among passers is scale-invariant."""
    v = np.asarray(v, float)
    if raw:
        passed = v * (1.0 - u) >= threshold
    else:
        v = v / np.sum(v)
        passed = v >= threshold
    out = np.zeros(len(v), dtype=int)
    if not passed.any():
        return out
    fvotes, fmembers, used = [], [], set()
    for a, b in pair_idx:
        if passed[a] and passed[b]:
            fvotes.append(v[a] + v[b]); fmembers.append([a, b]); used |= {a, b}
    for j in np.nonzero(passed)[0]:
        if j not in used:
            fvotes.append(v[j]); fmembers.append([int(j)])
    alloc = dhondt(np.array(fvotes), 120)
    for members, k in zip(fmembers, alloc):
        if len(members) == 1:
            out[members[0]] = k
        else:
            a, b = members
            inner = dhondt(np.array([v[a], v[b]]), int(k))
            out[a], out[b] = int(inner[0]), int(inner[1])
    return out


def project_cycle(data, idata, eday, threshold, pairs, params,
                  bloc_overrides, rng, resid_scale=None, layers=None,
                  weeks_override=None):
    if resid_scale is None:
        resid_scale = bm.RESID_SCALE          # production width
    L = dict(ALL_LAYERS, **(layers or {}))
    swing_sd, shocks = params["bloc_sd"], params["family"]
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    bloc_map.update(bloc_overrides or {})

    if L.get("posterior"):
        # a refit arm: the same window's posterior from another cache
        idata = alt_posterior(L["posterior"], project_cycle.job, data)
    post = idata.posterior
    z_last, tau, clr = latent_draws(post)
    take = rng.choice(len(z_last), N_PROJ, replace=True)
    z_last, tau = z_last[take], tau[take]
    weeks = max((eday - data["asof"]).days, 0) / 7.0
    if weeks_override is not None:
        weeks = float(weeks_override)
    # CLR: every list walks forward with its own tau (native, no adapter)
    z_e = z_last + np.sqrt(weeks) * tau * rng.standard_normal(z_last.shape)
    z_f = z_e if clr else np.concatenate([z_e, np.zeros((N_PROJ, 1))], axis=1)
    shares = np.exp(z_f - z_f.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)
    if L["house_centre"] == "operation":   # dossier s.53
        shares = np.clip(shares + bm.house_centre_shift(post, data, take), 0, None)
        shares /= shares.sum(axis=1, keepdims=True)

    # days_ahead from the real dates, never weeks_override (calendar weeks)
    days_ahead = max((eday - data["asof"]).days, 0)
    gone_days = 7 * WITHDRAWN_WEEKS
    if L["gone_days"] is not None and days_ahead <= L["gone_gate"]:
        gone_days = L["gone_days"]
    gone = data["last_obs_day"] < -gone_days
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)
    shares_pre = shares.copy()    # latent draws before any shock (draw gate)
    base0 = shares.mean(axis=0)
    # residual line (dossier s.48): the shipped seat record, its unique-label
    # fix, or the vote-share record of the lists that ran (all LOO)
    r_base, r_slope = params["resid_base"], params["resid_slope"]
    if L["resid_space"] != "seat":
        r_base, r_slope = params["resid_lines"][L["resid_space"]]
    sd_list = (r_base + r_slope * base0 * 120) / 120.0 * resid_scale
    if L["resid_relcap"] is not None:
        sd_list = np.minimum(sd_list, L["resid_relcap"] * base0)
    if L["gone_zero"]:
        sd_list = np.where(gone, 0.0, sd_list)
    if L["resid"]:
        if L["resid_df"] is None:
            eps = rng.standard_normal(shares.shape)
        else:
            # fat-tailed residual, sd matched (dossier s.48, arm D)
            rdf = (params["resid_tail"]["vote" if L["resid_space"] == "vote" else "seat"]
                   if L["resid_df"] == "loo" else float(L["resid_df"]))
            eps = rng.standard_t(rdf, shares.shape) * np.sqrt((rdf - 2.0) / rdf)
        shares = np.clip(shares + eps * sd_list, 0, None)
        shares /= shares.sum(axis=1, keepdims=True)

    comps = [set(c.split("+")) for c in data["components"]]
    blocs = np.array([
        (lambda bs: bs.pop() if len(bs) == 1 else "other")(
            {bloc_map.get(c, "other") for c in cp}) for cp in comps])
    fams = np.array([max([FAMILY_OF.get(c, "other") for c in cp],
                         key=[FAMILY_OF.get(c, "other") for c in cp].count)
                     for cp in comps])

    base = shares.mean(axis=0)
    is_nb = blocs == "netanyahu_bloc"
    # t-scale fix (dossier s.48, arm A): a t(df) draw has sd sqrt(df/(df-2))
    tu = float(np.sqrt((T_DF - 2.0) / T_DF)) if L["t_unit"] else 1.0
    if L["swing"] and is_nb.any() and (~is_nb).any():
        sw = rng.standard_t(T_DF, N_PROJ) * tu * swing_sd * L["shock_scale"] / 120.0
        w_nb, w_op = np.where(is_nb, base, 0), np.where(~is_nb, base, 0)
        shares = shares + sw[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())
    # Family shocks with the kalpi-measured haredi<->arab correlation,
    # mirrored from bayes_model (shared chi-square mixer -> correlated t).
    from bayes_model import KALPI_FAMILY_RHO, GEVALT_SD
    fam_names = [f for f in shocks if (fams == f).any() and not (fams == f).all()]
    rho = KALPI_FAMILY_RHO if len(fam_names) == 2 else 0.0
    cov = np.array([[1.0, rho], [rho, 1.0]]) if rho else np.eye(max(len(fam_names), 1))
    zf = rng.multivariate_normal(np.zeros(len(fam_names)), cov[:len(fam_names), :len(fam_names)],
                                 size=N_PROJ) if fam_names else np.zeros((N_PROJ, 0))
    mixer = np.sqrt(rng.chisquare(T_DF, N_PROJ) / T_DF) / tu   # z / mixer: unit-variance t under t_unit
    project_cycle.last_fams = fams
    for k, f in enumerate(fam_names):
        if not L["family"]:
            break
        mu_f, sd_f = shocks[f]
        in_f = fams == f
        if f == "haredi" and L["haredi_mean"] == "e0":
            mu_f = params["family_e0"]["haredi"][0]   # hared_e0 (s.51): LOO raw mean, e1 sd
        if f == "arab" and L["arab_mode"] == "add_e0":
            mu_f = params["family_e0"]["arab"][0]
        elif f == "arab" and L["arab_mode"] == "turnout":
            # production's ARAB_TURNOUT branch, per-cycle base and LOO mean
            at = params["arab_tab"]
            T_mean = at["realised"] if L["arab_T"] == "oracle" else at["mean_" + L["arab_regime"]]
            kk = at["k_loo"] if L["arab_k"] == "loo" else float(L["arab_k"])
            T = np.clip(T_mean + (zf[:, k] / mixer) * bm.ARAB_TURNOUT["sd"] * L["shock_scale"],
                        0.35, bm.ARAB_TURNOUT["max"])
            r = 1.0 + kk * (T_mean / at["base"] - 1.0) + (T - T_mean) / at["base"]
            tot = shares[:, in_f].sum(axis=1)
            delta = (r - 1.0) * tot
            w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
            if L["arab_intercept"] and L["arab_icpt_alloc"] == "lineage":
                # arab_raam_split (s.51): the LOO intercept's family total,
                # allocated by the LOO lineage under-count share
                a_i = bm.arab_intercept_weights(comps, in_f, base,
                                                params["arab_lineage"]["s_raam"])
                shares = shares + (-at["a_loo"] / 120.0) * (a_i - w_r / w_r.sum())
            elif L["arab_intercept"]:
                delta = delta - at["a_loo"] / 120.0
            shares = shares + delta[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())
            continue
        sk = (-mu_f + (zf[:, k] / mixer) * sd_f * L["shock_scale"]) / 120.0
        w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
        if f == "haredi" and L["haredi_alloc"] == "record":
            # hared_alloc (s.54): mean by the LOO lineage share, random part by base
            h_i = bm.haredi_mean_weights(comps, in_f, base, params["haredi_lineage"]["s_shas"])
            shares = shares + (-mu_f / 120.0) * (h_i - w_r / w_r.sum())
            sk = (zf[:, k] / mixer) * sd_f * L["shock_scale"] / 120.0
        shares = shares + sk[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())
    # Gevalt coupling, mirrored: zero-sum Likud <-> its bloc's non-haredi
    # satellites (the era's right-flank lists), sd GEVALT_SD seats.
    lk = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    sat = np.array([(blocs[i] == "netanyahu_bloc") and (fams[i] != "haredi") and i != lk
                    for i in range(len(comps))])
    if L["gevalt"] and lk is not None and sat.any():
        g = rng.standard_normal(N_PROJ) * GEVALT_SD / 120.0
        w_s = np.where(sat, base, 0)
        shares[:, lk] += g
        shares = shares - g[:, None] * (w_s / w_s.sum())

    # Party anchors (error-space means, negated to shift simulated truth).
    likud_col = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    non_likud = [i for i in range(len(comps)) if i != likud_col]
    leader_col = non_likud[int(np.argmax(base[non_likud]))] if non_likud else None
    for col, mu, on in ((likud_col, params["anchors"]["likud"], L["anchor_likud"]),
                        (leader_col, params["anchors"]["leader"], L["anchor_leader"])):
        if col is None or not L["anchors"] or not on:
            continue
        mu = mu * L["anchor_scale"]
        onehot = np.zeros(len(comps))
        onehot[col] = 1.0
        w_r = np.where(onehot == 0, base, 0)
        shares = shares + (-mu / 120.0) * (onehot - w_r / w_r.sum())

    # New-straddler desertion (accuracy round four #1): first-cycle lists
    # whose projected share sits in the threshold band get the LOO-measured
    # mean drift (negative) with its sd, zero-sum against the field.
    # s.57: nstrad_record "ran" reads the CEC-vote-share record's LOO drift
    ns = params.get("nstrad_ran" if L["nstrad_record"] == "ran" else "nstrad", {})
    if L["nstrad_record"] == "ran" and "nstrad_ran" not in params:
        raise KeyError("layer nstrad_record 'ran' needs params['nstrad_ran'] (add_threshold_params)")
    if L["new_straddler"] and ns.get("n", 0) >= 3 and "new_lists" in params:
        for i, cp in enumerate(comps):
            if not (cp <= params["new_lists"]):
                continue
            rel = base[i] * 100 - threshold * 100
            if NSTRAD_BAND[0] <= rel <= NSTRAD_BAND[1]:
                g = rng.normal(ns["mu"], ns["sd"], N_PROJ) / 100.0
                onehot = np.zeros(len(comps)); onehot[i] = 1.0
                w_r = np.where(onehot == 0, base, 0)
                shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]
        shares = np.clip(shares, 0, None)

    # Trailing-Likud conditional (accuracy round four #4): if Likud's
    # projected standing at the projection date trails or ties the largest
    # non-bloc list, add the LOO-measured miss of trailing years (mean mu,
    # sd over those years), zero-sum against the rest of the field.
    project_cycle.last_trail = {"frac": 0.0, "overflow": None}
    if L["gevalt_cond"] and likud_col is not None and "trail" in params:
        tp = params["trail"]
        if L["trail_wcal"]:
            # trail_ramp: calibrate on the record with the SAME ramp (strict LOO)
            tp = trail_ramp_params(tp, L["trail_lo"], L["trail_hi"])
        project_cycle.last_trail["mu"], project_cycle.last_trail["sd"] = tp["mu"], tp["sd"]
        non_nb = [i for i in range(len(comps)) if blocs[i] != "netanyahu_bloc" and i != likud_col]
        if non_nb and tp["n"] > 0:
            margin = (base[likud_col] - base[non_nb].max()) * 120.0
            project_cycle.last_trail["margin"] = float(margin)
            if L["trail_mode"] == "draw":
                m_d = (shares_pre[:, likud_col] - shares_pre[:, non_nb].max(axis=1)) * 120.0
                gate = (m_d <= TRAIL_MARGIN).astype(float)
            elif L["trail_mode"] == "ramp":
                gate = np.full(N_PROJ, float(trail_ramp_weight(margin, L["trail_lo"], L["trail_hi"])))
            elif L["trail_mode"] == "ramp_draw":
                # per posterior draw, on the pre-shock latent margin
                m_d = (shares_pre[:, likud_col] - shares_pre[:, non_nb].max(axis=1)) * 120.0
                gate = trail_ramp_weight(m_d, L["trail_lo"], L["trail_hi"])
            else:
                gate = np.full(N_PROJ, float(margin <= TRAIL_MARGIN))
            project_cycle.last_trail["frac"] = float(gate.mean())
            if gate.any():
                g = rng.normal(tp["mu"], tp["sd"], N_PROJ) * L["trail_scale"] / 120.0 * gate
                if L["trail_source"] == "sat":
                    src = sat
                elif L["trail_source"] == "era":
                    src = np.array([bool(cp & GEVALT_ERA_IDS) for cp in comps])
                else:
                    src = np.zeros(len(comps), bool)
                if src.any():
                    shares, ov = bm.trail_transfer(shares, g, likud_col, src, base)
                    project_cycle.last_trail["overflow"] = ov
                else:   # shipped geometry: zero-sum against the whole field
                    onehot = np.zeros(len(comps)); onehot[likud_col] = 1.0
                    w_r = np.where(onehot == 0, base, 0)
                    shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]

    # Loyal-electorate calibration, mirrored from bayes_model.LOYAL_SD:
    # standalone captive-base lists are shrunk to their measured total sd.
    from bayes_model import LOYAL_SD
    for pid, tgt in (LOYAL_SD.items() if L["loyal"] else []):
        want = set(pid.split("+"))
        col = next((i for i, cs in enumerate(comps) if cs == want), None)
        if col is None:
            continue
        v = shares[:, col]
        act = v.std() * 120.0
        if act > tgt:
            shares[:, col] = v.mean() + (v - v.mean()) * (tgt / act)
    shares = np.clip(shares, 0, None)
    if L["gone_zero"] and gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
    shares /= shares.sum(axis=1, keepdims=True)

    # Surplus pairs through the shared resolver (dossier s.40). pair_fix:
    # first occurrence wins + a list is never pooled twice in a draw (the
    # production fix; a provable no-op here). pair_alias additionally
    # resolves PAST_PAIRS ids that DECOMP renamed (urwp, blue_white,
    # labor_gesher, ...) - the harness analogue of 'together'.
    # pairs "registered" (seat_law_fidelity part A, s.47; the default): the
    # CEC-registered agreements, always resolved through the DECOMP map so
    # a renamed id (urwp, blue_white, labor_gesher, yamina 2020, ...) is
    # not dropped.
    reg = L["pairs"] == "registered"
    aliases = params.get("pair_alias") if L["pair_alias"] else None
    # the graded cycle: params["cycle"] (set by the three harnesses), else
    # the job tag "<cycle>_eve" / "<cycle>_D<h>"
    cyc = params.get("cycle") or str(project_cycle.job or "").split("_")[0]
    if reg:
        pairs = params.get("registered_pairs") or REGISTERED_PAIRS[cyc]
        aliases = params.get("pair_alias") or _decomp_map(cyc)
    pair_idx, comp_of, dropped = _sim.resolve_pairs(
        pairs, data["components"], aliases=aliases,
        fixed=L["pair_fix"] or L["pair_alias"] or reg)
    project_cycle.last_pairs = {"applied": [(data["components"][a], data["components"][b])
                                            for a, b in pair_idx], "dropped": dropped}
    # threshold denominator (part B, OFF): s.81(a) is 3.25% of ALL valid votes
    u = unmodelled_u(L["thr_u"], cyc)
    # production's central estimator: the seat law applied once to the
    # median share vector (official_forecast.allocate_central): renormalised
    # (shipped) or, central_raw, tested raw against 3.25% of all valid votes
    project_cycle.last_central = allocate_vector(
        np.median(shares, axis=0), threshold, pair_idx,
        raw=bool(L["central_raw"]), u=u if L["central_raw"] else 0.0)
    fixed_pairs = L["pair_fix"] or L["pair_alias"] or reg

    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        sh = shares[i]
        passed = sh * (1.0 - u) >= threshold
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers = _sim.form_factions(pair_idx, passed, votes,
                                              fixed=fixed_pairs)
        alloc = dhondt(np.array(fvotes), 120)
        for members, k in zip(fmembers, alloc):
            if len(members) == 1:
                seats[i, members[0]] = k
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats, blocs, base, comp_of


project_cycle.job = None   # "<cycle>_eve" / "<cycle>_D<h>": set by the harness loops (layer 'posterior')


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    rng = np.random.default_rng(SEED)

    rows, covered_all, list_rows, width_rows, abl_rows = [], [], [], [], []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        asof = eday - pd.Timedelta(days=1)
        cyc = harness_frame(polls, cycle, eday, asof)
        try:
            data = harness_prepare(cyc, asof)
            print(f"[{cycle}] {data['n_polls']} polls, "
                  f"{len(data['latent_blocks'])} lists, "
                  f"{data['n_weeks']} weeks — fitting...")
            idata = load_or_fit(CACHE_DIR / f"{cycle}_eve.nc", data, 600, 600)
            div = int(idata.sample_stats["diverging"].sum())
            params = decompose(exclude_cycle=cycle)
            params["trail"] = trailing_likud_params(polls, results, exclude_cycle=cycle)
            params["new_lists"] = new_lists_for_cycle(polls, cycle)
            params["nstrad"] = new_straddler_params(exclude_cycle=cycle)
            params["pair_alias"] = _decomp_map(cycle)
            params["arab_tab"] = arab_turnout_params(cycle)   # dossier s.43
            params["arab_lineage"] = bm.arab_lineage_share(exclude_cycle=cycle)   # s.51
            params["haredi_lineage"] = bm.haredi_lineage_share(exclude_cycle=cycle)   # s.54
            params["registered_pairs"] = REGISTERED_PAIRS[cycle]   # dossier s.47
            params["cycle"] = cycle
            add_calibration_params(params, cycle)              # dossier s.48
            add_threshold_params(params, cycle)                # dossier s.57
            project_cycle.job = f"{cycle}_eve"   # layer 'posterior' (refit arms)
            print(f"[{cycle}] trailing-Likud LOO: mu {params['trail']['mu']:+.2f} sd {params['trail']['sd']:.2f} n {params['trail']['n']}")
            seats, blocs, base, comp_of = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params,
                VAL_BLOC_OVERRIDES.get(cycle), rng)
        except Exception as e:
            print(f"[{cycle}] FAILED: {e}")
            continue

        res = apply_decomp(results[results["cycle"] == cycle], cycle)
        actual = np.zeros(seats.shape[1])
        unmatched = 0
        for r in res.itertuples():
            hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
            if len(hit) == 1:
                actual[hit.pop()] += r.seats
            else:
                unmatched += r.seats

        # Layer ablation (accuracy round 3, #1): which projection layers
        # help or hurt point accuracy on the graded record.
        # *_fixed columns grade every ablation on the SHIPPED config's list
        # mask, so a layer that moves a list across the 0.5% scoring cutoff
        # (e.g. holding dropped lists at zero) is not graded on a different
        # denominator (harness_compare --fixed).
        fixed = None
        for tag, flags in ABLATIONS:
            try:
                sa, bl_a, ba, _ = project_cycle(
                    data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                    PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                    np.random.default_rng(SEED + 11 + int(_os.environ.get("HARNESS_SEED_OFFSET", 0))),
                    layers=flags)
            except (FileNotFoundError, StaleArmCache) as e:   # a refit arm's cache is missing / stale
                print(f"[{cycle}] ablation {tag} skipped: {e}")
                continue
            act_a = (ba >= 0.005) | (actual > 0)
            if tag == "shipped":
                fixed = act_a
            lo_a, hi_a = np.percentile(sa, 5, axis=0), np.percentile(sa, 95, axis=0)
            ppa = (sa >= 1).mean(axis=0)
            isc_a = (hi_a - lo_a) + 20 * np.maximum(lo_a - actual, 0) + 20 * np.maximum(actual - hi_a, 0)
            ar_a = project_cycle.last_fams == "arab"
            cen_a = project_cycle.last_central   # the official central count's estimator
            nb_a = bl_a == "netanyahu_bloc"   # this arm's bloc labels
            row = {"cycle": cycle, "ablation": tag,
                   "n_pairs": len(project_cycle.last_pairs["applied"]),
                   # trailing-Likud gate weight (mean over draws) of this arm
                   "trail_frac": float(project_cycle.last_trail.get("frac", 0.0)),
                   # bloc Brier input (dossier s.48): P(NB >= 61) and the outcome
                   "p_nb61": float((sa[:, nb_a].sum(axis=1) >= 61).mean()),
                   "nb_actual": int(actual[nb_a].sum()),
                   # Arab family: mean projected seats - actual (dossier s.43)
                   "arab_fam_err": float(sa[:, ar_a].sum(axis=1).mean() - actual[ar_a].sum())
                   if ar_a.any() else np.nan}
            for sfx, m in (("", act_a), ("_fixed", fixed if fixed is not None else act_a)):
                row.update({"seat_mae" + sfx: float(np.abs(sa.mean(axis=0) - actual)[m].mean()),
                            "seat_mae_median" + sfx: float(np.abs(np.median(sa, axis=0) - actual)[m].mean()),
                            "coverage_90" + sfx: float(((actual >= lo_a) & (actual <= hi_a))[m].mean()),
                            "threshold_brier" + sfx: float(np.mean((ppa[m] - (actual[m] > 0)) ** 2)),
                            "interval_score" + sfx: float(isc_a[m].mean()),
                            # s.47: the published central count's estimator
                            "seat_mae_central" + sfx: float(np.abs(cen_a - actual)[m].mean())})
            abl_rows.append(row)

        # Interval-width calibration curve (audit improvement #2): the same
        # posterior re-projected under a grid of residual-width factors.
        for w in ([] if _os.environ.get("HARNESS_SKIP_WIDTH") else WIDTH_GRID):
            sw, _, bw, _ = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                np.random.default_rng(SEED + 7), resid_scale=w)
            act_w = (bw >= 0.005) | (actual > 0)
            lo_w, hi_w = np.percentile(sw, 5, axis=0), np.percentile(sw, 95, axis=0)
            pp = (sw >= 1).mean(axis=0)
            a = 0.10   # interval score (Gneiting-Raftery): width + miss penalties
            isc = (hi_w - lo_w) + (2/a) * np.maximum(lo_w - actual, 0) + (2/a) * np.maximum(actual - hi_w, 0)
            width_rows.append({"cycle": cycle, "width": w,
                               "coverage_90": float(((actual >= lo_w) & (actual <= hi_w))[act_w].mean()),
                               "seat_mae": float(np.abs(sw.mean(axis=0) - actual)[act_w].mean()),
                               "threshold_brier": float(np.mean((pp[act_w] - (actual[act_w] > 0)) ** 2)),
                               "interval_score": float(isc[act_w].mean())})

        pred_mean = seats.mean(axis=0)
        p05 = np.percentile(seats, 5, axis=0)
        p95 = np.percentile(seats, 95, axis=0)
        active = (base >= 0.005) | (actual > 0)
        cov = ((actual >= p05) & (actual <= p95))[active]
        p_pass = (seats >= 1).mean(axis=0)
        brier = float(np.mean((p_pass[active] - (actual[active] > 0)) ** 2))
        mae = float(np.abs(pred_mean - actual)[active].mean())
        nb_mask = blocs == "netanyahu_bloc"
        nb_sim = seats[:, nb_mask].sum(axis=1)
        nb_actual = int(actual[nb_mask].sum())
        for i in np.nonzero(active)[0]:
            list_rows.append({"cycle": cycle,
                              "components": data["components"][i]
                              if i < len(data["components"]) else "micro",
                              "pred": float(pred_mean[i]),
                              "actual": int(actual[i]),
                              # per-list calibration record (site's track-record
                              # section: reliability diagram, coverage by size)
                              "pred_median": float(np.median(seats[:, i])),
                              "p05": float(p05[i]), "p95": float(p95[i]),
                              "p_pass": float(p_pass[i]),
                              "share_base": float(base[i])})
        rows.append({
            "cycle": cycle, "n_lists": int(active.sum()),
            "coverage_90": round(float(cov.mean()), 2),
            "threshold_brier": round(brier, 3),
            "seat_mae": round(mae, 2),
            "p_bloc_61": round(float((nb_sim >= 61).mean()), 3),
            "bloc_actual": nb_actual,
            "bloc_61_happened": nb_actual >= 61,
            "divergences": div, "unmatched_actual_seats": unmatched,
        })
        covered_all.append(cov)
        print(f"[{cycle}] coverage {rows[-1]['coverage_90']:.0%} | "
              f"MAE {rows[-1]['seat_mae']} | brier "
              f"{rows[-1]['threshold_brier']} | P(bloc61) "
              f"{rows[-1]['p_bloc_61']:.1%} (actual {nb_actual})")

    if len(rows) != len(ORDER):
        # a cycle that failed (e.g. a stale cache) must not silently leave
        # the pooled score (ballot-fidelity cache safety)
        print(f"WARNING: only {len(rows)} of {len(ORDER)} cycles scored")
        if FIDELITY:
            raise SystemExit(f"only {len(rows)} of {len(ORDER)} cycles scored")
    out = pd.DataFrame(rows).set_index("cycle")
    out.to_csv(OUT_DIR / "model_validation_bayes.csv")
    pd.DataFrame(list_rows).to_csv(
        OUT_DIR / "model_validation_bayes_lists.csv", index=False)
    pooled = np.concatenate(covered_all)
    p61, hap = out["p_bloc_61"], out["bloc_61_happened"].astype(float)
    print("\n== BAYESIAN MODEL, eight-cycle grade ==")
    print(out.to_string())
    print(f"\npooled 90% coverage: {pooled.mean():.1%} "
          f"({int(pooled.sum())}/{len(pooled)})")
    print(f"bloc Brier {((p61 - hap) ** 2).mean():.3f} "
          f"(mean stated {p61.mean():.1%}, realized {hap.mean():.1%})")
    print(f"pooled seat MAE {out['seat_mae'].mean():.2f}")

    try:
        simple = pd.read_csv(PROCESSED_DIR / "model_validation.csv",
                             index_col=0)
        both = pd.DataFrame({
            "mae_bayes": out["seat_mae"], "mae_simple": simple["seat_mae"],
            "cov_bayes": out["coverage_90"], "cov_simple": simple["coverage_90"],
            "brier_bayes": out["threshold_brier"],
            "brier_simple": simple["threshold_brier"],
        })
        print("\n== HEAD-TO-HEAD vs simple pipeline ==")
        print(both.to_string())
        print(f"\npooled MAE: bayes {both['mae_bayes'].mean():.2f} vs "
              f"simple {both['mae_simple'].mean():.2f} | "
              f"threshold Brier: bayes {both['brier_bayes'].mean():.3f} vs "
              f"simple {both['brier_simple'].mean():.3f}")
    except FileNotFoundError:
        pass
    if abl_rows:
        adf = pd.DataFrame(abl_rows)
        adf.to_csv(OUT_DIR / "model_validation_ablation.csv", index=False)
        print("\nLayer ablation (pooled over cycles):")
        tab = adf.groupby("ablation").agg(mae=("seat_mae", "mean"), mae_med=("seat_mae_median", "mean"),
                                          coverage=("coverage_90", "mean"), brier=("threshold_brier", "mean"),
                                          cycles=("cycle", "nunique"))
        # an arm scored in fewer cycles than the shipped run is not comparable
        # in a pooled table (a refit arm whose cache is missing for some cycles
        # is skipped per cycle): drop it and say so (round-three critic, s.46)
        full = int(tab["cycles"].max()) if len(tab) else 0
        partial = tab[tab["cycles"] < full]
        if len(partial):
            print("  arms scored in fewer than %d cycles, left out of this table: %s"
                  % (full, ", ".join(f"{a} ({int(n)})" for a, n in partial["cycles"].items())))
        print(tab[tab["cycles"] == full].reindex([t for t, _ in ABLATIONS]).dropna(how="all")
              .round(3).to_string())   # skipped arms drop out
    if width_rows:
        wdf = pd.DataFrame(width_rows)
        wdf.to_csv(OUT_DIR / "model_validation_width.csv", index=False)
        pooled = wdf.groupby("width").agg(coverage=("coverage_90", "mean"), mae=("seat_mae", "mean"),
                                          brier=("threshold_brier", "mean"), iscore=("interval_score", "mean"))
        print("\nInterval-width calibration (pooled over cycles):")
        print(pooled.round(3).to_string())
        loo = []
        for cyc in wdf["cycle"].unique():
            other = wdf[wdf["cycle"] != cyc].groupby("width")["interval_score"].mean()
            loo.append((cyc, float(other.idxmin())))
        print("LOO width choices:", loo)
        print(f"pooled choice (min interval score): {pooled['iscore'].idxmin()}")
    print("\nwrote model_validation_bayes.csv")


if __name__ == "__main__":
    main()
