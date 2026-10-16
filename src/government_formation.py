"""Government-formation model: from simulated Knessets to P(government).

Runs every posterior seat draw (bayes_draws.parquet) through an explicit
coalition-formation tree. Unlike the polling model, this layer cannot be
estimated from data — coalition behavior has no likelihood — so it is
scenario analysis with parameterized political assumptions, every one
stated below and stress-tested in the sensitivity grid.

Behavioral assumptions (BEHAVIOR, drawn independently per simulation):
    amcha_right / amcha_center   Amcha Yisrael's unknown alignment
    raam_joins                   Ra'am sits IN a centre coalition (2021
                                 precedent); raam_supports = outside
                                 confidence-and-supply
    jl_supports                  Joint List outside support to block a
                                 Netanyahu government (2019-20 precedent)
    shas_defects / utj_defects   each haredi party separately crosses to a
                                 centre government once the Netanyahu path
                                 is arithmetically dead (UTJ transactional
                                 per the draft-law channel; Shas locked in)
    likud_sans_bibi              Likud ditches Netanyahu for a unity
                                 government as a last resort

Formation order per draw (who can actually assemble 61 first):
    1. Netanyahu bloc (+Amcha if right-aligned)            -> Netanyahu VI
    2. centre bloc (+Amcha if centre-aligned)              -> centre coalition
    3. centre + Ra'am inside                               -> centre + Ra'am
    4. centre + haredi defection                           -> centre-haredi
    5. centre minority with outside support (Ra'am/JL)     -> minority govt
    6. a centre list breaks its pledge and joins Netanyahu -> pledge-break
       (graded in validate_formation.py: without this branch the tree gave
       the realized 2020 outcome probability zero)
    7. unity: centre + Likud without Netanyahu             -> unity govt
    8. nothing reaches 61                                  -> repeat election
    9. post-deadlock stage (2026-10-15, dossier s.49): in a DEADLOCK - no
       side reaches 61 with its own lists plus the unaligned lists (and
       Amcha) that sided with it - WHETHER a government forms is drawn from
       the Israeli record (Beta posterior on DEADLOCK_RECORD: 2 repeats in 7
       parliamentary-era deadlocks), and WHICH government forms comes from
       the gates above (resampled until one fires). Outside a deadlock
       nothing changes; switched off, the stream is bit-identical to the
       pre-stage tree.

Outputs:
    data/processed/government_formation.csv     outcome probabilities
    data/processed/government_sensitivity.csv   assumption stress test
    data/processed/government_deadlock.csv      the deadlock stage's numbers
    output/figures/government_2026.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE
from scrape_polls import PROCESSED_DIR

SEED = 20261027

NB_CORE = ["Likud", "Otzma Yehudit", "Shas", "United Torah Judaism",
           "Religious Zionist Party", "Noam", "Zehut"]
# The Netanyahu bloc as the site's headline counts it (template BLOC "nb"):
# the seat axis of government_by_nb.csv (s.52)
NB_SITE = NB_CORE + ["Amcha Yisrael", "The Haredi Public"]
NB_K_LO, NB_K_HI = 44, 68
CENTRE = ["Yashar", "Bennett 2026 + Yesh Atid", "The Democrats",
          "Yisrael Beytenu"]
# Kingmakers (owner ruling 2026-09-03): neither list is a change-bloc
# member. Each draw sends its seats right, centre, or neither by the
# side priors below (Gantz: 2020 precedent of joining Netanyahu; Erdan
# and Edelstein: Likud alumni).
UNALIGNED = {"Blue and White": ("bw_right", "bw_centre"),
             "Unity": ("unity_right", "unity_centre"),
             # Owner ruling 2026-09-09: the Reservists-Economic list (Hendel,
             # Zelekha, Wilf) is counted like Blue and White - a kingmaker.
             "Reservists – Economic Party": ("res_right", "res_centre")}
HAREDI = ["Shas", "United Torah Judaism"]
JOINT_LIST = "Balad + Hadash-Ta'al"
RAAM = "Ra'am"
AMCHA = "Amcha Yisrael"

BEHAVIOR = {
    # Ofer Winter (Aug 27): "we will only recommend him [Netanyahu]" —
    # public, repeated, cheap to honor at the President's Residence
    # (JPost/Haaretz Aug 27); analysts doubt everything after that stage.
    # 2026-10-10: 0.87 -> 0.60 (NEFF 35 -> 15). The tree adds Amcha's seats
    # to the Netanyahu bloc's 61, so this is P(JOINS), not P(recommends);
    # Winter separated the two on 2 Sept: he recommends Netanyahu but joins
    # only if a national service law passes BEFORE the government is sworn
    # in, and recommending "does not commit the party to join"
    # (https://www.israelnationalnews.com/news/432614; Maariv 1362429;
    # Jewish Insider Oct 2026). Tripwire: if Winter signs Hendel's proposed
    # 8 Oct "Zionist government only" declaration (JPost 911020), move
    # Amcha into ZIONIST_ONLY below as well.
    "amcha_right": 0.60,
    # Winter deep-dive (Aug 30): the promotion-saga grudge is against
    # EISENKOT, not Liberman — Winter served as Liberman's military
    # secretary, Liberman publicly defends him (Srugim Aug 28), and Winter
    # vowed "I will do everything I can to prevent [Eisenkot's government]
    # from being formed" (INN Aug 27). So amcha_center is CONDITIONAL in
    # simulate_formation: it applies only in draws where Together outranks
    # Yashar (a Bennett-led centre government); under an Eisenkot-led one
    # Amcha's join probability is floored near zero (AMCHA_JOIN_EISENKOT).
    "amcha_center": 0.30,
    # Segalovitz-Ra'am deal OFFICIAL as of 2026-09-01 — the previous
    # values were deal-probability-weighted blends (P(deal)~0.8); with
    # the deal certain they unweight to the conditional-on-deal levels.
    # Eisenkot's camp published Ra'am-shaped entry conditions (Walla
    # Aug 16) but every Jewish party still pledges no Arab party INSIDE
    # at the outset — entry is modeled as post-formation expansion,
    # hence joins < supports.
    "raam_supports": 0.60,
    # Ra'am joins a change coalition outright (2021 precedent; the
    # Segalovitz bridge and Eisenkot's published entry conditions make
    # it live, the universal no-Arab-party-inside pledges cap it).
    "raam_joins": 0.40,
    # JL revived with Jabareen #1/Tibi #2 (ToI late Aug); Hadash-led list
    # likelier to abstain constructively than Balad-led; Tibi placated.
    "jl_supports": 0.45,
    # Split haredi defection, institution-derived (Aug 31 desk):
    # Shas — crossing now needs one psak from Yitzhak Yosef (newly
    # empowered, privately called Eisenkot "a warm Jew who can be
    # trusted"; the 1992 Ovadia precedent proves the mechanism), but the
    # centre's shared anti-exemption identity leaves no deal space ->
    # 0.10. UTJ — a full signature needs BOTH Moetzes incl. Gur; the
    # likelier form is a Degel-only partial (2004-06 Agudah-alone
    # precedent). Full-equivalent blend: 0.15 full + 0.22 partial x 1/2.
    # 2026-10-10: utj_defects 0.26 -> 0.15. Maariv/JPost 17 Sept: the
    # haredi parties lean to "recommend nobody" and sit in opposition for
    # about a year while the next government settles the draft law
    # (https://www.jpost.com/israel-election-2026/article-908924); UTJ chair
    # Asher, 29 Sept: no UTJ faction backs any government until the
    # exemption is "legally settled" (ToI); Eisenkot prefers another
    # election to compromising on the draft. 0.15 = the old "full UTJ"
    # term alone; the Degel-partial term is dropped. The reported Gur
    # (Goldknopf/Tessler) ABSTENTION on an Eisenkot minority is a separate,
    # weaker channel - see UTJ_ABSTAINS below (sensitivity only).
    "shas_defects": 0.10,
    "utj_defects": 0.15,
    # Liberman's haredi veto is his electoral identity since 2019
    # ("not a millimeter"); he relents on sitting WITH haredim only
    # rarely -> the centre-haredi branch must clear 61 without YB unless
    # this fires.
    "liberman_haredi_ok": 0.20,
    # 2026-10-15 (dossier s.49): set from the record, not by hand. No
    # Israeli party has dropped its sitting leader after an election to form
    # a government; all three unity governments kept both leaders (1984
    # Peres/Shamir rotation, 1988 Shamir with Peres, 2020 Netanyahu/Gantz;
    # COA-F24 verified, atlas D10-F24). Jeffreys on 0 of 3 = Beta(0.5, 3.5),
    # mean 0.125, NEFF 4. The old 0.18 rested on "unity resolved ~half of
    # deadlocks (1984/1988/2020)", but 1988 was not a deadlock (the
    # right-religious bloc held 65) and none of the three dropped a leader.
    # Narrower classes give less (0 of 5 deadlocks with a unity on the
    # table -> 0.083; 0 of 7 stage deadlocks -> 0.0625): sensitivity rows.
    # The one comparative case (PSOE, Oct 2016) came after two failed
    # elections. Herzog's plea-deal / unity push (NYT/JNS/ToI) is a
    # tripwire, not a prior.
    "likud_sans_bibi": 0.125,
    # Eisenkot has made the 58-59-seat minority government explicit
    # doctrine (ToI Aug 23); Liberman's stated veto ("no minority
    # government, no safety net", N12) is the binding constraint. He
    # relents in a minority of draws — under Herzog's unity-at-any-cost
    # pressure and with the alternative being Netanyahu VI or a sixth
    # election, vetoes of this kind have folded before (his own 2020
    # abstention precedent).
    "liberman_minority_ok": 0.25,
    # The branch the formation grading exposed (P(2020)=0 without it): a
    # centre list joins a Netanyahu-led government. Historical base rate
    # among feasible cases 1/3 (2020 yes; 2019a/2019s no); tempered to 0.12
    # for 2026, where all four centre parties were founded on never-Bibi —
    # as was Gantz's in 2019, which is why it isn't zero.
    "centre_defects": 0.12,
    # Kingmaker side priors (declared; residual = sits out / opposition)
    "bw_right": 0.40, "bw_centre": 0.45,
    "unity_right": 0.60, "unity_centre": 0.25,
    # Hendel: New Hope minister in the Bennett-Lapid government (2021),
    # refused Netanyahu in 2021-22, on record in 2026 against a Netanyahu
    # government AND against haredi/Arab partners ("a Zionist coalition");
    # Zelekha and Wilf are anti-Netanyahu. Lower right-side prior than
    # Gantz (who joined Netanyahu in 2020), a larger sit-out residual
    # because his stated conditions rule out most feasible coalitions.
    # 2026-10-10: the conditions are now STRUCTURAL (ZIONIST_ONLY below:
    # the list's centre-side seats count only in coalitions with no haredi
    # or Arab partner), so the sit-out residual no longer stands in for
    # them. Hendel (JPost 906335, 23 Aug): "our mission is solely to
    # establish a Zionist government" - he will not "complete a 61-seat
    # majority with the haredim", nor be the 61st seat of an Arab-backed
    # opposition government. Every feasible right-side close is Netanyahu +
    # Shas + UTJ, so res_right is now the probability of breaking that
    # pledge: 0.30 -> 0.12 (NEFF 12). res_centre 0.45 -> 0.70 now reads as
    # "joins a Zionist-only centre coalition"; the residual sit-out falls
    # 0.25 -> 0.18 (near Gantz's 0.15), so the conditions are not counted
    # twice (once in the gate, once in the residual).
    "res_right": 0.12, "res_centre": 0.70,
}

# Lists whose centre-side seats count only in a coalition with no haredi
# and no Arab partner (2026-10-10, Hendel's stated rule - see res_right).
# Empty set = the pre-10 Oct tree.
ZIONIST_ONLY = {"Reservists – Economic Party"}

# UTJ confidence-vote abstention on a JL-backed centre minority
# (2026-10-10). Ch12 via ToI 28-29 Sept: Gur MKs Goldknopf and Tessler plan
# to abstain on an Eisenkot-led government in a deadlock - one unsourced
# report, rebuffed the same night by chair Asher ("no desire to topple or
# install anyone"). Kept OUT of the headline (0.0) and carried as a
# sensitivity row at 0.25 until a second source confirms it. When on, only
# Agudah's share of UTJ's seats (Gur's faction, ~4 of 7) abstains, drawn
# from its own generator so the rest of the tree's random stream is
# unchanged.
UTJ_ABSTAINS = 0.0
AGUDAH_SHARE = 4 / 7

# PM allocation WITHIN a winning coalition — rotations are the Israeli norm
# (Bennett was PM with 7 seats in 2021). Probabilities are judgment,
# conditioned on the coalition type; rows sum to 1.
# Lapid is set to zero by editorial judgment: by taking the No. 2 slot in
# Bennett's Together alliance he subordinated his rotation claim — the 2021
# mechanism (Lapid gifting Bennett the first rotation from outside) cannot
# repeat from inside Bennett's own list. Cromwell's-rule caveat noted: a
# post-election faction split could resurrect a thin path (~0.2%); rounded
# to zero at the owner's call.
#           Eisenkot  Bennett  Liberman  Lapid  other
PM_ALLOC = {
    2: [0.75, 0.19, 0.04, 0.00, 0.02],   # change coalition (pure)
    3: [0.73, 0.21, 0.03, 0.00, 0.03],   # with unaligned / Amcha: closed by
                                          # Gantz/Hendel (Eisenkot-led) or by
                                          # Amcha (Bennett-led draws; the flip
                                          # rule makes Bennett the PM there)
    4: [0.64, 0.31, 0.00, 0.00, 0.05],   # with a haredi party: right-cred PM
                                          # helps, Liberman a dealbreaker
    5: [0.85, 0.10, 0.02, 0.00, 0.03],   # JL-backed minority: explicitly
                                          # Eisenkot's own doctrine
    8: [0.80, 0.13, 0.02, 0.00, 0.05],   # with Ra'am: the Segalovitz-bridge
                                          # scenario, Eisenkot's negotiation
    6: [0.35, 0.10, 0.05, 0.00, 0.50],   # unity: Likud successor/rotation heavy
}
PM_NAMES = ["Eisenkot", "Bennett", "Liberman", "Lapid",
            "rotation / Likud successor"]

# Evidence-quality concentrations for the behavioral parameters
# (2026-09-01, improvement #5): each BEHAVIOR value becomes
# Beta(p*n, (1-p)*n) with n reflecting how well-sourced the number is.
# High n = institutionally grounded or publicly pledged; low n =
# triangulated judgment. Drawn per hierarchical replication so the PM
# probabilities carry parameter uncertainty, not just seat uncertainty.
BEHAVIOR_NEFF = {
    "bw_right": 10, "bw_centre": 10, "unity_right": 12, "unity_centre": 10,
    "res_right": 12, "res_centre": 10,  # res_right: on-record pledge
    "amcha_right": 15,          # recommend pledge firm, JOINING conditional
    "amcha_center": 12,         # analog reasoning (Bennett-led condition)
    "raam_supports": 18,
    "jl_supports": 14,          # one Jabareen signal + precedent
    "shas_defects": 30,         # institutional (psak mechanism, re-lock)
    "utj_defects": 16,          # full/partial blend, two councils
    "liberman_haredi_ok": 25,   # identity veto, held at every fork
    "raam_joins": 18,           # desk-triangulated, deal official
    "liberman_minority_ok": 14, # doctrine vs veto, genuinely uncertain
    "likud_sans_bibi": 4,       # Jeffreys on 0 of 3: Beta(0.5, 3.5) (s.49)
    "centre_defects": 25,       # graded on the 2020 realization
}
PM_ALLOC_NEFF = 60              # Dirichlet concentration on rotation rows

# P(Amcha joins an Eisenkot-led centre government) — floored, not zeroed:
# Winter's vendetta is personal and public, but coalitions have bought
# stranger conversions (Cromwell caveat).
AMCHA_JOIN_EISENKOT = 0.03

# 2026-10-16 (dossier s.52): the owner's "Netanyahu + unaligned / defector
# coalition" is reported as two outcomes: closed by kingmakers / Amcha (1)
# and closed by a change-bloc list breaking its pledge (9, the 2020 Gantz
# path). The site groups them back under the owner's label. Codes 0-8 keep
# their meaning; the random stream is unchanged.
OUTCOMES = [
    "Netanyahu rightist coalition",
    "Netanyahu + unaligned / Amcha",
    "Change coalition (without Ra'am)",
    "Change coalition with unaligned / Amcha",
    "Change coalition with a haredi party",
    "Centre minority backed by the Joint List",
    "Unity government (Likud without Netanyahu)",
    "Repeat election",
    "Change coalition with Ra'am",
    "Netanyahu + a change-bloc defector",
]
# Who leads each outcome (site groups, s.52)
OUTCOME_GROUP = {0: "netanyahu", 1: "netanyahu", 9: "netanyahu",
                 2: "change", 3: "change", 4: "change", 5: "change", 8: "change",
                 6: "unity", 7: "repeat"}
PM_OTHER_UNITY = "Likud successor (unity)"
PM_OTHER = "another leader"


# Configuration-conditional gates (2026-09-03, Fable audit #4). The declared
# probabilities in BEHAVIOR are MARGINAL means; each draw's gate probability
# moves with the seat configuration through a logistic,
#     p = sigmoid(logit(p0) + beta * x),   x centred over the draws,
# so the marginal stays at p0 while pivotal configurations get more (or
# less) of it. Anchors, institutional record (text corrected 2026-10-15 per
# the COA verifier, s.49; the betas are unchanged):
#  - Shas joined non-Likud premiers when the right had no path and it was
#    a decisive partner: 1992 (Rabin), 1999 (Barak, PM directly elected),
#    2006 (Olmert), and the 1984 Peres-led unity. It also DECLINED viable
#    non-Likud premiers: 1990 (Peres), Oct 2008 (Livni, forcing the 2009
#    election) and Feb 2009 (recommended Netanyahu though Kadima was
#    largest), and it has joined none since 2006. UTJ joined only Barak in
#    1999, briefly (COA-F18 corrected, atlas D10-F28)
#    -> defection rises with the NB gap to 61 and when that party alone
#    closes the centre's gap;
#  - a centre list joined Netanyahu when a SMALL gap made one partner
#    sufficient (Gantz 2020, gap 3; no defector at gaps of 5-6 in 2019)
#    -> the defection gate falls with the gap;
#  - unity rises with deadlock depth: 1984 is the one deadlock resolved by
#    unity, and it kept both leaders. 1988 was NOT a deadlock (the
#    right-religious bloc held 65; Shamir chose unity anyway), and no
#    Israeli unity government has dropped a leader (COA-F24 verified), so
#    this beta has no direct record anchor; it is kept as judgment.
# Graded on the Israeli record 1977-2022 in validate_formation.py (s.49).
COND = {"gap_unit": 5.0,
        "haredi_beta_gap": 0.35, "haredi_beta_piv": 0.50,
        "defect_beta_gap": -0.35, "unity_beta_deadlock": 0.35}


def cond_prob(p0, x):
    """Logistic shift of a base probability by a centred covariate term."""
    p0 = np.clip(p0, 1e-4, 1 - 1e-4)
    return 1.0 / (1.0 + np.exp(-(np.log(p0 / (1 - p0)) + x)))


# Post-deadlock stage (2026-10-15, dossier s.49). The repeat election used to
# be the residual of every gate failing, which gave P(repeat | deadlock)
# about 0.6-0.7 against an Israeli record of 2 in 7. A DEADLOCK is an election
# after which no side reached 61 with its own lists plus the unaligned lists
# that sided with it; haredi crossings, Ra'am's seats, pledge-breaks, unity
# and minority investiture are the ways out (simulate_formation's
# `deadlock`). Seats and governments: ParlGov (view_election, view_cabinet)
# and the IDI election pages for 1984-2006; CEC results (results.csv) and
# the IDI pages for 2019-2021 (atlas D10-F22..F26, F28 verified; COA-F11,
# F15, F18 verified-corrected). position = place in a run of elections with
# no government formed in between (1 = the outgoing Knesset had one). The
# count uses the SAME event the stage conditions on; the conventional
# reading (1984, 2019a, 2019s, 2020, 2021: 2 of 5) leaves out 1992 and 2006,
# which are deadlocks on this arithmetic, and is a sensitivity row. 1999
# elected the PM directly (the parties faced a PM-elect): sensitivity only;
# 1996 was not a deadlock. Mid-term formations in a deadlocked Knesset
# (Peres Nov 1995, formed at 58-59 seats; Livni Oct 2008, failed -> the 2009
# election) are a sensitivity row too: the stage is about post-election
# formation.
#   cycle, position, regime, repeat?, how it ended
DEADLOCK_RECORD = [
    ("1984", 1, "parliamentary", False,
     "unity with rotation (Peres, then Shamir), inside Peres's first "
     "(extended) mandate; right 59, centre 53"),
    ("1992", 1, "parliamentary", False,
     "Labor-Meretz 56 + Shas 6; Hadash and ADP outside support; right 59"),
    ("2006", 1, "parliamentary", False,
     "Kadima-Labor-Meretz 53 + Gil 7 + Shas 12; right 50"),
    ("2019a", 1, "parliamentary", True,
     "Knesset dissolved before a government formed; right 60, YB 5 out"),
    ("2019s", 2, "parliamentary", True,
     "two mandates and the 21-day window lapsed; right 55, centre 44"),
    ("2020", 3, "parliamentary", False,
     "Gantz's faction joins Netanyahu (rotation); right 58, centre 47"),
    ("2021", 4, "parliamentary", False,
     "change + Yamina + Ra'am, Bennett PM (second mandate); right 52"),
    ("1999", 1, "direct", False,
     "PM-elect Barak + Shas, UTJ, NRP, Centre, YBA, Meretz; right 54"),
    ("1995m", 1, "midterm", False,
     "Peres II after Rabin's murder: Labor-Meretz-Yi'ud 58-59, Hadash and "
     "ADP outside"),
    ("2008m", 1, "midterm", True,
     "Livni fails (Shas and Degel refuse); Kadima-Labor-Gil-Meretz 60 -> "
     "the 2009 election"),
]
# the conventional deadlock list (desk COA, verified 2 of 5), for the
# sensitivity row: it is NOT the stage's event (it drops 1992 and 2006)
CONVENTIONAL_DEADLOCKS = ("1984", "2019a", "2019s", "2020", "2021")
REPEAT_PRIOR = (0.5, 0.5)   # Jeffreys
POST_DEADLOCK_STAGE = True
STAGE_RESAMPLE = 60         # gate re-draws to find WHICH government forms
STAGE_SEED_OFFSET = 4049    # own generators: the tree's stream is untouched


def deadlock_posterior(exclude=(), regimes=("parliamentary",), cycles=None,
                       prior=REPEAT_PRIOR):
    """Beta(a, b) posterior for P(repeat | deadlock) on the Israeli record."""
    rows = [r for r in DEADLOCK_RECORD if r[2] in regimes
            and r[0] not in exclude and (cycles is None or r[0] in cycles)]
    k = sum(1 for r in rows if r[3])
    return prior[0] + k, prior[1] + len(rows) - k


def load_draws():
    # Prefer the registration-mixture draws (they carry the RZP-Zehut
    # pass/fail and centre-fold events); fall back to the baseline draws.
    mix = PROCESSED_DIR / "mixture_draws.parquet"
    src = mix if mix.exists() else PROCESSED_DIR / "bayes_draws.parquet"
    d = pd.read_parquet(src)
    print(f"formation input: {src.name} ({len(d)} draws)")
    for col in NB_CORE + CENTRE + [JOINT_LIST, RAAM, AMCHA]:
        if col not in d.columns:
            d[col] = 0
    return d


def draw_behavior(rng) -> dict:
    """One parameter vector from the evidence-quality Beta priors."""
    out = {}
    for k, p in BEHAVIOR.items():
        n = BEHAVIOR_NEFF.get(k)
        out[k] = float(rng.beta(p * n, (1 - p) * n)) if n else p
    return out


def draw_pm_alloc(rng) -> dict:
    return {oc: rng.dirichlet(np.array(a) * PM_ALLOC_NEFF + 1e-3).tolist()
            for oc, a in PM_ALLOC.items()}


def simulate_formation(draws: pd.DataFrame, behavior: dict, seed=SEED,
                       pm_alloc=None, centres=None, unaligned=None):
    """One behavioural draw of the formation tree for every seat draw.

    centres: fixed centring constants for the COND covariates (keys gap_nb,
    piv_shas, piv_utj, dead). None = the input draws' own means (production).
    The record harness (validate_formation.py) passes the 2026 means so a
    single historical parliament is judged by the shipped gate functions.
    unaligned: {column: (right_key, centre_key)} kingmaker map (default
    UNALIGNED); the harness gives each historical kingmaker its own column.
    behavior["repeat_deadlock"]: P(repeat | deadlock) for the post-deadlock
    stage (absent or None = stage off).
    """
    rng = np.random.default_rng(seed)
    if pm_alloc is None:
        pm_alloc = PM_ALLOC
    n = len(draws)
    nb_core = draws[NB_CORE].sum(axis=1).values
    centre = draws[CENTRE].sum(axis=1).values
    raam = draws[RAAM].values
    jl = draws[JOINT_LIST].values
    amcha = draws[AMCHA].values
    yashar = draws["Yashar"].values
    together = draws["Bennett 2026 + Yesh Atid"].values

    u = rng.random((n, 7))
    # Winter's centre-join probability is conditional on WHO would lead:
    # near-zero under Eisenkot (sworn enemy), meaningful under a
    # Bennett-led government (Together > Yashar draws).
    amcha_center_eff = np.where(together > yashar,
                                behavior["amcha_center"],
                                AMCHA_JOIN_EISENKOT)
    amcha_side = np.select(
        [u[:, 0] < behavior["amcha_right"],
         u[:, 0] < behavior["amcha_right"] + amcha_center_eff],
        [1, 2], default=0)  # 1 right, 2 centre, 0 neither

    nb0 = nb_core + np.where(amcha_side == 1, amcha, 0)   # the bloc itself
    nb = nb0.copy()
    # Owner ruling 2026-09-09: Segalovitz's seat (Ra'am slot #2) is NOT
    # counted with the centre on its own; Ra'am enters whole or not at
    # all (the "with Ra'am" branch below).
    seg = np.zeros(n, dtype=int)
    ce0 = centre.copy()                           # the change lists alone
    ce_pure = centre                              # WITHOUT Amcha
    amcha_ce = np.where(amcha_side == 2, amcha, 0)

    # kingmakers: seats go right or centre by their side priors
    una_r = np.zeros(n)
    una_c = np.zeros(n)
    # ZIONIST_ONLY lists' centre-side seats: counted only where the
    # coalition has no haredi or Arab partner (unity, outcome 3, gap_ce)
    res_c = np.zeros(n)
    zo_seats = np.zeros(n)
    zo_right = np.zeros(n, dtype=bool)
    zo_centre = np.zeros(n, dtype=bool)
    king_sides = {}   # name -> (right mask, centre mask), for membership (s.52)
    for name, (kr, kc) in (UNALIGNED if unaligned is None
                           else unaligned).items():
        if name not in draws.columns:
            continue
        sv = draws[name].values
        uu = rng.random(n)
        una_r += np.where(uu < behavior[kr], sv, 0)
        cmask = (uu >= behavior[kr]) & (uu < behavior[kr] + behavior[kc])
        king_sides[name] = (uu < behavior[kr], cmask)
        if name in ZIONIST_ONLY:
            res_c += np.where(cmask, sv, 0)
        else:
            una_c += np.where(cmask, sv, 0)
        if name == "Reservists – Economic Party":   # diagnostic only
            zo_seats = sv.astype(float)
            zo_right, zo_centre = uu < behavior[kr], cmask
    nb = nb + una_r
    ce_pure = ce_pure + una_c

    # --- configuration-conditional gates (see COND) ---
    gap_nb = 61.0 - nb
    gap_ce = 61.0 - (ce_pure + res_c)
    shas_seats = draws["Shas"].values
    utj_seats = draws["United Torah Judaism"].values
    piv_shas = ((ce_pure < 61) & (ce_pure + shas_seats >= 61)).astype(float)
    piv_utj = ((ce_pure < 61) & (ce_pure + utj_seats >= 61)).astype(float)
    dead = np.minimum(gap_nb, gap_ce)
    c = centres if centres is not None else {
        "gap_nb": gap_nb.mean(), "piv_shas": piv_shas.mean(),
        "piv_utj": piv_utj.mean(), "dead": dead.mean()}
    simulate_formation.last_centres = {k: float(v) for k, v in c.items()}
    xg = (gap_nb - c["gap_nb"]) / COND["gap_unit"]
    p_shas = cond_prob(behavior["shas_defects"],
                       COND["haredi_beta_gap"] * xg
                       + COND["haredi_beta_piv"] * (piv_shas - c["piv_shas"]))
    p_utj = cond_prob(behavior["utj_defects"],
                      COND["haredi_beta_gap"] * xg
                      + COND["haredi_beta_piv"] * (piv_utj - c["piv_utj"]))
    p_defect = cond_prob(behavior["centre_defects"], COND["defect_beta_gap"] * xg)
    p_unity = cond_prob(behavior["likud_sans_bibi"],
                        COND["unity_beta_deadlock"] * (dead - c["dead"]) / COND["gap_unit"])
    # the remaining uniforms, in the order the pre-stage tree drew them
    r_utj = rng.random(n)
    # UTJ (Agudah share) abstains on a JL-backed minority; own generator so
    # the stream above and below is identical whatever UTJ_ABSTAINS is
    p_abst = behavior.get("utj_abstains", UTJ_ABSTAINS)
    a_abst = (np.random.default_rng(seed + 991).random(n) if p_abst > 0
              else None)
    r_lib_ok = rng.random(n)
    r_lib_har = rng.random(n)

    centre_seats = draws[CENTRE].values
    likud = draws["Likud"].values
    yb = draws["Yisrael Beytenu"].values
    # pledge-break: some centre list can close Netanyahu's gap
    gap = (61 - nb)[:, None]
    feasible = ((centre_seats >= gap) & (gap > 0)).any(axis=1)

    def gates(uu, r_utj, r_lib_ok, r_lib_har, a_abst):
        """The behavioural gates on the fixed configuration (kingmaker and
        Amcha sides held), in the tree's precedence order."""
        raam_joins = uu[:, 1] < behavior["raam_joins"]
        raam_supports = uu[:, 2] < behavior["raam_supports"]
        jl_supports = uu[:, 3] < behavior["jl_supports"]
        shas_on = uu[:, 4] < p_shas
        utj_on = r_utj < p_utj
        sans_bibi = uu[:, 5] < p_unity
        if a_abst is not None:
            utj_abst = (a_abst < p_abst) & ~utj_on
        else:
            utj_abst = np.zeros(n, dtype=bool)

        outcome = np.full(n, 7)  # default: repeat election
        outcome[(ce_pure + res_c + amcha_ce + likud >= 61) & sans_bibi] = 6
        outcome[(uu[:, 6] < p_defect) & feasible] = 9   # pledge-break (s.52)
        # minority: sworn by plurality with the JOINT LIST abstaining (the
        # named backer); a Ra'am abstention additionally lowers the bar
        abstaining = (np.where(jl_supports, jl, 0)
                      + np.where(raam_supports, raam - seg, 0)
                      + np.where(utj_abst, AGUDAH_SHARE * utj_seats, 0))
        present = 120 - abstaining
        lib_ok = r_lib_ok < behavior["liberman_minority_ok"]
        minority_ce = np.where(lib_ok, ce_pure, ce_pure - yb)
        outcome[jl_supports & (abstaining > 0)
                & (minority_ce > present / 2)] = 5
        defecting_haredi = (np.where(shas_on, shas_seats, 0)
                            + np.where(utj_on, utj_seats, 0))
        # Liberman won't sit WITH haredim (identity veto, ~0.80 held)
        lib_haredi = r_lib_har < behavior["liberman_haredi_ok"]
        ch_base = ce_pure + amcha_ce
        ch_seats = np.where(lib_haredi, ch_base, ch_base - yb) + defecting_haredi
        outcome[(ch_seats >= 61) & (defecting_haredi > 0)] = 4
        # change coalition WITH Ra'am inside: the camp is short alone and
        # Ra'am's remaining seats close it (Segalovitz's seat already in ce)
        outcome[(ce_pure < 61) & raam_joins
                & (ce_pure + (raam - seg) >= 61)] = 8
        # Owner taxonomy 2026-09-09: the change lists alone reach 61 (2), or
        # they are short and the UNALIGNED kingmakers and/or Amcha close the
        # gap (3); likewise Netanyahu's bloc alone (0), or short and closed
        # by unaligned seats or a pledge-breaking centrist (1).
        outcome[(ce0 < 61) & (ce_pure + res_c + amcha_ce >= 61)] = 3
        outcome[ce0 >= 61] = 2
        outcome[(nb0 < 61) & (nb >= 61)] = 1
        outcome[nb0 >= 61] = 0
        flags = {"shas_on": shas_on, "utj_on": utj_on, "lib_haredi": lib_haredi,
                 "lib_ok": lib_ok, "raam_supports": raam_supports,
                 "jl_supports": jl_supports}
        return outcome, flags

    outcome, flags = gates(u, r_utj, r_lib_ok, r_lib_har, a_abst)

    # --- post-deadlock stage (s.49) ---
    # deadlock: no side reaches 61 with its own lists plus the kingmakers
    # (and Amcha) that sided with it in this draw. Outside it the tree's
    # outcome is arithmetic (0-3); inside it the record decides WHETHER a
    # government forms and the gates decide WHICH one.
    deadlock = (nb < 61) & (ce_pure + res_c + amcha_ce < 61)
    tree_repeat = outcome == 7
    r_dead = behavior.get("repeat_deadlock")
    unresolved = 0
    if r_dead is not None:
        srng = np.random.default_rng(seed + STAGE_SEED_OFFSET)
        rep = srng.random(n) < r_dead
        outcome = outcome.copy()
        outcome[deadlock & rep] = 7
        need = deadlock & ~rep & tree_repeat
        for _ in range(STAGE_RESAMPLE):
            if not need.any():
                break
            oc2, fl2 = gates(srng.random((n, 7)), srng.random(n), srng.random(n),
                             srng.random(n),
                             srng.random(n) if a_abst is not None else None)
            fill = need & (oc2 != 7)
            outcome[fill] = oc2[fill]
            for k in flags:
                flags[k] = np.where(fill, fl2[k], flags[k])
            need &= ~fill
        unresolved = int(need.sum())   # no gate can fire: stays a repeat
    # the desk's narrower event (bloc cores only, Ra'am counted with the
    # change lists), for comparison with the site's earlier headline
    desk = (nb_core < 61) & (centre + raam < 61)
    simulate_formation.last_deadlock = {
        "p_deadlock": float(deadlock.mean()),
        "p_repeat_deadlock_tree": (float(tree_repeat[deadlock].mean())
                                   if deadlock.any() else float("nan")),
        "p_repeat_deadlock": (float((outcome == 7)[deadlock].mean())
                              if deadlock.any() else float("nan")),
        "p_deadlock_desk": float(desk.mean()),
        "p_repeat_desk": (float((outcome == 7)[desk].mean())
                          if desk.any() else float("nan")),
        "unresolved": unresolved,
    }

    # Diagnostic: P(Reservists' seats are counted in the government that
    # forms | the list passes) - right side in outcome 1; centre side in
    # 3/6 (and, when the list is not ZIONIST_ONLY, also in 4/5/8)
    c_oc = ([3, 6] if "Reservists – Economic Party" in ZIONIST_ONLY
            else [3, 4, 5, 6, 8])
    counted = ((zo_right & np.isin(outcome, [1, 9]))
               | (zo_centre & np.isin(outcome, c_oc)))
    passed = zo_seats > 0
    simulate_formation.last_res_counted = (
        float(counted[passed].mean()) if passed.any() else float("nan"))

    pm = np.full(n, "none (repeat election)", dtype=object)
    pm[outcome == 0] = "Netanyahu"
    pm[outcome == 1] = "Netanyahu"
    pm[outcome == 9] = "Netanyahu"
    u_pm = rng.random(n)
    for oc, alloc in pm_alloc.items():
        mask = outcome == oc
        cum = np.cumsum(alloc)
        pick = np.searchsorted(cum, u_pm[mask], side="right")
        pm[mask] = np.array(PM_NAMES)[np.minimum(pick, len(PM_NAMES) - 1)]
    # In coalitions where Together outweighs Yashar, the rotation flips:
    # Bennett leads and Eisenkot is the junior partner.
    flip = (together > yashar) & np.isin(outcome, [2, 3, 4, 5, 8])
    pm = np.where(flip & (pm == "Eisenkot"), "Bennett",
                  np.where(flip & (pm == "Bennett"), "Eisenkot", pm))
    # the allocation's last column: a Likud successor in a unity government,
    # someone outside the named leaders elsewhere (s.52)
    oth = pm == PM_NAMES[-1]
    pm = np.where(oth & (outcome == 6), PM_OTHER_UNITY,
                  np.where(oth, PM_OTHER, pm))

    # --- who sits in the government (s.52): membership implied by the gate
    # that formed it, with no new behavioural assumption. The pledge-breaker
    # of outcome 9 is NOT named (the record says that one happens, not who):
    # it is reported as its own row in government_membership.csv ---
    cols = list(draws.columns)
    member = np.zeros((n, len(cols)), dtype=bool)
    support = np.zeros((n, len(cols)), dtype=bool)
    sv_all = draws.values
    has = sv_all > 0
    j = {c: i for i, c in enumerate(cols)}
    nb_side = np.isin(outcome, [0, 1, 9])
    ch_side = np.isin(outcome, [2, 3, 4, 5, 6, 8])
    for c in NB_CORE:
        if c in j:
            member[:, j[c]] = nb_side & has[:, j[c]]
    if AMCHA in j:
        member[:, j[AMCHA]] = has[:, j[AMCHA]] & (
            (nb_side & (amcha_side == 1))
            | (np.isin(outcome, [2, 3, 4, 6]) & (amcha_side == 2)))
    for c in CENTRE:
        if c in j:
            inn = ch_side.copy()
            if c == "Yisrael Beytenu":
                inn &= ~((outcome == 4) & ~flags["lib_haredi"])
                inn &= ~((outcome == 5) & ~flags["lib_ok"])
            member[:, j[c]] = inn & has[:, j[c]]
    for c, (rmask, cmask) in king_sides.items():
        oc_c = [2, 3, 6] if c in ZIONIST_ONLY else [2, 3, 4, 5, 6, 8]
        member[:, j[c]] = has[:, j[c]] & ((nb_side & rmask)
                                          | (np.isin(outcome, oc_c) & cmask))
    if "Shas" in j:
        member[:, j["Shas"]] |= (outcome == 4) & flags["shas_on"] & has[:, j["Shas"]]
    if "United Torah Judaism" in j:
        member[:, j["United Torah Judaism"]] |= ((outcome == 4) & flags["utj_on"]
                                                 & has[:, j["United Torah Judaism"]])
    if "Likud" in j:
        member[:, j["Likud"]] |= (outcome == 6) & has[:, j["Likud"]]
    if RAAM in j:
        member[:, j[RAAM]] = (outcome == 8) & has[:, j[RAAM]]
        support[:, j[RAAM]] = (outcome == 5) & flags["raam_supports"] & has[:, j[RAAM]]
    if JOINT_LIST in j:
        support[:, j[JOINT_LIST]] = (outcome == 5) & flags["jl_supports"] & has[:, j[JOINT_LIST]]
    simulate_formation.last_member = (cols, member, support)
    return outcome, pm


