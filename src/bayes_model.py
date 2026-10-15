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
import simulate as _sim
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
# ---- Undecided pool (2026-09-03, audit improvement #1) ----
# Pool SIZE is measured from the CEC filings of firms that report a
# genuine undecided share (Lazar, Midgam Project & StatNet, Maagar Mochot;
# Kantar's figure includes non-voters, Midgam's is post-allocation): the
# median over the last 45 days, refreshed every build.
U_POOL_FIRMS = ("Lazar", "Midgam Project & StatNet", "Maagar Mochot")
U_POOL_DEFAULT = 0.12
U_TURNOUT = 0.65        # GIQ: the unsophisticated half of undecideds under-votes
U_EXCESS_ANTI = 0.35    # excess-vs-proportional arithmetic at the N12 lean (= the GAP excess, applied per side: see s.41)
# Pool LEAN is pooled over every published undecided-lean measurement in
# data/undecided_leans.csv (today: N12 only, ~43 leaned respondents) with
# a proportional-split prior of equal n - the pre-registered "half weight"
# made explicit, so each new wave shifts the posterior by its own n.
U_PROP_ANTI = 0.52      # the decided electorate's anti share (proportional baseline)
U_LEAN_BASE = 0.775     # the N12 lean the excess arithmetic was derived at
U_PRIOR_N = 43
U_MAG_SDLOG = 0.5
# ---- Undecided-lean correction (2026-10-10, dossier s.41; flags OFF) ----
# (a) U_LEAN_PER_SIDE. s.11's 0.35 = 0.71*(0.77-0.23) - 0.71*(0.52-0.48)
# is the excess change of the bloc GAP (anti minus NB) as a fraction of
# the pool, but _certainty_layer adds ub to anti AND removes ub from NB,
# so the gap moved 2 x 0.35 = 0.70 of the voting pool: double the
# measurement. The per-side transfer is leaned fraction x (lean - the
# proportional anti share) = 0.71 x (0.775 - 0.52) = 0.181. At the
# posterior lean the shipped layer moved ~1.40 seats per side = the FULL
# measured transfer (1.45), i.e. the pre-registered half weight (carried
# by the n=43 prior) was cancelled by the doubling. Source of 55/16/29:
# N12/Midgam, fieldwork 30 Jul 2026, n=505,
# https://www.mako.co.il/news-israel-elections/2026_q3/Article-b13ddbd17f8bf91027.htm
U_LEAN_PER_SIDE = True
U_LEANED_FRAC = 0.71    # 0.55 + 0.16 of the N12 undecided pool state a lean
U_EXCESS_PER_SIDE = U_LEANED_FRAC * (U_LEAN_BASE - U_PROP_ANTI)   # 0.181
# (b) U_LEAN_TAU: calendar staleness decay exp(-age/tau) on each lean
# measurement's n before pooling. JUDGMENT, not pre-registered (s.11
# pre-registered shrinkage through pool RESOLUTION, which U_POOL already
# measures; s.36 #5 kept the N12 lean at full pooled weight). None = off.
U_LEAN_TAU = None
# (c) U_POOL_ESTIMATOR: "pooled" (shipped: median of all filings in the
# last 45 days) or "house_balanced" (median per firm in the window, then
# the mean across firms, so the estimate does not track filing cadence).
U_POOL_ESTIMATOR = "pooled"
U_POOL_WINDOW = 45


def _undecided_pool() -> float:
    try:
        f = pd.read_csv(PROCESSED_DIR / "cec_filings.csv", parse_dates=["fieldwork_end"])
        f = f[f["pollster"].isin(U_POOL_FIRMS) & f["undecided_pct"].notna()]
        f = f[f["fieldwork_end"] >= f["fieldwork_end"].max() - pd.Timedelta(days=U_POOL_WINDOW)]
        if len(f) < 3:
            return U_POOL_DEFAULT
        if U_POOL_ESTIMATOR == "house_balanced":
            return float(f.groupby("pollster")["undecided_pct"].median().mean() / 100)
        return float(f["undecided_pct"].median() / 100)
    except FileNotFoundError:
        return U_POOL_DEFAULT


def _lean_posterior(asof=None) -> tuple:
    """Beta(a, b) on the anti share of the leaned pool: measurements pooled
    by their leaned n, plus the proportional prior of n = U_PRIOR_N.
    With U_LEAN_TAU set and an asof date, each measurement's n is
    discounted by exp(-age / U_LEAN_TAU)."""
    a = U_PROP_ANTI * U_PRIOR_N
    b = (1 - U_PROP_ANTI) * U_PRIOR_N
    try:
        L = pd.read_csv(PROCESSED_DIR.parent / "undecided_leans.csv",
                        parse_dates=["fieldwork_end"])
        for r in L.itertuples():
            n_lean = r.n_undecided * (r.anti + r.nb)
            if U_LEAN_TAU and asof is not None:
                n_lean *= np.exp(-max((asof - r.fieldwork_end).days, 0) / U_LEAN_TAU)
            a += r.anti / (r.anti + r.nb) * n_lean
            b += r.nb / (r.anti + r.nb) * n_lean
    except FileNotFoundError:
        pass
    return a, b


U_POOL = _undecided_pool()
U_LEAN_BETA = _lean_posterior()
UNDECIDED_BREAK_SEATS = U_POOL * U_TURNOUT * U_EXCESS_ANTI * 120   # at full lean (per side; gap = 2x)

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
CHURN_WITHIN, CHURN_CROSS, CHURN_ABSTAIN = 0.75, 0.10, 0.15   # declared (superseded below)
# MEASURED 2026-09-03 from the Kolot Nodedim 2021->2022 transition matrix
# with abstention (7,035 matched stations): of voters who left their 2021
# list, the change bloc's went 72.5% to another change list / 10.3% across
# / 17.2% abstained; the Netanyahu bloc's 85.5 / 6.6 / 7.9. Same-list
# loyalty: change 59%, right 82% - the bloc-level certainty asymmetry
# CERTAINTY encodes. Arab-list movers stayed in-family (0% cross).
CHURN_SPLIT = {"opposition_bloc": (0.725, 0.103, 0.172),
               "netanyahu_bloc": (0.855, 0.066, 0.079)}
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
    # Ra'am (2026-09-03): with sector turnout carried by ARAB_TURNOUT, the
    # remaining idiosyncratic risk is the JL/Ra'am split; measured final
    # error 0.6-1.0 seats over 2021-22 (n=2) x 2 buffer.
    "raam": 1.8,
}

