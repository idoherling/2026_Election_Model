"""Full Bayesian forecast: latent-trend state-space model over the poll data.

The model (Jackman/Linzer lineage, adapted to Israel):

  latent   z_w  (weeks x lists-1, additive-log-ratio space)
           z_w = z_{w-1} + tau_b * eps_w          random-walk trend,
                                                  innovation ESTIMATED
  house    delta_{f,b} ~ N(gamma_{g(f),b}, sigma_f)   firm effects nested in
           gamma_{g,b} ~ N(0, sigma_g)                correlation groups
  obs      y_{p,b} ~ StudentT(4, softmax(z_{w(p)})_b + delta_{f(p),b}, s_b)
                                                  fat-tailed, noise ESTIMATED

This replaces the weighted average, trendline adjustment, house-effect
shrinkage, and the days-remaining scale in one joint posterior: forecast
uncertainty is the random walk run forward to election day. What polls can
NEVER identify — how wrong the whole industry is together — enters at
projection with the backtest-calibrated industry shocks (bloc swing, Arab
and haredi family errors), exactly as in the simple model.

Micro-lists that no pollster carries as a column (Zehut, Noam, NEP, and any
polled-at-zero list) join at projection from historical priors, so the
forecast covers the entire registered party space.

Ra'am is modeled separately from the Joint List throughout; the few polls
that merged them into one composite are excluded.

Workflow: prior predictive sanity -> NUTS -> convergence diagnostics ->
posterior predictive coverage -> 14-day holdout check -> projection through
threshold + Bader-Ofer -> comparison against the simple model.

Outputs:
    data/processed/bayes_forecast_2026.csv    per-list seat distribution
    data/processed/bayes_forecast_blocs.csv   bloc probabilities
    data/processed/bayes_draws.parquet        election-day seat draws
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from backtest import merge_blocks, short_name
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from polling_average import ELECTION_DAY_2026, load_2026
from scrape_polls import PROCESSED_DIR
from simulate import BLOC_LABEL, SURPLUS_PAIRS, THRESHOLD, dhondt

warnings.filterwarnings("ignore")

WINDOW_DAYS = 240
HOLDOUT_DAYS = 14
# Non-uniform latent grid: weekly bins through the campaign, finer bins in
# the final stretch — Israeli campaigns break late, and the harness showed a
# weekly latent smooths away final-week movement the simple average catches.
FINE_DAYS = 28
FINE_STEP = 2


def time_grid():
    """Bin edges in days-relative-to-asof, and per-step dt in week units."""
    edges = list(range(-WINDOW_DAYS, -FINE_DAYS, 7)) \
        + list(range(-FINE_DAYS, 1, FINE_STEP))
    if edges[-1] != 0:
        edges.append(0)
    edges = np.array(edges, dtype=float)
    mids = (edges[:-1] + edges[1:]) / 2.0
    dt_weeks = np.diff(mids) / 7.0
    return edges, dt_weeks
N_PROJ = 8_000          # posterior projection draws
# Forward event-risk multiplier on the bloc swing (Aug 30 macro sweep):
# two incumbent-controlled escalation dials (Lebanon, Turkey/Syria), a
# sanctions "D-Day", trial resumption Sept 8, ~30% undecided among
# first-time voters, and an unprecedented count of threshold-straddling
# lists. Forward-looking judgment, NOT applied in the historical harness
# (validate_bayes has its own projection where election-eve scale is 1).
EVENT_RISK = 1.2
SEED = 20261027
T_DF = 5

# First-cycle de-novo lists carry wider final-poll error: measured on the
# own 9-cycle DB, new-list final-30d sd 2.83 vs 2.14 established (D-60
# window: 3.98 vs 2.93) -> ~1.35x. Mean fade is NOT significant (+0.1
# final / +1.1 D-60, two-sided tails: New Right +7.4 over-polled but
# Yesh Atid 2013 -7.9 UNDER-polled), so variance only, no drift.
NEW_LIST_MULT = 1.35
NEW_LIST_IDS = {"yashar", "amcha_yisrael", "zionist_home", "unity"}

# Vote-certainty layer (2026-09-01 desk; measured, not judgment):
# - Together is the softest major list (47% of its voters locked per the
#   JPPI/Midgam certainty series; ten consecutive weekly seat losses to
#   Yashar) -> widen its residual shock.
SOFT_LIST_MULT = {}   # retired 2026-09-03: the certainty layer carries soft-list risk
# - Within-bloc churn in the change bloc measures ~3x the Netanyahu
#   bloc's (Midgam Jul 27: 4.0% vs 1.3% of the electorate wavering
#   within-bloc). Zero-sum exchanges keep the bloc total stable while
#   the parts move - historically bloc error < sum-of-parts implies
#   exactly this covariance.
CENTRE_CHURN = [("yashar", "bennett_2026", 1.5),
                ("yashar", "democrats", 0.8)]
# - Amcha fade: the right-flank leader-vehicle reference class (Jewish
#   Home '13/'15, New Right '19a, Yamina '19s/'20/'21) over-polled at
#   D-60 by +4.2 seats on average, 5 of 6 cycles positive (the gevalt
#   squeeze); Winter's list is the softest on the board (38% locked,
#   40% of his base unattached a month ago). Scaled to his ~4-seat
#   size: -1.5 seats, returned to his measured sources (N12 Aug 27:
#   30% Likud / 15% RZ / 15% Otzma of inflow).
AMCHA_FADE = 1.5
AMCHA_FADE_TO = {"likud": 0.5, "otzma": 0.25, "rzp": 0.25}

# Gevalt coupling: Likud's final-days surges are paid by its own bloc's
# satellites, near 1:1 (2015: Likud +8.4 final-poll beat, Jewish Home -4,
# Yachad dead; 2019a: Likud +6.7, New Right/Zehut dead). The Likud anchor
# carries the MEAN of this record; this term adds the negative
# correlation, so satellite threshold deaths co-occur with Likud surges.
GEVALT_SD = 2.0            # seats, zero-sum Likud <-> NB satellites
GEVALT_SAT_IDS = {"otzma", "rzp", "amcha_yisrael", "zehut", "noam"}

# Loyal-electorate volatility calibration (2026-09-01 audit). The pooled
# per-list shock is right on average but wrong for sect-based veteran
# lists with captive electorates: measured D-60 -> result error sd over
# 7 cycles is Shas 0.92 (worst downside ever -0.4: it BEAT its polls
# every cycle), UTJ 0.74 (worst +1.3), YB-standalone 1.71 (worst +1.2)
# - yet the pooled machinery gave them total sd ~3.3 and 6-9%
# sub-threshold probability for events that have never happened.
# After all shocks, each list below is shrunk around its own center to
# the target TOTAL sd (measured lineage history x a 1.35-1.5 novelty
# buffer; the record already contains filing-day structural resolutions,
# since historical D-60 windows sat near list-closure dates just as
# 2026's does). Applied only on an exact component-set match, so a
# joint list outside its lineage (e.g. Likud-Beytenu 2013) keeps the
# pooled width. Audited 2026-09-01; full table in docs/priors_dossier.md
# section 7. Lists NOT here were checked and left at pooled width:
# Democrats (lineage sd includes the two-list threshold deaths the
# merger removed), Together (within buffer), Otzma/RZP (match), Ra'am
# (n=2, turnout risk real), new lists (NEW_LIST_MULT owns them).
# Kalpi layer (src/kalpi_model.py): the haredi<->arab family tides
# measured +0.92 correlated over the 2019-2022 locality panel; shrunk
# to 0.5 for n=4 transitions before use in the projection.
KALPI_FAMILY_RHO = 0.5

# Kalpi capacity constraints - administrative-data truncation of the
# posterior's physically impossible tails (audited 2026-09-01: each
# clipped ~1.5% of draws). Arab lists cannot jointly exceed what the
# Arab sector can cast: 839k eligible x 72% max turnout (max observed
# 64.8% + buffer) / 78% measured locality concentration ~= 16.3% of the
# vote. Shas+UTJ jointly cannot fall below the haredi demographic floor:
# 304k sector eligible x 74% turnout / 55% own-sector vote share, with
# a 0.8 leakage buffer ~= 6.7%.
KALPI_ARAB_CAP = 0.163      # joint arab-family share ceiling
KALPI_HAREDI_FLOOR = 0.066  # joint Shas+UTJ share floor

# ---- Measured undecided-allocation layer (2026-09-01, improvement #3) --
# Published seat polls already allocate undecideds by each house's opaque
# method (~proportionally). The 2026-measured break is NOT proportional:
# N12/Midgam Jul 30 (n=505): pool 12% of the electorate; 55% will vote
# "a candidate who is not Netanyahu", 16% Netanyahu, 29% true tossup.
# GIQ panel research: the unsophisticated half of undecideds under-votes
# -> 0.65 turnout haircut on the pool. Excess net anti-ward allocation
# vs proportional (decided split ~52/48): leaned 71% of pool breaking
# 77/23 minus proportional -> ~+35% of the voting pool. Raw effect
# ~2.7 seats anti-ward. NET_DISCOUNT 0.5: the decomposition's anchors
# already embed the HISTORICAL late-break (which favored Likud - the
# 2026 measurement is a sign reversal, which is exactly why it is
# cycle-specific information), but partial overlap cannot be excluded,
# so only half the measured excess is applied. Drawn with sd equal to
# the mean - the layer widens honesty as much as it shifts the center.
# Applied netanyahu_bloc <-> opposition_bloc only (the instrument
# sampled the Jewish electorate's Netanyahu question; Arab lists' own
# undecided dynamics live in the arab family shock/turnout dial).
# Harness-inactive by construction (inputs are 2026 measurements);
# revisit after Sept 9 - JPPI shows the pool shrinking ~2pp/month.
U_POOL = 0.12          # comparable CEC filings cluster at 10-16% (Lazar 12-16,
                       # Midgam Project/StatNet 12.3, Maagar 10); Kantar's
                       # 24-41% includes non-voters and is a different question
U_TURNOUT = 0.65
U_EXCESS_ANTI = 0.35
U_NET_DISCOUNT = 0.5
UNDECIDED_BREAK_SEATS = (U_POOL * U_TURNOUT * U_EXCESS_ANTI
                         * 120 * U_NET_DISCOUNT)   # ~1.6 seats, mean of the lean piece
# The N12 55/16 lean rests on ~60 respondents: carried as Beta(46.5, 13.5)
# on the anti share of the leaned pool (mean 0.775), against the ~0.52
# proportional baseline, times a LogNormal magnitude term for the turnout
# haircut and discount that the point estimate hides.
U_LEAN_BETA = (46.5, 13.5)
U_LEAN_BASE = 0.775
U_PROP_ANTI = 0.52
U_MAG_SDLOG = 0.5

# ---- Certainty layer (2026-09-03, improvement #1 of the Fable audit) ----
# Share of each list's current supporters who say they are certain to
# vote for it. Two entries are MEASURED (M) from the JPPI/Midgam certainty
# series and the N12 Winter panel; the rest are DECLARED tiers (J): sect-
# based veterans whose D-60 error record is tiny (Shas/UTJ have never
# missed downward by more than half a seat; see LOYAL_SD) sit high; new
# leader-vehicles and threshold-straddling centre micro-lists sit low.
# To be replaced list by list as certainty waves are published post
# Sept 9. Harness-inactive (inputs are 2026 measurements).
CERTAINTY = {
    "bennett_2026": 0.47,    # M  JPPI/Midgam: 47% locked, Aug 2026
    "yesh_atid": 0.47,       # M  (component of the same list)
    "amcha_yisrael": 0.38,   # M  Midgam/N12: 38% locked, 40% unattached
    "shas": 0.88, "utj": 0.90,                     # J  captive electorates
    "yisrael_beytenu": 0.80,                       # J  measured sd 1.7 class
    "balad": 0.75, "hadash_taal": 0.75, "raam": 0.70,  # J  turnout, not switching
    "likud": 0.78,           # J  N12 Likudnikim panel: high loyalty, some drift
    "otzma": 0.72, "rzp": 0.68, "zehut": 0.68,     # J  merged/right-flank lists
    "yashar": 0.65, "democrats": 0.70,             # J  new leader vehicle / merged left
    "zionist_home": 0.40, "blue_white": 0.40, "unity": 0.40,  # J  threshold-straddlers
}
CERTAINTY_DEFAULT = 0.50
# Soft supporters (1 - certainty) defect at rate d by election day:
# d ~ Beta(mean 0.25, sd 0.12), JUDGMENT anchored on INES panel switching
# (roughly a quarter to a third of Israeli voters change intention across
# a campaign, concentrated among the uncertain), with a per-list
# idiosyncratic LogNormal(0, 0.35) multiplier so soft lists carry
# asymmetric downside rather than a uniform haircut.
CHURN_D_MEAN, CHURN_D_SD = 0.25, 0.12
CHURN_LIST_SDLOG = 0.35
# Where churn goes. MEASURED: the change bloc's within-bloc wavering is
# ~3x the Netanyahu bloc's (Midgam Jul 27: 4.0% vs 1.3% of the
# electorate) - that asymmetry enters through CERTAINTY. The split of
# movers is DECLARED (J), anchored on the historical record that bloc
# error is smaller than the sum of its parts (movement is mostly within
# bloc): 0.75 within / 0.10 cross / 0.15 abstain. Arab-family churn
# stays in-family (different instrument).
CHURN_WITHIN, CHURN_CROSS, CHURN_ABSTAIN = 0.75, 0.10, 0.15
# Inflow (churn and undecideds) lands in proportion to certainty-weighted
# support: firm lists attract, soft lists do not.
AMCHA_FADE_TOTAL = 1.5   # the reference-class mean; the certainty layer's
                         # expected Amcha loss counts toward it (no double shift)

# ---- Campaign volatility calendar (2026-09-01, improvement #4) --------
# Measured from the own DB (7 cycles, RMS weekly movement of party
# averages by days-to-election): the list-formation window D-36..77
# moves ~1.3-1.5 seats/week; the final five weeks move ~0.6-0.75
# (a measurement that already includes holiday-freeze cycles); early
# campaign ~1.2. Weights are relative to the all-window mean (~1.04),
# so the fitted tau's overall scale is preserved - only the SHAPE of
# forward uncertainty changes. Effect: roughly neutral at today's
# horizon (spike+calm integrate to ~the uniform total), but after the
# Sept 9 filing the remaining path is all calm-zone and forward
# intervals tighten ~25% automatically, as they should.
# Herding was measured (final-window dispersion 0.88x mid-campaign,
# 0.6-0.9x sampling noise) and deliberately NOT added: the
# decomposition's election-day shocks are fitted on final-poll errors
# that already contain historical herding - adding it would
# double-count. Recorded in the dossier.
def campaign_vol_weight(dte: float) -> float:
    if dte <= 35:
        return 0.64
    if dte <= 77:
        return 1.25
    return 1.13

LOYAL_SD = {
    "shas": 1.5,             # measured 0.92, worst downside ever -0.4
    "utj": 1.3,              # measured 0.74
    "yisrael_beytenu": 2.2,  # measured 1.71 standalone
    "likud": 4.8,            # measured 3.53 x 1.35
    "balad+hadash_taal": 3.1,  # measured 2.30 x 1.35
    # Analog lineage (owner's reference-class suggestion): Blue & White
    # in its prime is Yashar's sociological twin - a new general-led
    # security-centrist mega-list. B&W D-60 errs -4.1/+1.6/-4.4
    # (sd 2.76, mean -2.3: UNDER-polled - the upside mean is already
    # carried by the leader anchor). 2.76 x 1.5:
    "yashar": 4.2,
}

# All election-day shocks come from the sequential decomposition of the
# eight-cycle error record (error_decomposition.py), so no component is
# double-counted. Means are in ERROR space (polled - actual): the projection
# applies the NEGATED mean, since simulated truth = polled - error.
from error_decomposition import decompose as _decompose

_P = _decompose()
BLOC_SWING_SD = _P["bloc_sd"]
FAMILY_SHOCK = _P["family"]        # {family: (error mean, sd)} in seats
ANCHORS = _P["anchors"]            # {"likud": .., "leader": ..} error means
LIST_SHOCK_BASE = _P["resid_base"]
LIST_SHOCK_SLOPE = _P["resid_slope"]
# A list with no polls in its final weeks has left the race by election day.
WITHDRAWN_WEEKS = 5

# Small-party layer, two measured pieces:
#
# 1. MICRO_POLLED — what pollsters measure today, from the footnote
#    itemizations of the firms publishing full percentages (Jul-Aug 2026,
#    Lazar/Midgam/Filber/Direct Polls/Maagar).
MICRO_POLLED = {
    # zehut RETIRED 2026-09-03: pollsters now publish a single "RZP - Zehut"
    # column (Sept 2 wave), so its support lives inside the rzp poll stream;
    # carving it separately would count Zehut's voters twice.
    "noam": (0.004, 0.003),            # 0.3% Filber 27 Aug; "<1%" elsewhere
    "nep": (0.013, 0.004),             # 1.0-1.7%, Aug 2026
    "haredi_public": (0.013, 0.004),   # 1.2-1.5% Jul-Aug (Midgam 31 Aug: 1.2%)
    "israel_first": (0.004, 0.003),    # 0.3-0.6% Aug 2026 (Lazar/Direct Polls)
    # Standing Together's list (Daoud/Green): Afkar Sept 2026 Arab-sector
    # poll has it at 7% of the sector, which is 0.7-1.3% of the national
    # vote depending on the turnout basis (their 60% assumption vs our
    # measured 54%); its Jewish support is unmeasured, so the sd is wide.
    "makom_lekulanu": (0.010, 0.006),
    # fiery_youth REMOVED (owner ruling, Sept 1): not running — Muchtar
    # is leading Likud's youth campaign.
    "fourth_quarter": (0.002, 0.002),  # 0.5% once (18 Jun); not itemized since
    "el_dagel": (0.002, 0.002),        # 0.4% once (18 Jun); not itemized since
}
# 2. MICRO_REALIZE — how sub-threshold lists' final itemized polls translated
#    into actual votes in the graded record:
#      NEP 2021        polled ~1.2%  -> 0.79%  (x0.66)
#      Jewish Home '22 polled  1.9%  -> 1.17%  (x0.62)
#      Yachad 2015     polled ~3.3%  -> 2.97%  (x0.90)
#      Zehut Apr '19   polled ~3.0%  -> 2.74%  (x0.91)
#      Otzma Sept '19  polled ~1.7%  -> 1.88%  (x1.11)
#    Non-sectoral lists shed ~30% to strategic desertion (voters flee a
#    wasted vote); lists with a committed sectarian/ideological core hold
#    their polling.
MICRO_REALIZE = {
    "noam": 1.0, "haredi_public": 1.0,
    "nep": 0.7, "israel_first": 0.7, "fourth_quarter": 0.7, "el_dagel": 0.7,
    "makom_lekulanu": 0.7,   # organized movement but no parliamentary base
}
# Forecast prior = polled x realization; the calibration's own dispersion
# (ratio spread ~0.6-1.1) is folded into the sd.
MICRO_PRIORS = {
    pid: (round(m * MICRO_REALIZE[pid], 4),
          round((sd ** 2 + (0.30 * m * MICRO_REALIZE[pid]) ** 2) ** 0.5, 4))
    for pid, (m, sd) in MICRO_POLLED.items()
}


# Mid-campaign mergers polled WITHOUT a column for the absorbed component
# create a step in the absorbing list's series that the random walk would
# otherwise smooth across. Make pre-merger observations comparable to the
# merged list by adding the absorbed list's measured pre-merger share.
#   2026-09-02: pollsters switched to a single "RZP - Zehut" column (5-6
#   seats vs 3.3 for RZP alone the week before). Before that Zehut lived
#   only in the small-party footnotes at ~1.6%, retained at 0.9 on merger.
STRUCTURAL_BREAKS = [
    {"component": "rzp", "from": "2026-09-02", "add_share": 0.9 * 0.016,
     "note": "Zehut absorbed into the RZP-Zehut technical bloc"},
]


def _apply_structural_breaks(obs: pd.DataFrame, block_of: dict) -> pd.DataFrame:
    for brk in STRUCTURAL_BREAKS:
        b = block_of.get(brk["component"])
        if b is None:
            continue
        m = (obs["block"] == b) & (obs["fieldwork_end"] < pd.Timestamp(brk["from"]))
        obs.loc[m, "share"] = obs.loc[m, "share"] + brk["add_share"]
        if m.any():
            print(f"structural break: +{brk['add_share']:.4f} share on "
                  f"{int(m.sum())} pre-{brk['from']} obs of {brk['component']} "
                  f"({brk['note']})")
    return obs


def prepare_data(polls: pd.DataFrame | None = None,
                 asof: pd.Timestamp | None = None,
                 modern_remaps: bool = True):
    """Build the model's data dict; parameterized so the validation harness
    can rebuild any past cycle's window (modern_remaps encodes 2026-only
    list identities — in earlier eras Ra'am really was inside the Joint
    List, so those rules must not apply)."""
    if polls is None:
        polls = load_2026()
    polls = polls[polls["pollster"] != "Unattributed"].copy()
    if modern_remaps:
        # Ra'am separate from the Joint List: joint_list == hadash_taal+balad,
        # and polls merging raam into a wider Arab composite are dropped.
        polls.loc[polls["party_id"] == "joint_list", "party_id"] = "balad+hadash_taal"
        # Together IS Yesh Atid + Bennett 2026: one entity across the merger,
        # so pre-merger component polls and post-merger joint polls share a
        # block.
        polls.loc[polls["party_id"] == "together", "party_id"] = "bennett_2026+yesh_atid"
        bad = polls[polls["party_id"].str.contains(r"raam.*\+|\+.*raam")]["poll_id"]
        polls = polls[~polls["poll_id"].isin(set(bad))]

    if asof is None:
        asof = polls["fieldwork_end"].max()
    win = polls[(polls["fieldwork_end"] > asof - pd.Timedelta(days=WINDOW_DAYS))
                & (polls["fieldwork_end"] <= asof)].copy()

    blocks = merge_blocks(win["party_id"].unique())
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    win["block"] = win["party_id"].map(lambda p: block_of[p.split("+")[0]])

    obs = implied_share_obs(win)
    if modern_remaps:
        obs = _merge_cec(obs, block_of, asof)
        obs = _apply_structural_breaks(obs, block_of)
        obs = _merge_sector(obs, block_of, asof)

    edges, dt_weeks = time_grid()
    obs["obs_day"] = (obs["fieldwork_end"] - asof).dt.days
    obs["week"] = np.clip(np.digitize(obs["obs_day"], edges) - 1,
                          0, len(edges) - 2)
    firms = sorted(obs["pollster"].unique())
    firm_ix = {f: i for i, f in enumerate(firms)}
    try:
        meta = pd.read_csv(PROCESSED_DIR.parent / "pollster_meta.csv")
        gmap = dict(zip(meta["pollster"], meta["correlation_group"]))
    except FileNotFoundError:
        gmap = {}
    groups = sorted({gmap.get(f, f) for f in firms})
    group_ix = {g: i for i, g in enumerate(groups)}
    firm_group = np.array([group_ix[gmap.get(f, f)] for f in firms])

    # Latent lists: blocks with real data; the rest become micro-lists.
    counts = obs.groupby("block")["share"].count()
    latent_blocks = sorted(counts[counts >= 5].index)
    lb_ix = {b: i for i, b in enumerate(latent_blocks)}
    obs = obs[obs["block"].isin(latent_blocks)]

    try:
        fil = pd.read_csv(PROCESSED_DIR / "cec_filings.csv",
                          dtype={"ref": str})
        umap = dict(zip("cec" + fil["ref"], fil["undecided_pct"] / 100.0))
        uvals = obs["poll_id"].map(umap)
        u_c = (uvals - uvals.mean()).fillna(0.0).values
    except FileNotFoundError:
        u_c = np.zeros(len(obs))

    last_obs_day = obs.groupby("block")["obs_day"].max()
    data = {
        "asof": asof,
        "blocks": blocks,
        "latent_blocks": latent_blocks,
        "last_obs_day": last_obs_day.reindex(latent_blocks).values,
        "obs_day": obs["obs_day"].values.astype(int),
        "u_c": u_c,
        "dt_weeks": dt_weeks,
        "components": ["+".join(sorted(blocks[b])) for b in latent_blocks],
        "y": obs["share"].values,
        "noise_mult": obs["noise_mult"].fillna(1.0).values.astype(float)
                      if "noise_mult" in obs.columns else np.ones(len(obs)),
        "n_resp": (obs["n"] if "n" in obs.columns else pd.Series(np.nan, index=obs.index))
                  .fillna(obs["pollster"].map(FIRM_N_DEFAULT)).fillna(N_DEFAULT).values.astype(float),
        "deff": obs["pollster"].map(DEFF).fillna(DEFF_DEFAULT).values.astype(float),
        "week": obs["week"].values.astype(int),
        "block_i": obs["block"].map(lb_ix).values.astype(int),
        "firm_i": obs["pollster"].map(firm_ix).values.astype(int),
        "firm_group": firm_group,
        "n_weeks": len(edges) - 1,
        "firms": firms,
        "groups": groups,
        "n_polls": obs["poll_id"].nunique(),
    }
    return data


def implied_share_obs(win: pd.DataFrame) -> pd.DataFrame:
    """Implied vote share per poll x block: seat rows share the
    above-threshold pie, "(x.y%)" rows are direct shares; component rows of
    a joint list contribute the SUM."""
    win = win.copy()
    wasted = (win[win["seats"] == 0].assign(w=win["vote_pct"].fillna(0) / 100)
              .groupby("poll_id")["w"].sum())
    win["wasted"] = win["poll_id"].map(wasted).fillna(0.0)
    seat_share = win["seats"] / 120.0 * (1.0 - win["wasted"] - 0.01)
    pct_share = win["vote_pct"] / 100.0
    win["share"] = np.where(win["seats"] > 0, seat_share, pct_share)
    return (win[win["share"].notna()]
            .groupby(["poll_id", "block"], as_index=False)
            .agg(share=("share", "sum"), pollster=("pollster", "first"),
                 fieldwork_end=("fieldwork_end", "first"),
                 n=("sample_size", "first")))


LAST_CEC_MERGE: dict = {}   # filled by _merge_cec, read into fit_summary.json

# ---- Sampling floor + design effects (2026-09-03 weighting audit) ----
# No poll can be more precise than its own sample. Within-firm scatter of
# the NB-bloc total around each firm's own trend measures 0.4-0.7 seats
# (Filber 0.43, Direct Polls 0.50, Lazar 0.54) against a binomial sampling
# error of 2-3 seats for n~550 - series smoothed by panel stickiness that
# the likelihood was reading as precision. A hard floor at the binomial
# sampling sd (x a declared design effect for opt-in panels) was built
# and REJECTED by the eight-cycle harness (see the switch in fit()); the
# machinery stays for research runs. What ships against the pathology:
# exit polls out of the scorecard, shrinkage by cycles graded, and a
# tighter lam prior (LAM_PRIOR_SIGMA) so the graded record holds.
FIRM_N_DEFAULT = {"Kantar": 550, "Midgam": 500, "Lazar": 500, "Panels Politics": 500,
                  "Maagar Mochot": 550, "Direct Polls": 500, "Filber": 600,
                  "Tatika": 500, "Dialog": 500}      # CEC filing medians
N_DEFAULT = 550
DEFF = {"Kantar": 1.0, "Smith Consulting": 1.0, "Midgam": 1.1, "Maagar Mochot": 1.1,
        "Camil Fuchs": 1.1, "Dialog": 1.2, "Afkar (sector)": 1.2,
        "Lazar": 1.3, "Panels Politics": 1.3, "Tatika": 1.3, "Midgam Project": 1.3,
        "Midgam Project & StatNet": 1.3, "TrendZone": 1.3, "Timor Group": 1.3,
        "Direct Polls": 1.4, "Filber": 1.4}
DEFF_DEFAULT = 1.3
LAM_PRIOR_SIGMA = 0.20   # was 0.25: the graded record holds more weight against
                         # 30-40 internally consistent within-cycle polls


def _merge_sector(obs: pd.DataFrame, block_of: dict, asof) -> pd.DataFrame:
    """Append sector-poll observations converted to national shares
    (src/sector_stream.py). They enter as polls by the sector firm with a
    noise multiplier for the conversion's own uncertainty."""
    from sector_stream import sector_observations
    reg = load_party_registry()
    so = sector_observations(dict(zip(reg["name_en"], reg["party_id"])))
    if "noise_mult" not in obs.columns:
        obs = obs.assign(noise_mult=1.0)
    if so.empty:
        return obs
    so = so[so["fieldwork_end"] <= asof]
    rows = []
    for r in so.itertuples():
        comp = r.party_id.split("+")[0]
        if comp not in block_of:
            continue
        rows.append({"poll_id": r.poll_id, "block": block_of[comp], "share": float(r.share),
                     "pollster": r.pollster, "fieldwork_end": r.fieldwork_end,
                     "noise_mult": float(r.noise_mult), "n": float(r.n)})
    if rows:
        print(f"sector stream: {len(rows)} converted observations from "
              f"{so['pollster'].nunique()} sector firm(s)")
        obs = pd.concat([obs, pd.DataFrame(rows)], ignore_index=True)
    return obs


