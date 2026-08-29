"""Grade the formation tree against eight real post-election outcomes.

The 2026 government-formation model is judgment encoded as a scenario tree.
This module runs the SAME branch logic and behavioral parameters on the
ACTUAL seat outcomes of 2009-2022 (roles era-adapted: who the kingmaker
was, whether an Arab party was politically available) and scores the
probability the tree assigned to what actually happened:

  2009  Netanyahu coalition (Kadima was largest; irrelevant, as the tree
        correctly ignores largest-list mythology)
  2013  Netanyahu coalition (with centre defectors: Yesh Atid, Hatnuah)
  2015  Netanyahu coalition (kingmaker Kulanu joined right)
  2019a NO government -> repeat election
  2019s NO government -> repeat election
  2020  unity via pledge-break: Gantz's centre faction joined Netanyahu
  2021  centre coalition WITH Ra'am and the kingmaker (Yamina), rotation PM
  2022  Netanyahu coalition

Era adaptations (documented, not tuned to outcomes):
  * raam_available: an Arab party joining/supporting was politically
    unprecedented before 2021 -> p(join)=0.05, p(support)=0.15 pre-2021.
  * kingmaker: the unaligned list of the cycle (Kulanu 2015, Yamina
    2019s-2021), with the same alignment split the 2026 tree gives Amcha.
  * centre_defection: the branch the 2026 tree LACKED — a centre party
    joining a Netanyahu-led government (happened 2009, 2013, 2015, 2020).
    Graded here both without it (the shipped tree) and with it, using the
    4/8 historical base rate.

Outputs: data/processed/formation_validation.csv
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR

warnings.filterwarnings("ignore")

SEED = 20261027
N = 20_000

BEHAVIOR = {  # identical to government_formation.BEHAVIOR where shared
    "king_right": 0.35, "king_centre": 0.35,
    "raam_joins": 0.55, "raam_supports": 0.40, "jl_supports": 0.25,
    "haredi_defect": 0.30, "likud_sans_bibi": 0.15,
}

# cycle: nb_core (right+haredi, excl. kingmaker), centre (excl. kingmaker),
# haredi, raam-analog, jl (outside-only Arab), kingmaker seats,
# raam politically available?, realized outcome, realized PM side
HISTORY = {
    "2009": dict(nb=65, centre=44, haredi=16, raam=0, jl=11, king=0,
                 raam_avail=False, outcome="nb", pm="netanyahu"),
    "2013": dict(nb=61, centre=48, haredi=18, raam=0, jl=11, king=0,
                 raam_avail=False, outcome="nb", pm="netanyahu"),
    "2015": dict(nb=57, centre=40, haredi=13, raam=0, jl=13, king=10,
                 raam_avail=False, outcome="nb_king", pm="netanyahu"),
    "2019a": dict(nb=56, centre=45, haredi=16, raam=0, jl=10, king=5,
                  raam_avail=False, outcome="repeat", pm="none"),  # king=YB
    "2019s": dict(nb=55, centre=44, haredi=16, raam=0, jl=13, king=8,
                  raam_avail=False, outcome="repeat", pm="none"),  # king=YB
    "2020": dict(nb=58, centre=40, haredi=16, raam=0, jl=15, king=7,
                 raam_avail=False, outcome="defect", pm="netanyahu"),  # king=YB
    "2021": dict(nb=52, centre=51, haredi=16, raam=4, jl=6, king=7,
                 raam_avail=True, outcome="centre_raam_king", pm="centre"),  # king=Yamina
    "2022": dict(nb=64, centre=45, haredi=18, raam=5, jl=5, king=0,
                 raam_avail=True, outcome="nb", pm="netanyahu"),
}

OUTCOMES = ["nb", "nb_king", "defect", "centre", "centre_king",
            "centre_raam_king", "centre_haredi", "minority", "unity",
            "repeat"]


def run_tree(h, with_defection, rng):
    """The 2026 tree's branch logic on one historical seat vector."""
    n = N
    u = rng.random((n, 7))
    king_side = np.select(
        [u[:, 0] < BEHAVIOR["king_right"],
         u[:, 0] < BEHAVIOR["king_right"] + BEHAVIOR["king_centre"]],
        [1, 2], default=0)
    p_join = BEHAVIOR["raam_joins"] if h["raam_avail"] else 0.05
    p_supp = BEHAVIOR["raam_supports"] if h["raam_avail"] else 0.15
    raam_joins = u[:, 1] < p_join
    raam_supports = u[:, 2] < p_supp
    jl_supports = u[:, 3] < BEHAVIOR["jl_supports"]
    haredi_defect = u[:, 4] < BEHAVIOR["haredi_defect"]
    sans_bibi = u[:, 5] < BEHAVIOR["likud_sans_bibi"]
    defects = u[:, 6] < (0.33 if with_defection else 0.0)

    nb = h["nb"] + np.where(king_side == 1, h["king"], 0)
    ce = h["centre"] + np.where(king_side == 2, h["king"], 0)

    out = np.full(n, "repeat", dtype=object)
    out[(ce + h["nb"] - h["haredi"] >= 61) & sans_bibi] = "unity"
    supp = (np.where(raam_supports & ~raam_joins, h["raam"], 0)
            + np.where(jl_supports, h["jl"], 0))
    out[ce + supp >= 61] = "minority"
    out[(ce + h["haredi"] >= 61) & haredi_defect] = "centre_haredi"
    m = (ce + h["raam"] >= 61) & raam_joins
    out[m] = np.where(king_side[m] == 2, "centre_raam_king", "centre_raam_king")
    out[(ce >= 61) & (king_side == 2)] = "centre_king"
    out[(ce >= 61) & (king_side != 2)] = "centre"
    # The defection branch: a centre partner joins a Netanyahu-led
    # government when that closes the gap (2009/13/15/20 pattern). In the
    # historical runs the "partner" is the era's actual defector size.
    can_defect = (h["nb"] + max(h["centre"] // 2, 11) >= 61) & (h["nb"] < 61)
    out[np.where(defects & can_defect & (out == "repeat"), True, False)] = "defect"
    out[nb >= 61] = np.where(king_side[nb >= 61] == 1, "nb_king", "nb")
    # plain-nb when core alone suffices
    out[h["nb"] >= 61] = "nb"
    return out


def grade(with_defection):
    rng = np.random.default_rng(SEED)
    rows = []
    for cycle, h in HISTORY.items():
        out = run_tree(h, with_defection, rng)
        # score family: count nb/nb_king as one family for realized "nb"
        realized = h["outcome"]
        fam_map = {"nb": {"nb", "nb_king"}, "nb_king": {"nb", "nb_king"},
                   "centre_raam_king": {"centre_raam_king", "centre_king",
                                        "centre"},
                   }
        ok = fam_map.get(realized, {realized})
        p = float(np.isin(out, list(ok)).mean())
        pm_side = {"netanyahu": {"nb", "nb_king", "defect"},
                   "centre": {"centre", "centre_king", "centre_raam_king",
                              "centre_haredi", "minority"},
                   "none": {"repeat"}}[h["pm"]]
        p_pm = float(np.isin(out, list(pm_side)).mean())
        rows.append({"cycle": cycle, "realized": realized,
                     "p_realized": round(p, 3),
                     "p_pm_side": round(p_pm, 3),
                     "log_score": round(float(np.log(max(p, 1e-3))), 2)})
    return pd.DataFrame(rows)


def main() -> None:
    without = grade(with_defection=False)
    withd = grade(with_defection=True)
    both = without.merge(withd, on=["cycle", "realized"],
                         suffixes=("_shipped", "_with_defection"))
    both.to_csv(PROCESSED_DIR / "formation_validation.csv", index=False)
    print("Formation tree graded on eight real outcomes:\n")
    print(both.to_string(index=False))
    for tag, df in (("shipped tree", without), ("with defection branch",
                                                withd)):
        print(f"\n{tag}: mean P(realized) "
              f"{df['p_realized'].mean():.2f} | mean P(PM side) "
              f"{df['p_pm_side'].mean():.2f} | mean log score "
              f"{df['log_score'].mean():.2f} "
              f"(uniform-over-outcomes baseline: {np.log(1/7):.2f})")


if __name__ == "__main__":
    main()