# All election-day shocks come from the sequential decomposition of the
# eight-cycle error record (error_decomposition.py), so no component is
# double-counted. Means are in ERROR space (polled - actual): the projection
# applies the NEGATED mean, since simulated truth = polled - error.
from error_decomposition import decompose as _decompose

_P = _decompose()
BLOC_SWING_SD = _P["bloc_sd"]
FAMILY_SHOCK = _P["family"]        # {family: (error mean, sd)} in seats
# Arab family error is regime-dependent (2026-09-03 audit, own backtest,
# error = polled - actual): with a UNIFIED Joint List the final polls
# under-counted the Arab lists every time - 2015 -0.4, 2019s -1.9, 2020
# -1.1, 2022 -2.0 (mean -1.35) - as unification lifts Arab turnout
# (56.5 -> 63.5% in 2015, 49 -> 59 -> 65% across 2019a/2019s/2020); in the
# split, demoralised years they over-counted (2019a +1.2, 2021 +1.5). The
# pooled -0.32 mixes both regimes. With balad_splits resolved False the
# 2026 list is unified, so the unified-regime mean applies; the pooled sd
# is kept (turnout risk cuts both ways).
ARAB_LIST_UNIFIED = True
# 2026-09-03 (audit improvement #3): the Arab lists' family error is now
# a TURNOUT mechanism instead of an additive seat mean. National panels
# weight the Arab sector to the last election's turnout (0.538 in 2022);
# realised turnout under a unified Joint List ran 63.5 / 59.2 / 64.8%
# (2015, 2019s, 2020; mean 0.625, sd 0.03) and 49.2 / 44.6% in the split
# years. Each simulation draws T, scales the Arab lists' joint share by
# T/base (JL and Ra'am move TOGETHER, which is what the data show), and
# takes the mass proportionally from every other list. The draw shares
# the haredi tide's correlated z (KALPI_FAMILY_RHO). The kalpi capacity
# ceiling still binds above. The additive -1.35 this replaces is the
# same history expressed in seats.
ARAB_TURNOUT = {"base": 0.538, "mean_unified": 0.580, "mean_split": 0.47,
                "sd": 0.05, "max": 0.72}
