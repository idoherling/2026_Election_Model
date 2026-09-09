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

Outputs:
    data/processed/government_formation.csv     outcome probabilities
    data/processed/government_sensitivity.csv   assumption stress test
    output/figures/government_2026.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE
from scrape_polls import PROCESSED_DIR

SEED = 20261027

NB_CORE = ["Likud", "Otzma Yehudit", "Shas", "United Torah Judaism",
           "Religious Zionist Party", "Noam", "Zehut"]
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
    "amcha_right": 0.87,
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
    "shas_defects": 0.10,
    "utj_defects": 0.26,
    # Liberman's haredi veto is his electoral identity since 2019
    # ("not a millimeter"); he relents on sitting WITH haredim only
    # rarely -> the centre-haredi branch must clear 61 without YB unless
    # this fires.
    "liberman_haredi_ok": 0.20,
    # No credible Likud heir emerged from the primary (Haaretz Jul 12),
    # but Herzog is actively advancing a plea-deal exit ramp (NYT/JNS) and
    # told MKs he'll push a unity government "at any cost" (ToI). Base
    # rates: unity resolved ~half of historical deadlocks (1984/1988/
    # 2020), and the institutions desk puts P(Netanyahu accepts exit |
    # post-election dead-end) at 0.35 — tempered here because 2026's
    # cleavage is personalized on Netanyahu (the condition under which
    # unity failed in Sept 2019).
    "likud_sans_bibi": 0.18,
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
    "res_right": 0.30, "res_centre": 0.45,
}

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
    "res_right": 10, "res_centre": 10,
    "amcha_right": 35,          # public, repeated pledge
    "amcha_center": 12,         # analog reasoning (Bennett-led condition)
    "raam_supports": 18,
    "jl_supports": 14,          # one Jabareen signal + precedent
    "shas_defects": 30,         # institutional (psak mechanism, re-lock)
    "utj_defects": 16,          # full/partial blend, two councils
    "liberman_haredi_ok": 25,   # identity veto, held at every fork
    "raam_joins": 18,           # desk-triangulated, deal official
    "liberman_minority_ok": 14, # doctrine vs veto, genuinely uncertain
    "likud_sans_bibi": 20,      # base rates + kalon precedent
    "centre_defects": 25,       # graded on the 2020 realization
}
PM_ALLOC_NEFF = 60              # Dirichlet concentration on rotation rows

# P(Amcha joins an Eisenkot-led centre government) — floored, not zeroed:
# Winter's vendetta is personal and public, but coalitions have bought
# stranger conversions (Cromwell caveat).
AMCHA_JOIN_EISENKOT = 0.03

OUTCOMES = [
    "Netanyahu rightist coalition",
    "Netanyahu + unaligned / defector coalition",
    "Change coalition (without Ra'am)",
    "Change coalition with unaligned / Amcha",
    "Change coalition with a haredi party",
    "Centre minority backed by the Joint List",
    "Unity government (Likud without Netanyahu)",
    "Repeat election",
    "Change coalition with Ra'am",
]


# Configuration-conditional gates (2026-09-03, Fable audit #4). The declared
# probabilities in BEHAVIOR are MARGINAL means; each draw's gate probability
# moves with the seat configuration through a logistic,
#     p = sigmoid(logit(p0) + beta * x),   x centred over the draws,
# so the marginal stays at p0 while pivotal configurations get more (or
# less) of it. Anchors, institutional record:
#  - haredi parties joined non-Likud governments exactly when the right had
#    no path (Shas 1992, Shas+UTJ 1999) and they were the decisive partner
#    -> defection rises with the NB gap to 61 and when that party alone
#    closes the centre's gap;
#  - a centre list joined Netanyahu when a SMALL gap made one partner
#    sufficient (Gantz 2020, gap 3; no defector at gaps of 5-6 in 2019)
#    -> the defection gate falls with the gap;
#  - Likud shedding Netanyahu for unity rises with deadlock depth (both
#    blocs short by more: 1984/1988 pattern).
# Graded on the eight real outcomes in validate_formation.py.
COND = {"gap_unit": 5.0,
        "haredi_beta_gap": 0.35, "haredi_beta_piv": 0.50,
        "defect_beta_gap": -0.35, "unity_beta_deadlock": 0.35}


