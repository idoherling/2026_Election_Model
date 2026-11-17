"""Derived numbers for the Playbook page (data/processed/targeting/research/content_tok_playbook.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.
Model constants (LIST_CONTACT: half of identified voters are reached; RESCUE_TO_CHANGE: 60% of
rescued voters go to change lists) come from targeting_model. Town names are CBS codes.

Realistic plans (bud.* facts; Arab localities, Arab-led stations, access-excluded and Druze towns out):
    range_lo, range_hi      lowest / highest net votes across the atlas's assumption sets (bud.*.lo/hi),
                            over the change-led-government and deny-61 plans (150k/400k, 0/30% identified)
    ve_min_all, ve_max_all  lowest / highest base-case net votes over all twelve plans (three objectives)
    druze_min_<o>, druze_max_<o>   Druze add-on if cleared (net votes), over the four plans of objective
                            o in govt, deny, seats
    list_gain_150k, list_gain_400k  net votes that list programmes at 30% identified add at the same
                            budget (change-led government)
    files_sup, files_pers, files_resc  identified voters the change-led-government 400k/30% plan needs on
                            file: supporters, soft Netanyahu-bloc voters, Blue and White / Reservists voters
                            (the plan's list contacts / LIST_CONTACT)
    sup_change_pct          change-bloc share (%) of the residents of the stations where that plan runs
                            supporter calls (the stations of the supporter-call tranches it uses; a partly
                            used tranche counts pro rata; residents = the model's contact pool)
    id_conversations        cold ID conversations needed to find files_sup supporters there
                            (files_sup / sup_change_pct)

The change-led-government 400k/30% plan, per locality (net votes; ranks by net votes):
    plan_ve_<town>          net votes in the plan: tlv, haifa, ramat_gan, jerusalem, rishon, herzliya,
                            netanya, beer_sheva, eilat, ashkelon, hadera
    plan_tlv_rank           Tel Aviv-Yafo's rank in the plan
    plan_top7_order_ok      1 if the seven towns the page lists (Tel Aviv-Yafo, Haifa, Ramat Gan,
                            Jerusalem, Rishon LeZion, Herzliya, Netanya) are the plan's top seven, in order
    plan_list_share_<town>  share of the town's net votes from list programmes (calls and asks to
                            identified voters): jerusalem, netanya, ashdod, bat_yam
    plan_door_<town>        door contacts in the plan: beer_sheva, eilat, ashkelon, hadera
    plan0_<150k|400k>_ve_<town>   net votes in the change-led-government plan WITHOUT lists (0% identified)
                            at that budget: beer_sheva, eilat, ashkelon, hadera (0 = not in the plan)

Supporter-call potential (change-led government; atlas saturation, not a plan):
    sup_pot_<code>          net votes from calls to identified supporters alone in locality <code>
                            (the supporter part of loc.<code>.change_govt__list_pot): 7400 Netanya,
                            9000 Be'er Sheva, 2600 Eilat, 2610 Beit Shemesh, 3000 Jerusalem, 70 Ashdod,
                            6200 Bat Yam, 6600 Holon

Saturation, pools and stations:
    sat_govt_contacts       contacts saturation needs (door + list), all localities, change-led govt
    persuadable_total, persuadable_pct   cross-pressured soft Netanyahu-bloc voters, and % of the
                            atlas's projected 2026 voters
    rescue_total, rescue_pct   Blue and White + Reservists voters at regular stations, and % of voters
    pos_yashar, pos_democrats, pos_yb, pos_together   positive-value stations (change-led govt) by lead
                            change list, outside Arab localities, Arab-led stations, access-excluded and
                            Druze towns (they sum to kal.positive_core_govt)
    tlv_pos_yashar, tlv_pos_democrats   Tel Aviv-Yafo's positive-value, non-Arab-led stations by lead list

Forecast and exchange rates:
    nb_below61              % of forecast draws with the Netanyahu bloc below 61: 100 minus bloc.nb61
                            rounded half-up to a whole percent, so the two printed shares sum to 100
    mv_govt_ytd_mean        mean change-led-government exchange rate of Yashar, Together and the Democrats
                            (points per 10,000 votes); mv_govt_ytd_spread = max - min of the three
    resc_res_deny_per_mover deny-61 value (points per 10,000 movers) of rescuing Reservists voters: movers
                            split RESCUE_TO_CHANGE to change lists (size-weighted) and the rest to Likud,
                            minus the Reservists' own deny-61 rate (<= 0 means rescue does not help)

Sensitivity (sensitivity_summary.json):
    always_top25_govt       localities in the change-led-government top 25 in every scenario
    sens_low_gotv_low       of the twelve plans, how many have their low end set by the half-size
                            turnout effect (scenario gotv_low)
    sens_high_gotv_flat     how many have their high end set by dropping the turnout hump (gotv_flat)
    sens_seats150k30_high_rescue   1 if the change-bloc-seats 150k/30% plan's high end is rescue x3

Atlas wording checks (1 = the page's wording holds):
    engines_top11_ok        how many of the eleven turnout engines the page names are the eleven
                            largest-potential turnout engines outside the low-confidence (Druze) towns
    pers_top5_ok            1 if Rishon LeZion, Petah Tikva, Holon, Jerusalem and Tel Aviv-Yafo are the
                            top five localities by persuasion value, in order
    druze_top_door_eff      1 if the non-Arab locality (5,000+ eligible) with the best door efficiency is Druze
    kibmosh_max_door        largest door capacity (contacts) of any kibbutz or moshav locality
    kibmosh_low_yield_share share of kibbutz and moshav localities tiered low yield
    yashar_lead_share_targets   share of target-tier localities (turnout engine, supporter-list ground,
                            persuasion battleground, secondary target) with 20,000+ eligible that Yashar leads

Generated town lists (strings, default objective; the site's English names via
build_targeting_site.clean_en; "A, B and C"; Arab localities, access-excluded and held-out Druze
towns are never named). Counts guard the wording in content_watch_playbook.json:
    engines_top, n_engines_core     the N_ENGINES largest-potential turnout engines; how many exist
    slg_towns, n_slg                supporter-list ground towns by potential; how many
    slg_min_nb                      lowest projected Netanyahu-bloc share among them (0 if none)
    slg_min_sup_minus_area          lowest (supporter-call value - door value) among them (0 if none)
    sup_heavy_towns, n_sup_heavy    other target-tier towns (turnout engine, persuasion battleground,
                                    secondary target) where supporter calls are SUP_HEAVY_SHARE+ of the
                                    town's potential, top N_LIST_TOWNS by supporter-call value; how many
    pers_top5_then, pers_top3       top five ("A, then B, C, D and E") and top three by persuasion value
    n_pers_pos                      named towns with any persuasion value
    pers_top5_min_gotv_minus_pers   lowest (turnout value - persuasion value) among those five
    n_pbg, pers_bg_sentence         persuasion battlegrounds (any town), and a sentence that is true
                                    for none, one or several
    plan_top7_text                  the 400k/30% plan's seven largest towns: "T yields about N net
                                    votes, U n, ... and Z n" (sig2, as the page's tokens print)
    plan_list_heavy_towns, n_plan_list_heavy   towns with door teams in that plan where list programmes
                                    give LIST_HEAVY_SHARE+ of the town's net votes, top N_LIST_TOWNS by
                                    net votes; how many
    calls_only_towns, n_calls_only  towns in that plan with no door teams and absent from both plans
                                    without lists (150k, 400k at 0%), top N_LIST_TOWNS by net votes; how many
The older checks above (engines_top11_ok, pers_top5_ok, plan_top7_order_ok, plan_list_share_*, plan_door_*,
plan0_*, sup_pot_<code>) are kept so content_tok_playbook.json still renders.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

OBJ = {"govt": "change_govt", "deny": "block_nb", "seats": "change_seats"}
PLANS = [f"{b}.{i}" for b in ("150k", "400k") for i in ("0", "30")]
TOWNS = {"tlv": 5000, "haifa": 4000, "ramat_gan": 8600, "jerusalem": 3000, "rishon": 8300,
         "herzliya": 6400, "netanya": 7400, "beer_sheva": 9000, "eilat": 2600, "ashkelon": 7100,
         "hadera": 6500, "ashdod": 70, "bat_yam": 6200}
TOP7 = ["tlv", "haifa", "ramat_gan", "jerusalem", "rishon", "herzliya", "netanya"]
ENGINES = [5000, 4000, 8600, 8300, 3000, 6400, 6600, 8400, 6200, 6900, 6300]   # timeline[0].actions[1]
PERS_TOP5 = [8300, 7900, 6600, 3000, 5000]   # Rishon LeZion, Petah Tikva, Holon, Jerusalem, Tel Aviv-Yafo
TARGET_TIERS = ["Turnout engine", "Supporter-list ground", "Persuasion battleground", "Secondary target"]
CALLS_ONLY = ["beer_sheva", "eilat", "ashkelon", "hadera"]   # sections[0].bullets[7]: "bring in ... through calls alone"
SUP_POT = [7400, 9000, 2600, 2610, 3000, 70, 6200, 6600]   # dos[1].text, timeline[0].actions[4]
# generated town lists (15 Oct onward)
N_ENGINES = 11          # timeline[0].actions[1]: how many turnout engines to name
N_LIST_TOWNS = 4        # list-heavy, calls-only and supporter-call towns named per sentence
SUP_HEAVY_SHARE = 0.25  # "a quarter or more of the value" (supporter calls / town potential)
LIST_HEAVY_SHARE = 0.4  # "40% or more of the plan's net votes" (list programmes / plan net votes)


def _en_names(ctx) -> dict:
    """CBS code -> the site's English name (build_targeting_site.clean_en: overrides, then cleaned CBS name)."""
    try:
        from build_targeting_site import clean_en
    except Exception:  # noqa: BLE001
        def clean_en(n, c):
            return str(n).strip()
    L = ctx.loc
    return {int(c): clean_en(n, int(c)) for c, n in zip(L["locality"], L["name_en"])}