# 15 Oct (dossier s.43): mean_unified 0.625 -> 0.580 (the LOO table-B regime
# mean, inside s.4's pre-registered 56-62% band), with the graded pass-through
# and intercept below. Shipped on the harness's POOLED route after an
# adversarial verification (strict-LOO fix in validate_bayes).
# 2026-10-13 candidate arab_turnout_regime (dossier s.43), all three OFF
# (recommended graded setting: mean_unified 0.580, K 0.247, INTERCEPT -0.634):
# ARAB_TURNOUT_K is the pass-through of the EXPECTED turnout ratio into the
# Arab lists' share, r = 1 + k (T_mean/base - 1) + (T - T_mean)/base (the
# draw noise is unscaled); 1.0 = shipped (polls miss the whole turnout
# swing). The record's regression of family error on the ratio-implied
# error has slope ~0.25. ARAB_FAMILY_FORM "additive_e0" replaces the
# mechanism with the additive raw-e0 family mean (decompose()["family_e0"])
# and the family's e1 sd - the control the mechanism was graded against.
ARAB_TURNOUT_K = 0.247            # shipped 15 Oct (s.43); full-sample fit, se 0.21
ARAB_FAMILY_FORM = "turnout"      # "turnout" (shipped) | "additive_e0"
# Error-space intercept (seats, polled - actual) added to the turnout form:
# the harness arm arab_regB is e0 = a + k x implied, fitted on the record
# (full sample a -0.634, k 0.247). None = shipped (no intercept).
ARAB_TURNOUT_INTERCEPT = -0.634   # shipped 15 Oct (s.43); seats, se 0.41
ANCHORS = _P["anchors"]            # {"likud": .., "leader": ..} error means
# 2026-09-03 (accuracy round three): anchors RETIRED. Eight-cycle harness
# ablation - full 1.665 / no anchors 1.589 seats per list (median 1.574
# -> 1.541), Brier 0.060 -> 0.058, coverage 0.983 -> 0.972; removing
# either anchor alone or halving both is worse than removing both. The
# Likud beat is +8.4 and +6.7 in two cycles and ~0 in six, so a mean
# applied everywhere is wrong six times in eight. Values kept for the
# record; a conditional gevalt (Likud rising in the final fortnight) is
# the principled successor to test.
ANCHORS_ON = False
# Interval-width calibration (audit improvement #2): one global factor on
# the per-list residual shock, fitted leave-one-cycle-out on the harness
# to bring 90% coverage to its target (validate_bayes writes the curve to
# model_validation_width.csv). 1.0 = the decomposition's raw width.
# 2026-09-03 harness: 0.9 chosen by every leave-one-cycle-out fold
# (interval score 8.36 vs 8.62 at 1.0; MAE 1.655 vs 1.659; Brier equal);
# 0.6-0.8 WORSEN MAE (1.90 at 0.6) through the threshold nonlinearity,
# and coverage stays ~98% at 0.9 - the over-width lives in other layers.
RESID_SCALE = 0.9
# Accuracy round four #2 (2026-09-10): joint width knobs, calibrated on the
# horizon cache (validate_horizon STACK_GRID x RW_GRID). STACK_SCALE
# multiplies the election-day shock stack (bloc swing, family shocks, the
# residual on top of RESID_SCALE); RW_FORWARD_SCALE multiplies the forward
# random-walk VARIANCE. 1.0 / 1.0 = the pre-calibration model.
STACK_SCALE = 1.0
RW_FORWARD_SCALE = 1.0
# Accuracy round four #4: the trailing-Likud conditional (successor to the
# retired fixed anchors). Measured on the record: in the cycles where Likud
# trailed or tied the largest non-bloc list in the final week (2015, April
# 2019, September 2019) it beat its final polls by +8.8 / +6.8 / -0.5 seats
# (mean +5.0, sd 4.9, n=3); when it led clearly the miss was ~0. Applied
# only when Likud's projected standing trails the leader by the margin.
# Ships only on the harness verdict (validate_bayes ABLATIONS
# no_anchors_trail / _half).
# HARNESS VERDICT (2026-09-11, dossier s.36): on top of the shipped
# no-anchor configuration the layer at HALF strength gives the best
# median-seat MAE of every ablation (1.467 vs 1.524 without; mean 1.578 vs
# 1.565), Brier 0.053 tie, coverage 0.983: 2015 2.09 -> 1.36, April 2019
# 2.54 -> 2.31, September 2019 0.57 -> 1.07, five cycles untouched. Full
# strength loses more in Sept 2019 (1.57) for the same gains. Shipped at
# 0.5 with the caveat that n=3 trailing cycles is thin evidence.
EXCLUDE_POLLSTERS = {"S.M.L.T."}
# Accuracy round four #1 (2026-09-11, dossier s.36): FIRST-CYCLE lists
# projected within the threshold band lose votes to strategic desertion.
# Measured on the horizon record (D-56/D-21 projections of every cycle):
# 11 new-list straddlers, 2 passed, mean drift -1.6 pp (sd 2.6; LOO means
# -1.1 to -2.2); established straddlers are calibrated (drift ~0). The
# layer cut the straddler Brier from 0.256 to 0.226 (D-56) and 0.245 to
# 0.234 (D-21) with established lists unchanged. First-cycle = no
# component polled before this cycle. In 2026: Amcha, Reservists-Economic.
NEW_STRADDLER_ON = True
NEW_STRADDLER = {"mu": -1.6, "sd": 2.6, "band": (-0.75, 1.5)}   # pp of the vote
# Candidate "amcha_double_count" (2026-10-10, dossier s.41). EVIDENCE class,
# not harness-validated: neither the fade nor the certainty layer exists in
# validate_bayes.project_cycle, so NEW_STRADDLER was measured on a base free
# of both, and in 2026 three desertion terms stack on Amcha (churn ~0.4 pp,
# fade 1.17 pp, NEW_STRADDLER 1.6 pp; shipped median share ~0 against a
# 3.3% posterior base and a 2.66% CEC-filing mean, refs 4173-4192).
# AMCHA_FADE_RETIRED: skip the AMCHA_FADE_TOTAL block. The fade is a D-60
#   term (s.8) applied at D-17; the posterior latent already fell 4.24% ->
#   3.26% since D-63..56 (~80% of the 1.5 seats realised), and its
#   reference class shares New Right '19a / Yamina '19s with NEW_STRADDLER.
# NEW_STRADDLER_CHURN_EXEMPT: lists hit by NEW_STRADDLER's band test keep
#   their soft support in the certainty layer (one desertion term per list);
#   their inflow attraction stays at their CERTAINTY. Caveat: NEW_STRADDLER's
#   -1.6/2.6 was graded on seat-implied shares (failed lists at 0% of the
#   vote, two non-runners counted as total desertion); on ballot shares the
#   record is mean -0.3 (n=9), D-21 +0.2 (n=7). Flip this only after that
#   re-grade keeps a negative mean on the harness.
AMCHA_FADE_RETIRED = True
NEW_STRADDLER_CHURN_EXEMPT = False
TRAIL_ON = True
TRAIL = {"mu": 5.0, "sd": 4.9, "margin": 0.5, "scale": 0.5}
# Candidate trail_geometry (2026-10-10, dossier s.41) - DEFAULT OFF. The
# shipped TRAIL takes Likud's beat from the whole field in proportion to
# size, so ~2/3 of it comes out of non-bloc lists and the layer adds
# ~+1.5 seats to the Netanyahu bloc. The record it is calibrated on shows
# no bloc-level move (2015 / April 2019 opposition-side final-poll error
# +0.12 / +0.33 seats): the beat was paid by the bloc's own right flank
# (Jewish Home 11.75 -> 8, Yachad dead; New Right and Zehut dead). With the
# flag on, the SAME draw (same mean, sd, half strength, same 0.5-seat
# gate) is sourced from the bloc's non-haredi satellites (GEVALT_SAT_IDS,
# the gevalt coupling's own pre-existing set), in proportion to each one's
# share IN THAT DRAW, capped at TRAIL_SAT_CAP of the satellites' share in
# that draw; the remainder comes from the rest of the field. Amcha is
# excluded from the source: AMCHA_FADE is already the gevalt squeeze on
# Amcha (same reference class, 50% routed to Likud) and NEW_STRADDLER
# drains it again; a third drain would count one record three times.
# Harness numbers (trail_sat): see dossier s.41.
TRAIL_SAT_SOURCE = True
TRAIL_SAT_CAP = 0.75
TRAIL_SAT_EXCLUDE = {"amcha_yisrael"}


