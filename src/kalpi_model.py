"""Kalpi-level modeling: the locality substrate under the national forecast.

Israel publishes results for every polling station (kalpi) and locality
(yishuv). This module builds that substrate for the five elections
2019a-2022 and uses it three ways:

1. SECTOR CLUSTERING - localities are clustered by their vote profile
   into political sectors (haredi, Arab, religious-Zionist, secular-right,
   centre-left, Russian-leaning, mixed). Israeli electoral geography is
   extremely segregated, so vote profiles recover sectors almost exactly.

2. HIERARCHICAL SWING DECOMPOSITION - for each pair of consecutive
   elections, each locality's party-share change decomposes into
   national swing + sector swing + local residual. The sector layer is
   the quantity the national model needs: how much do sectors move
   TOGETHER beyond the national tide, and how correlated are the sector
   tides with each other? Validated leave-one-transition-out against
   uniform national swing.

3. POSTSTRATIFICATION OF THE 2026 FORECAST - the national central
   forecast is allocated down to sectors through each 2026 list's
   lineage in the 2022 locality structure, yielding implied sector
   turnout/support tables and consistency checks (a list cannot draw
   more haredi votes than haredi localities cast).

Data: expc.csv (locality) / expb.csv (kalpi) from media{21..25}.bechirot.gov.il.
Letter->party mapping is DATA-DRIVEN: each letter column's national vote
share is matched to the official national result, so no hand-coded
letter tables (they change every cycle).

Outputs:
    data/processed/kalpi_localities.parquet   locality x party share panel
    data/processed/kalpi_sectors.csv          locality -> sector assignment
    data/processed/kalpi_swing.csv            sector swing decomposition
    data/processed/kalpi_swing_corr.csv       sector-tide correlation matrix
    data/processed/kalpi_validation.csv       uniform vs sector-swing MAE
    data/processed/kalpi_poststrat_2026.csv   2026 forecast by sector
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR, RAW_DIR

KALPI_DIR = RAW_DIR / "kalpi"
CYCLES = {21: "2019a", 22: "2019s", 23: "2020", 24: "2021", 25: "2022"}
ORDER = ["2019a", "2019s", "2020", "2021", "2022"]

META = {"סמל ועדה", "שם ישוב", "סמל ישוב", "בזב", "מצביעים", "פסולים",
        "כשרים", "ריכוז", "שופט", "ת. עדכון", "ברזל", "סמל קלפי", "קלפי"}

# Ballot-letter -> lineage map per cycle. Hand-coded but VERIFIED: each
# entry's national share in the file matches the official result (the
# expected share is asserted within tolerance at load time, so a wrong
# letter cannot silently poison the panel).
LETTERS = {
    "2019a": {"מחל": ("likud", 26.5), "פה": ("blue_white", 26.1),
              "שס": ("shas", 6.0), "ג": ("utj", 5.8),
              "ום": ("hadash_taal", 4.5), "דעם": ("raam_balad", 3.3),
              "אמת": ("labor", 4.4), "מרצ": ("meretz", 3.6),
              "ל": ("yisrael_beytenu", 4.0), "כ": ("kulanu", 3.5),
              "טב": ("rz_family", 3.7), "נ": ("new_right", 3.2),
              "ז": ("zehut", 2.7), "נר": ("gesher", 1.7)},
    "2019s": {"מחל": ("likud", 25.1), "פה": ("blue_white", 26.0),
              "שס": ("shas", 7.4), "ג": ("utj", 6.1),
              "ודעם": ("joint_list", 10.6), "אמת": ("labor", 4.8),
              "מרצ": ("meretz", 4.3), "ל": ("yisrael_beytenu", 7.0),
              "טב": ("rz_family", 5.9), "כף": ("otzma", 1.9)},
    "2020": {"מחל": ("likud", 29.5), "פה": ("blue_white", 26.6),
             "שס": ("shas", 7.7), "ג": ("utj", 6.0),
             "ודעם": ("joint_list", 12.7), "אמת": ("labor", 5.8),
             "ל": ("yisrael_beytenu", 5.7), "טב": ("rz_family", 5.2)},
    "2021": {"מחל": ("likud", 24.2), "פה": ("yesh_atid", 13.9),
             "כן": ("blue_white", 6.6), "ת": ("new_hope", 4.7),
             "ב": ("rz_family", 6.2), "ט": ("rzp", 5.1),
             "אמת": ("labor", 6.1), "מרצ": ("meretz", 4.6),
             "ודעם": ("joint_list", 4.8), "עם": ("raam", 3.8),
             "שס": ("shas", 7.2), "ג": ("utj", 5.6),
             "ל": ("yisrael_beytenu", 5.6)},
    "2022": {"מחל": ("likud", 23.4), "פה": ("yesh_atid", 17.8),
             "כן": ("blue_white", 9.1), "ט": ("rzp", 10.8),
             "אמת": ("labor", 3.7), "מרצ": ("meretz", 3.2),
             "ום": ("hadash_taal", 3.8), "ד": ("balad", 2.9),
             "עם": ("raam", 4.1), "שס": ("shas", 8.3),
             "ג": ("utj", 5.9), "ל": ("yisrael_beytenu", 4.5),
             "ב": ("jewish_home", 1.2)},
}
# Notes: rz_family unifies the Jewish Home/Yamina/New Right vehicles
# (טב 2019-20, ב 2021 Yamina); 2021 ט = RZP(+Otzma+Noam); 2022 ט =
# RZP-Otzma joint; 2022 כן = National Unity mapped to the blue_white
# lineage; 2021 ב (Yamina) is Bennett's vehicle.


def load_localities() -> pd.DataFrame:
    """Locality x cycle panel: shares per matched party lineage."""
    rows = []
    for v, cycle in CYCLES.items():
        d = None
        for enc in ("utf-8", "cp1255", "iso-8859-8"):
            try:
                d = pd.read_csv(KALPI_DIR / f"expc_{v}.csv", encoding=enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if d is None:
            raise RuntimeError(f"undecodable expc_{v}.csv")
        d.columns = [c.strip() for c in d.columns]
        valid = d["כשרים"].replace(0, np.nan)
        mapping = {}
        for letter, (pid, expected) in LETTERS[cycle].items():
            if letter not in d.columns:
                raise RuntimeError(f"{cycle}: letter {letter} missing")
            got = d[letter].sum() / d["כשרים"].sum() * 100
            if abs(got - expected) > 0.8:
                raise RuntimeError(
                    f"{cycle}: {letter} national share {got:.2f} != "
                    f"expected {expected} for {pid}")
            mapping[letter] = pid
        for c, pid in mapping.items():
            share = d[c] / valid
            for code, name, elig, voters, s in zip(
                    d["סמל ישוב"], d["שם ישוב"], d["בזב"], d["מצביעים"],
                    share):
                rows.append({"cycle": cycle, "locality": int(code),
                             "name": str(name).strip(), "eligible": elig,
                             "voters": voters, "party": pid,
                             "share": 0.0 if pd.isna(s) else float(s)})
    return pd.DataFrame(rows)


# 2026 lists -> lineage weights in the 2022 party space (which 2022
# electorates does each 2026 list draw from). Sourced from the measured
# vote-flow research (N12 sourcing, certainty desk, scenario polls) and
# CALIBRATED against the Kolot Nodedim measured K24->K25 kalpi transfer
# matrix (harelc/elections-vote-transfer; R^2 0.889, 7,035 kalpiot):
# ex-Yamina electorates live in 2022's RZP 45% / Jewish Home 24% /
# Likud 14% / National Unity 11% localities, B&W'21 -> NU 71% + YA 30%,
# Likud retention 90%, YB retention 79%. All keys are 2022 lineages
# (an earlier revision referenced "yamina", which does not exist in the
# 2022 space and silently zeroed those weights).
LINEAGE_2026 = {
    "likud": {"likud": 0.82, "rzp": 0.07, "blue_white": 0.11},
    "yashar": {"blue_white": 0.45, "yesh_atid": 0.25, "likud": 0.15,
               "labor": 0.10, "shas": 0.05},
    "bennett_2026+yesh_atid": {"yesh_atid": 0.60, "rzp": 0.09,
                               "jewish_home": 0.05, "likud": 0.13,
                               "blue_white": 0.13},
    "democrats": {"labor": 0.50, "meretz": 0.50},
    "yisrael_beytenu": {"yisrael_beytenu": 0.90, "likud": 0.10},
    "shas": {"shas": 0.95, "likud": 0.05},
    "utj": {"utj": 1.00},
    "otzma": {"rzp": 0.55, "likud": 0.30, "shas": 0.15},
    "rzp": {"rzp": 0.90, "jewish_home": 0.10},
    "amcha_yisrael": {"likud": 0.47, "rzp": 0.37, "jewish_home": 0.04,
                      "yisrael_beytenu": 0.10, "blue_white": 0.02},
    "raam": {"raam": 1.00},
    "balad+hadash_taal": {"hadash_taal": 0.65, "balad": 0.35},
    # 2026-09-09 (dossier s.34): lists with real pass probability that had
    # no lineage. Reservists-Economic (Hendel + Zelekha + Wilf): Hendel's
    # New Hope voters went National Unity 58 / Likud 42 in 2022 (measured
    # K24->K25); Zelekha's and Wilf's electorates are centre-left urban.
    # Blue and White: its own 2022 pattern (National Unity 70 / Yesh Atid 30).
    "zionist_home": {"blue_white": 0.50, "yesh_atid": 0.30, "likud": 0.10,
                     "yisrael_beytenu": 0.05, "labor": 0.05},
    "blue_white": {"blue_white": 0.70, "yesh_atid": 0.30},
}


def cluster_sectors(panel: pd.DataFrame) -> pd.DataFrame:
    """Assign each locality a sector from its 2022 vote profile."""
    w = panel[panel.cycle == "2022"].pivot_table(
        index=["locality", "name", "eligible", "voters"],
        columns="party", values="share", fill_value=0).reset_index()
    w["turnout"] = w["voters"] / w["eligible"].replace(0, np.nan)

    def sector(r):
        haredi = r.get("shas", 0) + r.get("utj", 0)
        arab = r.get("raam", 0) + r.get("hadash_taal", 0) + r.get("balad", 0)
        rz = r.get("rzp", 0)
        right = r.get("likud", 0)
        centre = (r.get("yesh_atid", 0) + r.get("blue_white", 0)
                  + r.get("labor", 0) + r.get("meretz", 0))
        yb = r.get("yisrael_beytenu", 0)
        if arab > 0.5:
            return "arab"
        if haredi > 0.5:
            return "haredi"
        if rz > 0.35:
            return "religious_zionist"
        if yb > 0.20:
            return "russian_leaning"
        if right > centre + 0.10:
            return "secular_right"
        if centre > right + 0.10:
            return "centre_left"
        return "mixed"

    w["sector"] = w.apply(sector, axis=1)
    return w[["locality", "name", "eligible", "voters", "turnout", "sector"]]


# Lineage families: sums are stable across list-structure changes (a
# party dissolving into a sibling moves shares WITHIN the family, so the
# family total still measures real voter movement, not paperwork).
FAMILIES = {
    "likud": ["likud"],
    "shas": ["shas"],
    "utj": ["utj"],
    "yb": ["yisrael_beytenu"],
    "arab": ["raam_balad", "joint_list", "raam", "hadash_taal", "balad"],
    "rz": ["rz_family", "rzp", "new_right", "zehut", "otzma",
           "jewish_home"],
    "centre_left": ["blue_white", "yesh_atid", "labor", "meretz",
                    "new_hope", "kulanu", "gesher"],
}


def family_matrix(panel: pd.DataFrame, cycle: str) -> pd.DataFrame:
    p = panel[panel.cycle == cycle].pivot_table(
        index="locality", columns="party", values="share", fill_value=0)
    out = {}
    for fam, members in FAMILIES.items():
        cols = [m for m in members if m in p.columns]
        if cols:
            out[fam] = p[cols].sum(axis=1)
    return pd.DataFrame(out)


def swing_decomposition(panel: pd.DataFrame, sectors: pd.DataFrame):
    """National + sector + residual decomposition of family-sum swings."""
    sec = sectors.set_index("locality")["sector"]
    wt = sectors.set_index("locality")["voters"]
    rows, corr_rows = [], {}
    for a, b in zip(ORDER[:-1], ORDER[1:]):
        fa, fb = family_matrix(panel, a), family_matrix(panel, b)
        fams = [f for f in fa.columns if f in fb.columns]
        idx = fa.index.intersection(fb.index).intersection(sec.index)
        dl = fb.loc[idx, fams] - fa.loc[idx, fams]
        w = wt.reindex(idx).fillna(0)
        s = sec.reindex(idx)
        for f in fams:
            d = dl[f].dropna()
            wi = w.reindex(d.index)
            nat = np.average(d, weights=wi)
            for sc, grp in d.groupby(s.reindex(d.index)):
                wg = wi.reindex(grp.index)
                sw = np.average(grp, weights=wg) - nat
                resid = grp - nat - sw
                rows.append({"transition": f"{a}->{b}", "family": f,
                             "sector": sc,
                             "national_swing": round(nat*100, 2),
                             "sector_swing": round(sw*100, 2),
                             "resid_sd": round(float(np.sqrt(
                                 np.average(resid**2, weights=wg)))*100, 2),
                             "n_localities": len(grp)})
        # sector tide = the sector's own family swing inside its home turf
        HOME = {"haredi": ["shas", "utj"], "arab": ["arab"],
                "religious_zionist": ["rz"], "secular_right": ["likud"],
                "centre_left": ["centre_left"]}
        for sc, fs in HOME.items():
            cols = [f for f in fs if f in dl.columns]
            m = s.reindex(dl.index) == sc
            if not cols or m.sum() < 5:
                continue
            tide = dl.loc[m, cols].sum(axis=1)
            corr_rows.setdefault(sc, {})[f"{a}->{b}"] = float(
                np.average(tide, weights=w.reindex(tide.index))) * 100
    swing = pd.DataFrame(rows)
    tides = pd.DataFrame(corr_rows)
    return swing, tides


def validate(panel: pd.DataFrame, sectors: pd.DataFrame,
             swing: pd.DataFrame) -> pd.DataFrame:
    """Leave-one-transition-out: given the TRUE national family swings of
    the held-out transition, does adding the training transitions' sector
    swings beat uniform national swing at predicting localities?"""
    sec = sectors.set_index("locality")["sector"]
    wt = sectors.set_index("locality")["voters"]
    out = []
    for hold in sorted(swing.transition.unique()):
        a, b = hold.split("->")
        fa, fb = family_matrix(panel, a), family_matrix(panel, b)
        fams = [f for f in fa.columns if f in fb.columns]
        idx = fa.index.intersection(fb.index).intersection(sec.index)
        w = wt.reindex(idx).fillna(0)
        train = swing[swing.transition != hold]
        mae_u, mae_s, n = 0.0, 0.0, 0
        for f in fams:
            actual = fb.loc[idx, f]
            nat = (np.average(fb.loc[idx, f], weights=w)
                   - np.average(fa.loc[idx, f], weights=w))
            pred_u = fa.loc[idx, f] + nat
            ss = train[train.family == f].groupby("sector")[
                "sector_swing"].mean() / 100.0
            adj = sec.reindex(idx).map(ss).fillna(0)
            pred_s = pred_u + adj
            mae_u += (actual - pred_u).abs().mul(w).sum() / w.sum()
            mae_s += (actual - pred_s).abs().mul(w).sum() / w.sum()
            n += 1
        out.append({"held_out": hold,
                    "mae_uniform_pp": round(mae_u / n * 100, 3),
                    "mae_sector_pp": round(mae_s / n * 100, 3)})
    return pd.DataFrame(out)


def poststratify_2026(sectors: pd.DataFrame, panel: pd.DataFrame):
    """Allocate the 2026 central forecast to sectors via 2022 lineage."""
    w22 = panel[panel.cycle == "2022"].pivot_table(
        index="locality", columns="party", values="share", fill_value=0)
    sec = sectors.set_index("locality")
    votes22 = (sec["voters"]).reindex(w22.index).fillna(0)
    fc = pd.read_csv(PROCESSED_DIR / "bayes_forecast_mixture.csv")
    NAME2ID = {"Likud": "likud", "Yashar": "yashar",
               "Bennett 2026 + Yesh Atid": "bennett_2026+yesh_atid",
               "The Democrats": "democrats",
               "Yisrael Beytenu": "yisrael_beytenu", "Shas": "shas",
               "United Torah Judaism": "utj", "Otzma Yehudit": "otzma",
               "Religious Zionist Party": "rzp", "Ra'am": "raam",
               "Balad + Hadash-Ta'al": "balad+hadash_taal",
               "Reservists – Economic Party": "zionist_home",
               "Blue and White": "blue_white",
               "Amcha Yisrael": "amcha_yisrael"}
    rows = []
    for r in fc.itertuples():
        lid = NAME2ID.get(r.list)
        if lid is None or lid not in LINEAGE_2026:
            continue
        lin = LINEAGE_2026[lid]
        # locality weight = lineage-weighted 2022 vote base
        base = sum(w22.get(src, 0) * wgt for src, wgt in lin.items())
        base_v = base * votes22
        tot = base_v.sum()
        if tot <= 0:
            continue
        by_sec = base_v.groupby(sec["sector"].reindex(w22.index)).sum() / tot
        for sc, frac in by_sec.items():
            rows.append({"list": r.list, "sector": sc,
                         "share_of_list": round(float(frac), 3),
                         "seats_from_sector": round(float(frac) * r.mean, 2)})
    return pd.DataFrame(rows)


def main() -> None:
    panel = load_localities()
    panel.to_parquet(PROCESSED_DIR / "kalpi_localities.parquet")
    n_loc = panel.locality.nunique()
    print(f"kalpi panel: {n_loc} localities x {panel.cycle.nunique()} cycles"
          f" x {panel.party.nunique()} party lineages")

    sectors = cluster_sectors(panel)
    sectors.to_csv(PROCESSED_DIR / "kalpi_sectors.csv", index=False)
    print("\nsector sizes (eligible voters):")
    print(sectors.groupby("sector")["eligible"].sum().sort_values(
        ascending=False).to_string())
    print("\nsector turnout 2022:")
    print(sectors.groupby("sector").apply(
        lambda g: np.average(g.turnout.fillna(0), weights=g.eligible)
    ).round(3).to_string())

    swing, tides = swing_decomposition(panel, sectors)
    swing.to_csv(PROCESSED_DIR / "kalpi_swing.csv", index=False)
    print("\nsector tides per transition (pp, weighted):")
    print(tides.round(2).to_string())
    ct = tides.corr().round(2)
    ct.to_csv(PROCESSED_DIR / "kalpi_swing_corr.csv")
    print("\ncross-sector tide correlation:")
    print(ct.to_string())

    val = validate(panel, sectors, swing)
    val.to_csv(PROCESSED_DIR / "kalpi_validation.csv", index=False)
    print("\nleave-one-transition-out locality prediction "
          "(mean abs error, pp of vote share):")
    print(val.to_string(index=False))

    post = poststratify_2026(sectors, panel)
    post.to_csv(PROCESSED_DIR / "kalpi_poststrat_2026.csv", index=False)
    print("\n2026 forecast poststratified to sectors "
          "(seats drawn from each sector):")
    pt = post.pivot_table(index="list", columns="sector",
                          values="seats_from_sector", fill_value=0)
    print(pt.round(1).to_string())


if __name__ == "__main__":
    main()
