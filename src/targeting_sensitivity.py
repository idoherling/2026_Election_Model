"""Targeting layer, part 3: how robust are the rankings?

Re-scores every locality under alternative assumptions for the parameters
the literature leaves most uncertain (turnout effect size and shape,
persuasion and rescue rates, residents abroad, the marginal-voter model)
and records each locality's rank under each scenario. A target that stays
near the top whatever the assumptions is a safe call; one that moves a lot
depends on a judgement the reader should know about.

Outputs:
    data/processed/targeting/sensitivity_ranks.csv
    data/processed/targeting/sensitivity_summary.json
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import targeting_model as tm

OBJS = ["change_govt", "block_nb"]
BUDGET_OBJS = ["change_govt", "block_nb", "change_seats"]
BUDGETS = [(150_000, 0.0), (150_000, 0.3), (400_000, 0.0), (400_000, 0.3)]
SCENARIOS = {
    "base": {},
    "gotv_low": {"GOTV_BASE": 0.008},
    "gotv_high": {"GOTV_BASE": 0.025},
    "gotv_flat": {"GOTV_HUMP_M": [0.8] * 8},
    # same average lift in door turf as the base case, but no hump
    "gotv_flat_matched": {"GOTV_HUMP_M": [0.32] * 8},
    # the steepest published shape: effects concentrated among 30-50% propensity
    "gotv_steep": {"GOTV_HUMP_M": [0.6, 1.4, 2.2, 1.3, 0.5, 0.25, 0.12, 0.05]},
    "persuasion_high": {"RHO_PERSUADE": tm.RHO_PERSUADE * 4},
    "persuasion_zero": {"RHO_PERSUADE": 0.0},
    "persuasion_no_side": {"PERSUASION_TURNOUT_SIDE": 0.0},
    "rescue_high": {"RHO_RESCUE": tm.RHO_RESCUE * 3},
    "rescue_low": {"RHO_RESCUE": tm.RHO_RESCUE * 0.3},
    "lists_off": {"LIST_IDENTIFIED": 0.0},
    "abroad_high": {"ROLL_ABROAD_BY_SEGMENT": {k: min(0.25, v * 1.6) for k, v in
                                               tm.ROLL_ABROAD_BY_SEGMENT.items()}},
    "cross_pressure_low": {"CROSS_PRESSURE": 0.10},
    "cross_pressure_high": {"CROSS_PRESSURE": 0.40},
    "druze_minus20": {"DRUZE_SHIFT": 0.20},
    "no_blend": {"CAMP_BLEND": 0.0},
    "composition_tilt": {"FORCE_COMPOSITION": "multiplicative"},
}
LABELS = {
    "base": "Base case",
    "gotv_low": "Turnout effect about half as large (0.8 instead of 1.5 pts at the reference point)",
    "gotv_high": "Turnout effect two-thirds larger (2.5 instead of 1.5 pts)",
    "gotv_flat": "No turnout hump: ×0.8 at every turnout level",
    "gotv_flat_matched": "No turnout hump, same average lift in door turf (×0.32 everywhere)",
    "gotv_steep": "Steeper hump (effect concentrated at 30-50% turnout)",
    "persuasion_high": "Persuasion ×4 (upper end of field estimates)",
    "persuasion_zero": "No persuasion effect",
    "persuasion_no_side": "No turnout side-effect of persuasion calls",
    "rescue_high": "Rescue ×3", "rescue_low": "Rescue ×0.3",
    "lists_off": "No supporter lists (door canvassing only)",
    "abroad_high": "Residents abroad ×1.6",
    "cross_pressure_low": "Cross-pressured share 10% (national pool about 1%)",
    "cross_pressure_high": "Cross-pressured share 40% (national pool about 4%)",
    "druze_minus20": "Druze towns: 20 points moved from change to Netanyahu-bloc lists",
    "no_blend": "Pure flow-matrix projection (no uniform-swing blend)",
    "composition_tilt": "Turnout-tilted marginal voters (model rejected out of sample)",
}


def main() -> None:
    import targeting_planner as tp
    panel, lc, meta, nat, mv, shares = tm.load()
    cw = tm.camp_wide(panel, lc)
    seg = tm.assign_segments(meta, cw, panel)
    base_vals = {k: getattr(tm, k) for s in SCENARIOS.values() for k in s if hasattr(tm, k)}
    ranks, budgets = {}, {}
    for name, patch in SCENARIOS.items():
        for k, v in base_vals.items():
            setattr(tm, k, v)
        for k, v in patch.items():
            setattr(tm, k, v)
        loc, kal, _, _, planner = tm.score(seg, cw, panel, mv, shares)
        loc = loc.sort_index()
        if name == "base":
            base_loc = loc
        for o in OBJS:   # ranks among all localities, as on the site
            ranks[(name, o, "pot")] = loc[f"{o}__potential"].rank(ascending=False, method="average")
            ranks[(name, o, "eff")] = loc[f"{o}__area_eff1k"].rank(ascending=False, method="average")
        # realistic budgets, as on the summary page: Arab, access-excluded
        # and low-confidence (Druze) localities left out
        tr = tp.tranches(planner, loc.index)
        idx = {lid: k for k, lid in enumerate(loc.index)}
        ex = {idx[l] for l in loc.index[loc["segment"].str.startswith("arab")
                                        | (loc["field_excluded"] != "")
                                        | (loc["low_confidence"] != "")]}
        budgets[name] = {o: {f"{b}_{i}": round(tp.allocate(tr[o], b, i, exclude=ex)["ve"], 1)
                             for b, i in BUDGETS} for o in BUDGET_OBJS}
        print(f"scenario {name}: done", budgets[name]["change_govt"])
    for k, v in base_vals.items():
        setattr(tm, k, v)
    R = pd.DataFrame({f"{o}__{n}": r for (n, o, kind), r in ranks.items() if kind == "pot"})
    R.index.name = "locality"
    R.to_csv(tm.OUT / "sensitivity_ranks.csv")
    E = pd.DataFrame({f"{o}__{n}": r for (n, o, kind), r in ranks.items() if kind == "eff"})
    summ = {"labels": LABELS, "objectives": {}, "budgets": budgets}
    loc = base_loc     # all sets are defined on the base case
    big = loc.index[loc["eligible"] >= 1000]
    target = loc.index[(loc["eligible"] >= 1000) & ~loc["segment"].str.startswith("arab")
                       & (loc["field_excluded"] == "")]
    for o in OBJS:
        rows = {}
        for n in SCENARIOS:
            def stab(M, ids, col):
                b_ = M.loc[ids, f"{o}__base"]
                r_ = M.loc[ids, f"{o}__{n}"]
                rb = b_.rank(method="first"); rr = r_.rank(method="first")
                t25 = set(rb[rb <= 25].index)
                return {"spearman": round(float(spearmanr(b_, r_).correlation), 3),
                        "top25_overlap": int(len(t25 & set(rr[rr <= 25].index)))}
            pos_ids = [i for i in target if loc.at[i, f"{o}__area_contacts"] > 0]
            rows[n] = {**stab(R, big, "pot"),
                       "target": stab(R, target, "pot"),
                       "door_eff": stab(E, pos_ids, "eff")}
        cols = [f"{o}__{n}" for n in SCENARIOS]
        rt = R.loc[target, cols].rank(method="first")
        always = rt.max(axis=1)
        summ["objectives"][o] = {"scenarios": rows,
                                 "n_always_top25": int((R.loc[big, cols].max(axis=1) <= 25).sum()),
                                 "n_always_top25_target": int((always <= 25).sum()),
                                 "n_ranked": int(len(big)), "n_target": int(len(target)),
                                 "n_door": int(len(pos_ids))}
        print(o, json.dumps({k: (v["spearman"], v["target"]["spearman"], v["door_eff"]["top25_overlap"])
                             for k, v in rows.items()}))
    (tm.OUT / "sensitivity_summary.json").write_text(json.dumps(summ, indent=1))

if __name__ == "__main__":
    main()