def cond_prob(p0, x):
    """Logistic shift of a base probability by a centred covariate term."""
    p0 = np.clip(p0, 1e-4, 1 - 1e-4)
    return 1.0 / (1.0 + np.exp(-(np.log(p0 / (1 - p0)) + x)))


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
                       pm_alloc=None):
    rng = np.random.default_rng(seed)
    if pm_alloc is None:
        pm_alloc = PM_ALLOC
    n = len(draws)
    nb_core = draws[NB_CORE].sum(axis=1).values
    centre = draws[CENTRE].sum(axis=1).values
    haredi = draws[HAREDI].sum(axis=1).values
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
    raam_joins = u[:, 1] < behavior["raam_joins"]
    raam_supports = u[:, 2] < behavior["raam_supports"]
    jl_supports = u[:, 3] < behavior["jl_supports"]

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
    for name, (kr, kc) in UNALIGNED.items():
        if name not in draws.columns:
            continue
        sv = draws[name].values
        uu = rng.random(n)
        una_r += np.where(uu < behavior[kr], sv, 0)
        una_c += np.where((uu >= behavior[kr]) & (uu < behavior[kr] + behavior[kc]), sv, 0)
    nb = nb + una_r
    ce_pure = ce_pure + una_c

    # --- configuration-conditional gates (see COND) ---
    gap_nb = 61.0 - nb
    gap_ce = 61.0 - ce_pure
    xg = (gap_nb - gap_nb.mean()) / COND["gap_unit"]
    shas_seats = draws["Shas"].values
    utj_seats = draws["United Torah Judaism"].values
    piv_shas = ((ce_pure < 61) & (ce_pure + shas_seats >= 61)).astype(float)
    piv_utj = ((ce_pure < 61) & (ce_pure + utj_seats >= 61)).astype(float)
    p_shas = cond_prob(behavior["shas_defects"],
                       COND["haredi_beta_gap"] * xg
                       + COND["haredi_beta_piv"] * (piv_shas - piv_shas.mean()))
    p_utj = cond_prob(behavior["utj_defects"],
                      COND["haredi_beta_gap"] * xg
                      + COND["haredi_beta_piv"] * (piv_utj - piv_utj.mean()))
    p_defect = cond_prob(behavior["centre_defects"], COND["defect_beta_gap"] * xg)
    dead = np.minimum(gap_nb, gap_ce)
    p_unity = cond_prob(behavior["likud_sans_bibi"],
                        COND["unity_beta_deadlock"] * (dead - dead.mean()) / COND["gap_unit"])
    shas_on = u[:, 4] < p_shas
    utj_on = rng.random(n) < p_utj
    sans_bibi = u[:, 5] < p_unity

    outcome = np.full(n, 7)  # default: repeat election
    outcome[np.where((ce_pure + amcha_ce
                      + draws["Likud"].values >= 61) & sans_bibi)] = 6
    # pledge-break: some centre list can close Netanyahu's gap and does
    centre_seats = draws[CENTRE].values
    gap = (61 - nb)[:, None]
    feasible = ((centre_seats >= gap) & (gap > 0)).any(axis=1)
    outcome[np.where((u[:, 6] < p_defect) & feasible)] = 1
    # minority: sworn by plurality with the JOINT LIST abstaining (the
    # named backer); a Ra'am abstention additionally lowers the bar
    yb = draws["Yisrael Beytenu"].values
    abstaining = (np.where(jl_supports, jl, 0)
                  + np.where(raam_supports, raam - seg, 0))
    present = 120 - abstaining
    lib_ok = rng.random(n) < behavior["liberman_minority_ok"]
    minority_ce = np.where(lib_ok, ce_pure, ce_pure - yb)
    outcome[np.where(jl_supports & (abstaining > 0)
                     & (minority_ce > present / 2))] = 5
    defecting_haredi = (np.where(shas_on, draws["Shas"].values, 0)
                        + np.where(utj_on,
                                   draws["United Torah Judaism"].values, 0))
    # Liberman won't sit WITH haredim (identity veto, ~0.80 held)
    lib_haredi = rng.random(n) < behavior["liberman_haredi_ok"]
    ch_base = ce_pure + amcha_ce
    ch_seats = np.where(lib_haredi, ch_base, ch_base - yb) + defecting_haredi
    outcome[np.where((ch_seats >= 61) & (defecting_haredi > 0))] = 4
    # change coalition WITH Ra'am inside: the camp is short alone and
    # Ra'am's remaining seats close it (Segalovitz's seat already in ce)
    outcome[np.where((ce_pure < 61) & raam_joins
                     & (ce_pure + (raam - seg) >= 61))] = 8
    # change coalition WITH Amcha: the camp is short alone, Winter's
    # seats close it, and he joins (conditional on a Bennett-led draw)
    # Owner taxonomy 2026-09-09: the change lists alone reach 61 (2), or
    # they are short and the UNALIGNED kingmakers and/or Amcha close the
    # gap (3); likewise Netanyahu's bloc alone (0), or short and closed by
    # unaligned seats or a pledge-breaking centrist (1).
    outcome[np.where((ce0 < 61)
                     & (ce_pure + amcha_ce >= 61))] = 3
    outcome[np.where(ce0 >= 61)] = 2
    outcome[np.where((nb0 < 61) & (nb >= 61))] = 1
    outcome[np.where(nb0 >= 61)] = 0

    pm = np.full(n, "none (repeat election)", dtype=object)
    pm[outcome == 0] = "Netanyahu"
    pm[outcome == 1] = "Netanyahu"
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
    return outcome, pm