def stage_draws(M: int, on: bool):
    """Per-parameter-vector P(repeat | deadlock) from the record's Beta
    posterior (own generator, so the behavioural stream is unchanged)."""
    if not on:
        return [None] * M
    a, b = deadlock_posterior()
    srng = np.random.default_rng(SEED + STAGE_SEED_OFFSET)
    return [float(x) for x in srng.beta(a, b, size=M)]


def main(out_dir=None, stage: bool = POST_DEADLOCK_STAGE) -> None:
    out_dir = Path(out_dir) if out_dir is not None else PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    draws = load_draws()

    # Hierarchical over parameter uncertainty: M parameter vectors from
    # the evidence-quality priors, each evaluated on all seat draws.
    M = 200
    prng = np.random.default_rng(SEED + 7)
    r_stage = stage_draws(M, stage)
    oc_mat = np.zeros((M, len(OUTCOMES)))
    pm_names_all = PM_NAMES[:-1] + [PM_OTHER_UNITY, PM_OTHER, "Netanyahu",
                                    "none (repeat election)"]
    groups = ["netanyahu", "change", "unity", "repeat", "netanyahu_in_office"]
    grp_mat = np.zeros((M, len(groups)))
    cols0 = list(draws.columns)
    mem_sum = np.zeros(len(cols0))
    sup_sum = np.zeros(len(cols0))
    # outcome group by the Netanyahu bloc's seats as the headline counts them
    nb_cols = [c for c in NB_SITE if c in draws.columns]
    nb_k = np.clip(draws[nb_cols].sum(axis=1).values.astype(int), NB_K_LO, NB_K_HI)
    kk = nb_k - NB_K_LO
    curve = np.zeros((NB_K_HI - NB_K_LO + 1, 4))
    pm_mat = np.zeros((M, len(pm_names_all)))
    res_counted = np.zeros(M)
    dl_keys = ["p_deadlock", "p_repeat_deadlock_tree", "p_repeat_deadlock",
               "p_deadlock_desk", "p_repeat_desk"]
    dl_mat = np.zeros((M, len(dl_keys)))
    unresolved = 0
    for m in range(M):
        b = draw_behavior(prng)
        pa = draw_pm_alloc(prng)
        if r_stage[m] is not None:
            b["repeat_deadlock"] = r_stage[m]
        oc, pmv = simulate_formation(draws, b, seed=SEED + m, pm_alloc=pa)
        res_counted[m] = simulate_formation.last_res_counted
        dl = simulate_formation.last_deadlock
        dl_mat[m] = [dl[k] for k in dl_keys]
        unresolved += dl["unresolved"]
        cnt = pd.Series(oc).value_counts(normalize=True)
        for i in range(len(OUTCOMES)):
            oc_mat[m, i] = cnt.get(i, 0.0)
        gi = np.array([["netanyahu", "change", "unity", "repeat"].index(OUTCOME_GROUP[int(o)])
                       for o in range(len(OUTCOMES))])[oc]
        for g in range(4):
            grp_mat[m, g] = (gi == g).mean()
        grp_mat[m, 4] = ((gi == 0) | (gi == 3)).mean()
        for g in range(4):
            curve[:, g] += np.bincount(kk, weights=(gi == g), minlength=curve.shape[0])
        _c, mem, sup = simulate_formation.last_member
        mem_sum += mem.mean(axis=0)
        sup_sum += sup.mean(axis=0)
        pcnt = pd.Series(pmv).value_counts(normalize=True)
        for j, nmn in enumerate(pm_names_all):
            pm_mat[m, j] = pcnt.get(nmn, 0.0)

    table = pd.DataFrame({
        "outcome": OUTCOMES,
        "probability": oc_mat.mean(axis=0).round(3),
        "p05": np.percentile(oc_mat, 5, axis=0).round(3),
        "p95": np.percentile(oc_mat, 95, axis=0).round(3),
    })
    table.to_csv(out_dir / "government_formation.csv", index=False)
    print(f"Government formation ({len(draws)} Knessets x {M} parameter "
          "vectors x behavioral draws; post-deadlock stage "
          f"{'ON' if stage else 'OFF'}):\n")
    print(table.to_string(index=False))

    # s.52 outputs: who leads, who sits in the government, and the outcome
    # group by the Netanyahu bloc's seat count
    gdf = pd.DataFrame({"group": groups,
                        "probability": grp_mat.mean(axis=0).round(3),
                        "p05": np.percentile(grp_mat, 5, axis=0).round(3),
                        "p95": np.percentile(grp_mat, 95, axis=0).round(3)})
    gdf.to_csv(out_dir / "government_groups.csv", index=False)
    passp = (draws.values > 0).mean(axis=0)
    mdf = pd.DataFrame({"list": cols0, "p_pass": passp.round(3),
                        "p_in_government": (mem_sum / M).round(3),
                        "p_outside_support": (sup_sum / M).round(3)})
    mdf["p_in_given_pass"] = np.where(passp > 0, mem_sum / M / np.maximum(passp, 1e-9),
                                      np.nan).round(3)
    mdf = mdf.sort_values("p_in_government", ascending=False)
    mdf.loc[len(mdf)] = ["(a change-bloc list joining Netanyahu)", np.nan,
                         round(float(oc_mat[:, 9].mean()), 3), 0.0, np.nan]
    mdf.to_csv(out_dir / "government_membership.csv", index=False)
    nk = np.bincount(kk, minlength=curve.shape[0]).astype(float)
    cdf = pd.DataFrame({"nb_seats": np.arange(NB_K_LO, NB_K_HI + 1),
                        "p_seats": (nk / nk.sum()).round(4), "n": nk.astype(int)})
    for g, name in enumerate(["netanyahu", "change", "unity", "repeat"]):
        cdf["p_" + name] = np.where(nk > 0, curve[:, g] / (M * np.maximum(nk, 1)), np.nan).round(3)
    cdf.to_csv(out_dir / "government_by_nb.csv", index=False)
    print("\nWho leads (groups):"); print(gdf.to_string(index=False))
    print("\nP(in the government) by list:"); print(mdf.to_string(index=False))
    print("\nOutcome group by Netanyahu-bloc seats:"); print(cdf.to_string(index=False))

    pm_df = pd.DataFrame({
        "pm": pm_names_all,
        "probability": pm_mat.mean(axis=0).round(3),
        "p05": np.percentile(pm_mat, 5, axis=0).round(3),
        "p95": np.percentile(pm_mat, 95, axis=0).round(3),
    }).sort_values("probability", ascending=False)
    pm_df = pm_df[pm_df.probability > 0.001]
    pm_df.to_csv(out_dir / "pm_probabilities.csv", index=False)
    pm_probs = pd.Series(pm_df.probability.values, index=pm_df.pm)
    print("\nP(next prime minister) [90% CI over parameter uncertainty]:")
    for r in pm_df.itertuples():
        print(f"  {r.probability:6.1%}  [{r.p05:.1%}-{r.p95:.1%}]  {r.pm}")
    print("\nP(Reservists' seats counted in the government formed | list "
          f"passes): {np.nanmean(res_counted):.3f}")

    # The deadlock stage's own numbers: P(deadlock), P(repeat | deadlock)
    # before the stage (the gates alone) and after it, and the same on the
    # desk's narrower event (bloc cores; Ra'am counted with the change
    # lists), which is what the site's earlier "~0.61" referred to.
    a_, b_ = deadlock_posterior()
    dl_df = pd.DataFrame({
        "quantity": dl_keys,
        "mean": dl_mat.mean(axis=0).round(3),
        "p05": np.nanpercentile(dl_mat, 5, axis=0).round(3),
        "p95": np.nanpercentile(dl_mat, 95, axis=0).round(3)})
    dl_df.loc[len(dl_df)] = ["record_beta_a", a_, np.nan, np.nan]
    dl_df.loc[len(dl_df)] = ["record_beta_b", b_, np.nan, np.nan]
    dl_df.loc[len(dl_df)] = ["stage_on", float(stage), np.nan, np.nan]
    dl_df.to_csv(out_dir / "government_deadlock.csv", index=False)
    print("\nDeadlock stage (deadlock = no side at 61 with its own lists and "
          "the kingmakers that sided with it):")
    print(dl_df.to_string(index=False))
    if stage:
        print(f"record: Beta({a_:g}, {b_:g}) = {a_ / (a_ + b_):.3f}; draws "
              f"left unresolved by the gate re-draws: {unresolved}")

    # Sensitivity (re-centred 2026-10-10 on the new central values):
    # UTJ defection x Amcha alignment grid, then one-at-a-time rows for
    # the Reservists' right side and the UTJ abstention channel; with the
    # stage on, its reference-class variants (s.49).
    r_central = a_ / (a_ + b_) if stage else None

    def _sens_row(**over):
        b = dict(BEHAVIOR, **over)
        if "repeat_deadlock" not in over:
            b["repeat_deadlock"] = r_central
        oc, pm_s = simulate_formation(draws, b)
        row = {"utj_defects": b["utj_defects"],
               "amcha_right": b["amcha_right"],
               "res_right": b["res_right"],
               "utj_abstains": b.get("utj_abstains", UTJ_ABSTAINS)}
        if stage:
            rd = b.get("repeat_deadlock")
            row["repeat_deadlock"] = None if rd is None else round(rd, 3)
            row["likud_sans_bibi"] = b["likud_sans_bibi"]
            row["p_successor_pm"] = round(float(
                (pm_s == PM_OTHER_UNITY).mean()), 3)
        row.update({
            "p_netanyahu_pm": round(float((pm_s == "Netanyahu").mean()), 3),
            "p_eisenkot_pm": round(float((pm_s == "Eisenkot").mean()), 3),
            "p_repeat_election": round(float((oc == 7).mean()), 3)})
        return row
    rows = [_sens_row(utj_defects=ud, amcha_right=ar,
                      amcha_center=min(0.9 - ar, 0.35))
            for ud in (0.05, 0.15, 0.30) for ar in (0.60, 0.80, 0.95)]
    rows += [_sens_row(res_right=rr) for rr in (0.12, 0.20, 0.30)]
    rows += [_sens_row(utj_abstains=ua) for ua in (0.0, 0.25)]
    if stage:
        # reference-class variants (s.49): the record; with 1999 (direct);
        # with the mid-term Oct 2008 failure; with both mid-term cases; the
        # bloc era 2019-21; the conventional five, with and without 2008
        # (definition mismatch: see CONVENTIONAL_DEADLOCKS). Then the unity
        # gate's record classes with the stage on (0 of 3 unity governments
        # = the shipped 0.125; 0 of 5 deadlocks with a unity on the table =
        # 0.083; 0 of 7 stage deadlocks = 0.0625; the pre-s49 hand value
        # 0.18), and the stage off (shipped unity, and the pre-s49 central
        # tree: stage off with 0.18).
        P, D, Mt = "parliamentary", "direct", "midterm"
        variants = [dict(), dict(regimes=(P, D)),
                    dict(regimes=(P, Mt), exclude=("1995m",)),
                    dict(regimes=(P, Mt)),
                    dict(cycles=("2019a", "2019s", "2020", "2021")),
                    dict(cycles=CONVENTIONAL_DEADLOCKS),
                    dict(regimes=(P, Mt),
                         cycles=CONVENTIONAL_DEADLOCKS + ("2008m",))]
        for v in variants:
            a2, b2 = deadlock_posterior(**v)
            rows.append(_sens_row(repeat_deadlock=a2 / (a2 + b2)))
        for k, n in ((0, 5), (0, 7)):
            rows.append(_sens_row(likud_sans_bibi=(k + 0.5) / (n + 1)))
        rows.append(_sens_row(likud_sans_bibi=0.18))
        rows.append(_sens_row(repeat_deadlock=None))
        rows.append(_sens_row(repeat_deadlock=None, likud_sans_bibi=0.18))
    sens = pd.DataFrame(rows)
    sens.to_csv(out_dir / "government_sensitivity.csv", index=False)
    print("\nSensitivity (UTJ defection x Amcha alignment; Reservists right "
          "side; UTJ abstention; deadlock stage: record 2/7 / +1999 / "
          "+Oct 2008 / +1995 and 2008 / bloc era / conventional 2/5 / "
          "conventional + 2008; unity 0 of 5 / 0 of 7 / pre-s49 0.18; stage "
          "off / stage off with 0.18 = pre-s49 central):")
    print(sens.to_string(index=False))

    fig_dir = FIG_DIR if out_dir == PROCESSED_DIR else out_dir
    plot(table, pm_probs, fig_dir)
    print(f"\nwrote government_formation.csv, pm_probabilities.csv, "
          f"government_deadlock.csv, government_sensitivity.csv -> {out_dir}; "
          f"{fig_dir / 'government_2026.png'}")