def _merge_cec(obs: pd.DataFrame, block_of: dict, asof) -> pd.DataFrame:
    """Swap in CEC-filed RAW percentages where available.

    Filings (scrape_cec.py) carry each list's raw support share, including
    sub-threshold lists — strictly better observations than inverting
    published seat tables. Only filings whose parsed distribution sums to
    90-105% are trusted; each one displaces the matching seat-derived poll
    (same pollster within 3 days) to avoid double counting. Unmatched
    filings (polls absent from the public tables) enter as new polls.
    """
    try:
        pcts = pd.read_csv(PROCESSED_DIR / "cec_party_pcts.csv",
                           parse_dates=["fieldwork_end"], dtype={"ref": str})
    except FileNotFoundError:
        return obs
    sums = pcts.groupby("ref")["raw_pct"].sum()
    good = set(sums[(sums >= 90) & (sums <= 105)].index)
    pcts = pcts[pcts["ref"].isin(good)
                & (pcts["fieldwork_end"] <= asof)].copy()
    if pcts.empty:
        return obs

    remap = {"together": "bennett_2026"}
    rows, displaced = [], set()
    for ref, g in pcts.groupby("ref"):
        pollster = g["pollster"].iloc[0]
        fw = g["fieldwork_end"].iloc[0]
        near = obs[(obs["pollster"] == pollster)
                   & ((obs["fieldwork_end"] - fw).dt.days.abs() <= 3)]
        displaced |= set(near["poll_id"])
        for r in g.itertuples():
            comp = remap.get(r.party_id, r.party_id).split("+")[0]
            if comp not in block_of:
                continue
            rows.append({"poll_id": f"cec{ref}", "block": block_of[comp],
                         "share": r.raw_pct / 100.0, "pollster": pollster,
                         "fieldwork_end": fw})
    cec_obs = pd.DataFrame(rows).groupby(
        ["poll_id", "block"], as_index=False).agg(
        share=("share", "sum"), pollster=("pollster", "first"),
        fieldwork_end=("fieldwork_end", "first"))
    kept = obs[~obs["poll_id"].isin(displaced)]
    LAST_CEC_MERGE.update({"cec_filings_merged": int(cec_obs["poll_id"].nunique()),
                           "cec_obs": int(len(cec_obs)),
                           "polls_displaced": int(len(displaced))})
    print(f"CEC filings merged: {cec_obs['poll_id'].nunique()} filings "
          f"({len(cec_obs)} obs) displacing {len(displaced)} table-derived "
          f"polls")
    return pd.concat([kept, cec_obs], ignore_index=True)


