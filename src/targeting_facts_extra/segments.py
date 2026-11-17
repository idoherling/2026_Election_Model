"""Derived numbers for the Segments page (data/processed/targeting/research/content_tok_segments.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.
Localities are addressed by CBS code (identifiers, not model values). Station counts follow the
atlas convention: a station is "positive" when its door value under the default objective
(change_govt__area_ve1k) is above zero and Arab lists do not lead it (Arab-led stations get no door
or list programme). "Realistic plans" are the four planner runs of the summary budgets
(150,000 / 400,000 contacts x 0% / 30% identified) under the default objective unless a name says
otherwise. Flags (1/0) exist only for the page's value-dependent wording (content_watch_segments.json).

String facts (tier lists, lead-list splits, ranked towns, plan phrases) are generated from the data so
the sentences stay true when the forecast is refitted. Town names follow the page's spelling
(PAGE_NAME), with a cleaned CBS English name as the fallback. Numbers inside generated strings use
the same rounding as the page's tokens (half-up; sig2 then thousands for net votes, one decimal for
efficiencies).
"""
from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal

from targeting_model import RESCUE_TO_CHANGE

# CBS locality codes named on the page
MUGHAR, ISIFYA, PEQIIN = 481, 534, 536
DALIYAT, BEIT_JANN, YIRKA, KISRA, YANUH, JULIS, SAJUR = 494, 480, 502, 1296, 1295, 485, 525
BET_SHEMESH, BNEI_BRAK, NETIVOT, ZEFAT, GIVAT_ZEEV = 2610, 6100, 246, 8000, 3730
JERUSALEM, TEL_AVIV, HAIFA, RAMAT_GAN = 3000, 5000, 4000, 8600
HERZLIYA, KFAR_SAVA, GIVATAYIM = 6400, 6900, 6300
TIVON, CAESAREA, RAMAT_HASHARON = 2300, 1167, 2650
LOD, RAMLA, AKKO, NOF_HAGALIL, MAALOT = 7000, 8500, 7600, 1061, 1063
RISHON, PETAH_TIKVA, REHOVOT = 8300, 7900, 8400
HOLON, NETANYA, BEER_SHEVA, EILAT, TIBERIAS, DIMONA, MOTZKIN, BIALIK = 6600, 7400, 9000, 2600, 6700, 2200, 8200, 9500
GIVAT_SHMUEL, YAD_BINYAMIN, NOF_AYALON, BAREQET = 681, 577, 1333, 2038
ASHDOD, BAT_YAM, ASHKELON, KARMIEL, NESHER, KIRYAT_YAM, ARAD, MIGDAL_HAEMEK, BNEI_AYISH = \
    70, 6200, 7100, 1139, 2500, 9600, 2560, 874, 1066
EFRAT, BET_EL, KIRYAT_ARBA, ELKANA = 3650, 3574, 3611, 3560
ARIEL, MAALE_ADUMIM, ORANIT, ALFEI_MENASHE = 3570, 3616, 3760, 3750
MAAGAN_MICHAEL, YAGUR, NAAN, GIVAT_BRENNER, GESHER_HAZIV = 694, 96, 158, 147, 574

DRUZE_TURNOUT_ENGINES = {DALIYAT, BEIT_JANN, YIRKA, KISRA, YANUH, ISIFYA, JULIS, MUGHAR, SAJUR}
DRUZE_PROJECTION_TOWNS = [DALIYAT, YIRKA, ISIFYA, BEIT_JANN, KISRA]
LIB_POT_NAMED = [RAMAT_GAN, HERZLIYA, KFAR_SAVA, GIVATAYIM]                         # in page order
HAREDI_LIST_TOWNS = {BET_SHEMESH, ZEFAT, BNEI_BRAK, NETIVOT}
CHANGE = ["Yashar", "Together", "Democrats", "Yisrael Beytenu"]
TE, SLG, PB, ST, LY, NBS = ("Turnout engine", "Supporter-list ground", "Persuasion battleground",
                            "Secondary target", "Low yield", "Netanyahu-bloc stronghold")
PLANS = [(b, i) for b in (150_000, 400_000) for i in (0.0, 0.3)]
NEVE_SHALOM = 1259
MIXED_CITIES = [LOD, RAMLA, AKKO, NOF_HAGALIL, MAALOT]          # page order; Neve Shalom is a village
MU_BIG4 = [HAIFA, RISHON, PETAH_TIKVA, REHOVOT]                   # named in the Middle Israel approach