def trail_transfer(shares, g, lk, src, base, cap=TRAIL_SAT_CAP):
    """Zero-sum move of g (share units, one value per draw) INTO column lk
    out of the `src` columns, in proportion to each source column's share in
    that draw and capped at `cap` x the source pool in that draw; whatever
    the pool cannot pay (all of it when the pool is empty) comes from the
    remaining columns in proportion to `base`. Negative g runs the other
    way (lk pays the sources). Shared by project() and the harness's
    project_cycle so both use identical geometry. Returns (shares,
    overflow), overflow = mean fraction of positive g paid by the field."""
    k = shares.shape[1]
    src = np.asarray(src, bool).copy()
    src[lk] = False
    pw = np.where(src[None, :], np.clip(shares, 0, None), 0.0)
    pool = pw.sum(axis=1)
    from_src = np.where(g > 0, np.minimum(g, cap * pool), g)
    from_src = np.where(pool > 0, from_src, 0.0)
    rest = g - from_src
    w_src = pw / np.maximum(pool, 1e-12)[:, None]
    field = np.ones(k, bool)
    field[lk] = False
    if (field & ~src).any():
        field &= ~src
    w_f = np.where(field, base, 0.0)
    w_f = w_f / w_f.sum()
    out = shares.copy()
    out[:, lk] += g
    out -= from_src[:, None] * w_src + rest[:, None] * w_f[None, :]
    pos = g > 0
    overflow = float(rest[pos].sum() / g[pos].sum()) if pos.any() else 0.0
    return out, overflow
LIST_SHOCK_BASE = _P["resid_base"]
LIST_SHOCK_SLOPE = _P["resid_slope"]
# A list with no polls in its final weeks has left the race by election day.
WITHDRAWN_WEEKS = 5
# Candidate gone14 (2026-10-10, dossier s.41) - OFF. WITHDRAWN_DAYS_LATE =
# 14 drops a list unpolled for more than 14 days when the projection date
# is within WITHDRAWN_LATE_GATE days of the election (35 days otherwise);
# GONE_STAY_ZERO keeps a dropped list at zero through the residual shock
# (without it the shock's floor sd resurrects it at a ~0.55-0.75% mean).
# Mirrored in validate_bayes (layers gone_days / gone_gate / gone_zero).
# Harness, fixed list mask: both on = eve median 1.496 -> 1.470 (1 win /
# 7 ties), D-21 mean 1.857 -> 1.709, Brier .070 -> .055, cov .973 -> .979,
# D-56 tie; the D-21 gain is off-ballot phantoms. 2026: removes Unity's
# frozen-latent fold transfer (P(NB>=61) .217 -> .212, Likud -0.45 seats).
WITHDRAWN_DAYS_LATE = 14
WITHDRAWN_LATE_GATE = 28
GONE_STAY_ZERO = True
# Candidate resid_relcap (2026-10-13, dossier s.42) - OFF until graded. The
# residual shock is additive (1.83 + 0.044 x seats, in seats), so a list
# polled at 0.3% draws a ~1.4 pp sd shock (x1.35 if first-cycle) that the
# zero clip turns into a ~0.7-0.9% mean. Harmless while only established
# lists were modelled; with every polled list in the latent it would add
# several pp of phantom small-party vote. Cap: sd <= RESID_REL_CAP x the
# list's own projected share. Mirrored in validate_bayes (resid_relcap).
RESID_REL_CAP = None

# Small-party layer, two measured pieces:
#
# 1. MICRO_POLLED — what pollsters measure today, from the footnote
#    itemizations of the firms publishing full percentages (Jul-Aug 2026,
#    Lazar/Midgam/Filber/Direct Polls/Maagar).
MICRO_POLLED_RETIRED = {
    # Kept for the record (13 Oct 2026). These lists are now LATENT COLUMNS
    # like every other polled list (owner: "treat all the lists that have
    # polls equally"): their archive footnote itemizations
    # (scrape_polls.footnote_items) and CEC filing shares enter the
    # likelihood, with house effects, the random walk and every projection
    # layer - the same treatment the harness has always given small lists
    # in past cycles (NEP 2021, Jewish Home 2022, Zehut 2019 are graded
    # there as ordinary blocks).
    "noam": (0.006, 0.003), "haredi_public": (0.006, 0.003),
    "israel_first": (0.003, 0.002),
}
MICRO_POLLED = {}
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
# Lists that polled in 2026 but are not on the ballot (did not file or
# withdrew before filing); Unity (withdrew 4 Sept) stays a column so the
# registration mixture can route its polled support.
NOT_ON_BALLOT_2026 = {"makom_lekulanu", "fourth_quarter", "el_dagel", "fiery_youth",
                      "ale_yarok"}
MIN_LIST_POLLS = 3
# The 2026 ballot is known (all 38 lists approved by the CEC on 27 Sept, with
# their letters), so the withdrawn rule below - built to catch lists that left
# the race - never drops a modelled list that is on the ballot. Today this
# only keeps Israel First (itemized 0.0-0.5% until 22 Sept, then folded into
# the pollsters' "others") instead of zeroing it. Unity withdrew and is not
# on the ballot, so the rule still removes it.
ON_BALLOT_2026 = {"likud", "yashar", "bennett_2026", "yesh_atid", "democrats",
                  "yisrael_beytenu", "shas", "utj", "otzma", "rzp", "raam",
                  "balad", "hadash_taal", "amcha_yisrael", "zionist_home",
                  "blue_white", "noam", "haredi_public", "israel_first", "ahi",
                  "beit_yisrael", "code_black"}
ABSORBED_IDS = {"zehut",   # inside RZP-Zehut from 2026-09-02 (see STRUCTURAL_BREAKS)
                "nep"}     # inside Reservists-Economic from 2026-09-06 (archive column "Reserv. - NEP" -> zionist_home)
# From these dates a CEC filing's separate line for the absorbed list (a
# scenario table left in the report) would double count voters already in
# the absorbing list's line: dropped before the filing is summed.
ABSORBED_FROM = {"zehut": "2026-09-02", "nep": "2026-09-06",
                 # Unity withdrew on Sept 4: a later filing line matching its
                 # keyword is a "unity government" question, not the list
                 "unity": "2026-09-05"}