def fit(data, draws=800, tune=800, holdout_mask=None):
    import pymc as pm
    import pytensor.tensor as pt

    B = len(data["latent_blocks"])
    W = data["n_weeks"]
    F = len(data["firms"])
    G = len(data["groups"])
    keep = slice(None) if holdout_mask is None else ~holdout_mask
    y, wk = data["y"][keep], data["week"][keep]
    bi, fi = data["block_i"][keep], data["firm_i"][keep]
    u_c = np.asarray(data.get("u_c", np.zeros(len(data["y"]))))[keep]
    nmult = np.asarray(data.get("noise_mult", np.ones(len(data["y"]))))[keep]
    n_resp = np.asarray(data.get("n_resp", np.full(len(data["y"]), N_DEFAULT)))[keep]
    deff = np.asarray(data.get("deff", np.full(len(data["y"]), DEFF_DEFAULT)))[keep]
    yc = np.clip(y, 0.01, 0.99)
    floor = np.sqrt(yc * (1 - yc) / n_resp * deff)   # binomial sampling sd x design effect
    import os
    # Default OFF. Eight-cycle harness ablation (2026-09-03, dossier s.23):
    # with the floor, pooled MAE 1.66 -> 1.71, 90% coverage 97.3% -> 98.4%
    # (already over-wide), threshold Brier 0.062 -> 0.065; without it the
    # harness reproduces the committed record exactly. The panel-stickiness
    # diagnosis stands, but historically the smooth series still carried
    # real signal, so the pre-registered arbiter rejects the floor. Set
    # BAYES_FLOOR=1 to re-enable for research runs.
    if os.environ.get("BAYES_FLOOR", "0") != "1":
        floor = np.zeros_like(floor)
    # centred time coordinate per observation (drift identifiability)
    edges_, _ = time_grid()
    mids_ = (edges_[:-1] + edges_[1:]) / 2.0
    tcent = ((mids_[wk] - mids_.mean()) / WINDOW_DAYS).astype(float)

    # Empirical ALR start point for faster convergence.
    first = pd.DataFrame({"b": data["block_i"], "y": data["y"],
                          "w": data["week"]})
    early = first[first["w"] <= 8].groupby("b")["y"].mean()
    early = early.reindex(range(B)).fillna(0.01).clip(lower=0.004)
    mu0 = np.log(early.values[:-1] / early.values[-1])

    with pm.Model() as model:
        z0 = pm.Normal("z0", mu=mu0, sigma=0.5, shape=B - 1)
        tau = pm.HalfNormal("tau", 0.06, shape=B - 1)
        steps = pm.Normal("steps", 0, 1, shape=(W - 1, B - 1))
        z = pm.Deterministic(
            "z", pt.concatenate(
                [z0[None, :],
                 z0[None, :] + pt.cumsum(
                     steps * tau
                     * np.sqrt(data["dt_weeks"])[:, None], axis=0)],
                axis=0))
        shares = pm.Deterministic(
            "shares", pt.special.softmax(
                pt.concatenate([z, pt.zeros((W, 1))], axis=1), axis=1))

        sigma_g = pm.HalfNormal("sigma_g", 0.015)
        sigma_f = pm.HalfNormal("sigma_f", 0.008)
        gamma = pm.Normal("gamma", 0, sigma_g, shape=(G, B))
        delta = pm.Normal("delta", gamma[data["firm_group"]], sigma_f,
                          shape=(F, B))
        delta_c = pm.Deterministic("delta_c", delta - delta.mean(axis=0))
        # Time-varying house effects (2026-09-03, Fable audit #3): each
        # firm's lean drifts linearly over the window, slope_c centred
        # across firms per list so a common drift stays in the latent
        # trend. Prior scale 0.01 share (~1.2 seats end to end).
        sigma_slope = pm.HalfNormal("sigma_slope", 0.01)
        slope = pm.Normal("slope", 0, sigma_slope, shape=(F, B))
        slope_c = pm.Deterministic("slope_c", slope - slope.mean(axis=0))

        s_obs = pm.HalfNormal("s_obs", 0.012, shape=B)
        # Firm reliability: per-firm noise multipliers with priors from the
        # results-graded accuracy scorecard — the information a within-cycle
        # likelihood cannot see. A firm with a poor final-poll record enters
        # with a wider prior noise; the 2026 data can still update it.
        from polling_average import QUALITY_ALIAS, quality_map
        q = np.array([quality_map().get(QUALITY_ALIAS.get(f, f), 1.0)
                      for f in data["firms"]])
        lam = pm.LogNormal("lam", mu=np.log(1.0 / q ** 2), sigma=LAM_PRIOR_SIGMA,
                           shape=F)
        # Undecided-share effect on informativeness: a filing-reported
        # undecided share above the field average widens that poll's noise
        # by an ESTIMATED factor (beta_u -> 0 if undecideds don't matter).
        beta_u = pm.HalfNormal("beta_u", 3.0)
        mu = shares[wk, bi] + delta_c[fi, bi] + slope_c[fi, bi] * tcent
        sig_model = (s_obs[bi] + 0.002) * lam[fi] * nmult * pt.exp(beta_u * u_c)
        pm.StudentT("y", nu=4, mu=mu,
                    sigma=pt.sqrt(sig_model ** 2 + floor ** 2), observed=y)

        idata = pm.sample(draws=draws, tune=tune, chains=4, cores=4,
                          target_accept=0.92, random_seed=SEED,
                          progressbar=False,
                          compute_convergence_checks=False)
    return model, idata


