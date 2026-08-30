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
          "Yisrael Beytenu", "Zionist Home – The Reservists",
          "Blue and White", "Unity"]
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
    # Segalovitz deal effectively signed (Maariv Aug 5: agreement in
    # principle; slot #2 reserved at the Aug 22 primaries). Eisenkot's camp
    # published Ra'am-shaped entry conditions (Walla Aug 16) but every
    # Jewish party still pledges no Arab party INSIDE at the outset —
    # entry is modeled as post-formation expansion, hence joins < supports.
    "raam_joins": 0.35,
    "raam_supports": 0.55,
    # JL revived with Jabareen #1/Tibi #2 (ToI late Aug); Hadash-led list
    # likelier to abstain constructively than Balad-led; Tibi placated.
    "jl_supports": 0.45,
    # Split haredi defection: Deri re-locked Shas ("We support Netanyahu,
    # period"); UTJ/Degel broke with Netanyahu over the draft law, met
    # Eisenkot positively in secret (Ch12), and Agudat says "whoever
    # delivers a draft law" - but Eisenkot vows no draft compromise.
    "shas_defects": 0.08,
    "utj_defects": 0.35,
    # No credible Likud heir emerged from the primary (Haaretz Jul 12),
    # but Herzog is actively advancing a plea-deal exit ramp (NYT/JNS) and
    # told MKs he'll push a unity government "at any cost" (ToI) — the
    # president is a formation actor, not a notary.
    "likud_sans_bibi": 0.15,
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
    2: [0.75, 0.19, 0.04, 0.00, 0.02],   # centre coalition
    3: [0.75, 0.19, 0.04, 0.00, 0.02],   # centre + Ra'am
    4: [0.64, 0.31, 0.00, 0.00, 0.05],   # centre-haredi: right-cred PM helps,
                                          # Liberman is a dealbreaker for haredim
    5: [0.75, 0.19, 0.04, 0.00, 0.02],   # centre minority
    6: [0.35, 0.10, 0.05, 0.00, 0.50],   # unity: Likud successor/rotation heavy
}
PM_NAMES = ["Eisenkot", "Bennett", "Liberman", "Lapid",
            "rotation / Likud successor"]

# P(Amcha joins an Eisenkot-led centre government) — floored, not zeroed:
# Winter's vendetta is personal and public, but coalitions have bought
# stranger conversions (Cromwell caveat).
AMCHA_JOIN_EISENKOT = 0.03

OUTCOMES = [
    "Netanyahu coalition",
    "Netanyahu-led with centre defector (pledge-break)",
    "Centre coalition (own majority)",
    "Centre + Ra'am",
    "Centre-haredi coalition",
    "Centre minority (outside support)",
    "Unity govt (Likud without Netanyahu)",
    "No government -> repeat election",
]


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


def simulate_formation(draws: pd.DataFrame, behavior: dict, seed=SEED):
    rng = np.random.default_rng(seed)
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
    shas_on = u[:, 4] < behavior["shas_defects"]
    utj_on = rng.random(n) < behavior["utj_defects"]
    sans_bibi = u[:, 5] < behavior["likud_sans_bibi"]

    nb = nb_core + np.where(amcha_side == 1, amcha, 0)
    ce = centre + np.where(amcha_side == 2, amcha, 0)

    outcome = np.full(n, 7)  # default: repeat election (last index)
    outcome[np.where((ce + draws["Likud"].values >= 61) & sans_bibi)] = 6
    # pledge-break: some centre list can close Netanyahu's gap and does
    centre_seats = draws[CENTRE].values
    gap = (61 - nb)[:, None]
    feasible = ((centre_seats >= gap) & (gap > 0)).any(axis=1)
    outcome[np.where((u[:, 6] < behavior["centre_defects"]) & feasible)] = 1
    yb = draws["Yisrael Beytenu"].values
    abstaining = (np.where(raam_supports & ~raam_joins, raam, 0)
                  + np.where(jl_supports, jl, 0))
    present = 120 - abstaining
    lib_ok = rng.random(n) < behavior["liberman_minority_ok"]
    minority_ce = np.where(lib_ok, ce, ce - yb)
    outcome[np.where((abstaining > 0)
                     & (minority_ce > present / 2))] = 5
    defecting_haredi = (np.where(shas_on, draws["Shas"].values, 0)
                        + np.where(utj_on,
                                   draws["United Torah Judaism"].values, 0))
    outcome[np.where((ce + defecting_haredi >= 61)
                     & (defecting_haredi > 0))] = 4
    outcome[np.where((ce + raam >= 61) & raam_joins)] = 3
    outcome[np.where(ce >= 61)] = 2
    outcome[np.where(nb >= 61)] = 0

    pm = np.full(n, "none (repeat election)", dtype=object)
    pm[outcome == 0] = "Netanyahu"
    pm[outcome == 1] = "Netanyahu"
    u_pm = rng.random(n)
    for oc, alloc in PM_ALLOC.items():
        mask = outcome == oc
        cum = np.cumsum(alloc)
        pick = np.searchsorted(cum, u_pm[mask], side="right")
        pm[mask] = np.array(PM_NAMES)[np.minimum(pick, len(PM_NAMES) - 1)]
    # In coalitions where Together outweighs Yashar, the rotation flips:
    # Bennett leads and Eisenkot is the junior partner.
    flip = (together > yashar) & np.isin(outcome, [2, 3, 4, 5])
    pm = np.where(flip & (pm == "Eisenkot"), "Bennett",
                  np.where(flip & (pm == "Bennett"), "Eisenkot", pm))
    return outcome, pm


def main() -> None:
    draws = load_draws()
    outcome, pm = simulate_formation(draws, BEHAVIOR)

    probs = pd.Series(outcome).value_counts(normalize=True).sort_index()
    table = pd.DataFrame({
        "outcome": OUTCOMES,
        "probability": [round(float(probs.get(i, 0.0)), 3)
                        for i in range(len(OUTCOMES))],
    })
    table.to_csv(PROCESSED_DIR / "government_formation.csv", index=False)
    print("Government formation (8,000 Knessets x behavioral draws):\n")
    print(table.to_string(index=False))

    pm_probs = pd.Series(pm).value_counts(normalize=True)
    print("\nP(next prime minister):")
    for name, p in pm_probs.items():
        print(f"  {p:6.1%}  {name}")

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