# Lists whose COMPOSITION changed mid-campaign (2026-09-10, accuracy round
# four #5): observations taken before the change measured a different
# list, so they carry a noise multiplier - they still inform the level
# (the electorate is mostly the same) but cannot pin it, and the per-firm
# drift term is not fitted to a discontinuity. Reservists: Tropper left
# for Yashar and Zelekha's NEP joined (Sept 6); RZP: Zehut absorbed
# (Sept 2; the structural break already shifts the level, this widens it).
REFORMED_NOISE = {"zionist_home": ("2026-09-06", 1.5), "rzp": ("2026-09-02", 1.3)}
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
        # a poll that already published the merged column ("RZP - Zehut")
        # before the break date is not pre-merger data
        if "party_id" in obs.columns:
            m &= ~obs["party_id"].astype(str).str.contains("zehut")
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

    # One poll per firm and fieldwork date: the archive carries "a/b"
    # variants of the same survey (with/without a list, joint vs split
    # Arab lists). Keeping both counts one sample twice (2026-09-03 audit:
    # 14 extra polls in the window, one pair byte-identical). Keep the most
    # complete configuration - the variant with the most list rows.
    rows_per = win.groupby("poll_id").size()
    order = (win.drop_duplicates("poll_id")[["poll_id", "pollster", "fieldwork_end"]]
             .assign(n=lambda d: d["poll_id"].map(rows_per))
             .sort_values(["pollster", "fieldwork_end", "n", "poll_id"],
                          ascending=[True, True, False, True]))
    keep_ids = order.drop_duplicates(["pollster", "fieldwork_end"])["poll_id"]
    dropped = win["poll_id"].nunique() - len(keep_ids)
    if dropped:
        print(f"same-day variants dropped: {dropped} polls")
    win = win[win["poll_id"].isin(set(keep_ids))]

    # Lists absorbed into another list before the fit window's end are not
    # separate columns: the archive keeps a standalone "Zehut" column for
    # its pre-merger polls, but that support is carried inside the RZP
    # stream by the structural break (below), and a Zehut column of its
    # own would count the same voters twice.
    win = win[~win["party_id"].isin(ABSORBED_IDS)]
    # Every list ON THE BALLOT with polling is a latent column (13 Oct 2026,
    # MICRO_POLLED retired). Lists that did not file are dropped, and a
    # list needs MIN_LIST_POLLS polls in the window to be identified.
    if modern_remaps:
        win = win[~win["party_id"].isin(NOT_ON_BALLOT_2026)]
        n_polls_list = win.groupby("party_id")["poll_id"].nunique()
        # legal filings that itemize the list count as polls too
        try:
            _pc = pd.read_csv(PROCESSED_DIR / "cec_party_pcts.csv",
                              parse_dates=["fieldwork_end"], dtype={"ref": str})
            _pc = _pc[(_pc["fieldwork_end"] >= win["fieldwork_end"].min())
                      & (_pc["fieldwork_end"] <= win["fieldwork_end"].max())]
            n_polls_list = n_polls_list.add(_pc.groupby("party_id")["ref"].nunique(),
                                            fill_value=0)
        except FileNotFoundError:
            pass
        n_polls_list = n_polls_list[n_polls_list.index.isin(set(win["party_id"]))]
        thin = set(n_polls_list[n_polls_list < MIN_LIST_POLLS].index)
        if thin:
            print(f"lists below {MIN_LIST_POLLS} polls in the window, not modelled: {sorted(thin)}")
            win = win[~win["party_id"].isin(thin)]
        # Firms with no series and no track record whose one entry is an
        # outlier (the archive's "S.M.L.T." row is the DRI filing, see
        # scrape_cec.EXCLUDED_EDITORS) do not enter the likelihood.
        win = win[~win["pollster"].isin(EXCLUDE_POLLSTERS)]

    blocks = merge_blocks(win["party_id"].unique())
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    win["block"] = win["party_id"].map(lambda p: block_of[p.split("+")[0]])

    obs = implied_share_obs(win)
    if modern_remaps:
        obs = _merge_cec(obs, block_of, asof)
    if modern_remaps:
        # Re-formed lists: widen every observation taken before the change
        # (table-derived and filed alike; see REFORMED_NOISE).
        if "noise_mult" not in obs.columns:
            obs = obs.assign(noise_mult=1.0)
        obs["noise_mult"] = obs["noise_mult"].fillna(1.0)
        for pid, (since, mult) in REFORMED_NOISE.items():
            if pid in block_of:
                pre = (obs["block"] == block_of[pid]) & (obs["fieldwork_end"] < pd.Timestamp(since))
                obs.loc[pre, "noise_mult"] *= mult
                if pre.any():
                    print(f"re-formed list {pid}: {int(pre.sum())} pre-{since} obs x{mult} noise")
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
        "on_ballot": (np.array([bool(blocks[bk] & ON_BALLOT_2026) for bk in latent_blocks])
                      if modern_remaps else np.zeros(len(latent_blocks), bool)),
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
    for pid, since in ABSORBED_FROM.items():
        pcts = pcts[~((pcts["party_id"] == pid) & (pcts["fieldwork_end"] >= since))]
    # Duplicate filings: a firm sometimes files the same survey twice
    # (Lazar's Walla/Maariv reports 4120/4121; Direct Polls 4136/4138) -
    # identical party vectors within 3 days count once (first ref kept).
    sig = (pcts.sort_values(["ref", "party_id"])
           .groupby("ref").agg(pollster=("pollster", "first"), fw=("fieldwork_end", "first"),
                               vec=("raw_pct", lambda v: tuple(np.round(v.values, 2)))))
    dup_refs = set()
    seen = []
    for ref, r in sig.sort_index().iterrows():
        if any(p == r.pollster and v == r.vec and abs((f - r.fw).days) <= 3 for p, f, v in seen):
            dup_refs.add(ref)
        else:
            seen.append((r.pollster, r.fw, r.vec))
    if dup_refs:
        print(f"CEC duplicate filings dropped: {sorted(dup_refs)}")
        pcts = pcts[~pcts["ref"].isin(dup_refs)]
    sums = pcts.groupby("ref")["raw_pct"].sum()
    # A filing is trusted when its party table accounts for the sample:
    # parties alone within 90-105%, or parties plus the undecided share the
    # filing reports separately within 95-105% (Maagar Mochot files 86-89%
    # of parties beside a 9-13% undecided line; the renormalisation below
    # then puts those lists on the same footing as everyone else).
    good = set(sums[(sums >= 90) & (sums <= 105)].index)
    try:
        und = pd.read_csv(PROCESSED_DIR / "cec_filings.csv", dtype={"ref": str}
                          ).set_index("ref")["undecided_pct"]
        tot = sums.add(und.reindex(sums.index).fillna(0.0))
        good |= set(tot[(sums >= 80) & (tot >= 95) & (tot <= 105)].index)
    except FileNotFoundError:
        pass
    pcts = pcts[pcts["ref"].isin(good)
                & (pcts["fieldwork_end"] <= asof)].copy()
    if pcts.empty:
        return obs

    remap = {"together": "bennett_2026"}
    rows, displaced = [], set()
    disp_by_ref = {}
    for ref, g in pcts.groupby("ref"):
        pollster = g["pollster"].iloc[0]
        fw = g["fieldwork_end"].iloc[0]
        near = obs[(obs["pollster"] == pollster)
                   & ((obs["fieldwork_end"] - fw).dt.days.abs() <= 3)]
        displaced |= set(near["poll_id"])
        disp_by_ref[ref] = set(near["poll_id"])
        for r in g.itertuples():
            comp = remap.get(r.party_id, r.party_id).split("+")[0]
            if comp not in block_of:
                continue
            rows.append({"poll_id": f"cec{ref}", "block": block_of[comp],
                         # renormalised to the filing's parsed party sum:
                         # a filing summing to 92% (undecided excluded)
                         # otherwise understates every list by 8% relative,
                         # which is decisive for threshold-straddlers
                         # (2026-09-03 Arab-lists audit)
                         "share": r.raw_pct / float(sums[ref]), "pollster": pollster,
                         "fieldwork_end": fw})
    cec_obs = pd.DataFrame(rows).groupby(
        ["poll_id", "block"], as_index=False).agg(
        share=("share", "sum"), pollster=("pollster", "first"),
        fieldwork_end=("fieldwork_end", "first"))
    kept = obs[~obs["poll_id"].isin(displaced)]
    # A filing replaces only the lists it REPORTS: the displaced table
    # poll's rows for blocks the filing lacks (lists the parser did not
    # find, or footnote itemizations of small lists the report omits) are
    # kept, so a list is never dropped from a poll that measured it.
    covered = cec_obs.groupby("poll_id")["block"].apply(set).to_dict()
    retained = []
    for ref, pids in disp_by_ref.items():
        have = covered.get(f"cec{ref}", set())
        if not have:
            continue
        extra = obs[obs["poll_id"].isin(pids) & ~obs["block"].isin(have)]
        if len(extra):
            retained.append(extra.drop_duplicates(["block"]))
    if retained:
        kept = pd.concat([kept] + retained, ignore_index=True)
        LAST_CEC_MERGE["table_rows_retained"] = int(sum(len(x) for x in retained))
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