def diagnostics(idata):
    import arviz as az
    div = int(idata.sample_stats["diverging"].sum())
    summ = az.summary(idata, var_names=["tau", "sigma_g", "sigma_f", "s_obs"],
                      kind="diagnostics")
    rhat = float(summ["r_hat"].max())
    ess = float(summ["ess_bulk"].min())
    print(f"diagnostics: {div} divergences | max r_hat {rhat:.3f} | "
          f"min bulk ESS {ess:.0f}")
    return div, rhat, ess


def posterior_predictive_check(data, idata):
    post = idata.posterior
    shares = post["shares"].values.reshape(-1, *post["shares"].shape[2:])
    delta = post["delta_c"].values.reshape(-1, *post["delta_c"].shape[2:])
    s_obs = post["s_obs"].values.reshape(-1, post["s_obs"].shape[-1])
    idx = np.random.default_rng(0).choice(len(shares), 500, replace=False)
    edges_, _ = time_grid()
    mids_ = (edges_[:-1] + edges_[1:]) / 2.0
    tcent = (mids_[data["week"]] - mids_.mean()) / WINDOW_DAYS
    mu = shares[idx][:, data["week"], data["block_i"]] \
        + delta[idx][:, data["firm_i"], data["block_i"]]
    if "slope_c" in post:
        slope = post["slope_c"].values.reshape(-1, *post["slope_c"].shape[2:])
        mu = mu + slope[idx][:, data["firm_i"], data["block_i"]] * tcent[None, :]
    yc = np.clip(data["y"], 0.01, 0.99)
    floor = np.sqrt(yc * (1 - yc) / data["n_resp"] * data["deff"])
    sd = np.sqrt((s_obs[idx][:, data["block_i"]] + 0.002) ** 2 + floor[None, :] ** 2)
    lo = np.percentile(mu - 1.96 * sd, 2.5, axis=0)
    hi = np.percentile(mu + 1.96 * sd, 97.5, axis=0)
    cover = ((data["y"] >= lo) & (data["y"] <= hi)).mean()
    print(f"posterior predictive: {cover:.1%} of poll observations inside "
          f"95% predictive band")


