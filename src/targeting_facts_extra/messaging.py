"""Derived numbers for the messaging page (research/content_final_messaging.json).

field_govt_pp_min / field_govt_pp_max: the smallest and largest effect, in points of
P(change-led government), of the four realistic field plans for the change_govt objective
(150k or 400k contacts, 0% or 30% identified). The intro quotes them as the range of what
"a realistic field programme adds"; the watch file compares lever effects with the maximum.

n_pers_towns: localities with positive persuasion value (change_govt__pers_pot > 0) outside the
planner's core exclusions (Arab localities, access-excluded and the held-out Druze towns).
pers_top3: the three of them with the largest persuasion value, best first, as site English names
joined "A, B and C" (audiences[0].channel). Generated from the data so it follows every refit,
whatever tiers exist; the watch file requires n_pers_towns >= 3.
"""

PLANS = [("150k", "0"), ("150k", "30"), ("400k", "0"), ("400k", "30")]


def _join(names):
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def facts(ctx, get):
    from build_targeting_site import clean_en

    pp = [get(f"bud.govt.{budget}.{ident}.pp") for budget, ident in PLANS]
    L = ctx.loc_sorted
    core, _ = ctx.exclusions
    pers = L[~L.index.isin(core) & (L["change_govt__pers_pot"] > 0)]
    top = pers.sort_values("change_govt__pers_pot", ascending=False).head(3)
    return {
        "field_govt_pp_min": min(pp),
        "field_govt_pp_max": max(pp),
        "n_pers_towns": int(len(pers)),
        "pers_top3": _join([clean_en(r.name_en, int(r.locality)) for r in top.itertuples()]),
    }