# Page spellings for towns that generated lists can name (identifiers, not model values)
PAGE_NAME = {
    # secular-liberal urban
    5000: "Tel Aviv-Yafo", 8600: "Ramat Gan", 6400: "Herzliya", 6900: "Kfar Saba", 8700: "Ra'anana",
    1200: "Modi'in", 6300: "Givatayim", 9700: "Hod HaSharon", 2650: "Ramat HaSharon", 7200: "Ness Ziona",
    7800: "Pardes Hanna-Karkur", 2620: "Kiryat Ono", 9300: "Zichron Ya'akov", 1304: "Shoham",
    229: "Ganei Tikva", 195: "Kadima-Zoran", 2300: "Kiryat Tiv'on", 28: "Mazkeret Batya",
    9800: "Binyamina-Giv'at Ada", 154: "Tel Mond", 182: "Even Yehuda", 1268: "Meitar", 1224: "Kochav Yair",
    53: "Atlit", 666: "Omer", 1113: "Tzur Hadassah", 122: "Ramat Yishai", 171: "Pardesiya", 1271: "Lehavim",
    1167: "Caesarea", 1263: "Kfar Vradim", 1319: "Bat Hefer", 587: "Savyon", 1345: "Tzur Yitzhak",
    47: "Kfar Tavor", 1315: "Matan", 26: "Rosh Pina", 1243: "Katzir", 1284: "Nofit", 276: "Tzur Moshe",
    1337: "Shimshit", 267: "Kfar Shmaryahu", 1310: "Lapid", 1050: "Beit Hashmonai", 43: "Metula",
    # Middle Israel (mixed urban)
    4000: "Haifa", 8300: "Rishon LeZion", 7900: "Petah Tikva", 8400: "Rehovot", 2640: "Rosh HaAyin",
    2660: "Yavne", 9400: "Yehud-Monosson", 2550: "Gedera", 168: "Kfar Yona", 2530: "Be'er Ya'akov",
    166: "Gan Yavne", 1247: "Harish", 99: "Mitzpe Ramon", 1330: "Ahuzat Barak",
    # Likud-leaning periphery
    7400: "Netanya", 9000: "Be'er Sheva", 6600: "Holon", 6500: "Hadera", 9100: "Nahariya", 2600: "Eilat",
    6800: "Kiryat Ata", 7700: "Afula", 2630: "Kiryat Gat", 8200: "Kiryat Motzkin", 9500: "Kiryat Bialik",
    6700: "Tiberias", 2200: "Dimona", 2400: "Or Yehuda", 31: "Ofakim", 1031: "Sderot", 2100: "Tirat Carmel",
    1015: "Mevaseret Zion", 240: "Yokneam Illit", 2800: "Kiryat Shmona", 1034: "Kiryat Malakhi",
    1020: "Or Akiva", 9200: "Beit She'an", 565: "Azor", 469: "Kiryat Ekron", 831: "Yeruham",
    2034: "Hatzor HaGlilit", 812: "Shlomi", 466: "Beit Dagan", 41: "Elyakhin", 1274: "Gan Ner",
    1293: "Giv'at Avni", 65: "Migdal",
    # Russian-speaking
    70: "Ashdod", 6200: "Bat Yam", 7100: "Ashkelon", 1139: "Karmiel", 9600: "Kiryat Yam",
    874: "Migdal HaEmek", 2560: "Arad", 2500: "Nesher", 4100: "Katzrin", 1066: "Bnei Ayish",
    # mixed cities
    7000: "Lod", 8500: "Ramla", 7600: "Akko", 1061: "Nof HaGalil", 1063: "Ma'alot-Tarshiha",
    1259: "Neve Shalom",
}
LIST_ORDER = {"Yashar": 0, "Together": 1, "Democrats": 2, "Yisrael Beytenu": 3}
TIER_VERB = {TE: ("is a turnout engine", "are turnout engines"),
             SLG: ("is supporter-list ground", "are supporter-list ground"),
             PB: ("is a persuasion battleground", "are persuasion battlegrounds"),
             ST: ("is a secondary target", "are secondary targets"),
             NBS: ("is a Netanyahu-bloc stronghold", "are Netanyahu-bloc strongholds")}
WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


def _num(n: int) -> str:
    """Counts in prose: words up to twelve, digits with separators above."""
    n = int(n)
    return WORDS[n] if 0 <= n <= 12 else f"{n:,}"


def _rhu(x: float, nd: int) -> float:
    return float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def _votes(x: float) -> str:
    """Net votes as the page prints them: two significant figures, then whole numbers with separators."""
    x = float(x)
    if x != 0 and math.isfinite(x):
        x = _rhu(x, 2 - 1 - int(math.floor(math.log10(abs(x)))))
    return format(_rhu(x, 0), ",.0f")


def _join(items: list[str]) -> str:
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _clauses(parts: list[str]) -> str:
    """Join independent clauses: 'A', 'A, and B', 'A, B, and C'."""
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _list_name(lst: str, cap: bool = False) -> str:
    if lst == "Democrats":
        return "The Democrats" if cap else "the Democrats"
    return lst


def _en(code: int, name_en) -> str:
    code = int(code)
    if code in PAGE_NAME:
        return PAGE_NAME[code]
    n = str(name_en or "").strip()
    for a, b_ in [("Qiryat", "Kiryat"), ("Kefar ", "Kfar "), ("Bet ", "Beit "), ("Tiqwa", "Tikva"),
                  ("Ziyyona", "Ziona"), ("Ziyyon", "Zion"), ("Sede ", "Sde ")]:
        n = n.replace(a, b_)
    n = re.sub(r"yy", "y", n)
    n = re.sub(r"\bQ", "K", n)
    return re.sub(r"\s*-\s*", "-", re.sub(r"\s+", " ", n))