def _join(names) -> str:
    """'A', 'A and B', 'A, B and C' (empty string for no names)."""
    names = [n for n in names if n]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _govt_plan(ctx, budget, ident):
    """ctx.plan('change_govt', ...), building only the change_govt tranches when ctx has none cached."""
    import targeting_planner as tp
    if "tranches" in ctx.__dict__:
        tr = ctx.tranches["change_govt"]
    else:
        tr = tp.tranches({"change_govt": ctx.units["change_govt"]}, ctx.loc_sorted["locality"])["change_govt"]
    core, _ = ctx.exclusions
    return tr, tp.allocate(tr, budget, ident, exclude=core)


def _prog_value(tr_rows, i, amount, ident, area):
    """Net votes from `amount` contacts of one programme in locality i (tranches taken best first)."""
    left, v = amount, 0.0
    for _, cap, val in sorted((r for r in tr_rows if r[0] == i), key=lambda r: -r[2]):
        take = min(left, cap if area else cap * ident)
        left -= take
        v += take * val / 1000
        if left <= 1e-9:
            break
    return v


def facts(ctx, get):
    import targeting_model as tm
    import targeting_planner as tp
    out = {}

    # ---- realistic plans
    lo = [get(f"bud.{o}.{p}.lo") for o in ("govt", "deny") for p in PLANS]
    hi = [get(f"bud.{o}.{p}.hi") for o in ("govt", "deny") for p in PLANS]
    out["range_lo"], out["range_hi"] = min(lo), max(hi)
    ve = [get(f"bud.{o}.{p}.ve") for o in OBJ for p in PLANS]
    out["ve_min_all"], out["ve_max_all"] = min(ve), max(ve)
    for o in OBJ:
        d = [get(f"bud.{o}.{p}.druze") for p in PLANS]
        out[f"druze_min_{o}"], out[f"druze_max_{o}"] = min(d), max(d)
    for b in ("150k", "400k"):
        out[f"list_gain_{b}"] = get(f"bud.govt.{b}.30.ve") - get(f"bud.govt.{b}.0.ve")
    for k in ("sup", "pers", "resc"):
        out[f"files_{k}"] = get(f"bud.govt.400k.30.{k}") / tm.LIST_CONTACT

    # ---- the change-led-government 400k / 30% plan
    ident = 0.3
    tr, plan = _govt_plan(ctx, 400_000, ident)
    alloc = plan["alloc"]
    Ls = ctx.loc_sorted
    li = {int(code): k for k, code in enumerate(Ls["locality"])}
    order = sorted(alloc, key=lambda i: -alloc[i]["ve"])
    rank = {i: r + 1 for r, i in enumerate(order)}
    for slug, code in TOWNS.items():
        a = alloc.get(li[code], {"ve": 0.0, "area": 0.0})
        out[f"plan_ve_{slug}"] = a["ve"]
        if slug in ("beer_sheva", "eilat", "ashkelon", "hadera"):
            out[f"plan_door_{slug}"] = a["area"]
    out["plan_tlv_rank"] = rank.get(li[TOWNS["tlv"]], 0)
    out["plan_top7_order_ok"] = int([rank.get(li[TOWNS[s]], 0) for s in TOP7] == list(range(1, 8)))
    for slug in ("jerusalem", "netanya", "ashdod", "bat_yam"):
        i = li[TOWNS[slug]]
        a = alloc.get(i)
        lv = sum(_prog_value(tr[p], i, a[p], ident, False) for p in ("sup", "pers", "resc")) if a else 0.0
        out[f"plan_list_share_{slug}"] = lv / a["ve"] if a and a["ve"] > 0 else 0.0

    # the same objective without lists (0% identified): are the calls-only towns absent?
    core, _ = ctx.exclusions
    alloc0 = {}
    for b in ("150k", "400k"):
        alloc0[b] = tp.allocate(tr, int(b[:-1]) * 1000, 0.0, exclude=core)["alloc"]
        for slug in CALLS_ONLY:
            out[f"plan0_{b}_ve_{slug}"] = alloc0[b].get(li[TOWNS[slug]], {"ve": 0.0})["ve"]

    # supporter-call potential per locality (supporter part of change_govt__list_pot)
    locs, val, cap = ctx.units["change_govt"]["sup"]
    sp = pd.DataFrame({"l": np.asarray(locs).astype(int), "v": val, "c": cap})
    sp = sp[(sp.v > 0) & (sp.c > 0)]
    sup_pot = (sp.v * sp.c * tm.LIST_IDENTIFIED / 1000).groupby(sp.l).sum()
    for code in SUP_POT:
        out[f"sup_pot_{code}"] = float(sup_pot.get(code, 0.0))

    # ---- generated town lists (default objective). Arab localities, access-excluded and the
    # held-out Druze (low-confidence) towns are never named.
    from targeting_facts import fmt_value
    en = _en_names(ctx)
    Lx = ctx.loc.copy()
    Lx["locality"] = Lx["locality"].astype(int)
    Lx["en"] = Lx["locality"].map(en)
    Lx["sup_pot"] = Lx["locality"].map(sup_pot).fillna(0.0)
    tier = Lx["change_govt__tier"]
    named = ~Lx.segment.str.startswith("arab") & Lx.field_excluded.isna() & Lx.low_confidence.isna()
    by_pot = Lx[named].sort_values("change_govt__potential", ascending=False)

    eng = by_pot[by_pot["change_govt__tier"] == "Turnout engine"]
    out["n_engines_core"] = int(len(eng))
    out["engines_top"] = _join(eng["en"].head(N_ENGINES))

    slg = by_pot[by_pot["change_govt__tier"] == "Supporter-list ground"]
    out["n_slg"] = int(len(slg))
    out["slg_towns"] = _join(slg["en"])
    out["slg_min_nb"] = float(slg["p26_nb"].min()) if len(slg) else 0.0
    out["slg_min_sup_minus_area"] = (float((slg["sup_pot"] - slg["change_govt__area_pot"]).min())
                                     if len(slg) else 0.0)

    sh = by_pot[by_pot["change_govt__tier"].isin(["Turnout engine", "Persuasion battleground", "Secondary target"])]
    sh = sh[sh["sup_pot"] >= SUP_HEAVY_SHARE * sh["change_govt__potential"]].sort_values("sup_pot", ascending=False)
    out["n_sup_heavy"] = int(len(sh))
    out["sup_heavy_towns"] = _join(sh["en"].head(N_LIST_TOWNS))

    out["n_pers_pos"] = int((Lx.loc[named, "change_govt__pers_pot"] > 0).sum())
    pers = Lx[named].sort_values("change_govt__pers_pot", ascending=False).head(5)
    pn = list(pers["en"])
    out["pers_top5_then"] = pn[0] + (", then " + _join(pn[1:]) if len(pn) > 1 else "")
    out["pers_top3"] = _join(pn[:3])
    out["pers_top5_min_gotv_minus_pers"] = float((pers["change_govt__gotv_pot"] - pers["change_govt__pers_pot"]).min())
    pbg = Lx[tier == "Persuasion battleground"].sort_values("change_govt__potential", ascending=False)
    out["n_pbg"] = int(len(pbg))
    if len(pbg) == 0:
        out["pers_bg_sentence"] = ("No town is a persuasion battleground in the current atlas: even in these "
                                   "towns turnout is worth at least as much, so pair persuasion with turnout work.")
    elif len(pbg) == 1:
        out["pers_bg_sentence"] = (f"{pbg['en'].iloc[0]} is the only persuasion battleground, the one town where "
                                   "persuasion is the main mechanism.")
    else:
        out["pers_bg_sentence"] = (f"{_join(pbg['en'])} are the persuasion battlegrounds, where persuasion is "
                                   "the main mechanism.")

    # the 400k / 30% plan by town: top seven, list-heavy towns with door teams, calls-only towns
    code_of = {k: int(c) for k, c in enumerate(Ls["locality"])}
    rows = []
    for i, a in alloc.items():
        lv = (sum(_prog_value(tr[p], i, a[p], ident, False) for p in ("sup", "pers", "resc"))
              if a["area"] > 0 else a["ve"])
        rows.append({"en": en[code_of[i]], "ve": a["ve"], "door": a["area"],
                     "list_share": lv / a["ve"] if a["ve"] > 0 else 0.0,
                     "in_plan0": any(alloc0[b].get(i, {"ve": 0.0})["ve"] > 0 for b in alloc0)})
    P = pd.DataFrame(rows).sort_values("ve", ascending=False)
    top7 = P.head(7)
    parts = [f"{r.en} {fmt_value(r.ve, ['sig2', 'f:,.0f'])}" for r in top7.itertuples()]
    if parts:
        parts[0] = f"{top7.en.iloc[0]} yields about {fmt_value(top7.ve.iloc[0], ['sig2', 'f:,.0f'])} net votes"
    out["plan_top7_text"] = _join(parts)
    lh = P[(P.door > 0) & (P.ve > 0) & (P.list_share >= LIST_HEAVY_SHARE)]
    out["n_plan_list_heavy"] = int(len(lh))
    out["plan_list_heavy_towns"] = _join(lh["en"].head(N_LIST_TOWNS))
    co = P[(P.door == 0) & (P.ve > 0) & ~P.in_plan0]
    out["n_calls_only"] = int(len(co))
    out["calls_only_towns"] = _join(co["en"].head(N_LIST_TOWNS))

    # change-bloc share of the residents of the stations behind the plan's supporter calls
    K = ctx.kal
    locs, val, cap = ctx.units["change_govt"]["sup"]
    df = pd.DataFrame({"l": np.asarray(locs).astype(int), "v": val, "c": cap, "st": np.arange(len(locs))})
    df = df[(df.v > 0) & (df.c > 0) & df.l.isin(li)]
    ch = K["p26_change"].values
    n = tp.N_TRANCHES
    sup_res = pool_res = 0.0
    for lid, g in df.groupby("l"):          # same tranches as targeting_planner.tranches
        a = alloc.get(li[lid])
        if not a or a["sup"] <= 0:
            continue
        g = g.sort_values("v", ascending=False)
        share = (g.c.cumsum() - g.c / 2) / g.c.sum()
        q = np.minimum((share.values * n).astype(int), n - 1)
        left = a["sup"]
        for _, gg in g.groupby(q):          # best tranche first, as the greedy allocation takes them
            capt = gg.c.sum() * ident
            take = min(left, capt)
            left -= take
            if take <= 0:
                break
            f = take / capt
            res = gg.c.values / tm.LIST_CONTACT / ch[gg.st.values]      # residents (contact pool)
            sup_res += f * (res * ch[gg.st.values]).sum()
            pool_res += f * res.sum()
    out["sup_change_pct"] = 100 * sup_res / pool_res
    out["id_conversations"] = out["files_sup"] / (sup_res / pool_res)

    # ---- saturation, pools, stations
    out["sat_govt_contacts"] = get("sat.govt.area_contacts") + get("sat.govt.list_contacts")
    L = ctx.loc
    voters = L["voters_2026_est"].sum()
    out["persuadable_total"] = float(L["persuadable_voters"].sum())
    out["persuadable_pct"] = 100 * out["persuadable_total"] / voters
    out["rescue_total"] = float(L["rescue_voters"].sum())
    out["rescue_pct"] = 100 * out["rescue_total"] / voters
    core_loc = set(L.loc[~(L.segment.str.startswith("arab") | L.field_excluded.notna()
                           | L.low_confidence.notna()), "locality"])
    pos = (K["change_govt__area_ve1k"] > 0) & ~K["arab_led"]
    lead = K.loc[pos & K.locality.isin(core_loc), "lead_change_list"].value_counts()
    for slug, name in [("yashar", "Yashar"), ("democrats", "Democrats"), ("yb", "Yisrael Beytenu"),
                       ("together", "Together")]:
        out[f"pos_{slug}"] = int(lead.get(name, 0))
    tlv = K.loc[pos & (K.locality == TOWNS["tlv"]), "lead_change_list"].value_counts()
    out["tlv_pos_yashar"] = int(tlv.get("Yashar", 0))
    out["tlv_pos_democrats"] = int(tlv.get("Democrats", 0))

    # ---- forecast and exchange rates
    # complement of the ROUNDED share (half-up, as the renderer rounds), so 12.5 prints 13% / 87%
    out["nb_below61"] = 100 - math.floor(get("bloc.nb61") + 0.5)
    ytd = [get(f"mv.{s}.govt") for s in ("Yashar", "Together", "Democrats")]
    out["mv_govt_ytd_mean"] = sum(ytd) / len(ytd)
    out["mv_govt_ytd_spread"] = max(ytd) - min(ytd)
    ch_lists = ("Yashar", "Together", "Democrats", "YB")
    w = [get(f"mv.{s}.share") for s in ch_lists]
    ch_deny = sum(wi * get(f"mv.{s}.deny") for wi, s in zip(w, ch_lists)) / sum(w)
    out["resc_res_deny_per_mover"] = (tm.RESCUE_TO_CHANGE * ch_deny + (1 - tm.RESCUE_TO_CHANGE)
                                      * get("mv.Likud.deny") - get("mv.Reservists.deny"))

    # ---- sensitivity
    sens = ctx.sens
    out["always_top25_govt"] = int(sens["objectives"]["change_govt"]["n_always_top25"])
    n_low = n_high = 0
    for o, obj in OBJ.items():
        for p in PLANS:
            b, i = p.split(".")
            sk = f"{int(b[:-1]) * 1000}_{'0.3' if i == '30' else '0.0'}"
            vals = {s: d[obj][sk] for s, d in sens["budgets"].items() if obj in d}
            n_low += int(vals.get("gotv_low") == get(f"bud.{o}.{p}.lo"))
            n_high += int(vals.get("gotv_flat") == get(f"bud.{o}.{p}.hi"))
            if o == "seats" and p == "150k.30":
                out["sens_seats150k30_high_rescue"] = int(vals.get("rescue_high") == get(f"bud.{o}.{p}.hi"))
    out["sens_low_gotv_low"], out["sens_high_gotv_flat"] = n_low, n_high

    # ---- atlas wording checks
    eng = L[(L["change_govt__tier"] == "Turnout engine") & L.low_confidence.isna()]
    top11 = set(eng.sort_values("change_govt__potential", ascending=False)["locality"].head(len(ENGINES)))
    out["engines_top11_ok"] = len(top11 & set(ENGINES))
    out["pers_top5_ok"] = int(list(L.sort_values("change_govt__pers_pot", ascending=False)["locality"]
                                   .head(len(PERS_TOP5))) == PERS_TOP5)
    nonarab = L[~L.segment.str.startswith("arab") & (L["eligible"] >= 5000)]
    best = nonarab.sort_values("change_govt__area_eff1k", ascending=False).iloc[0]
    out["druze_top_door_eff"] = int(best["segment"] == "druze")
    km = L[L.segment.isin(["kibbutz", "moshav_rural"])]
    out["kibmosh_max_door"] = float(km["change_govt__area_contacts"].max())
    out["kibmosh_low_yield_share"] = float((km["change_govt__tier"] == "Low yield").mean())
    tgt = L[L["change_govt__tier"].isin(TARGET_TIERS) & (L["eligible"] >= 20_000)]
    out["yashar_lead_share_targets"] = float((tgt["lead_change_list"] == "Yashar").mean())
    return out
