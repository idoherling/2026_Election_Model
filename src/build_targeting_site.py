"""Build the Field Atlas site: payload JSON + one self-contained HTML page.

Reads the targeting layer's outputs (targeting_model.py), the forecast's
headline files and the map geometry, compacts everything into one JSON
payload, and injects it into site/targeting_template.html.

Outputs:
    output/targeting/site_data.json
    output/targeting/index.html
    output/targeting/localities.csv   (published alongside the page)
    output/targeting/kalpi_targets.csv
"""

from __future__ import annotations

import json
import re
from datetime import date

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR, RAW_DIR

ROOT = PROCESSED_DIR.parent.parent
T = PROCESSED_DIR / "targeting"
SITE_OUT = ROOT / "output" / "targeting"
TEMPLATE = ROOT / "site" / "targeting_template.html"
CONTENT = ROOT / "site" / "targeting_content.json"
ELECTION_DAY = date(2026, 10, 27)

OBJ = ["change_govt", "block_nb", "change_seats", "change61", "change_raam61"]
OBJ_LABEL = {
    "change_govt": "Change-led government",
    "block_nb": "Deny Netanyahu 61",
    "change_seats": "Change-bloc seats",
    "change61": "Change bloc alone ≥ 61",
    "change_raam61": "Change bloc + Ra'am ≥ 61",
}
PLANNER_OBJ = ["change_govt", "block_nb", "change_seats"]

DISTRICT_EN = {"הצפון": "North", "הדרום": "South", "המרכז": "Centre",
               "חיפה": "Haifa", "ירושלים": "Jerusalem", "תל אביב": "Tel Aviv",
               "אזור יהודה ושומרון": "Judea & Samaria"}
EN_OVERRIDE = {
    5000: "Tel Aviv-Yafo", 8300: "Rishon LeZion", 7900: "Petah Tikva",
    9000: "Be'er Sheva", 7100: "Ashkelon", 6100: "Bnei Brak",
    6400: "Herzliya", 6900: "Kfar Saba", 2610: "Beit Shemesh",
    8700: "Ra'anana", 1200: "Modi'in-Maccabim-Re'ut", 9100: "Nahariya",
    2600: "Eilat", 6300: "Givatayim", 2640: "Rosh HaAyin",
    6800: "Kiryat Ata", 2630: "Kiryat Gat", 7600: "Acre (Akko)",
    1139: "Karmiel", 8200: "Kiryat Motzkin", 9600: "Kiryat Yam",
    9500: "Kiryat Bialik", 7200: "Ness Ziona", 2620: "Kiryat Ono",
    8800: "Shefa-'Amr", 2730: "Tayibe", 3780: "Beitar Illit",
    3616: "Ma'ale Adumim", 8000: "Safed (Tzfat)", 31: "Ofakim",
    1031: "Sderot", 1309: "Elad", 2800: "Kiryat Shmona",
    1034: "Kiryat Malakhi", 9200: "Beit She'an", 168: "Kfar Yona",
    634: "Kafr Qasim", 494: "Daliyat al-Karmel", 534: "Isfiya",
    480: "Beit Jann", 1295: "Yanuh-Jat", 1296: "Kisra-Sumei",
    496: "Hurfeish", 485: "Julis", 502: "Yarka", 536: "Peki'in", 3400: "Hebron",
    1136: "Tzohar",
    525: "Sajur", 508: "Kafr Kama", 540: "Reihaniye", 3000: "Jerusalem",
    1161: "Rahat", 2710: "Umm al-Fahm", 7300: "Nazareth", 1061: "Nof HaGalil",
    1063: "Ma'alot-Tarshiha", 7000: "Lod", 8500: "Ramla", 6200: "Bat Yam",
    9400: "Yehud-Monosson", 2660: "Yavne", 7700: "Afula",
    3570: "Ariel", 3650: "Efrat", 681: "Givat Shmuel", 2400: "Or Yehuda",
    2200: "Dimona", 246: "Netivot", 6700: "Tiberias", 6500: "Hadera",
}