def facts(ctx, get):
    out = {}
    L = ctx.loc
    Li = L.set_index("locality")
    K = ctx.kal.merge(L[["locality", "segment"]], on="locality", how="left")
    K["pos"] = (K["change_govt__area_ve1k"] > 0) & ~K["arab_led"].astype(bool)
    seg = ctx.seg.set_index("segment")
    S = lambda s: L[L["segment"] == s]
    b = lambda x: int(bool(x))

    def pos(code, lead=None):
        m = (K["locality"] == code) & K["pos"]
        if lead is not None:
            m &= K["lead_change_list"] == lead
        return int(m.sum())

    def n_st(code):
        return int((K["locality"] == code).sum())

    def arab_led(code):
        return int(K.loc[K["locality"] == code, "arab_led"].astype(bool).sum())

    def seg_pos(s, lead=None):
        m = (K["segment"] == s) & K["pos"]
        if lead is not None:
            m &= K["lead_change_list"] == lead
        return int(m.sum())

    def tiers(s):
        return S(s)["change_govt__tier"].value_counts()

    def leads(s):
        return S(s)["lead_change_list"].value_counts()

    v = lambda code, col: Li.loc[code, col]
    nm = lambda code: _en(code, Li.loc[int(code), "name_en"])

    def tier_clause(s, tiers, values=False, strongholds_named=0):
        """'A (about N net votes at saturation), B (N) and C (N) are turnout engines, and D is a
        persuasion battleground' for one segment's localities in the given tiers (default objective).
        Towns in a tier are ordered by change-led-government potential. A stronghold group names its
        `strongholds_named` largest towns by eligible voters and counts the rest."""
        g = S(s)
        parts, first = [], True
        for t in tiers:
            gt = g[g["change_govt__tier"] == t]
            if gt.empty:
                continue
            if t == NBS and strongholds_named:
                big = gt.nlargest(strongholds_named, "eligible")
                names = [nm(c) for c in big["locality"]]
                rest = len(gt) - len(big)
                if rest:
                    names.append(f"{_num(rest)} smaller town" + ("s" if rest > 1 else ""))
            else:
                gt = gt.sort_values("change_govt__potential", ascending=False)
                names = []
                for c, p in zip(gt["locality"], gt["change_govt__potential"]):
                    if values:
                        names.append(f"{nm(c)} (about {_votes(p)} net votes at saturation)" if first
                                     else f"{nm(c)} ({_votes(p)})")
                        first = False
                    else:
                        names.append(nm(c))
            parts.append(f"{_join(names)} {TIER_VERB[t][0 if len(gt) == 1 else 1]}")
        return _clauses(parts)

    def lead_groups(codes):
        """Lead change list -> towns it leads (page order kept), lists ordered by towns led."""
        grp = {}
        for c in codes:
            grp.setdefault(v(c, "lead_change_list"), []).append(c)
        return sorted(grp.items(), key=lambda kv: (-len(kv[1]), LIST_ORDER.get(kv[0], 9)))

    def city_leads(codes, all_word):
        """'Yisrael Beytenu leads the citywide change vote in A, B and C, and Yashar in D'."""
        grp = lead_groups(codes)
        if len(grp) == 1:
            return f"{_list_name(grp[0][0], True)} leads the citywide change vote in all {all_word}"
        parts = [f"{_list_name(grp[0][0], True)} leads the citywide change vote in {_join(nm(c) for c in grp[0][1])}"]
        parts += [f"{_list_name(lst)} in {_join(nm(c) for c in cs)}" for lst, cs in grp[1:]]
        return _clauses(parts)

    def other_leads(s, named):
        """Lead-list counts in segment s for the lists not already named, largest first."""
        cnt = S(s)["lead_change_list"].value_counts()
        return sorted(((lst, int(n)) for lst, n in cnt.items() if lst not in named and n > 0),
                      key=lambda kv: (-kv[1], LIST_ORDER.get(kv[0], 9)))

    # ---------------------------------------------------------------- planner (default objective)
    LS = ctx.loc_sorted
    code_of = LS["locality"].to_dict()
    plans = {}
    for obj in ("change_govt", "block_nb", "change_seats"):
        for bud, ident in PLANS:
            a = ctx.plan(obj, bud, ident)["alloc"]
            plans[(obj, bud, ident)] = {code_of[k]: x for k, x in a.items()}

    def ve(obj, bud, ident, code):
        return float(plans[(obj, bud, ident)].get(code, {}).get("ve", 0.0))

    def ranking(obj, bud, ident):
        p = plans[(obj, bud, ident)]
        return sorted(p, key=lambda c: -p[c].get("ve", 0.0))

    def rank(obj, bud, ident, code):
        """1-based rank of a locality in a plan; one past the last locality if the plan does not fund it."""
        r = ranking(obj, bud, ident)
        return r.index(code) + 1 if code in r else len(LS) + 1

    def door(obj, bud, ident):
        return {c for c, x in plans[(obj, bud, ident)].items() if x.get("area", 0) > 0}

    govt = [("change_govt", bud, i) for bud, i in PLANS]
    every = list(plans)

    def door_phrase(code):
        """Which of the four realistic change-led-government plans send a door team to a town."""
        hit = [(bud, i) for _, bud, i in govt if code in door("change_govt", bud, i)]
        n, buds = len(hit), {bud for bud, _ in hit}
        if n == 0:
            return "none of the four realistic plans sends a door team there"
        if n == 4:
            return "all four realistic plans send a door team there"
        if n == 2 and len(buds) == 1:
            return f"only the two {next(iter(buds)):,}-contact plans send a door team there"
        if n == 1:
            bud, i = hit[0]
            lists = "without supporter lists" if i == 0 else f"with {int(round(100 * i))}% of supporters identified"
            return f"only the {bud:,}-contact plan {lists} sends a door team there"
        return f"{_num(n)} of the four realistic plans send a door team there"

    # ---------------------------------------------------------------- Arab segments
    def lead_share(s, col):
        g = S(s)
        w = g["voters_2026_est"]
        return float((g[col] * w).sum() / w.sum())
    out["negev_raam_share"] = 100 * lead_share("arab_bedouin_south", "p26_Ra'am")
    out["negev_jl_share"] = 100 * lead_share("arab_bedouin_south", "p26_Joint List")
    out["christian_jl_share"] = 100 * lead_share("arab_christian", "p26_Joint List")
    out["christian_dem_share"] = 100 * lead_share("arab_christian", "p26_Democrats")
    out["christian_dem_leads"] = int(leads("arab_christian").get("Democrats", 0))
    nt_r, nt_j = lead_share("arab_north_triangle", "p26_Ra'am"), lead_share("arab_north_triangle", "p26_Joint List")
    # change-led-government value (points per 10,000 votes) of the segment's Arab-list vote mix
    out["north_arab_mix_govt"] = (nt_r * get("mv.Raam.govt") + nt_j * get("mv.JL.govt")) / (nt_r + nt_j)

    # ---------------------------------------------------------------- Druze
    d = S("druze")
    out["druze_named_change_min"] = float(Li.loc[DRUZE_PROJECTION_TOWNS, "p26_change"].min())
    out["druze_named_change_max"] = float(Li.loc[DRUZE_PROJECTION_TOWNS, "p26_change"].max())
    arab_lead = d[d["p26_arab"] > d[["p26_change", "p26_nb"]].max(axis=1)]
    out["druze_arab_lead_count"] = int(len(arab_lead))
    out["druze_arab_lead_is_mughar"] = b(len(arab_lead) == 1 and int(arab_lead["locality"].iloc[0]) == MUGHAR)
    druze_adds = [get(f"bud.govt.{bud // 1000}k.{int(round(i * 100))}.druze") for bud, i in PLANS]
    out["druze_add_min"], out["druze_add_max"] = float(min(druze_adds)), float(max(druze_adds))
    # door yield (net votes per 1,000 door contacts) by segment; rank of the Druze segment among
    # the non-Arab segments (the atlas publishes no Arab-segment values)
    g = L[~L["segment"].str.startswith("arab")].groupby("segment")
    yld = g["change_govt__area_pot"].sum() / g["change_govt__area_contacts"].sum()
    out["druze_door_yield_rank"] = int((yld > yld["druze"]).sum() + 1)
    eff = L[(L["eligible"] >= 5000) & ~L["segment"].str.startswith("arab")] \
        .sort_values("change_govt__area_eff1k", ascending=False)
    out["druze_eff_top3_match"] = b(list(eff["locality"].head(3)) == [KISRA, BEIT_JANN, DALIYAT])
    out["druze_turnout_engines"] = int(tiers("druze").get(TE, 0))
    out["druze_te_match"] = b(set(d.loc[d["change_govt__tier"] == TE, "locality"]) == DRUZE_TURNOUT_ENGINES)
    out["druze_leads_match"] = b(
        all(v(c, "lead_change_list") == "Yashar" for c in (DALIYAT, YIRKA, ISIFYA, KISRA, SAJUR))
        and all(v(c, "lead_change_list") == "Yisrael Beytenu" for c in (MUGHAR, JULIS, YANUH))
        and v(BEIT_JANN, "lead_change_list") == "Democrats")
    out["arab_led_mughar"], out["arab_led_isifya"], out["arab_led_peqiin"] = \
        arab_led(MUGHAR), arab_led(ISIFYA), arab_led(PEQIIN)
    out["druze_arab_led_total"] = int(K.loc[K["segment"] == "druze", "arab_led"].astype(bool).sum())
    sc = ctx.sens["objectives"]["change_govt"]["scenarios"]
    out["druze_stress_changed"] = int(sc["base"]["top25_overlap"] - sc["druze_minus20"]["top25_overlap"])

    # ---------------------------------------------------------------- Haredi
    h = S("haredi")
    out["haredi_strongholds"] = int(tiers("haredi").get(NBS, 0))
    out["haredi_mixed_change_min"] = float(Li.loc[[NETIVOT, ZEFAT, GIVAT_ZEEV], "p26_change"].min())
    out["haredi_mixed_change_max"] = float(Li.loc[[NETIVOT, ZEFAT, GIVAT_ZEEV], "p26_change"].max())
    out["haredi_positive"] = seg_pos("haredi")
    out["haredi_yashar_leads"] = int(leads("haredi").get("Yashar", 0))
    out["haredi_top4_list_match"] = b(set(h.nlargest(4, "change_govt__list_pot")["locality"]) == HAREDI_LIST_TOWNS)

    # ---------------------------------------------------------------- Jerusalem
    jk = K[(K["locality"] == JERUSALEM) & K["pos"]]
    out["jerusalem_positive"] = pos(JERUSALEM)
    out["jerusalem_positive_frac"] = pos(JERUSALEM) / n_st(JERUSALEM)
    out["jerusalem_pos_change_min"] = float(jk["p26_change"].min())
    out["jerusalem_pos_change_max"] = float(jk["p26_change"].max())
    out["jerusalem_pos_yashar"] = pos(JERUSALEM, "Yashar")
    out["jerusalem_pos_democrats"] = pos(JERUSALEM, "Democrats")
    out["arab_led_jerusalem"] = arab_led(JERUSALEM)
    out["jerusalem_door_plans"] = sum(JERUSALEM in door(*p) for p in govt)
    out["jerusalem_govt_150k_0"] = ve("change_govt", 150_000, 0.0, JERUSALEM)
    out["jerusalem_govt_400k_0"] = ve("change_govt", 400_000, 0.0, JERUSALEM)
    out["jerusalem_govt_400k_30"] = ve("change_govt", 400_000, 0.3, JERUSALEM)
    r = ranking("change_govt", 400_000, 0.3)
    out["jerusalem_govt_400k_30_rank"] = rank("change_govt", 400_000, 0.3, JERUSALEM)
    out["top3_400k_30_match"] = b(r[:3] == [TEL_AVIV, HAIFA, RAMAT_GAN])

    # ---------------------------------------------------------------- Kibbutz
    k = S("kibbutz")
    kt, kl = tiers("kibbutz"), leads("kibbutz")
    out["kibbutz_change_lead"] = int((k["p26_change"] > k[["p26_nb", "p26_arab"]].max(axis=1)).sum())
    out["kibbutz_nb_lead"] = int((k["p26_nb"] > k[["p26_change", "p26_arab"]].max(axis=1)).sum())
    out["kibbutz_low_yield"] = int(kt.get(LY, 0))
    out["kibbutz_secondary"] = int(kt.get(ST, 0))
    out["kibbutz_strongholds"] = int(kt.get(NBS, 0))
    out["kibbutz_tiers_other"] = int(len(k) - kt.get(LY, 0) - kt.get(ST, 0) - kt.get(NBS, 0))
    ks = k[k["change_govt__tier"] == NBS]
    out["kibbutz_strongholds_nb_led"] = b((ks["p26_nb"] > ks["p26_change"]).all())
    knb = k[k["p26_nb"] > k[["p26_change", "p26_arab"]].max(axis=1)]
    out["kibbutz_nb_lead_religious_frac"] = float((knb["religiosity_modal"] == "religious").mean()) if len(knb) else 0.0
    out["kibbutz_strongholds_religious"] = b((ks["religiosity_modal"] == "religious").all())
    out["kibbutz_lead_democrats"] = int(kl.get("Democrats", 0))
    out["kibbutz_lead_yashar"] = int(kl.get("Yashar", 0))
    out["kibbutz_lead_together"] = int(kl.get("Together", 0))
    out["kibbutz_lead_other"] = int(len(k) - kl.get("Democrats", 0) - kl.get("Yashar", 0) - kl.get("Together", 0))
    out["kibbutz_examples_match"] = b(
        all(v(c, "lead_change_list") == "Democrats" for c in (MAAGAN_MICHAEL, YAGUR, NAAN))
        and all(v(c, "lead_change_list") == "Yashar" for c in (GIVAT_BRENNER, GESHER_HAZIV)))
    kib = set(k["locality"])
    out["kibbutz_door_plans"] = sum(len(door(*p) & kib) > 0 for p in every)

    # ---------------------------------------------------------------- Secular-liberal urban
    lu = S("liberal_urban")
    out["tel_aviv_national_share"] = 100 * float(v(TEL_AVIV, "change_govt__potential")) / get("sat.govt.potential")
    out["lib_pot_order_match"] = b(list(lu.nlargest(5, "change_govt__potential")["locality"])
                                   == [TEL_AVIV] + LIB_POT_NAMED)
    sp = seg["rescue_voters"]
    out["lib_rescue_largest"] = b(sp.idxmax() == "liberal_urban")
    out["liberal_positive"] = seg_pos("liberal_urban")
    out["liberal_pos_yashar_frac"] = seg_pos("liberal_urban", "Yashar") / max(seg_pos("liberal_urban"), 1)
    out["arab_led_tel_aviv"] = arab_led(TEL_AVIV)
    non_druze = eff[eff["segment"] != "druze"]
    out["tel_aviv_best_eff_non_druze"] = b(int(non_druze["locality"].iloc[0]) == TEL_AVIV)
    lu5 = lu[(lu["eligible"] >= 5000) & (lu["locality"] != TEL_AVIV)] \
        .sort_values("change_govt__area_eff1k", ascending=False)
    # the six next-best towns of 5,000+ voters by door efficiency, in rank order with their values
    nxt = lu5.head(6)
    out["lib_eff_next6"] = _join(f"{nm(c)} ({_rhu(e, 1):.1f})"
                                 for c, e in zip(nxt["locality"], nxt["change_govt__area_eff1k"]))
    out["lib_eff_next_n"] = int(len(nxt))
    out["tel_aviv_govt_150k_0"] = ve("change_govt", 150_000, 0.0, TEL_AVIV)
    out["tel_aviv_tops_all_plans"] = b(all(ranking(*p)[0] == TEL_AVIV for p in every))
    out["tel_aviv_positive"] = pos(TEL_AVIV)
    out["tel_aviv_pos_democrats"] = pos(TEL_AVIV, "Democrats")
    out["tel_aviv_pos_democrats_frac"] = pos(TEL_AVIV, "Democrats") / max(pos(TEL_AVIV), 1)
    sec = lu["second_change_list"].value_counts()
    out["lib_together_usual_second"] = b(sec.idxmax() == "Together")
    # Blue and White + Reservists voters as a share (%) of projected 2026 voters
    out["liberal_rescue_share"] = 100 * float(lu["rescue_voters"].sum() / lu["voters_2026_est"].sum())
    out["national_rescue_share"] = 100 * float(L["rescue_voters"].sum() / L["voters_2026_est"].sum())
    # value of rescuing one voter (points per 10,000 votes): RESCUE_TO_CHANGE to the national
    # change-list mix, the rest to Likud, minus the vote's value where it stands (the model's rescue rule)
    ch = {"Yashar": "Yashar", "Together": "Together", "Democrats": "Democrats", "Yisrael Beytenu": "YB"}
    w = {s: get(f"mv.{s}.share") for s in ch.values()}
    for obj in ("govt", "deny"):
        vch = sum(w[s] * get(f"mv.{s}.{obj}") for s in w) / sum(w.values())
        for lst, key in (("BW", "bw"), ("Reservists", "res")):
            try:   # a withdrawn list (Blue and White, 19 Oct) has no exchange rate
                out[f"rescue_gain_{key}_{obj}"] = (RESCUE_TO_CHANGE * vch + (1 - RESCUE_TO_CHANGE) * get(f"mv.Likud.{obj}")
                                                   - get(f"mv.{lst}.{obj}"))
            except KeyError:
                out[f"rescue_gain_{key}_{obj}"] = float("nan")

    # ---------------------------------------------------------------- Mixed cities
    out["lod_ramla_nb_min"] = float(Li.loc[[LOD, RAMLA], "p26_nb"].min())
    out["lod_ramla_nb_max"] = float(Li.loc[[LOD, RAMLA], "p26_nb"].max())
    out["lod_ramla_same_change"] = b(round(100 * v(LOD, "p26_change")) == round(100 * v(RAMLA, "p26_change")))
    gap = lambda c: abs(v(c, "p26_nb") - v(c, "p26_change"))
    out["nof_maalot_closer"] = b(max(gap(NOF_HAGALIL), gap(MAALOT)) < min(gap(LOD), gap(RAMLA)))
    out["mixed_city_leads"] = city_leads(MIXED_CITIES, "five cities")
    out["mixed_city_positive"] = seg_pos("mixed_city")
    for name, c in (("lod", LOD), ("maalot", MAALOT), ("nof_hagalil", NOF_HAGALIL), ("akko", AKKO), ("ramla", RAMLA)):
        out[f"{name}_positive"] = pos(c)
    out["mixed_city_positive_named_sum"] = sum(pos(c) for c in (LOD, MAALOT, NOF_HAGALIL, AKKO, RAMLA))
    lk = K[(K["locality"] == LOD) & K["pos"]]
    out["lod_pos_change_min"], out["lod_pos_change_max"] = float(lk["p26_change"].min()), float(lk["p26_change"].max())
    mc = set(S("mixed_city")["locality"])
    out["lod_only_mixed_door_400k"] = b(all(door(*p) & mc == ({LOD} if p[1] == 400_000 else set()) for p in govt))
    out["mixed_city_pos_yb"] = seg_pos("mixed_city", "Yisrael Beytenu")
    out["mixed_city_pos_yashar"] = seg_pos("mixed_city", "Yashar")
    out["mixed_city_pos_other"] = seg_pos("mixed_city") - out["mixed_city_pos_yb"] - out["mixed_city_pos_yashar"]
    lod_yb = pos(LOD, "Yisrael Beytenu")
    out["lod_pos_yb"] = lod_yb
    out["lod_pos_yb_phrase"] = (f"all {pos(LOD)}" if lod_yb == pos(LOD)
                                else f"{lod_yb} of the {pos(LOD)}")

    # ---------------------------------------------------------------- Middle Israel (mixed urban)
    mu = S("mixed_urban")
    for name, c in (("rishon", RISHON), ("haifa", HAIFA), ("petah_tikva", PETAH_TIKVA), ("rehovot", REHOVOT)):
        out[f"{name}_positive"] = pos(c)
    out["arab_led_haifa"] = arab_led(HAIFA)
    out["haifa_pos_yb"] = pos(HAIFA, "Yisrael Beytenu")
    out["rishon_largest_pers"] = b(int(L.loc[L["change_govt__pers_pot"].idxmax(), "locality"]) == RISHON)
    # top tiers of the segment, generated with each town's saturation value
    out["mu_tiers"] = tier_clause("mixed_urban", [TE, SLG, PB], values=True)
    out["mu_n_top"] = int(mu["change_govt__tier"].isin([TE, SLG, PB]).sum())
    # Petah Tikva: persuasion against turnout value, as a comparison phrase
    pt_p, pt_g = float(v(PETAH_TIKVA, "change_govt__pers_pot")), float(v(PETAH_TIKVA, "change_govt__gotv_pot"))
    ratio = pt_p / pt_g if pt_g > 0 else math.inf
    out["pt_pers_vs_gotv"] = ("about as much as" if 0.85 <= ratio <= 1.15
                              else "more than" if ratio > 1.15 else "less than")
    # the segment's other towns where persuasion outweighs turnout
    oth = mu[~mu["locality"].isin(MU_BIG4)]
    pl = oth[oth["change_govt__pers_pot"] > oth["change_govt__gotv_pot"]] \
        .sort_values("change_govt__pers_pot", ascending=False)
    out["mu_other_n"], out["mu_pers_led_other_n"] = int(len(oth)), int(len(pl))
    if len(pl) == 0:
        out["mu_pers_led_clause"] = ""
    elif len(pl) == 1:
        out["mu_pers_led_clause"] = (f", and it outweighs turnout in one of the segment's other "
                                     f"{_num(len(oth))} towns, {nm(pl['locality'].iloc[0])}")
    else:
        out["mu_pers_led_clause"] = (f", and it outweighs turnout in {_num(len(pl))} of the segment's other "
                                     f"{_num(len(oth))} towns, such as "
                                     f"{_join(nm(c) for c in pl['locality'].head(2))}")
    out["haifa_second_all_plans"] = b(all(ranking(*p)[1] == HAIFA for p in every))
    out["mixed_urban_pos_yashar_frac"] = seg_pos("mixed_urban", "Yashar") / max(seg_pos("mixed_urban"), 1)
    out["mixed_urban_together_usual_second"] = b(mu["second_change_list"].value_counts().idxmax() == "Together")

    # ---------------------------------------------------------------- Moshav & rural
    m = S("moshav_rural")
    mt, ml = tiers("moshav_rural"), leads("moshav_rural")
    out["moshav_lead_yashar"] = int(ml.get("Yashar", 0))
    out["moshav_lead_democrats"] = int(ml.get("Democrats", 0))
    out["moshav_lead_yb"] = int(ml.get("Yisrael Beytenu", 0))
    out["moshav_lead_other"] = int(len(m) - ml.get("Yashar", 0) - ml.get("Democrats", 0) - ml.get("Yisrael Beytenu", 0))
    # ", the Democrats in 21 and Yisrael Beytenu in two" after "Yashar leads ... in N of the 458"
    rest = [f"{_list_name(lst)} in {_num(n)}" for lst, n in other_leads("moshav_rural", ["Yashar"])]
    out["moshav_lead_rest"] = ("" if not rest else f", and {rest[0]}" if len(rest) == 1
                               else ", " + _join(rest))
    out["moshav_low_yield"] = int(mt.get(LY, 0))
    out["moshav_strongholds"] = int(mt.get(NBS, 0))
    out["moshav_nb_majority"] = int((m["p26_nb"] > 0.5).sum())
    out["moshav_change_lead_frac"] = float((m["p26_change"] > m["p26_nb"]).mean())
    mos = set(m["locality"])
    out["moshav_door_plans"] = sum(len(door(*p) & mos) > 0 for p in every)

    # ---------------------------------------------------------------- Likud-leaning periphery
    pl = S("periphery_likud")
    out["persuadable_largest_periphery"] = b(seg["persuadable_voters"].idxmax() == "periphery_likud")
    out["periphery_change_lead_count"] = int((pl["p26_change"] > pl["p26_nb"]).sum())
    out["motzkin_bialik_lead"] = b(all(v(c, "p26_change") > v(c, "p26_nb") for c in (MOTZKIN, BIALIK)))
    out["periphery_tiers"] = tier_clause("periphery_likud", [TE, SLG, PB, NBS], strongholds_named=2)
    out["periphery_n_top"] = int(pl["change_govt__tier"].isin([TE, SLG, PB]).sum())
    slg = pl[pl["change_govt__tier"] == SLG].sort_values("change_govt__potential", ascending=False)
    out["periphery_slg"] = _join(nm(c) for c in slg["locality"])
    out["periphery_n_slg"] = int(len(slg))
    pk = K[K["segment"] == "periphery_likud"]
    out["periphery_stations"] = int(len(pk))
    out["periphery_positive"] = int(pk["pos"].sum())
    out["periphery_negative"] = int((pk["change_govt__area_ve1k"] < 0).sum())
    out["tiberias_door_plans"] = sum(TIBERIAS in door(*p) for p in every)
    out["netanya_govt_150k_30"] = ve("change_govt", 150_000, 0.3, NETANYA)
    out["beer_sheva_govt_150k_30"] = ve("change_govt", 150_000, 0.3, BEER_SHEVA)
    out["netanya_beer_sheva_150k_30_worst_rank"] = max(rank("change_govt", 150_000, 0.3, NETANYA),
                                                        rank("change_govt", 150_000, 0.3, BEER_SHEVA))
    for name, c in (("holon", HOLON), ("netanya", NETANYA), ("beer_sheva", BEER_SHEVA), ("eilat", EILAT),
                    ("tiberias", TIBERIAS)):
        out[f"{name}_positive"] = pos(c)
    out["motzkin_bialik_pos_min_frac"] = min(pos(MOTZKIN) / n_st(MOTZKIN), pos(BIALIK) / n_st(BIALIK))
    out["periphery_positive_frac"] = seg_pos("periphery_likud") / int((K["segment"] == "periphery_likud").sum())
    out["periphery_all_yashar"] = b((pl["lead_change_list"] == "Yashar").all())

    # ---------------------------------------------------------------- Religious-Zionist
    rz = S("religious_zionist")
    rt, rl = tiers("religious_zionist"), leads("religious_zionist")
    out["rz_strongholds"] = int(rt.get(NBS, 0))
    out["rz_secondary"] = int(rt.get(ST, 0))
    out["rz_named_change_min"] = float(Li.loc[[YAD_BINYAMIN, NOF_AYALON, BAREQET], "p26_change"].min())
    out["rz_named_change_max"] = float(Li.loc[[YAD_BINYAMIN, NOF_AYALON, BAREQET], "p26_change"].max())
    out["givat_shmuel_positive"] = pos(GIVAT_SHMUEL)
    out["givat_shmuel_area_frac"] = float(v(GIVAT_SHMUEL, "change_govt__area_pot")) / float(rz["change_govt__area_pot"].sum())
    out["givat_shmuel_door_plans"] = sum(GIVAT_SHMUEL in door(*p) for p in govt)
    out["rz_lead_yashar"] = int(rl.get("Yashar", 0))
    out["rz_lead_together"] = int(rl.get("Together", 0))
    out["rz_leads_examples_match"] = b(v(GIVAT_SHMUEL, "lead_change_list") == "Yashar"
                                       and all(v(c, "lead_change_list") == "Together" for c in (YAD_BINYAMIN, NOF_AYALON)))
    out["givat_shmuel_door_phrase"] = door_phrase(GIVAT_SHMUEL)
    # " Yisrael Beytenu leads in one." after the Yashar and Together counts ("" when they cover all)
    rest = other_leads("religious_zionist", ["Yashar", "Together"])
    if rest:
        head = f"{_list_name(rest[0][0], True)} leads in {_num(rest[0][1])}"
        out["rz_lead_rest_sentence"] = " " + _join([head] + [f"{_list_name(l_)} in {_num(n)}" for l_, n in rest[1:]]) + "."
    else:
        out["rz_lead_rest_sentence"] = ""

    # ---------------------------------------------------------------- Russian-speaking
    ru = seg.loc["russian_speaking"]
    for part in ("gotv", "pers", "resc"):
        out[f"russian_{part}_share"] = 100 * float(ru[f"change_govt__{part}_pot"] / ru["change_govt__potential"])
    for name, c in (("ashdod", ASHDOD), ("bat_yam", BAT_YAM), ("ashkelon", ASHKELON)):
        out[f"{name}_positive"] = pos(c)
        out[f"{name}_pos_yb"] = pos(c, "Yisrael Beytenu")
        out[f"{name}_pos_yb_frac"] = pos(c, "Yisrael Beytenu") / max(pos(c), 1)
    out["ru_most_positive_min_frac"] = min(pos(c) / n_st(c) for c in (KARMIEL, NESHER, KIRYAT_YAM, ARAD))
    out["bat_yam_ashdod_door_match"] = b(
        BAT_YAM in door("change_govt", 150_000, 0.0)
        and all(ASHDOD in door("change_govt", 400_000, i) for i in (0.0, 0.3))
        and not any(ASHDOD in door("change_govt", 150_000, i) for i in (0.0, 0.3)))
    # citywide lead lists, generated: Yisrael Beytenu's towns by size, then who leads the rest
    rs = S("russian_speaking").sort_values("eligible", ascending=False)
    yb_t = list(rs.loc[rs["lead_change_list"] == "Yisrael Beytenu", "locality"])
    others = [c for c in rs["locality"] if c not in yb_t]
    if not others:
        ru = "It also leads the citywide change vote in every town."
    else:
        ru = f"It also leads the citywide change vote in {_join(nm(c) for c in yb_t)}." if yb_t else ""
        if all(v(c, "lead_change_list") == "Yashar" for c in others):
            ru += " Yashar leads the rest." if yb_t else " Yashar leads the citywide change vote in every town."
        else:
            ru += " " + city_leads(others, "the other towns") + "."
    out["ru_leads_sentence"] = ru.strip()
    out["ru_yb_lead_n"] = len(yb_t)
    out["ru_te_match"] = b(set(rs.loc[rs["change_govt__tier"] == TE, "locality"]) == {ASHDOD, BAT_YAM})
    out["ashdod_ashkelon_nb_min"] = float(Li.loc[[ASHDOD, ASHKELON], "p26_nb"].min())
    out["ashdod_ashkelon_nb_max"] = float(Li.loc[[ASHDOD, ASHKELON], "p26_nb"].max())

    # ---------------------------------------------------------------- West Bank
    sr = S("settlement_rz")
    out["settlement_rz_strongholds"] = int(tiers("settlement_rz").get(NBS, 0))
    out["settlement_rz_positive"] = seg_pos("settlement_rz")
    out["settlement_rz_lead_together"] = int(leads("settlement_rz").get("Together", 0))
    out["settlement_rz_together_examples"] = b(all(v(c, "lead_change_list") == "Together" for c in (EFRAT, BET_EL, ELKANA)))
    big = sr.nlargest(6, "eligible")
    out["bet_el_kiryat_arba_least_open"] = b(set(big.nsmallest(2, "p26_change")["locality"]) == {BET_EL, KIRYAT_ARBA})
    out["efrat_largest"] = b(int(sr.loc[sr["eligible"].idxmax(), "locality"]) == EFRAT)
    out["ariel_maale_nb_min"] = float(Li.loc[[ARIEL, MAALE_ADUMIM], "p26_nb"].min())
    out["ariel_maale_nb_max"] = float(Li.loc[[ARIEL, MAALE_ADUMIM], "p26_nb"].max())
    out["oranit_alfei_yashar_all_stations"] = b(all(
        (K.loc[K["locality"] == c, "lead_change_list"] == "Yashar").all() for c in (ORANIT, ALFEI_MENASHE)))
    ss = S("settlement_secular")
    out["ariel_maale_top2_pers"] = b(set(ss.nlargest(2, "change_govt__pers_pot")["locality"]) == {ARIEL, MAALE_ADUMIM})
    out["oranit_alfei_pers_min_frac"] = min(float(v(c, "change_govt__pers_pot") / v(c, "change_govt__potential"))
                                            for c in (ORANIT, ALFEI_MENASHE))
    # persuasion is the largest of the three mechanisms (turnout, persuasion, rescue) in both
    out["oranit_alfei_pers_largest"] = b(all(
        v(c, "change_govt__pers_pot") > max(v(c, "change_govt__gotv_pot"), v(c, "change_govt__resc_pot"))
        for c in (ORANIT, ALFEI_MENASHE)))
    return out