def _certainty_layer(shares, comps, blocs, fams, rng):
    """Soft-support churn + certainty-weighted allocation of the undecided
    pool. Operates on the share matrix (draws x lists); returns it
    renormalised. See the CERTAINTY block for sources."""
    n, k = shares.shape
    cert = np.array([np.mean([CERTAINTY.get(c, CERTAINTY_DEFAULT) for c in cs])
                     for cs in comps])
    is_nb = blocs == "netanyahu_bloc"
    is_op = blocs == "opposition_bloc"
    is_arab = fams == "arab"
    # defection rate: common Beta draw x per-list LogNormal idiosyncrasy
    m = CHURN_D_MEAN
    v = CHURN_D_SD ** 2
    kk = m * (1 - m) / v - 1
    d = rng.beta(m * kk, (1 - m) * kk, size=(n, 1))
    d = np.clip(d * np.exp(rng.normal(0, CHURN_LIST_SDLOG, size=(n, k))), 0, 0.8)
    churn = shares * (1 - cert)[None, :] * d
    out = shares - churn
    attract = shares * cert[None, :]
    def spread(mass, mask):
        w = np.where(mask[None, :], attract, 0.0)
        tot = w.sum(axis=1, keepdims=True)
        return np.where(tot > 0, w / np.maximum(tot, 1e-12), 0.0) * mass[:, None]
    for own, other in ((is_nb, is_op), (is_op, is_nb)):
        if not own.any():
            continue
        pool = churn[:, own].sum(axis=1)
        out += spread(pool * CHURN_WITHIN, own)
        if other.any():
            out += spread(pool * CHURN_CROSS, other)
        # the abstaining fifth simply leaves the pie
    if is_arab.any():
        pool = churn[:, is_arab].sum(axis=1)
        out += spread(pool * (1 - CHURN_ABSTAIN), is_arab)
    # undecided pool: N12 lean with its own sampling uncertainty (n~60)
    if is_nb.any() and is_op.any():
        f_anti = rng.beta(*U_LEAN_BETA, size=n)
        mag = np.exp(rng.normal(0, U_MAG_SDLOG, size=n))
        excess = (f_anti - U_PROP_ANTI) / (U_LEAN_BASE - U_PROP_ANTI)
        ub = UNDECIDED_BREAK_SEATS / 120.0 * excess * mag
        out += spread(np.maximum(ub, 0), is_op) - spread(np.maximum(ub, 0), is_nb)
        out += spread(np.maximum(-ub, 0), is_nb) - spread(np.maximum(-ub, 0), is_op)
    out = np.clip(out, 0, None)
    return out / out.sum(axis=1, keepdims=True)