def clean_en(name: str, code: int) -> str:
    if code in EN_OVERRIDE:
        return EN_OVERRIDE[code]
    if not isinstance(name, str) or not name.strip():
        return ""
    n = name.strip()
    for a, b in [("Qiryat", "Kiryat"), ("Kefar ", "Kfar "), ("Bet ", "Beit "),
                 ("Tiqwa", "Tikva"), ("Ziyyon", "Zion"), ("Ziyyona", "Ziona"),
                 ("Ma'ale ", "Ma'ale "), ("Sede ", "Sde "), ("Nahal ", "Nahal ")]:
        n = n.replace(a, b)
    n = re.sub(r"yy", "y", n)
    n = re.sub(r"\bQ", "K", n)
    n = re.sub(r"\s+", " ", n)
    return n


def he_name(r) -> str:
    n = r["name_cbs"] if isinstance(r["name_cbs"], str) and r["name_cbs"].strip() \
        else r["name_he"]
    n = re.sub(r"\s+-\s*|\s*-\s+", "-", str(n).strip())
    return re.sub(r"\s+", " ", n)


def rnd(x, d=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), d)


def col(df, c, d=3):
    return [rnd(v, d) for v in df[c].tolist()]


def simplify_ring(ring, tol=0.004):
    """Douglas-Peucker on [lon, lat] pairs (degrees)."""
    pts = np.asarray(ring, float)
    if len(pts) < 5:
        return pts.round(3).tolist()

    def dp(a, b):
        if b <= a + 1:
            return [a, b]
        seg = pts[b] - pts[a]
        L = np.hypot(*seg)
        if L == 0:
            d = np.hypot(*(pts[a + 1:b] - pts[a]).T)
        else:
            d = np.abs(np.cross(seg, pts[a + 1:b] - pts[a])) / L
        i = int(np.argmax(d))
        if d[i] > tol:
            left = dp(a, a + 1 + i)
            return left[:-1] + dp(a + 1 + i, b)
        return [a, b]
    keep = dp(0, len(pts) - 1)
    return pts[keep].round(3).tolist()


