"""Targeting layer, part 1: the locality substrate.

Builds a harmonised locality x election panel for the seven Knesset
elections 2013-2022 (K19-K25) from the Central Elections Committee's
official per-locality results, and a locality metadata table joining the
Central Bureau of Statistics locality file (coordinates, district,
regional council, settlement type, population), the 2022 Census
(religion, religiosity, age, education, origin, income) and the CBS
socio-economic cluster.

Every ballot letter with a meaningful national share is mapped to a party
lineage, a party FAMILY (stable across mergers - used for volatility) and
a contemporaneous BLOC (how the list was positioned in that election -
used for bloc swing). Expected national shares are asserted at load, so a
mis-mapped letter fails loudly instead of poisoning the panel.

Sources (all official, downloaded to data/raw/):
    CEC results by locality, K19-K25 - data.gov.il dataset "votes-knesset"
        (https://data.gov.il/dataset/votes-knesset); K21-K25 originally
        from media21-25.bechirot.gov.il
    CBS locality file 2023 (bycode2023.xlsx) - data.gov.il dataset
        "localities-in-israel"
    CBS Census 2022, selected data by locality and statistical area -
        data.gov.il dataset "2022" (census)
    CBS socio-economic cluster 2019 of localities in regional councils -
        data.gov.il dataset "social_economic_cluster"

Outputs:
    data/processed/targeting/panel.parquet        long: cycle x locality x party
    data/processed/targeting/locality_cycle.parquet  wide: cycle x locality
    data/processed/targeting/locality_meta.csv     one row per locality
    data/processed/targeting/national.csv          national totals per cycle
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR, RAW_DIR

KALPI_DIR = RAW_DIR / "kalpi"
CBS_DIR = RAW_DIR / "cbs"
OUT = PROCESSED_DIR / "targeting"

CYCLES = {19: "2013", 20: "2015", 21: "2019a", 22: "2019s", 23: "2020",
          24: "2021", 25: "2022"}
ORDER = list(CYCLES.values())
ELECTION_DATE = {"2013": "2013-01-22", "2015": "2015-03-17",
                 "2019a": "2019-04-09", "2019s": "2019-09-17",
                 "2020": "2020-03-02", "2021": "2021-03-23",
                 "2022": "2022-11-01"}

META = {"סמל ועדה", "שם ישוב", "סמל ישוב", "בזב", "מצביעים", "פסולים",
        "כשרים", "ריכוז", "שופט", "ת. עדכון", "ברזל", "סמל קלפי", "קלפי",
        "מספר קלפי"}

# letter: (lineage id, family, bloc, expected % of REGULAR-station valid
# votes - double-envelope votes sit in a separate pseudo-locality (code 0 /
# 9999) from 2015 on and are absent from the 2013 file, so these differ
# slightly from the official national result).
# Families: likud, haredi, rz (religious-Zionist / radical right), centre,
# left, yb, arab. Blocs are CONTEMPORANEOUS: nb = the Netanyahu / right-
# religious camp, ch = the anti-Netanyahu (centre-left) camp, ar = Arab
# lists, un = lists whose camp was genuinely open at that election.
LETTERS = {
    "2013": {"מחל": ("likud_beytenu", "likud", "nb", 23.27),
             "פה": ("yesh_atid", "centre", "ch", 14.22),
             "אמת": ("labor", "left", "ch", 11.42),
             "שס": ("shas", "haredi", "nb", 8.84),
             "טב": ("jewish_home", "rz", "nb", 8.77),
             "ג": ("utj", "haredi", "nb", 5.33),
             "צפ": ("hatnuah", "centre", "ch", 5.03),
             "מרץ": ("meretz", "left", "ch", 4.59),
             "עם": ("raam_taal", "arab", "ar", 3.80),
             "ו": ("hadash", "arab", "ar", 3.12),
             "ד": ("balad", "arab", "ar", 2.67),
             "כן": ("kadima", "centre", "ch", 2.07),
             "נץ": ("otzma_leyisrael", "rz", "nb", 1.72),
             "ץ": ("am_shalem", "haredi", "un", 1.20)},
    "2015": {"מחל": ("likud", "likud", "nb", 23.27),
             "אמת": ("zionist_union", "left", "ch", 18.73),
             "ודעם": ("joint_list", "arab", "ar", 11.04),
             "פה": ("yesh_atid", "centre", "ch", 8.79),
             "כ": ("kulanu", "centre", "un", 7.41),
             "טב": ("jewish_home", "rz", "nb", 6.41),
             "שס": ("shas", "haredi", "nb", 5.81),
             "ל": ("yisrael_beytenu", "yb", "nb", 5.17),
             "ג": ("utj", "haredi", "nb", 5.12),
             "מרצ": ("meretz", "left", "ch", 3.89),
             "קץ": ("yachad", "haredi", "nb", 2.98)},
    "2019a": {"מחל": ("likud", "likud", "nb", 26.29),
              "פה": ("blue_white", "centre", "ch", 25.97),
              "שס": ("shas", "haredi", "nb", 6.10),
              "ג": ("utj", "haredi", "nb", 5.92),
              "ום": ("hadash_taal", "arab", "ar", 4.65),
              "אמת": ("labor", "left", "ch", 4.42),
              "ל": ("yisrael_beytenu", "yb", "un", 4.14),
              "טב": ("urwp", "rz", "nb", 3.65),
              "מרצ": ("meretz", "left", "ch", 3.64),
              "כ": ("kulanu", "centre", "nb", 3.56),
              "דעם": ("raam_balad", "arab", "ar", 3.46),
              "נ": ("new_right", "rz", "nb", 3.14),
              "ז": ("zehut", "rz", "nb", 2.51),
              "נר": ("gesher", "centre", "un", 1.75)},
    "2019s": {"פה": ("blue_white", "centre", "ch", 25.66),
              "מחל": ("likud", "likud", "nb", 24.92),
              "ודעם": ("joint_list", "arab", "ar", 11.02),
              "שס": ("shas", "haredi", "nb", 7.52),
              "ל": ("yisrael_beytenu", "yb", "ch", 7.12),
              "ג": ("utj", "haredi", "nb", 6.19),
              "טב": ("yamina", "rz", "nb", 5.67),
              "אמת": ("labor_gesher", "left", "ch", 4.80),
              "מרצ": ("dem_union", "left", "ch", 4.30),
              "כף": ("otzma", "rz", "nb", 1.85)},
    "2020": {"מחל": ("likud", "likud", "nb", 29.22),
             "פה": ("blue_white", "centre", "ch", 26.34),
             "ודעם": ("joint_list", "arab", "ar", 13.22),
             "שס": ("shas", "haredi", "nb", 7.73),
             "ג": ("utj", "haredi", "nb", 6.12),
             "אמת": ("labor_gesher_meretz", "left", "ch", 5.71),
             "ל": ("yisrael_beytenu", "yb", "ch", 5.88),
             "טב": ("yamina", "rz", "nb", 5.01),
             "נץ": ("otzma", "rz", "nb", 0.42)},
    "2021": {"מחל": ("likud", "likud", "nb", 24.17),
             "פה": ("yesh_atid", "centre", "ch", 13.94),
             "שס": ("shas", "haredi", "nb", 7.32),
             "כן": ("blue_white", "centre", "ch", 6.66),
             "ב": ("yamina", "rz", "un", 5.87),
             "אמת": ("labor", "left", "ch", 5.88),
             "ג": ("utj", "haredi", "nb", 5.88),
             "ל": ("yisrael_beytenu", "yb", "ch", 5.54),
             "ט": ("rzp", "rz", "nb", 4.98),
             "ודעם": ("joint_list", "arab", "ar", 5.05),
             "ת": ("new_hope", "centre", "ch", 4.69),
             "מרצ": ("meretz", "left", "ch", 4.56),
             "עם": ("raam", "arab", "ar", 4.02)},
    "2022": {"מחל": ("likud", "likud", "nb", 23.40),
             "פה": ("yesh_atid", "centre", "ch", 17.88),
             "ט": ("rzp", "rz", "nb", 10.35),
             "כן": ("blue_white", "centre", "ch", 8.91),
             "שס": ("shas", "haredi", "nb", 8.40),
             "ג": ("utj", "haredi", "nb", 6.11),
             "ל": ("yisrael_beytenu", "yb", "ch", 4.36),
             "עם": ("raam", "arab", "ar", 4.32),
             "ום": ("hadash_taal", "arab", "ar", 3.97),
             "אמת": ("labor", "left", "ch", 3.54),
             "מרצ": ("meretz", "left", "ch", 3.17),
             "ד": ("balad", "arab", "ar", 3.05),
             "ב": ("jewish_home", "rz", "nb", 1.16)},
}
# Bloc notes. 2015: YB sat in the right camp (joined Netanyahu 2016);
# Kulanu ran as a centrist list and joined Netanyahu - "un". 2019a: Kulanu
# recommended Netanyahu (nb); YB recommended him but then refused to
# join, forcing 2019s - its April voters are coded "un", and from 2019s on
# YB is anti-Netanyahu (ch). 2021: Yamina refused to commit to either camp
# and formed the change government - "un"; New Hope ran explicitly
# anti-Netanyahu (ch). 2022: Shaked's Jewish Home pledged a right-wing
# government (nb); National Unity (Gantz) ran in the change camp (it is
# UNALIGNED in 2026 by owner ruling, which the 2026 projection respects).
# 2013: Likud and Yisrael Beytenu ran as one list (family likud).

# The 2022 lineage space used by the 2026 projection (kalpi_model.LINEAGE_2026)
LINEAGE22 = {"likud", "yesh_atid", "rzp", "blue_white", "shas", "utj",
             "yisrael_beytenu", "raam", "hadash_taal", "labor", "meretz",
             "balad", "jewish_home"}


def read_expc(v: int) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp1255", "iso-8859-8"):
        try:
            d = pd.read_csv(KALPI_DIR / f"expc_{v}.csv", encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise RuntimeError(f"undecodable expc_{v}.csv")
    d.columns = [c.strip() for c in d.columns]
    d = d.rename(columns={"שם ישוב": "name", "סמל ישוב": "locality",
                          "בזב": "eligible", "מצביעים": "voters",
                          "פסולים": "invalid", "כשרים": "valid"})
    d["name"] = d["name"].astype(str).str.strip()
    return d


def build_panel():
    rows, wide, nat = [], [], []
    for v, cycle in CYCLES.items():
        d = read_expc(v)
        letters = LETTERS[cycle]
        env = d[(d["locality"].isin([0, 9999])) | (d["eligible"] == 0)]
        loc = d[~d.index.isin(env.index)].copy()
        valid_tot = loc["valid"].sum()
        for letter, (pid, fam, bloc, expected) in letters.items():
            if letter not in loc.columns:
                raise RuntimeError(f"{cycle}: letter {letter} missing")
            got = loc[letter].sum() / valid_tot * 100
            if abs(got - expected) > 0.35:
                raise RuntimeError(f"{cycle}: {letter} {got:.2f}% != {expected} ({pid})")
        party_cols = [c for c in loc.columns if c not in META
                      and c not in ("name", "locality", "eligible", "voters",
                                    "invalid", "valid")]
        mapped = set(letters)
        loc["other"] = loc[[c for c in party_cols if c not in mapped]].sum(axis=1)
        for letter, (pid, fam, bloc, _) in letters.items():
            part = loc[["locality", letter]].rename(columns={letter: "votes"})
            part["party"], part["family"], part["bloc"] = pid, fam, bloc
            part["cycle"] = cycle
            rows.append(part)
        part = loc[["locality", "other"]].rename(columns={"other": "votes"})
        part["party"], part["family"], part["bloc"] = "other", "other", "ot"
        part["cycle"] = cycle
        rows.append(part)
        w = loc[["locality", "name", "eligible", "voters", "invalid", "valid"]].copy()
        w["cycle"] = cycle
        wide.append(w)
        env_voters = int(env["voters"].sum())
        nat.append({"cycle": cycle, "date": ELECTION_DATE[cycle],
                    "eligible": int(loc["eligible"].sum()),
                    "voters_regular": int(loc["voters"].sum()),
                    "voters_envelopes": env_voters,
                    "valid_regular": int(valid_tot),
                    "turnout_regular": loc["voters"].sum() / loc["eligible"].sum(),
                    "turnout_total": (loc["voters"].sum() + env_voters)
                                     / loc["eligible"].sum()})
    panel = pd.concat(rows, ignore_index=True)
    panel["locality"] = panel["locality"].astype(int)
    lc = pd.concat(wide, ignore_index=True)
    lc["locality"] = lc["locality"].astype(int)
    lc["turnout"] = lc["voters"] / lc["eligible"].replace(0, np.nan)
    bl = panel.pivot_table(index=["cycle", "locality"], columns="bloc",
                           values="votes", aggfunc="sum", fill_value=0)
    bl.columns = [f"v_{c}" for c in bl.columns]
    lc = lc.merge(bl.reset_index(), on=["cycle", "locality"], how="left")
    fa = panel.pivot_table(index=["cycle", "locality"], columns="family",
                           values="votes", aggfunc="sum", fill_value=0)
    fa.columns = [f"f_{c}" for c in fa.columns]
    lc = lc.merge(fa.reset_index(), on=["cycle", "locality"], how="left")
    return panel, lc, pd.DataFrame(nat)


def itm_to_wgs84(code) -> tuple[float, float]:
    """CBS 'coordinates' = 12 digits: ITM easting (6) + northing (6)."""
    from pyproj import CRS, Transformer
    s = f"{int(code):012d}"
    x, y = int(s[:6]), int(s[6:])
    tr = getattr(itm_to_wgs84, "tr", None)
    if tr is None:
        # Israeli Transverse Mercator (EPSG:2039) as an explicit proj string:
        # pyproj's EPSG database is unreachable from this repo's path.
        itm = ("+proj=tmerc +lat_0=31.7343936111111 +lon_0=35.2045169444444 "
               "+k=1.0000067 +x_0=219529.584 +y_0=626907.39 +ellps=GRS80 "
               "+towgs84=-24.0024,-17.1032,-17.8444,-0.33077,-1.85269,"
               "1.66969,5.4248 +units=m +no_defs")
        tr = itm_to_wgs84.tr = Transformer.from_crs(
            CRS.from_proj4(itm),
            CRS.from_proj4("+proj=longlat +datum=WGS84 +no_defs"),
            always_xy=True)
    lon, lat = tr.transform(x, y)
    return lat, lon


SETTLEMENT_TYPE = {
    # CBS "current settlement form" codes (verified against named examples)
    **{c: "jewish_urban" for c in (120, 130, 140, 150, 160, 170, 180, 190)},
    # 191-193: large rural localities counted by size (Beit Yitzhak-Sha'ar
    # Hefer, Shtulim = moshavim; Nordiya = moshav shitufi; Givat Brenner,
    # Ma'agan Michael = kibbutzim)
    191: "moshav", 192: "moshav_shitufi", 193: "kibbutz",
    **{c: "arab_urban" for c in (250, 260, 270, 280, 290)},
    310: "moshav", 320: "moshav_shitufi", 330: "kibbutz",
    340: "institutional", 350: "rural_other", 370: "community",
    440: "arab_rural", 450: "arab_rural", 460: "bedouin_tribe",
    510: "rural_other", 520: "institutional", 530: "aggregate",
}


def build_meta(lc: pd.DataFrame) -> pd.DataFrame:
    b = pd.read_excel(CBS_DIR / "bycode2023.xlsx")
    b = b.rename(columns={
        "שם יישוב": "name_cbs", "סמל יישוב": "locality",
        "שם יישוב באנגלית": "name_en", "שם מחוז": "district",
        "שם נפה": "subdistrict", "אזור טבעי": "natural_region",
        "שם מעמד מונציפאלי": "municipal", "דת יישוב": "religion_cbs",
        "סך הכל אוכלוסייה 2023 - ארעי": "pop2023",
        "ערבים - ארעי": "arabs2023", "שנת ייסוד": "founded",
        "צורת יישוב שוטפת - ארעי": "form", "קואורדינטות": "coord",
        "שיוך מטרופוליני": "metro"})
    b["locality"] = b["locality"].astype(int)
    keep = ["locality", "name_cbs", "name_en", "district", "subdistrict",
            "natural_region", "municipal", "religion_cbs", "pop2023",
            "arabs2023", "founded", "form", "coord", "metro"]
    b = b[keep]
    latlon = b["coord"].apply(lambda c: itm_to_wgs84(c) if pd.notna(c) and c > 0
                              else (np.nan, np.nan))
    b["lat"] = [p[0] for p in latlon]
    b["lon"] = [p[1] for p in latlon]
    b["settlement_type"] = b["form"].map(SETTLEMENT_TYPE).fillna("other")
    b["arab_share_pop"] = (b["arabs2023"].fillna(0)
                           / b["pop2023"].replace(0, np.nan))

    c = pd.read_csv(CBS_DIR / "census2022_selected.csv", low_memory=False)
    c = c[c["StatArea"].isna() & c["LocalityCode"].notna()].copy()
    c["locality"] = c["LocalityCode"].astype(int)
    cen_cols = {"religion": "census_religion", "pop_approx": "census_pop",
                "age_median": "age_median", "age65_pcnt": "age65_pct",
                "age20_64_pcnt": "age20_64_pct",
                "AcadmCert_pcnt": "academic_pct",
                "j_abr_pcnt": "jews_born_abroad_pct",
                "aliya2002_pcnt": "aliya2002_pct",
                "europe_pcnt": "born_europe_pct", "asia_pcnt": "born_asia_pct",
                "africa_pcnt": "born_africa_pct",
                "america_pcnt": "born_america_pct",
                "israel_pcnt": "born_israel_pct",
                "employeesAnnual_medWage": "median_wage",
                "Empl_pcnt": "employed_pct", "Vehicle0_pcnt": "no_car_pct",
                "hh_MidatDatiyut": "religiosity_modal",
                "ChldBorn_avg": "children_avg", "pop_density": "pop_density",
                "WrkOutLoc_pcnt": "work_outside_pct"}
    c = c[["locality"] + list(cen_cols)].rename(columns=cen_cols)
    for col in cen_cols.values():
        if col != "religiosity_modal":
            c[col] = pd.to_numeric(c[col], errors="coerce")
    c["census_religion"] = c["census_religion"].map(
        {1: "jewish", 2: "muslim", 3: "christian", 5: "druze", 6: "other"})
    c["religiosity_modal"] = c["religiosity_modal"].map(
        {"חילוני": "secular", "מסורתי": "traditional",
         "דתי/ דתי מאוד": "religious", "חרדי": "haredi", "אחר": "other"})

    s = pd.read_csv(CBS_DIR / "ses2019.csv", low_memory=False).dropna(
        axis=1, how="all")
    s = s.rename(columns={"LOCALITY SYMBOL": "locality",
                          "ESHKOL 2019": "ses_cluster"})[["locality", "ses_cluster"]]
    s["locality"] = pd.to_numeric(s["locality"], errors="coerce")
    s = s.dropna().astype({"locality": int})

    last = lc[lc["cycle"] == "2022"][["locality", "name"]].rename(
        columns={"name": "name_he"})
    names_any = (lc.sort_values("cycle").groupby("locality")["name"].last()
                 .rename("name_he_any").reset_index())
    meta = names_any.merge(last, on="locality", how="left")
    meta["name_he"] = meta["name_he"].fillna(meta["name_he_any"])
    meta = meta.drop(columns="name_he_any")
    meta = (meta.merge(b, on="locality", how="left")
                .merge(c, on="locality", how="left")
                .merge(s, on="locality", how="left"))
    return meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel, lc, nat = build_panel()
    panel.to_parquet(OUT / "panel.parquet")
    lc.to_parquet(OUT / "locality_cycle.parquet")
    nat.to_csv(OUT / "national.csv", index=False)
    print(nat.to_string(index=False))
    meta = build_meta(lc)
    meta.to_csv(OUT / "locality_meta.csv", index=False)
    n22 = lc[lc.cycle == "2022"]
    print(f"\nlocalities: {lc.locality.nunique()} across cycles; "
          f"{len(n22)} in 2022")
    print(f"meta: {len(meta)} rows; coords for {meta.lat.notna().sum()}; "
          f"census for {meta.census_religion.notna().sum()}; "
          f"SES (regional councils) for {meta.ses_cluster.notna().sum()}")
    miss = meta[meta.lat.isna()].merge(
        n22[["locality", "eligible"]], on="locality", how="left")
    print(f"no coords: {len(miss)} localities, "
          f"{int(miss.eligible.fillna(0).sum())} eligible voters in 2022")
    print(miss.sort_values("eligible", ascending=False).head(15)[
        ["locality", "name_he", "eligible"]].to_string(index=False))


if __name__ == "__main__":
    main()