def project(data, idata, rng, config="current", config_params=None):
    """Election-day seat draws: RW forward + industry shocks + micro-lists.

    config reshapes the list structure before shocks and threshold:
      "balad_splits"  Balad leaves the Joint List at its scenario-polled
                      standalone share; "segalovitz" adds a new
                      centre-aligned list at its scenario-polled size
                      (parameters from arab_scenarios.py).
    """
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    names = dict(zip(reg["party_id"], reg["name_en"]))

    post = idata.posterior
    z_last = post["z"].values[:, :, -1, :].reshape(-1, post["z"].shape[-1])
    tau = post["tau"].values.reshape(-1, post["tau"].shape[-1])
    n_post = len(z_last)
    take = rng.choice(n_post, N_PROJ, replace=True)
    z_last, tau = z_last[take], tau[take]

    # Calendar-shaped forward variance: each remaining week is weighted
    # by the measured campaign volatility profile (see campaign_vol_weight).
    days_ahead = max((ELECTION_DAY_2026 - data["asof"]).days, 0)
    eff_weeks = 0.0
    d = days_ahead
    while d > 0:
        step = min(d, 7)
        eff_weeks += campaign_vol_weight(d) ** 2 * (step / 7.0)
        d -= step
    z_e = z_last + np.sqrt(eff_weeks) * tau * rng.standard_normal(z_last.shape)
    z_full = np.concatenate([z_e, np.zeros((N_PROJ, 1))], axis=1)
    shares = np.exp(z_full - z_full.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)

    # Lists with no polls in their final weeks have left the race.
    gone = data["last_obs_day"] < -7 * WITHDRAWN_WEEKS
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)

    # Per-list election-day shock: residual final-poll error beyond
    # bloc/family components, calibrated on the backtest.
    base0 = shares.mean(axis=0)
    sd_list = (LIST_SHOCK_BASE + LIST_SHOCK_SLOPE * base0 * 120) / 120.0
    comps0 = [set(c.split("+")) for c in data["components"]]
    is_new = np.array([bool(cs & NEW_LIST_IDS) for cs in comps0])
    sd_list = np.where(is_new, sd_list * NEW_LIST_MULT, sd_list)
    for pid, m in SOFT_LIST_MULT.items():
        soft = np.array([pid in cs for cs in comps0])
        sd_list = np.where(soft, sd_list * m, sd_list)
    shares = np.clip(
        shares + rng.standard_normal(shares.shape) * sd_list, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    labels = [short_name(c, names) for c in data["components"]]
    comps = [set(c.split("+")) for c in data["components"]]

    # Micro-lists from priors, carved out of the modeled pie.
    micro_names, micro_draws = [], []
    for pid, (m, s) in MICRO_PRIORS.items():
        micro_names.append(names.get(pid, pid))
        comps.append({pid})
        micro_draws.append(np.clip(rng.normal(m, s, N_PROJ), 0, None))
    micro = np.column_stack(micro_draws)
    shares = np.concatenate([shares * (1 - micro.sum(axis=1, keepdims=True)),
                             micro], axis=1)
    labels += micro_names

    blocs = []
    for comp in comps:
        bs = {bloc_map.get(c, "other") for c in comp}
        blocs.append(bs.pop() if len(bs) == 1 else "other")
    blocs = np.array(blocs)
    fams = np.array([max([FAMILY_OF.get(c, "other") for c in comp],
                         key=[FAMILY_OF.get(c, "other") for c in comp].count)
                     for comp in comps])

    # Configuration scenarios (registration-deadline what-ifs).
    cp = config_params or {}
    if config == "mixture":
        from registration_scenarios import apply_registration_events
        shares, comps, labels, blocs, fams, events = \
            apply_registration_events(shares, comps, labels, blocs, fams,
                                      rng, cp)
        project.last_events = events
    elif config == "balad_splits":
        jl = next((i for i, c in enumerate(comps) if "hadash_taal" in c), None)
        if jl is not None:
            split = cp.get("balad_alone_pct", 1.8) / 100.0
            take = np.minimum(shares[:, jl], split)
            shares = np.concatenate([shares, take[:, None]], axis=1)
            shares[:, jl] = shares[:, jl] - take
            comps.append({"balad"})
            labels.append("Balad (alone)")
            blocs = np.append(blocs, "other")
            fams = np.append(fams, "arab")
    elif config == "segalovitz":
        # Segalovitz joins Ra'am's slate: Ra'am gains crossover votes carved
        # from the centre bloc (no new list).
        boost = cp.get("segalovitz_boost_seats", 1.3) / 120.0
        raam = next((i for i, c in enumerate(comps) if "raam" in c), None)
        centre = blocs == "opposition_bloc"
        w = np.where(centre, shares.mean(axis=0), 0.0)
        if raam is not None:
            shares = shares - boost * (w / w.sum())
            shares[:, raam] = shares[:, raam] + boost
    elif config == "arab_turnout":
        # Differential-turnout dial: scale Arab-family shares by a factor
        # calibrated on the 2021->2022 turnout swing (44.6% -> 53.2% moved
        # the Arab lists' national share by ~+24%; +/-12% spans the range).
        fct = cp.get("factor", 1.0)
        in_a = fams == "arab"
        shares[:, in_a] = shares[:, in_a] * fct
    if config != "current":
        shares = np.clip(shares, 0, None)
        shares /= shares.sum(axis=1, keepdims=True)

    # Industry shocks (unidentifiable from polls).
    base = shares.mean(axis=0)
    is_nb = blocs == "netanyahu_bloc"
    swing = rng.standard_t(T_DF, N_PROJ) * BLOC_SWING_SD * EVENT_RISK / 120.0
    w_nb, w_op = np.where(is_nb, base, 0), np.where(~is_nb, base, 0)
    shares = shares + swing[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())

    # Certainty layer: soft support churns (asymmetric, list-specific),
    # churn and the undecided pool land by certainty-weighted attraction.
    shares = _certainty_layer(shares, comps, blocs, fams, rng)
    # Family shocks with kalpi-measured correlation: the haredi and Arab
    # sector tides correlated +0.92 across the 2019-2022 locality panel
    # (both are turnout-machine sectors) - shrunk hard to rho=0.5 for
    # n=4 transitions. Correlated t draws via a shared chi-square mixer.
    fam_names = [f for f in FAMILY_SHOCK if (fams == f).any()]
    rho = KALPI_FAMILY_RHO if len(fam_names) == 2 else 0.0
    cov = np.array([[1.0, rho], [rho, 1.0]]) if rho else np.eye(
        max(len(fam_names), 1))
    z = rng.multivariate_normal(np.zeros(len(fam_names)),
                                cov[:len(fam_names), :len(fam_names)],
                                size=N_PROJ)
    mix = np.sqrt(rng.chisquare(T_DF, N_PROJ) / T_DF)
    tdraws = z / mix[:, None]
    for k, f in enumerate(fam_names):
        mu_f, sd_f = FAMILY_SHOCK[f]
        in_f = fams == f
        shock = (-mu_f + tdraws[:, k] * sd_f) / 120.0
        w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
        shares = shares + shock[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())

    # Party anchors: deterministic truth-shifts for Likud and the poll
    # leader (their variance already lives in the residual shock).
    likud_col = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    non_likud = [i for i in range(len(comps)) if i != likud_col]
    leader_col = non_likud[int(np.argmax(base[non_likud]))] if non_likud else None
    for col, mu in ((likud_col, ANCHORS["likud"]),
                    (leader_col, ANCHORS["leader"])):
        if col is None:
            continue
        onehot = np.zeros(len(comps))
        onehot[col] = 1.0
        w_r = np.where(onehot == 0, base, 0)
        shares = shares + (-mu / 120.0) * (onehot - w_r / w_r.sum())

    # Gevalt coupling: zero-sum transfer between Likud and its bloc's
    # satellites, proportional to satellite size (see GEVALT_SD note).
    sat = np.array([bool(cs & GEVALT_SAT_IDS) for cs in comps])
    if likud_col is not None and sat.any():
        onehot = np.zeros(len(comps))
        onehot[likud_col] = 1.0
        w_s = np.where(sat, base, 0)
        g = rng.standard_normal(N_PROJ) * GEVALT_SD / 120.0
        shares = shares + g[:, None] * (onehot - w_s / w_s.sum())

    # Centre churn: zero-sum within-bloc exchanges (measured 3x the NB
    # bloc's internal wavering) - parts move, bloc total holds.
    def _c(pid):
        return next((i for i, cs in enumerate(comps) if pid in cs), None)
    for a, b, sd in CENTRE_CHURN:
        ca, cb = _c(a), _c(b)
        if ca is None or cb is None:
            continue
        g = rng.standard_normal(N_PROJ) * sd / 120.0
        shares[:, ca] += g
        shares[:, cb] -= g

    # Amcha fade: reference-class D-60 over-polling, returned to sources.
    am = next((i for i, cs in enumerate(comps) if cs == {"amcha_yisrael"}),
              None)
    if am is not None:
        c_am = CERTAINTY["amcha_yisrael"]
        exp_loss = (1 - c_am) * CHURN_D_MEAN * (1 - CHURN_WITHIN) \
            * float(base[am]) * 120          # seats already removed above
        f = max(AMCHA_FADE_TOTAL - exp_loss, 0.0) / 120.0
        shares[:, am] -= f
        lk = _c("likud")
        for pid, w in AMCHA_FADE_TO.items():
            c = _c(pid)
            if c is None:
                c = lk
            # a list absorbed/withdrawn in this draw can't receive votes
            alive = shares[:, c] > 0
            shares[alive, c] += f * w
            if lk is not None and (~alive).any():
                shares[~alive, lk] += f * w

    # Loyal-electorate calibration: shrink each captive-base list's
    # draws around its own center to the measured target sd (LOYAL_SD).
    for pid, tgt in LOYAL_SD.items():
        want = set(pid.split("+"))
        col = next((i for i, cs in enumerate(comps) if cs == want), None)
        if col is None:
            continue
        v = shares[:, col]
        act = v.std() * 120.0
        if act > tgt:
            shares[:, col] = v.mean() + (v - v.mean()) * (tgt / act)
    # Kalpi capacity truncation: clip draws that exceed what the sector
    # geography can physically cast (see KALPI_ARAB_CAP/HAREDI_FLOOR).
    arab_cols = np.array([f == "arab" for f in fams])
    har_cols = np.array([cs in ({"shas"}, {"utj"}) for cs in comps])
    if arab_cols.any():
        tot = shares[:, arab_cols].sum(axis=1)
        over = tot > KALPI_ARAB_CAP
        if over.any():
            shares[np.ix_(over, arab_cols)] *= (
                KALPI_ARAB_CAP / tot[over])[:, None]
    if har_cols.any():
        tot = shares[:, har_cols].sum(axis=1)
        under = (tot > 0) & (tot < KALPI_HAREDI_FLOOR)
        if under.any():
            shares[np.ix_(under, har_cols)] *= (
                KALPI_HAREDI_FLOOR / tot[under])[:, None]
    shares = np.clip(shares, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    comp_of = {c: i for i, cs in enumerate(comps) for c in cs}
    pairs = [(comp_of[a], comp_of[b]) for a, b in SURPLUS_PAIRS
             if a in comp_of and b in comp_of and comp_of[a] != comp_of[b]]

    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        sh = shares[i]
        passed = sh >= THRESHOLD
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers, used = [], [], set()
        for a, b in pairs:
            if passed[a] and passed[b]:
                fvotes.append(votes[a] + votes[b])
                fmembers.append([a, b])
                used |= {a, b}
        for j in np.nonzero(passed)[0]:
            if j not in used:
                fvotes.append(votes[j])
                fmembers.append([int(j)])
        alloc = dhondt(np.array(fvotes), 120)
        for members, k in zip(fmembers, alloc):
            if len(members) == 1:
                seats[i, members[0]] = k
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats, labels, blocs


def main() -> None:
    rng = np.random.default_rng(SEED)
    data = prepare_data()
    print(f"data: {data['n_polls']} polls, {len(data['y'])} observations, "
          f"{len(data['latent_blocks'])} lists, {data['n_weeks']} weeks, "
          f"{len(data['firms'])} firms in {len(data['groups'])} groups")

    # Holdout: refit without the last 14 days, predict them.
    cut = data["asof"] - pd.Timedelta(days=HOLDOUT_DAYS)
    holdout = data["obs_day"] > -HOLDOUT_DAYS
    if holdout.sum() >= 10:
        _, idata_h = fit(data, draws=500, tune=600, holdout_mask=holdout)
        post = idata_h.posterior
        sh = post["shares"].values.reshape(-1, *post["shares"].shape[2:])
        wk_last = min(int(data["week"][~holdout].max()),
                      sh.shape[1] - 1)
        pred = sh[:, wk_last, :]  # frozen at last fitted week
        y_h = data["y"][holdout]
        b_h = data["block_i"][holdout]
        err = np.abs(np.median(pred, axis=0)[b_h] - y_h) * 120
        fit_summary_holdout = {"holdout_obs": int(holdout.sum()),
                               "holdout_median_err": round(float(np.median(err)), 2)}
        print(f"holdout ({int(holdout.sum())} obs, last {HOLDOUT_DAYS}d): "
              f"median |error| {np.median(err):.2f} seats "
              f"(no-update prediction)")

    model, idata = fit(data)
    import arviz as az, json
    az.to_netcdf(idata, PROCESSED_DIR / "m3_idata.nc")  # shared with mixture
    div, rhat, ess = diagnostics(idata)
    fit_summary = {
        "asof": data["asof"].date().isoformat(),
        "n_polls": int(data["n_polls"]), "n_obs": int(len(data["y"])),
        "n_lists": int(len(data["latent_blocks"])), "n_bins": int(data["n_weeks"]),
        "n_firms": int(len(data["firms"])), "n_groups": int(len(data["groups"])),
        "divergences": div, "rhat_max": round(rhat, 3), "ess_min": int(ess),
        "firm_weights": {f: round(float(w), 2) for f, w in zip(
            data["firms"], idata.posterior["lam"].mean(dim=("chain", "draw")).values)},
        **LAST_CEC_MERGE,
        **(fit_summary_holdout if "fit_summary_holdout" in dir() else {}),
    }
    (PROCESSED_DIR / "fit_summary.json").write_text(json.dumps(fit_summary, indent=1))
    if "beta_u" in idata.posterior:
        bu = idata.posterior["beta_u"].values.ravel()
        print(f"undecided coefficient beta_u: mean {bu.mean():.2f}, "
              f"90% CI [{np.percentile(bu, 5):.2f}, "
              f"{np.percentile(bu, 95):.2f}]  "
              f"(x{np.exp(bu.mean() * 0.05):.2f} noise per +5pp undecided)")
    posterior_predictive_check(data, idata)

    seats, labels, blocs = project(data, idata, rng)
    is_max = seats == seats.max(axis=1, keepdims=True)
    p_largest = (is_max / is_max.sum(axis=1, keepdims=True)).mean(axis=0)

    dist = pd.DataFrame({
        "list": labels,
        "bloc": [BLOC_LABEL.get(b, b) for b in blocs],
        "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p50": np.percentile(seats, 50, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
        "p_largest": p_largest.round(3),
    }).sort_values("mean", ascending=False)
    dist["asof"] = data["asof"].date().isoformat()
    dist.to_csv(PROCESSED_DIR / "bayes_forecast_2026.csv", index=False)
    pd.DataFrame(seats, columns=labels).to_parquet(
        PROCESSED_DIR / "bayes_draws.parquet")

    nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
    # Segalovitz's own seat (Ra'am slot #2) is a centre vote: count it
    # toward the anti-bloc 61 whenever Ra'am wins at least 2 seats.
    anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
    _ri = next((i for i, l in enumerate(labels) if l == "Ra'am"), None)
    if _ri is not None:
        anti = anti + (seats[:, _ri] >= 2).astype(int)
    summary = pd.DataFrame([{
        "asof": data["asof"].date().isoformat(), "n_proj": N_PROJ,
        "p_netanyahu_bloc_61": (nb >= 61).mean().round(3),
        "p_anti_bloc_61": (anti >= 61).mean().round(3),
        "p_neither": ((nb < 61) & (anti < 61)).mean().round(3),
        "nb_mean": nb.mean().round(1),
        "nb_p05": int(np.percentile(nb, 5)),
        "nb_p95": int(np.percentile(nb, 95)),
    }])
    summary.to_csv(PROCESSED_DIR / "bayes_forecast_blocs.csv", index=False)

    print(f"\nBayesian forecast as of {data['asof'].date()}:\n")
    print(dist.drop(columns="asof").to_string(index=False))
    s = summary.iloc[0]
    print(f"\nP(Netanyahu bloc >= 61) = {s['p_netanyahu_bloc_61']:.1%}   "
          f"P(anti bloc >= 61) = {s['p_anti_bloc_61']:.1%}   "
          f"P(neither) = {s['p_neither']:.1%}")
    print(f"Netanyahu bloc mean {s['nb_mean']}, 90% interval "
          f"[{s['nb_p05']}, {s['nb_p95']}]")
    print("\nwrote bayes_forecast_2026.csv, bayes_forecast_blocs.csv, "
          "bayes_draws.parquet")


if __name__ == "__main__":
    main()