def _certainty_layer(shares, comps, blocs, fams, rng, asof=None, exempt=None):
    """Soft-support churn + certainty-weighted allocation of the undecided
    pool. Operates on the share matrix (draws x lists); returns it
    renormalised. See the CERTAINTY block for sources.
    `exempt` (bool per list) switches churn off for lists whose desertion
    another layer owns (NEW_STRADDLER_CHURN_EXEMPT); their attraction weight
    is unchanged. Churn of unaligned lists (Blue and White, Reservists-
    Economic) is not redistributed - it is treated as abstention."""
    n, k = shares.shape
    cert = np.array([np.mean([CERTAINTY.get(c, CERTAINTY_DEFAULT) for c in cs])
                     for cs in comps])
    cert_churn = cert if exempt is None else np.where(exempt, 1.0, cert)
    is_nb = blocs == "netanyahu_bloc"
    is_op = blocs == "opposition_bloc"
    is_arab = fams == "arab"
    # defection rate: common Beta draw x per-list LogNormal idiosyncrasy
    m = CHURN_D_MEAN
    v = CHURN_D_SD ** 2
    kk = m * (1 - m) / v - 1
    d = rng.beta(m * kk, (1 - m) * kk, size=(n, 1))
    d = np.clip(d * np.exp(rng.normal(0, CHURN_LIST_SDLOG, size=(n, k))), 0, 0.8)
    churn = shares * (1 - cert_churn)[None, :] * d
    out = shares - churn
    attract = shares * cert[None, :]
    def spread(mass, mask):
        w = np.where(mask[None, :], attract, 0.0)
        tot = w.sum(axis=1, keepdims=True)
        return np.where(tot > 0, w / np.maximum(tot, 1e-12), 0.0) * mass[:, None]
    for own, other, key in ((is_nb, is_op, "netanyahu_bloc"), (is_op, is_nb, "opposition_bloc")):
        if not own.any():
            continue
        w_in, w_x, _w_abs = CHURN_SPLIT[key]
        pool = churn[:, own].sum(axis=1)
        out += spread(pool * w_in, own)
        if other.any():
            out += spread(pool * w_x, other)
        # the abstaining share simply leaves the pie
    if is_arab.any():
        pool = churn[:, is_arab].sum(axis=1)
        out += spread(pool * (1 - CHURN_ABSTAIN), is_arab)
    # undecided pool: N12 lean with its own sampling uncertainty (n~60)
    if is_nb.any() and is_op.any():
        beta = _lean_posterior(asof) if U_LEAN_TAU else U_LEAN_BETA
        f_anti = rng.beta(*beta, size=n)   # pooled posterior (see _lean_posterior)
        mag = np.exp(rng.normal(-0.5 * U_MAG_SDLOG ** 2, U_MAG_SDLOG, size=n))  # mean one
        excess = (f_anti - U_PROP_ANTI) / (U_LEAN_BASE - U_PROP_ANTI)
        if U_LEAN_PER_SIDE:   # share moved NB -> anti; the gap moves 2 x ub
            ub = U_POOL * U_TURNOUT * U_EXCESS_PER_SIDE * excess * mag
            # identity: 2 x per-side = s.11's gap excess 0.71*(0.55 - 0.04)
            assert np.isclose(2 * U_EXCESS_PER_SIDE, U_LEANED_FRAC * (
                (2 * U_LEAN_BASE - 1) - (2 * U_PROP_ANTI - 1)))
        else:
            ub = UNDECIDED_BREAK_SEATS / 120.0 * excess * mag
        print(f"undecided lean: pool {U_POOL:.3f}, leaned n {sum(beta) - U_PRIOR_N:.1f}, "
              f"lean {beta[0] / sum(beta):.3f}, mean transfer {ub.mean() * 120:.2f} seats "
              f"per side ({'per-side' if U_LEAN_PER_SIDE else 'shipped gap'} constant)")
        out += spread(np.maximum(ub, 0), is_op) - spread(np.maximum(ub, 0), is_nb)
        out += spread(np.maximum(-ub, 0), is_nb) - spread(np.maximum(-ub, 0), is_op)
    out = np.clip(out, 0, None)
    return out / out.sum(axis=1, keepdims=True)