def plot(table: pd.DataFrame, pm_probs: pd.Series, fig_dir=None) -> None:
    fig_dir = FIG_DIR if fig_dir is None else Path(fig_dir)
    BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    NEUTRAL = "#898781"
    color = {
        "Netanyahu coalition": BLUE,
        "Netanyahu-led with centre defector (pledge-break)": BLUE,
        "Unity govt (Likud without Netanyahu)": NEUTRAL,
        "No government -> repeat election": NEUTRAL,
    }
    t = table.sort_values("probability")
    fig, ax = plt.subplots(figsize=(8.8, 4.4), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ys = range(len(t))
    for y, row in zip(ys, t.itertuples()):
        c = color.get(row.outcome, ORANGE)
        ax.barh(y, row.probability, height=0.62, color=c, linewidth=0)
        ax.text(row.probability + 0.008, y, f"{row.probability:.0%}",
                va="center", fontsize=9, color=INK_2)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(t["outcome"], fontsize=9.5, color=INK)
    ax.set_xlim(0, max(t["probability"]) * 1.18)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Probability across simulated Knessets and behavioral draws",
                  fontsize=9, color=INK_2)
    ax.set_title("Who governs? Formation scenarios for the 26th Knesset",
                 fontsize=11, color=INK, loc="left", pad=12)
    fig.tight_layout()
    fig.savefig(fig_dir / "government_2026.png", facecolor=SURFACE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=None,
                    help="output directory (default data/processed)")
    ap.add_argument("--stage", choices=("on", "off"), default=None,
                    help="post-deadlock stage (default POST_DEADLOCK_STAGE)")
    args = ap.parse_args()
    main(args.out, POST_DEADLOCK_STAGE if args.stage is None
         else args.stage == "on")