def main() -> None:
    draws = load_draws()

    # Hierarchical over parameter uncertainty: M parameter vectors from
    # the evidence-quality priors, each evaluated on all seat draws.
    M = 200
    prng = np.random.default_rng(SEED + 7)
    oc_mat = np.zeros((M, len(OUTCOMES)))
    pm_names_all = PM_NAMES + ["Netanyahu", "none (repeat election)"]
    pm_mat = np.zeros((M, len(pm_names_all)))
    for m in range(M):
        b = draw_behavior(prng)
        pa = draw_pm_alloc(prng)
        oc, pmv = simulate_formation(draws, b, seed=SEED + m, pm_alloc=pa)
        cnt = pd.Series(oc).value_counts(normalize=True)
        for i in range(len(OUTCOMES)):
            oc_mat[m, i] = cnt.get(i, 0.0)
        pcnt = pd.Series(pmv).value_counts(normalize=True)
        for j, nmn in enumerate(pm_names_all):
            pm_mat[m, j] = pcnt.get(nmn, 0.0)

    table = pd.DataFrame({
        "outcome": OUTCOMES,
        "probability": oc_mat.mean(axis=0).round(3),
        "p05": np.percentile(oc_mat, 5, axis=0).round(3),
        "p95": np.percentile(oc_mat, 95, axis=0).round(3),
    })
    table.to_csv(PROCESSED_DIR / "government_formation.csv", index=False)
    print(f"Government formation ({len(draws)} Knessets x {M} parameter "
          "vectors x behavioral draws):\n")
    print(table.to_string(index=False))

    pm_df = pd.DataFrame({
        "pm": pm_names_all,
        "probability": pm_mat.mean(axis=0).round(3),
        "p05": np.percentile(pm_mat, 5, axis=0).round(3),
        "p95": np.percentile(pm_mat, 95, axis=0).round(3),
    }).sort_values("probability", ascending=False)
    pm_df = pm_df[pm_df.probability > 0.001]
    pm_df.to_csv(PROCESSED_DIR / "pm_probabilities.csv", index=False)
    pm_probs = pd.Series(pm_df.probability.values, index=pm_df.pm)
    print("\nP(next prime minister) [90% CI over parameter uncertainty]:")
    for r in pm_df.itertuples():
        print(f"  {r.probability:6.1%}  [{r.p05:.1%}-{r.p95:.1%}]  {r.pm}")

    # Sensitivity: the two assumptions with the most leverage.
    rows = []
    for ud in (0.15, 0.35, 0.55):
        for ar in (0.60, 0.80, 0.95):
            b = dict(BEHAVIOR, utj_defects=ud, amcha_right=ar,
                     amcha_center=min(0.9 - ar, 0.35))
            oc, pm_s = simulate_formation(draws, b)
            rows.append({
                "utj_defects": ud, "amcha_right": ar,
                "p_netanyahu_pm": round(float((pm_s == "Netanyahu").mean()), 3),
                "p_eisenkot_pm": round(float((pm_s == "Eisenkot").mean()), 3),
                "p_repeat_election": round(float((oc == 7).mean()), 3),
            })
    sens = pd.DataFrame(rows)
    sens.to_csv(PROCESSED_DIR / "government_sensitivity.csv", index=False)
    print("\nSensitivity (UTJ defection x Amcha alignment):")
    print(sens.to_string(index=False))

    plot(table, pm_probs)
    print(f"\nwrote government_formation.csv, government_sensitivity.csv, "
          f"{FIG_DIR / 'government_2026.png'}")


def plot(table: pd.DataFrame, pm_probs: pd.Series) -> None:
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
    fig.savefig(FIG_DIR / "government_2026.png", facecolor=SURFACE)


if __name__ == "__main__":
    main()