def _first_cycle_ids() -> set:
    """Component ids with no polls before the 2026 cycle."""
    try:
        p = pd.read_csv(PROCESSED_DIR / "polls.csv", usecols=["cycle", "party_id"])
    except FileNotFoundError:
        return set()
    old = set(p[p["cycle"].astype(str) != "2026"]["party_id"].str.split("+").explode())
    now = set(p[p["cycle"].astype(str) == "2026"]["party_id"].str.split("+").explode())
    return {c for c in now if c not in old}


def _new_straddler_mask(comps, base) -> np.ndarray:
    """NEW_STRADDLER's band test: first-cycle lists whose projected share
    `base` sits within the band around the threshold."""
    new_ids = _first_cycle_ids()
    lo_b, hi_b = NEW_STRADDLER["band"]
    return np.array([cp <= new_ids and lo_b <= base[i] * 100 - THRESHOLD * 100 <= hi_b
                     for i, cp in enumerate(comps)], dtype=bool)


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
    eff_weeks *= RW_FORWARD_SCALE
    z_e = z_last + np.sqrt(eff_weeks) * tau * rng.standard_normal(z_last.shape)
    z_full = np.concatenate([z_e, np.zeros((N_PROJ, 1))], axis=1)
    shares = np.exp(z_full - z_full.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)

    # Lists with no polls in their final weeks have left the race.
    gone_days = 7 * WITHDRAWN_WEEKS
    if WITHDRAWN_DAYS_LATE is not None and days_ahead <= WITHDRAWN_LATE_GATE:
        gone_days = WITHDRAWN_DAYS_LATE
    gone = data["last_obs_day"] < -gone_days
    if "on_ballot" in data:
        gone = gone & ~data["on_ballot"]
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)
    project.last_gone = [data["components"][i] for i in np.nonzero(gone)[0]]

    # Per-list election-day shock: residual final-poll error beyond
    # bloc/family components, calibrated on the backtest.
    base0 = shares.mean(axis=0)
    sd_list = (LIST_SHOCK_BASE + LIST_SHOCK_SLOPE * base0 * 120) / 120.0 * RESID_SCALE * STACK_SCALE
    comps0 = [set(c.split("+")) for c in data["components"]]
    is_new = np.array([bool(cs & NEW_LIST_IDS) for cs in comps0])
    sd_list = np.where(is_new, sd_list * NEW_LIST_MULT, sd_list)
    for pid, m in SOFT_LIST_MULT.items():
        soft = np.array([pid in cs for cs in comps0])
        sd_list = np.where(soft, sd_list * m, sd_list)
    if RESID_REL_CAP is not None:
        sd_list = np.minimum(sd_list, RESID_REL_CAP * base0)
    if GONE_STAY_ZERO:
        # base-weighted layers below (swing, family, certainty, gevalt)
        # then leave the column at zero too
        sd_list = np.where(gone, 0.0, sd_list)
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
    if micro_draws:          # empty since every polled list is modelled (s.42)
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
    swing = rng.standard_t(T_DF, N_PROJ) * BLOC_SWING_SD * EVENT_RISK * STACK_SCALE / 120.0
    w_nb, w_op = np.where(is_nb, base, 0), np.where(~is_nb, base, 0)
    shares = shares + swing[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())

    # Certainty layer: soft support churns (asymmetric, list-specific),
    # churn and the undecided pool land by certainty-weighted attraction.
    exempt = (_new_straddler_mask(comps, base)
              if NEW_STRADDLER_ON and NEW_STRADDLER_CHURN_EXEMPT else None)
    shares = _certainty_layer(shares, comps, blocs, fams, rng, asof=data.get("asof"),
                              exempt=exempt)
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
        sd_f = sd_f * STACK_SCALE
        in_f = fams == f
        if f == "arab" and ARAB_FAMILY_FORM == "additive_e0":
            mu_f = _P["family_e0"]["arab"][0]      # raw-e0 mean, e1 sd kept
        elif f == "arab":
            # turnout mechanism (ARAB_TURNOUT): joint scaling of the Arab lists
            T_mean = ARAB_TURNOUT["mean_unified" if ARAB_LIST_UNIFIED else "mean_split"]
            T = np.clip(T_mean + tdraws[:, k] * ARAB_TURNOUT["sd"] * STACK_SCALE, 0.35, ARAB_TURNOUT["max"])
            r = T / ARAB_TURNOUT["base"]
            if ARAB_TURNOUT_K != 1.0:
                r = (1.0 + ARAB_TURNOUT_K * (T_mean / ARAB_TURNOUT["base"] - 1.0)
                     + (T - T_mean) / ARAB_TURNOUT["base"])
            project.last_arab_r_mean = float(r.mean())
            tot = shares[:, in_f].sum(axis=1)
            delta = (r - 1.0) * tot
            if ARAB_TURNOUT_INTERCEPT is not None:
                delta = delta - ARAB_TURNOUT_INTERCEPT / 120.0
            w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
            shares = shares + delta[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())
            continue
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
        if col is None or not ANCHORS_ON:
            continue
        onehot = np.zeros(len(comps))
        onehot[col] = 1.0
        w_r = np.where(onehot == 0, base, 0)
        shares = shares + (-mu / 120.0) * (onehot - w_r / w_r.sum())

    # New-straddler desertion (see NEW_STRADDLER): first-cycle lists whose
    # projected share sits in the threshold band.
    if NEW_STRADDLER_ON:
        in_band = _new_straddler_mask(comps, base)
        hit = []
        for i, cp in enumerate(comps):
            if in_band[i]:
                g = rng.normal(NEW_STRADDLER["mu"], NEW_STRADDLER["sd"], N_PROJ) / 100.0
                onehot = np.zeros(len(comps)); onehot[i] = 1.0
                w_r = np.where(onehot == 0, base, 0)
                shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]
                hit.append("+".join(sorted(cp)))
        shares = np.clip(shares, 0, None)
        project.last_new_straddlers = hit
        if hit:
            print(f"new-straddler desertion applied to: {hit}")

    # Trailing-Likud conditional (see TRAIL): fires only when Likud's
    # projected standing trails or ties the largest non-bloc list.
    project.last_trail_on, project.last_trail_margin = False, None
    project.last_trail_overflow = None
    if TRAIL_ON and likud_col is not None:
        non_nb = [i for i in range(len(comps)) if blocs[i] != "netanyahu_bloc" and i != likud_col]
        if non_nb:
            project.last_trail_margin = float((base[likud_col] - base[non_nb].max()) * 120.0)
        if non_nb and base[likud_col] * 120.0 <= base[non_nb].max() * 120.0 + TRAIL["margin"]:
            g = rng.normal(TRAIL["mu"], TRAIL["sd"], N_PROJ) * TRAIL["scale"] / 120.0
            src = np.array([bool(cs & (GEVALT_SAT_IDS - TRAIL_SAT_EXCLUDE))
                            and blocs[i] == "netanyahu_bloc"
                            for i, cs in enumerate(comps)])
            if TRAIL_SAT_SOURCE and src.any():
                shares, project.last_trail_overflow = trail_transfer(
                    shares, g, likud_col, src, base)
            else:
                onehot = np.zeros(len(comps)); onehot[likud_col] = 1.0
                w_r = np.where(onehot == 0, base, 0)
                shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]
            project.last_trail_on = True

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
    if am is not None and not AMCHA_FADE_RETIRED:
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

    # Surplus pairs via the shared resolver (simulate.PAIR_RESOLVER_FIX,
    # dossier s.40): first occurrence wins, so the appended "Balad (alone)"
    # column cannot capture 'balad' from the Joint List block, and
    # 'together' resolves to the bennett_2026+yesh_atid block. With the fix
    # on (8 Oct posterior, same seed, both pairs together): JL+Ra'am +1 seat
    # in 30% of draws, Together+YB +1 in 35% (-1 in 1% each, the other
    # pair's remainder); P(NB>=61) 19.4 -> 17.8; central seats unchanged.
    pairs, _, dropped = _sim.resolve_pairs(SURPLUS_PAIRS, comps,
                                           aliases=_sim.PAIR_ALIASES_2026)
    if dropped and _sim.PAIR_RESOLVER_FIX:
        print(f"WARNING surplus pairs not resolved (not pooled): {dropped}")
    project.last_pairs = [(labels[a], labels[b]) for a, b in pairs]

    # Expose the final projected share distribution's mean vector: the
    # official forecast allocates the central seats from it (one pass
    # through the seat law), so the point estimate and the intervals come
    # from the same distribution.
    project.last_share_mean = shares.mean(axis=0)
    # The harness scores the MEDIAN as the better point estimate (MAE 1.57
    # vs 1.67 for the mean, in every ablation configuration): threshold
    # deaths skew the means of straddling lists downward.
    project.last_share_median = np.median(shares, axis=0)
    project.last_labels = list(labels)
    project.last_components = ["+".join(sorted(c)) for c in comps]
    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        sh = shares[i]
        passed = sh >= THRESHOLD
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers = _sim.form_factions(pairs, passed, votes)
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
    import os
    if os.environ.get("BAYES_PROJECT_ONLY") == "1":
        # re-project from the saved posterior (no refit; fit_summary kept)
        import arviz as az
        project_and_write(data, az.from_netcdf(PROCESSED_DIR / "m3_idata.nc"), rng)
        return

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
    project_and_write(data, idata, rng)


def project_and_write(data, idata, rng) -> None:
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
    # Owner ruling 2026-09-09: the change bloc "without Arab seats" is the
    # opposition lists alone - Segalovitz's seat (Ra'am slot #2) is no
    # longer added to it; it counts only where Ra'am counts as a whole.
    anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
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