def geo_payload():
    g = {}
    ne = json.loads((RAW_DIR / "geo" / "ne10m_region.json").read_text())
    g["neighbors"] = []
    for name in ("Lebanon", "Syria", "Jordan", "Egypt"):
        for poly in ne[name]:
            ring = [p for p in poly[0] if 33.6 <= p[0] <= 37.2 and 28.8 <= p[1] <= 34.0]
            if len(ring) > 3:
                g["neighbors"].append(simplify_ring(poly[0], 0.01))
    g["israel"] = [simplify_ring(poly[0], 0.002) for poly in ne["Israel"]]
    isr = json.loads((RAW_DIR / "geo" / "isr_adm1.geojson").read_text())
    g["districts"] = []
    for f in isr["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            g["districts"].append(simplify_ring(poly[0], 0.002))
    pse = json.loads((RAW_DIR / "geo" / "pse_adm1.geojson").read_text())
    g["palestine"] = {}
    for f in pse["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        g["palestine"][f["properties"]["shapeName"]] = [simplify_ring(p[0], 0.002)
                                                        for p in polys]
    return g


TIER_NAMES = ["Turnout engine", "Supporter-list ground", "Persuasion battleground",
              "Secondary target", "Arab-list turf (partner-led)", "Netanyahu-bloc stronghold",
              "Low yield", "Not targeted (access)"]
OBJ_PARTS = [("potential", 1), ("area_pot", 1), ("list_pot", 1), ("gotv_pot", 1),
             ("pers_pot", 1), ("resc_pot", 1), ("eff1k", 2), ("area_eff1k", 2),
             ("list_eff1k", 2), ("per100h", 2), ("area_avg_ve1k", 2),
             ("area_contacts", 0), ("list_contacts", 0), ("neg_share", 3), ("rank", 0)]
RESEARCH = T / "research"
KEY_DATES = {"surplus_deadline": "2026-10-16", "final_polls": "2026-10-23",
             "blackout": "2026-10-24", "election": "2026-10-27"}


def reservists_polls(since: str = "2026-09-15") -> dict:
    """How many published polls since mid-September show the Reservists
    (zionist_home) above the threshold, for the summary's rescue card."""
    p = pd.read_csv(PROCESSED_DIR / "polls.csv", low_memory=False)
    p = p[(p["cycle"].astype(str) == "2026") & (p["party_id"] == "zionist_home")].copy()
    p["fe"] = pd.to_datetime(p["fieldwork_end"], errors="coerce")
    p = p[p["fe"] >= since]
    g = p.groupby("poll_id").agg(seats=("seats", "max"), fe=("fe", "max"))
    return {"n": int(len(g)), "above": int((g["seats"] >= 4).sum()), "since": since,
            "latest": g["fe"].max().date().isoformat() if len(g) else None}


def assemble_content() -> dict:
    """Site content from the research workflow: the final checked files when
    present, else the latest drafts."""
    def pick(name):
        for stem in ("content_final_", "content_v4_", "content_v3_", "content_v2_", "content_draft_"):
            p = RESEARCH / f"{stem}{name}.json"
            if p.exists():
                return json.loads(p.read_text()), p.name
        return {}, None
    seg, f1 = pick("segments")
    pb, f2 = pick("playbook")
    src, f3 = pick("sources")
    st, f4 = pick("strategy")
    ms, f5 = pick("messaging")
    co, f6 = pick("coalition")
    vi, f7 = pick("victory")
    content = {"segments": seg.get("segments", []), "playbook": pb,
               "sources": src.get("sources", []), "strategy": st, "messaging": ms,
               "coalition": co, "victory": vi, "files": [f1, f2, f3, f4, f5, f6, f7]}
    # model numbers in the prose are {{tokens}} filled from the current pipeline outputs
    import targeting_facts as tf
    facts = tf.Facts()
    n_tok = len(tf.tokens_in(content))
    content = tf.render_tree(content, facts, "content")
    content["facts_asof"] = facts.get("fc.asof")
    print(f"rendered {n_tok} model-number tokens (forecast {content['facts_asof']})")
    for wf in sorted(RESEARCH.glob("content_watch_*.json")):
        bad = tf.check_watch(json.loads(wf.read_text()), facts)
        for b in bad:
            print(f"WARNING {wf.name}: wording no longer matches the numbers: {json.dumps(b, ensure_ascii=False)}")
    CONTENT.write_text(json.dumps(content, ensure_ascii=False, indent=1))
    print("content from", content["files"])
    return content


def fmt_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Round for publication: counts to integers, shares to 4 decimals,
    vote-equivalents to 2, so the CSV never shows scientific notation."""
    out = df.copy()
    for c in out.columns:
        if not pd.api.types.is_float_dtype(out[c]):
            continue
        s = out[c]
        if c in ("eligible", "eligible_2026_est", "persuadable_voters", "rescue_voters",
                 "change_abstained_est", "change_supporters", "voters", "valid") or \
                c.endswith("_contacts") or c.endswith("__rank") or c.endswith("_index"):
            out[c] = s.round(0).astype("Int64")
        elif c.endswith(("_ve1k", "_pot", "__potential", "eff1k", "per100h")):
            out[c] = s.round(2)
        elif s.abs().max() <= 1.5:
            out[c] = s.round(4)
        else:
            out[c] = s.round(2)
    return out


def main() -> None:
    import sys
    import targeting_planner as tp
    SITE_OUT.mkdir(parents=True, exist_ok=True)
    content = assemble_content() if ("--assemble-content" in sys.argv or not CONTENT.exists()) \
        else json.loads(CONTENT.read_text())
    loc = pd.read_csv(T / "localities.csv")
    kal = pd.read_parquet(T / "kalpi_all.parquet")
    hist = pd.read_parquet(T / "camp_history.parquet")
    seg = pd.read_csv(T / "segments.csv")
    val = json.loads((T / "validation.json").read_text())
    mv = pd.read_csv(T / "marginal_values.csv")
    mmeta = json.loads((T / "marginal_meta.json").read_text())
    fc = pd.read_csv(PROCESSED_DIR / "official_forecast.csv")
    blocs = pd.read_csv(PROCESSED_DIR / "mixture_blocs.csv").iloc[0].to_dict()
    gov = pd.read_csv(PROCESSED_DIR / "government_formation.csv")
    pm = pd.read_csv(PROCESSED_DIR / "pm_probabilities.csv")
    nat = pd.read_csv(T / "national.csv")

    loc = loc.sort_values("locality").reset_index(drop=True)
    loc["he"] = loc.apply(he_name, axis=1)
    loc["en"] = [clean_en(n, c) for n, c in zip(loc["name_en"], loc["locality"])]
    loc["en"] = np.where(loc["en"] == "", loc["he"], loc["en"])
    loc["district_en"] = loc["district"].map(DISTRICT_EN).fillna("")
    asof = json.loads((T / "share_draws_meta.json").read_text())["asof"]
    for c in ("displaced", "field_excluded", "low_confidence"):
        loc[c] = loc[c].fillna("")

    ses = pd.read_csv(RAW_DIR / "cbs" / "ses2019.csv", low_memory=False).dropna(axis=1, how="all")
    fix_ap = lambda t: re.sub(r"(['’])([A-Z])", lambda m: m.group(1) + m.group(2).lower(), t.title())
    rc = dict(zip(ses["HEBREW NAME OF REGIONAL COUNCIL "].astype(str).str.strip(),
                  ses["NAME OF REGIONAL COUNCIL "].astype(str).str.strip().map(fix_ap)))
    rc.update({"שדות דן": "Sdot Dan", "בוסתן אל-מרג'": "Bustan al-Marj", "אל-בטוף": "Al-Batuf"})

    def council(m):
        if not isinstance(m, str):
            return ""
        m = m.strip()
        if m.startswith("מועצה אזורית"):
            nm = m.replace("מועצה אזורית", "").strip()
            return (rc.get(nm, nm) + " Regional Council")
        return {"עירייה": "Municipality", "מועצה מקומית": "Local council",
                "חסר מעמד מוניציפלי": "No municipal status"}.get(m, m)
    loc["council_en"] = loc["municipal"].map(council)
    # The atlas makes no field recommendation for Arab localities, so it
    # publishes no town-level values or ranks for them (segment totals only).
    arab = loc["segment"].str.startswith("arab")
    target = ~arab & (loc["field_excluded"] == "")
    for o in OBJ:
        loc[f"{o}__rank"] = loc[f"{o}__potential"].where(target).rank(
            ascending=False, method="first")
        hide = [c for c in loc.columns if c.startswith(o + "__") and c != f"{o}__tier"]
        loc.loc[arab, hide] = np.nan
    for c in ("lead_change_list", "second_change_list"):
        loc[c] = loc[c].where(~arab & (loc["p26_change"] >= 0.15))
    for c in ("swing_index", "turnout_index", "rescue_index", "impact_index"):
        loc[c] = loc[c].where(~arab)

    # ---- localities, columnar
    L = {
        "id": loc["locality"].astype(int).tolist(),
        "he": loc["he"].tolist(), "en": loc["en"].tolist(),
        "dist": loc["district_en"].tolist(),
        "council": loc["council_en"].tolist(),
        "seg": loc["segment"].tolist(),
        "stype": loc["settlement_type"].fillna("other").tolist(),
        "lat": col(loc, "lat", 4), "lon": col(loc, "lon", 4),
        "elig": loc["eligible"].astype(int).tolist(),
        "elig26": col(loc, "eligible_2026_est", 0),
        "t22": col(loc, "turnout_2022"), "tres": col(loc, "turnout_resident"),
        "tceil": col(loc, "turnout_ceiling"),
        "abroad": col(loc, "roll_abroad", 3), "phantom": col(loc, "phantom_roll", 3),
        "env": col(loc, "envelope_addback", 3),
        "s22C": col(loc, "s22_C"), "s22R": col(loc, "s22_R"), "s22A": col(loc, "s22_A"),
        "pch": col(loc, "p26_change"), "pnb": col(loc, "p26_nb"),
        "par": col(loc, "p26_arab"), "pun": col(loc, "p26_unaligned"),
        "pers": col(loc, "persuadable_share", 4), "persv": col(loc, "persuadable_voters", 0),
        "resc": col(loc, "rescue_share", 4), "rescv": col(loc, "rescue_voters", 0),
        "rbw": col(loc, "rescue_bw_share", 4), "rres": col(loc, "rescue_res_share", 4),
        "open": col(loc, "openness"),
        "lift": [None if a else v for a, v in zip(arab, col(loc, "gotv_lift_pp", 2))],
        "netg": [None if a else v for a, v in zip(arab, col(loc, "net_change_per1k_gotv_turf", 2))],
        "netga": [None if a else v for a, v in zip(arab, col(loc, "net_change_per1k_gotv_avg", 2))],
        "chabst": col(loc, "change_abstained_est", 0),
        "chsup": col(loc, "change_supporters", 0),
        "nk": loc["n_kalpiot"].astype(int).tolist(),
        "cph": col(loc, "conv_per_hour", 1),
        "lead": loc["lead_change_list"].fillna("").tolist(),
        "lead2": loc["second_change_list"].fillna("").tolist(),
        "disp": loc["displaced"].tolist(), "excl": loc["field_excluded"].tolist(),
        "lowc": loc["low_confidence"].tolist(),
        "capm": col(loc, "capacity_mult", 2),
        "swi": col(loc, "swing_index", 0), "tui": col(loc, "turnout_index", 0),
        "rei": col(loc, "rescue_index", 0), "imi": col(loc, "impact_index", 0),
        "age": col(loc, "age_median", 0), "acad": col(loc, "academic_pct", 1),
        "eur": col(loc, "born_europe_pct", 1),
        "asaf": [rnd(a + b, 1) if pd.notna(a) and pd.notna(b) else None
                 for a, b in zip(loc["born_asia_pct"], loc["born_africa_pct"])],
        "relig": loc["religiosity_modal"].fillna("").tolist(),
        "ses": col(loc, "ses_score", 2), "km": col(loc, "km_tel_aviv", 0),
        "pop": col(loc, "pop2023", 0),
    }
    tix = {t: k for k, t in enumerate(TIER_NAMES)}
    for o in PLANNER_OBJ:
        for part, d in OBJ_PARTS:
            L[f"{o}.{part}"] = col(loc, f"{o}__{part}", d)
        L[f"{o}.tier"] = [tix[t] for t in loc[f"{o}__tier"]]
    short = ["Likud", "Yashar", "Together", "Democrats", "Yisrael Beytenu", "Shas",
             "UTJ", "Otzma", "RZP-Zehut", "Ra'am", "Joint List", "Blue & White",
             "Reservists", "Amcha"]
    L["p26"] = [[rnd(v, 3) for v in row] for row in
                loc[[f"p26_{s}" for s in short]].values.tolist()]

    # ---- history (camp shares + turnout), aligned with L order
    cyc = ["2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
    h = hist.copy()
    for c in ["C", "R", "A"]:
        h[c] = h[f"c_{c}"] / h["valid"].replace(0, np.nan)
    H = {"cycles": cyc}
    for c in ["C", "R", "A", "turnout"]:
        p = h.pivot_table(index="locality", columns="cycle", values=c)
        p = p.reindex(index=loc["locality"], columns=cyc)
        H[c] = [[rnd(v, 3) for v in row] for row in p.values.tolist()]

    # ---- polling stations (every locality)
    kal = kal.copy()
    kal["kalpi"] = kal["kalpi"].astype(str).str.replace(r"\.0$", "", regex=True)
    # rows: [kalpi, eligible, turnout, resident turnout, change, NB, Arab lists,
    # lead change list, door value per 1,000 (change govt, of which turnout,
    # persuasion; deny 61; seats), Arab-led flag]. Arab localities carry only
    # [kalpi, eligible]; stations where Arab lists lead carry no values.
    K = {}
    arab_ids = set(loc.loc[arab, "locality"])
    for lid, g in kal.groupby("locality"):
        if int(lid) in arab_ids:
            K[int(lid)] = [[r.kalpi, int(r.eligible)] for r in g.itertuples()]
            continue
        rows = []
        for r in g.itertuples():
            al = bool(r.arab_led)
            lead = r.lead_change_list if isinstance(r.lead_change_list, str) and r.p26_change >= 0.15 else ""
            vals = [None] * 5 if al else [rnd(r.change_govt__area_ve1k, 2), rnd(r.change_govt__gotv_ve1k, 2),
                                          rnd(r.change_govt__pers_ve1k, 2), rnd(r.block_nb__area_ve1k, 2),
                                          rnd(r.change_seats__area_ve1k, 2)]
            rows.append([r.kalpi, int(r.eligible), rnd(r.turnout, 3), rnd(r.turnout_resident, 3),
                         rnd(r.p26_change, 3), rnd(r.p26_nb, 3), rnd(r.p26_arab, 3),
                         "" if al else lead] + vals + [1 if al else 0])
        K[int(lid)] = rows

    # ---- segments
    S = []
    for r in seg.itertuples():
        S.append({k: (rnd(v, 4) if isinstance(v, float) else v)
                  for k, v in r._asdict().items() if k != "Index"})

    # ---- marginal values
    MV = []
    camp = {"Yashar": "ch", "Bennett 2026 + Yesh Atid": "ch", "The Democrats": "ch",
            "Yisrael Beytenu": "ch", "Likud": "nb", "Shas": "nb",
            "United Torah Judaism": "nb", "Otzma Yehudit": "nb",
            "Religious Zionist Party": "nb", "Amcha Yisrael": "nb",
            "Noam": "nb", "The Haredi Public": "nb", "Ra'am": "ar",
            "Balad + Hadash-Ta'al": "ar", "Blue and White": "un",
            "Reservists – Economic Party": "un", "Israel First": "ot"}
    sh = {"Bennett 2026 + Yesh Atid": "Together", "The Democrats": "Democrats",
          "United Torah Judaism": "UTJ", "Otzma Yehudit": "Otzma",
          "Religious Zionist Party": "RZP-Zehut", "Balad + Hadash-Ta'al": "Joint List",
          "Blue and White": "Blue & White", "Reservists – Economic Party": "Reservists",
          "Amcha Yisrael": "Amcha", "The Haredi Public": "Haredi Public"}
    for r in mv.itertuples():
        MV.append({"list": sh.get(r.list, r.list), "camp": camp.get(r.list, "ot"),
                   "share": rnd(r.share_mean, 4), "p_pass": r.p_pass,
                   **{o: rnd(getattr(r, o) * (1 if o == "change_seats" else 100), 4)
                      for o in OBJ}})

    # ---- national summary
    def total(o, part="potential"):
        return float(loc[f"{o}__{part}"].sum())
    conc = {}
    for o in PLANNER_OBJ:
        top = loc[target].sort_values(f"{o}__potential", ascending=False)[f"{o}__potential"]
        conc[o] = {n: rnd(top.head(n).sum() / top.clip(lower=0).sum(), 3) for n in (10, 25, 50)}
    summary = {
        "asof": asof,
        "built": date.today().isoformat(),
        "days_to_election": (ELECTION_DAY - date.today()).days,
        "dates": KEY_DATES,
        "n_localities": int(len(loc)), "n_kalpiot": int(len(kal)),
        "eligible_2022": int(loc["eligible"].sum()),
        "persuadable_voters": int(loc["persuadable_voters"].sum()),
        "rescue_voters": int(loc["rescue_voters"].sum()),
        "rescue_bw": int((loc["rescue_voters"] * loc["rescue_bw_share"]
                          / loc["rescue_share"].replace(0, np.nan)).fillna(0).sum()),
        "change_abstained_est": int(loc["change_abstained_est"].sum()),
        "change_supporters": int(loc["change_supporters"].sum()),
        "voters_2026": int(loc["voters_2026_est"].sum()),
        "potential": {o: {p: rnd(total(o, p), 0) for p in
                          ("potential", "area_pot", "list_pot", "gotv_pot", "pers_pot",
                           "resc_pot", "area_contacts", "list_contacts")} for o in PLANNER_OBJ},
        "mv_ref": val["mv_ref_per_vote"],
        "concentration": conc,
        "tiers": {o: loc[f"{o}__tier"].value_counts().to_dict() for o in PLANNER_OBJ},
        "arab_share": {o: rnd(seg.loc[seg["segment"].str.startswith("arab"), f"{o}__potential"].clip(lower=0).sum()
                              / seg[f"{o}__potential"].clip(lower=0).sum(), 3) for o in PLANNER_OBJ},
        "arab_led_stations": int(kal["arab_led"].sum()),
        "flags": {"displaced": int((loc["displaced"] != "").sum()),
                  "displaced_gaza": int((loc["displaced"] == "Gaza border").sum()),
                  "displaced_lebanon": int((loc["displaced"] == "Lebanon border").sum()),
                  "excluded": int((loc["field_excluded"] != "").sum()),
                  "low_confidence": int((loc["low_confidence"] != "").sum())},
        "list_identified": tp.LIST_IDENTIFIED, "min_area": tp.MIN_AREA,
        "forecast": {
            "p_nb_61": blocs["p_nb_61"], "p_change_61": blocs["p_anti_61"],
            "p_change_raam_61": blocs["p_anti_raam_61"],
            "p_neither": blocs["p_neither"],
            "baseline": mmeta["baseline"],
            "seats": [{"list": r.list, "seats": int(r.central_seats),
                       "interval": r.interval_90, "p_pass": r.p_pass}
                      for r in fc.itertuples()],
            "gov": [{"outcome": r.outcome, "p": r.probability} for r in gov.itertuples()],
            "pm": [{"pm": r.pm, "p": r.probability} for r in pm.itertuples()],
        },
        "national": nat.to_dict(orient="records"),
        "reservists_polls": reservists_polls(),
        "valid_votes_2026": 4_823_026,
        "votes_per_seat": round(4_823_026 * 0.95 / 120),
    }
    sens_p = T / "sensitivity_ranks.csv"
    sens_summary = {}
    if sens_p.exists():
        sr = pd.read_csv(sens_p).set_index("locality")
        # re-rank among targetable localities, as the site's own ranks are
        sr = sr.loc[sr.index.isin(loc.loc[target, "locality"])].rank(method="first")
        for o in ("change_govt", "block_nb"):
            cols = [c for c in sr.columns if c.startswith(o + "__")]
            mn = sr[cols].min(axis=1).reindex(loc["locality"])
            mx = sr[cols].max(axis=1).reindex(loc["locality"])
            L[f"{o}.rmin"] = [None if pd.isna(x) or a else int(x) for x, a in zip(mn, arab)]
            L[f"{o}.rmax"] = [None if pd.isna(x) or a else int(x) for x, a in zip(mx, arab)]
        sens_summary = json.loads((T / "sensitivity_summary.json").read_text())

    planner = tp.tranches(tp.load_units(), loc["locality"])
    arab_ix = set(np.flatnonzero(arab.values))
    planner = {o: {p: [r for r in rows if r[0] not in arab_ix] for p, rows in d.items()}
               for o, d in planner.items()}
    levers = json.loads((T / "levers.json").read_text()) if (T / "levers.json").exists() else {}
    payload = {"summary": summary, "objectives": {o: OBJ_LABEL[o] for o in PLANNER_OBJ},
               "levers": levers,
               "tiers": TIER_NAMES,
               "loc": L, "hist": H, "kalpi": K, "segments": S, "mv": MV,
               "lists": short, "validation": val,
               "planner": planner, "geo": geo_payload(),
               "sensitivity": sens_summary,
               "content": {k: content.get(k) for k in ("segments", "playbook", "sources", "strategy",
                                                        "messaging", "coalition", "victory")}}
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    (SITE_OUT / "site_data.json").write_text(js)
    html = TEMPLATE.read_text()
    app = (ROOT / "site" / "targeting_app.js").read_text()
    html = html.replace("/*__APP__*/", app)
    html = html.replace("/*__DATA__*/null", js.replace("</", "<\\/"))
    (SITE_OUT / "index.html").write_text(html)
    (SITE_OUT / "preview.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '</head><body>' + html + '</body></html>')
    print(f"wrote {SITE_OUT / 'index.html'} ({len(html) / 1e6:.2f} MB)")

    # ---- published data files
    loc["tier_change_govt"] = loc["change_govt__tier"]
    loc["tier_block_nb"] = loc["block_nb__tier"]
    cols = ["locality", "he", "en", "district_en", "council_en", "segment_label",
            "eligible", "eligible_2026_est", "turnout_2022", "turnout_resident",
            "roll_abroad", "s22_C", "s22_R", "s22_A", "p26_change", "p26_nb", "p26_arab",
            "p26_unaligned", "lead_change_list", "second_change_list",
            "persuadable_voters", "rescue_voters", "change_abstained_est",
            "openness", "displaced", "field_excluded", "low_confidence",
            "tier_change_govt", "tier_block_nb"] + \
        [f"{o}__{p}" for o in PLANNER_OBJ
         for p in ("potential", "area_pot", "list_pot", "gotv_pot", "pers_pot", "resc_pot",
                   "area_contacts", "list_contacts", "eff1k", "per100h", "rank")]
    fmt_csv(loc[cols]).to_csv(SITE_OUT / "localities.csv", index=False)
    # station file: targetable stations only (no Arab localities, no stations
    # where Arab lists lead, no access-excluded villages)
    kt = kal.merge(loc.loc[target, ["locality", "he", "en"]], on="locality")
    kt = kt[~kt["arab_led"].astype(bool)].copy()
    kt.loc[kt["p26_change"] < 0.15, "lead_change_list"] = None
    kcols = ["locality", "he", "en", "kalpi", "eligible", "turnout", "turnout_resident",
             "p26_change", "p26_nb", "p26_arab", "lead_change_list",
             "change_govt__area_ve1k", "change_govt__gotv_ve1k", "change_govt__pers_ve1k",
             "block_nb__area_ve1k", "change_seats__area_ve1k"]
    fmt_csv(kt[kcols]).to_csv(SITE_OUT / "kalpi_targets.csv", index=False)
    print(f"payload {len(js) / 1e6:.2f} MB; localities {len(loc)}; stations {len(kal)}; "
          f"station file rows {len(kt)}")


if __name__ == "__main__":
    main()
