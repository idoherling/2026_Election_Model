"""Targeting layer, part 2: where should the change bloc campaign?

The question has no "swing district" answer in Israel: the Knesset is
elected in one national district, so a vote is worth the same wherever it
is cast. Geography matters for a different reason - it is where the
campaign FINDS the voters it needs, and where each hour of field work buys
the most expected outcome. This module scores every locality on that
basis, with three mechanisms and one exchange rate:

  1. PERSUASION - soft supporters of Netanyahu-bloc lists and of the
     unaligned sub-threshold lists who are open to a change-bloc list.
     Universe = projected 2026 list votes x the list's measured/declared
     soft share (1 - CERTAINTY, bayes_model) x a cross-pressure fraction,
     localised by an OPENNESS index that is fitted to predict observed
     cross-camp movement out of sample (2013-2021 -> 2022).
  2. MOBILISATION - non-voters. The partisan composition of the marginal
     voter is the locality's own projected vote tilted by the segment's
     measured differential turnout (an ecological regression of camp vote
     on turnout change across localities, 2019s-2022, validated by
     predicting 2021->2022 out of sample). The per-contact turnout effect
     is constant on the logit scale (largest near 50% turnout), applied to
     roll-adjusted turnout.
  3. WASTED-VOTE RESCUE - voters of sub-threshold unaligned lists
     (Reservists-Economic, Blue and White) moved to a viable change list.
  EXCHANGE RATE - the marginal value of a vote for each list under the
     campaign's objective, from the forecast's own draws
     (targeting_marginal.py): P(change-led government) by default, with
     blocking (P(Netanyahu bloc < 61)) and change-bloc seats as
     alternatives.

Per locality: expected objective gain per 1,000 field contacts (efficiency)
and at saturation (scale), plus swing / turnout / rescue indices, a 2026
projected vote, a priority tier and the recommended mode of contact. Large
localities also get polling-station (kalpi) level targeting from the 2022
results, which shows how much better a campaign does by choosing its turf.

Outputs (data/processed/targeting/):
    localities.csv          one row per locality, all metrics
    kalpi.csv               polling-station targeting (localities >= 8 kalpiot)
    segments.csv            segment summaries
    validation.json         all backtests
    summary.json            national figures for the executive summary
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR, RAW_DIR

warnings.filterwarnings("ignore")

OUT = PROCESSED_DIR / "targeting"
KALPI_DIR = RAW_DIR / "kalpi"

# ---------------------------------------------------------------- constants
ELIGIBLE_2026 = 7_287_030        # Kolot Nodedim K26 estimate (kn26 json)
ELIGIBLE_2022 = 6_788_804        # CEC, K25
ROLL_ABROAD = 0.08               # share of the roll living abroad (IDI-range
                                 # estimate; refined by segment below)
TEL_AVIV = (32.0853, 34.7818)

# 2026 lists (mixture labels) -> camp. B&W and Reservists are UNALIGNED
# (owner rulings 2026-09-03 / 09-09); Amcha, Noam and the Haredi Public
# sit in the Netanyahu bloc (registry).
LIST_CAMP = {
    "Yashar": "ch", "Bennett 2026 + Yesh Atid": "ch", "The Democrats": "ch",
    "Yisrael Beytenu": "ch",
    "Likud": "nb", "Shas": "nb", "United Torah Judaism": "nb",
    "Otzma Yehudit": "nb", "Religious Zionist Party": "nb",
    "Amcha Yisrael": "nb", "Noam": "nb", "The Haredi Public": "nb",
    "Ra'am": "ar", "Balad + Hadash-Ta'al": "ar",
    "Blue and White": "un", "Reservists – Economic Party": "un",
    "Israel First": "ot",
}
LIST_ID = {
    "Likud": "likud", "Yashar": "yashar",
    "Bennett 2026 + Yesh Atid": "bennett_2026+yesh_atid",
    "The Democrats": "democrats", "Yisrael Beytenu": "yisrael_beytenu",
    "Shas": "shas", "United Torah Judaism": "utj",
    "Otzma Yehudit": "otzma", "Religious Zionist Party": "rzp",
    "Ra'am": "raam", "Balad + Hadash-Ta'al": "balad+hadash_taal",
    "Reservists – Economic Party": "zionist_home",
    "Blue and White": "blue_white", "Amcha Yisrael": "amcha_yisrael",
    "Noam": "noam", "The Haredi Public": "haredi_public",
    "Israel First": "israel_first",
}
SHORT = {"Likud": "Likud", "Yashar": "Yashar",
         "Bennett 2026 + Yesh Atid": "Together", "The Democrats": "Democrats",
         "Yisrael Beytenu": "Yisrael Beytenu", "Shas": "Shas",
         "United Torah Judaism": "UTJ", "Otzma Yehudit": "Otzma",
         "Religious Zionist Party": "RZP-Zehut", "Ra'am": "Ra'am",
         "Balad + Hadash-Ta'al": "Joint List",
         "Reservists – Economic Party": "Reservists",
         "Blue and White": "Blue & White", "Amcha Yisrael": "Amcha",
         "Noam": "Noam", "The Haredi Public": "Haredi Public",
         "Israel First": "Israel First"}
CHANGE_LISTS = [k for k, v in LIST_CAMP.items() if v == "ch"]

# Camps for the HISTORICAL panel (ideological, consistent across cycles):
# R = right-religious, C = centre-left/anti-Netanyahu, A = Arab lists.
# Yisrael Beytenu is R until April 2019 and C from September 2019 (the
# 2019a->2019s transition is therefore excluded from volatility); Kulanu is
# R (in Netanyahu's governments 2015-19, merged into Likud); New Hope 2021
# is C (ran explicitly against Netanyahu); Yamina 2021 is R (its voters
# returned to the right in 2022 - Kolot Nodedim K24->K25).
R_PARTIES = {"likud_beytenu", "likud", "shas", "utj", "yachad", "jewish_home",
             "otzma_leyisrael", "otzma", "urwp", "new_right", "zehut",
             "kulanu", "yamina", "rzp", "am_shalem"}
C_PARTIES = {"yesh_atid", "labor", "hatnuah", "meretz", "kadima",
             "zionist_union", "blue_white", "labor_gesher",
             "dem_union", "labor_gesher_meretz", "new_hope"}
A_FAMILY = "arab"
SOFT_RIGHT = {("2015", "kulanu"), ("2019a", "kulanu"), ("2019a", "gesher"),
              ("2019a", "yisrael_beytenu"), ("2021", "yamina"),
              ("2021", "new_hope"), ("2022", "jewish_home"),
              ("2013", "am_shalem"), ("2013", "kadima")}
VOL_TRANSITIONS = [("2013", "2015"), ("2015", "2019a"), ("2019s", "2020"),
                   ("2020", "2021"), ("2021", "2022")]
COMP_TRANSITIONS = [("2019s", "2020"), ("2020", "2021"), ("2021", "2022")]

# ---------------------------------------------------------------- field-effect parameters
# Calibrated to the field-experiment literature (sources and ranges on the
# methodology page; research desks D3 and P of 2026-10-11).
#
# GOTV: a completed door conversation raises the contacted person's turnout
# by GOTV_BASE in a high-salience European-style election (about half the
# US high-salience CACE of ~3 pp, Mann & Haenschen 2024; European pooled
# canvassing 0.8 pp, Bhatti et al. 2019), times a HUMP in baseline turnout
# (canvassing effects peak at 30-50% control turnout and vanish above 70-80%:
# 4.6 / 6.2 / 1.4 / 0.6 pp by band, Gerber & Green), times household
# spillover (~60% to the other household member, Nickerson 2008; discounted).
GOTV_BASE = 0.015
# Softened version of the US canvassing gradient (CACE 6.2 / 1.4 / 0.6 pp at
# 30-50 / 50-70 / 70%+ control turnout, i.e. 2.5x / 0.56x / 0.24x the
# average): peak x1.8 at ~42% resident turnout, x0.4 at 75%, x0.22 at 85%.
GOTV_HUMP_P = [0.15, 0.30, 0.425, 0.55, 0.65, 0.75, 0.85, 0.95]
GOTV_HUMP_M = [1.00, 1.50, 1.80, 1.20, 0.70, 0.40, 0.22, 0.10]
HOUSEHOLD_SPILLOVER = 1.3
# Persuasion: cross-bloc switching ~0.3 pp per conversation with a soft
# Netanyahu-bloc voter (Kalla & Broockman 2018 pooled 0.13 pp; personal
# contact 0.58 pp; Pons 2018 upper bound) -> per CROSS-PRESSURED soft voter
# 0.003 / CROSS_PRESSURE.
RHO_PERSUADE = 0.003 / 0.22
# Wasted-vote rescue: ~5 pp of contacted sub-threshold-list supporters move
# to a viable list (insurance-voting evidence; Fredén 2017, Shikano et al.
# 2009, Bargsted & Kedar 2009), ~60% of whom land on a change-bloc list.
RHO_RESCUE = 0.05          # share of contacted sub-threshold supporters who move
RESCUE_TO_CHANGE = 0.60    # of movers, share choosing a change list (rest: Likud)
PERSUASION_TURNOUT_SIDE = 0.5  # turnout effect of a persuasion call on a soft
                           # NB voter, relative to a GOTV conversation (Pons
                           # 2018 found no turnout effect of persuasion canvassing)
SUPPORTER_PROPENSITY_GAP = 0.10  # identified supporters vote ~10 pts above area
CROSS_PRESSURE = 0.22      # share of soft NB voters open to a change list
                           # (calibrated: national persuadable ~2.5% of voters,
                           # between N12's 0.6-1.6% between-bloc undecided and
                           # the ~5% of NB intenders reporting a switch, 9 Oct)
# Cross-bloc persuasion is identity-bounded (Shamir & Arian 1999; Bassan-
# Nygate & Weiss 2022): scaled down where the soft right is religious.
PERSUASION_SEGMENT_MULT = {"haredi": 0.15, "settlement_rz": 0.35,
                           "religious_zionist": 0.6, "arab_bedouin_south": 0.0,
                           "arab_north_triangle": 0.0, "arab_christian": 0.3}
CONTACT_CAP = 0.35         # max share of a locality's eligible reachable
REGULAR_SHARE_2022 = 4_306_028 / 4_764_742   # valid votes at regular stations, 2022
DOOR_RESCUE = False        # rescue asks are not made at the door: rescue runs as
                           # media and calls to identified voters (playbook)
FORCE_COMPOSITION = None   # sensitivity runs only: "multiplicative"


def gotv_lift(p: np.ndarray) -> np.ndarray:
    """Turnout lift per completed door conversation at baseline turnout p."""
    return GOTV_BASE * np.interp(p, GOTV_HUMP_P, GOTV_HUMP_M) * HOUSEHOLD_SPILLOVER


# ---------------------------------------------------------------- helpers

def camp_of(cycle: str, party: str, family: str) -> str:
    if family == A_FAMILY:
        return "A"
    if party == "yisrael_beytenu":
        return "R" if cycle in ("2013", "2015", "2019a") else "C"
    if party in R_PARTIES:
        return "R"
    if party in C_PARTIES:
        return "C"
    return "O"


def wavg(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w)
    return float(np.sum(x[m] * w[m]) / np.sum(w[m])) if m.any() else np.nan


def haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p)
         * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


# Localities on the CEC roll that the CBS 2023 locality file does not carry.
META_FIX = {3400: {"name_cbs": "חברון", "name_en": "Hebron", "lat": 31.5247, "lon": 35.1100,
                   "district": "אזור יהודה ושומרון", "religion_cbs": 1,
                   "settlement_type": "community"}}


def load():
    panel = pd.read_parquet(OUT / "panel.parquet")
    lc = pd.read_parquet(OUT / "locality_cycle.parquet")
    meta = pd.read_csv(OUT / "locality_meta.csv")
    for lid, fix in META_FIX.items():
        m = meta["locality"] == lid
        for k, v in fix.items():
            if k in meta.columns:
                meta.loc[m & meta[k].isna(), k] = v
    nat = pd.read_csv(OUT / "national.csv")
    mv = pd.read_csv(OUT / "marginal_values.csv")
    shares = pd.read_csv(PROCESSED_DIR / "mixture_shares.csv")
    panel["camp"] = [camp_of(c, p, f) for c, p, f in
                     zip(panel.cycle, panel.party, panel.family)]
    return panel, lc, meta, nat, mv, shares


def camp_wide(panel: pd.DataFrame, lc: pd.DataFrame) -> pd.DataFrame:
    cw = panel.pivot_table(index=["cycle", "locality"], columns="camp",
                           values="votes", aggfunc="sum", fill_value=0)
    cw.columns = [f"c_{c}" for c in cw.columns]
    out = lc.merge(cw.reset_index(), on=["cycle", "locality"], how="left")
    sr = panel[[(c, p) in SOFT_RIGHT for c, p in zip(panel.cycle, panel.party)]]
    sr = sr.groupby(["cycle", "locality"])["votes"].sum().rename("soft_right")
    out = out.merge(sr.reset_index(), on=["cycle", "locality"], how="left")
    out["soft_right"] = out["soft_right"].fillna(0)
    return out


# ---------------------------------------------------------------- segments

CIRCASSIAN = {508, 540}    # Kafr Kama, Reihaniye: IDF-serving, vote like Druze towns

SEGMENTS = {
    "arab_bedouin_south": "Arab – Negev Bedouin",
    "arab_north_triangle": "Arab – Galilee & Triangle",
    "arab_christian": "Arab – Christian localities",
    "druze": "Druze & Circassian",
    "mixed_city": "Mixed Jewish–Arab city",
    "jerusalem": "Jerusalem",
    "haredi": "Haredi",
    "settlement_rz": "West Bank – national-religious",
    "settlement_secular": "West Bank – secular & mixed",
    "religious_zionist": "Religious-Zionist (inside Green Line)",
    "kibbutz": "Kibbutz",
    "moshav_rural": "Moshav & rural community",
    "russian_speaking": "Russian-speaking towns",
    "liberal_urban": "Secular-liberal urban",
    "periphery_likud": "Likud-leaning cities & development towns",
    "mixed_urban": "Middle Israel (mixed urban)",
}


def assign_segments(meta: pd.DataFrame, cw: pd.DataFrame,
                    panel: pd.DataFrame) -> pd.DataFrame:
    p22 = panel[panel.cycle == "2022"].pivot_table(
        index="locality", columns="party", values="votes", aggfunc="sum",
        fill_value=0)
    tot = p22.sum(axis=1).replace(0, np.nan)
    s = p22.div(tot, axis=0)
    g = lambda c: s[c] if c in s else 0
    f = pd.DataFrame({
        "s_haredi": g("shas") + g("utj"),
        "s_arab": g("raam") + g("hadash_taal") + g("balad"),
        "s_rz": g("rzp") + g("jewish_home"),
        "s_likud": g("likud"),
        "s_cl": g("yesh_atid") + g("blue_white") + g("labor") + g("meretz"),
        "s_yb": g("yisrael_beytenu")}).reset_index()
    yb_avg = (cw[cw.cycle.isin(["2019s", "2020", "2021", "2022"])]
              .assign(yb=lambda d: d["f_yb"] / d["valid"].replace(0, np.nan))
              .groupby("locality")["yb"].mean().rename("s_yb_avg"))
    m = meta.merge(f, on="locality", how="left").merge(
        yb_avg.reset_index(), on="locality", how="left")

    z = lambda x: (x - x.mean()) / x.std()
    ses = pd.concat([z(np.log(m["median_wage"])), z(m["academic_pct"]),
                     -z(m["no_car_pct"]), z(m["employed_pct"])], axis=1)
    m["ses_score"] = ses.mean(axis=1, skipna=True)
    m["km_tel_aviv"] = haversine_km(m["lat"], m["lon"], *TEL_AVIV)

    def seg(r):
        rel, st = r.census_religion, r.settlement_type
        if st == "bedouin_tribe" or r.religion_cbs == 3 or (
                (rel == "muslim" or r.s_arab > 0.6) and r.district == "הדרום"):
            return "arab_bedouin_south"
        if rel == "druze" or r.locality in CIRCASSIAN:
            return "druze"
        if rel == "christian":
            return "arab_christian"
        if rel == "muslim" or (rel == "other" and r.religion_cbs != 1) or (r.religion_cbs == 2) or (
                pd.notna(r.s_arab) and r.s_arab > 0.6):
            return "arab_north_triangle"
        if r.locality == 3000:
            return "jerusalem"
        if r.religion_cbs == 4 and pd.notna(r.arab_share_pop) and \
                r.arab_share_pop >= 0.15:
            return "mixed_city"
        if (pd.notna(r.s_haredi) and r.s_haredi >= 0.45) or \
                r.religiosity_modal == "haredi":
            return "haredi"
        if r.district == "אזור יהודה ושומרון":
            return ("settlement_rz" if (r.s_rz >= 0.30 or
                                        r.religiosity_modal == "religious")
                    else "settlement_secular")
        if st == "kibbutz":
            return "kibbutz"
        if (pd.notna(r.s_rz) and r.s_rz >= 0.30) or \
                r.religiosity_modal == "religious":
            return "religious_zionist"
        if st in ("moshav", "moshav_shitufi", "community", "rural_other",
                  "institutional"):
            return "moshav_rural"
        if pd.notna(r.s_yb_avg) and r.s_yb_avg >= 0.12:
            return "russian_speaking"
        if pd.notna(r.s_cl) and r.s_cl >= 0.48:
            return "liberal_urban"
        if pd.notna(r.s_likud) and r.s_likud >= 0.30 and pd.notna(r.ses_score) and (
                r.ses_score < 0 or (r.km_tel_aviv > 45 and r.ses_score < 0.5)):
            return "periphery_likud"
        return "mixed_urban"

    m["segment"] = m.apply(seg, axis=1)
    m["segment_label"] = m["segment"].map(SEGMENTS)
    return m


# ---------------------------------------------------------------- 2026 projection

def lineage_votes_2022(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel[panel.cycle == "2022"].pivot_table(
        index="locality", columns="party", values="votes", aggfunc="sum",
        fill_value=0)
    return p


def envelope_ratio_2022() -> dict:
    """Official (incl. double envelopes) vs regular-station share, by 2022 list."""
    from targeting_data import LETTERS, read_expc
    d = read_expc(25)
    env = d[(d["locality"].isin([0, 9999])) | (d["eligible"] == 0)]
    loc = d[~d.index.isin(env.index)]
    out = {}
    tot_all, tot_loc = d["valid"].sum(), loc["valid"].sum()
    for letter, (pid, *_rest) in LETTERS["2022"].items():
        out[pid] = (d[letter].sum() / tot_all) / (loc[letter].sum() / tot_loc)
    return out


def ipf(P: np.ndarray, row_tot: np.ndarray, col_tot: np.ndarray,
        iters: int = 60) -> np.ndarray:
    X = P.copy()
    for _ in range(iters):
        cs = X.sum(axis=0)
        X *= np.where(cs > 0, col_tot / np.maximum(cs, 1e-12), 0)[None, :]
        rs = X.sum(axis=1)
        X *= np.where(rs > 0, row_tot / np.maximum(rs, 1e-12), 0)[:, None]
    return X


DRUZE_POOL = 0.6     # weight on the segment-average vote in Druze localities
CAMP_BLEND = 0.5     # weight on uniform camp swing (held-out test: the 50/50
                     # blend beat both pure methods across 2020-21 and 2021-22)
CAMP22 = {"C": ["yesh_atid", "blue_white", "labor", "meretz", "yisrael_beytenu"],
          "R": ["likud", "rzp", "shas", "utj", "jewish_home"],
          "A": ["raam", "hadash_taal", "balad"], "O": ["other"]}
CAMP26 = {"ch": "C", "un": "C", "nb": "R", "ar": "A", "ot": "O"}


def camp_blend(P: np.ndarray, sh22: pd.DataFrame, lists: list, nat_shift: dict) -> np.ndarray:
    """Pull each row's camp totals halfway toward uniform camp swing from its
    own 2022 camp shares, scaling the lists inside each camp."""
    if CAMP_BLEND <= 0:
        return P
    camp_of_list = np.array([CAMP26[LIST_CAMP[l]] for l in lists])
    out = P.copy()
    for c in ["C", "R", "A", "O"]:
        cols = [k for k in CAMP22[c] if k in sh22.columns]
        u = np.clip(sh22[cols].sum(axis=1).values + nat_shift[c], 0, 1)
        m = camp_of_list == c
        cur = P[:, m].sum(axis=1)
        tgt = (1 - CAMP_BLEND) * cur + CAMP_BLEND * u
        out[:, m] = P[:, m] * (tgt / np.maximum(cur, 1e-9))[:, None]
    return out / np.maximum(out.sum(axis=1, keepdims=True), 1e-12)


def coherent_flows(lists, G, S22, srcs):
    """National 2022-source x 2026-list flow matrix. Start from the forecast's
    lineage compositions (F0[s,j] = c_j(s) * G_j; 2022 'other' spread pro
    rata) and rake to BOTH margins - each 2022 source's size and each 2026
    list's share - so every 2022 vote is carried forward with weight one.
    Returns T[s][j] = share of source s's voters going to list j."""
    from kalpi_model import LINEAGE_2026
    rows = list(srcs) + ["other"]
    F0 = np.zeros((len(rows), len(lists)))
    for j, l in enumerate(lists):
        for src, w in LINEAGE_2026[LIST_ID[l]].items():
            if src in srcs:
                F0[rows.index(src), j] += w * G[l]
    S = np.array([S22[r] for r in rows])
    F0[-1, :] = S[-1] * G.values          # small 2022 lists: pro rata
    F0[F0.sum(axis=1) == 0, :] = 1e-6
    F = F0.copy()
    for _ in range(500):
        F *= (S / np.maximum(F.sum(axis=1), 1e-15))[:, None]
        F *= (G.values / np.maximum(F.sum(axis=0), 1e-15))[None, :]
    T = pd.DataFrame(F / S[:, None], index=rows, columns=lists)
    return T


def pooled_shares(sh: pd.DataFrame, loc_of: pd.Series, pool_locs: set,
                  seg_mean: pd.Series) -> pd.DataFrame:
    """Shrink 2022 shares toward the segment mean in pooled localities
    (Druze home-village candidate effects do not carry to 2026 lists).
    Only the split among non-Arab lists is pooled: each locality keeps its
    own Arab-list share, so mixed Druze-Muslim-Christian towns such as
    Mughar keep their Arab-list voters."""
    m = loc_of.isin(pool_locs).values
    if m.any():
        sh = sh.copy()
        ar = [c for c in sh.columns if c in CAMP22["A"]]
        nar = [c for c in sh.columns if c not in ar]
        own = sh.loc[m, nar].values
        a_own = sh.loc[m, ar].sum(axis=1).values if ar else np.zeros(m.sum())
        own_n = own / np.maximum(own.sum(axis=1, keepdims=True), 1e-12)
        sm = seg_mean.reindex(nar).fillna(0).values
        sm = sm / max(sm.sum(), 1e-12)
        mix = (1 - DRUZE_POOL) * own_n + DRUZE_POOL * sm[None, :]
        sh.loc[m, nar] = mix * (1 - a_own)[:, None]
    return sh


def project_2026(panel: pd.DataFrame, shares: pd.DataFrame,
                 pool_locs: set | None = None):
    """2022 locality vote -> 2026 lists through a coherent national flow
    matrix (lineages raked to both margins), then raked locally to the
    forecast's national means (converted to regular-station shares)."""
    from kalpi_model import LINEAGE_2026
    v22 = lineage_votes_2022(panel)
    srcs = [c for c in v22.columns if c != "other"]
    S22 = v22.sum() / v22.values.sum()
    r_env = envelope_ratio_2022()
    lists = [l for l in LIST_CAMP if l in set(shares["list"])]
    F = shares.set_index("list").loc[lists, "share_mean"].clip(lower=0)
    F = F / F.sum()
    G = {}
    for l in lists:
        lin = LINEAGE_2026[LIST_ID[l]]
        ratio = sum(w * r_env.get(src, 1.0) for src, w in lin.items())
        G[l] = F[l] / ratio
    G = pd.Series(G)
    G = G / G.sum()
    T = coherent_flows(lists, G, S22, srcs)
    sh22 = v22.div(v22.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    pool_locs = pool_locs or set()
    seg_mean = (v22.loc[v22.index.isin(pool_locs)].sum()
                / max(1.0, v22.loc[v22.index.isin(pool_locs)].values.sum()))
    sh22 = pooled_shares(sh22, pd.Series(sh22.index, index=sh22.index),
                         pool_locs, seg_mean)
    P = sh22[T.index].values @ T.values
    row = v22.sum(axis=1).values.astype(float)
    P = P / np.maximum(P.sum(axis=1, keepdims=True), 1e-12)
    camp_of_list = np.array([CAMP26[LIST_CAMP[l]] for l in lists])
    nat_shift = {c: float(G.values[camp_of_list == c].sum()
                          - S22[[k for k in CAMP22[c] if k in S22.index]].sum())
                 for c in ["C", "R", "A", "O"]}
    P = camp_blend(P, sh22, lists, nat_shift)
    P = P * row[:, None]
    X = ipf(P, row, G.values * row.sum())
    proj = pd.DataFrame(X / np.maximum(row[:, None], 1e-9), index=v22.index,
                        columns=lists)
    pre = pd.DataFrame(P / np.maximum(row[:, None], 1e-9), index=v22.index,
                       columns=lists)
    project_2026.setup = {"T": T, "G": G, "lists": lists, "pre": pre,
                          "pool_locs": pool_locs, "seg_mean": seg_mean,
                          "nat_shift": nat_shift}
    return proj, G, T


def backtest_projection(panel: pd.DataFrame) -> dict:
    """Project 2022 from 2021 with the measured national flow matrix
    (Kolot Nodedim K24->K25) and IPF to the true 2022 national result;
    compare locality camp shares with the truth and with uniform swing.
    NB: the flow matrix was itself estimated from these stations, so this
    tests the LOCAL ALLOCATION assumption (uniform transfer rates), not the
    national forecast."""
    T = json.loads((RAW_DIR / "transfer" / "transfer_24_to_25.json").read_text())
    sym21 = {"מחל": "likud", "פה": "yesh_atid", "שס": "shas",
             "כן": "blue_white", "ב": "yamina", "אמת": "labor", "ג": "utj",
             "ל": "yisrael_beytenu", "ט": "rzp", "ודעם": "joint_list",
             "ת": "new_hope", "מרצ": "meretz", "עם": "raam"}
    sym22 = {"מחל": "likud", "פה": "yesh_atid", "ט": "rzp",
             "כן": "blue_white", "שס": "shas", "ג": "utj",
             "ל": "yisrael_beytenu", "עם": "raam", "ום": "hadash_taal",
             "אמת": "labor", "מרצ": "meretz", "ד": "balad",
             "ב": "jewish_home"}
    M = {}
    for t in T["transfers"]:
        a, b = sym21.get(t["source_symbol"]), sym22.get(t["target_symbol"])
        if a and b:
            M.setdefault(a, {})[b] = t["percentage"] / 100.0
    p21 = panel[panel.cycle == "2021"].pivot_table(
        index="locality", columns="party", values="votes", aggfunc="sum",
        fill_value=0)
    p22 = panel[panel.cycle == "2022"].pivot_table(
        index="locality", columns="party", values="votes", aggfunc="sum",
        fill_value=0)
    idx = p21.index.intersection(p22.index)
    p21, p22 = p21.loc[idx], p22.loc[idx]
    tgt_lists = list(sym22.values()) + ["other"]
    sh21 = p21.div(p21.sum(axis=1), axis=0).fillna(0)
    P = np.zeros((len(idx), len(tgt_lists)))
    for j, b in enumerate(tgt_lists):
        if b == "other":
            P[:, j] = sh21.get("other", 0)
            continue
        for a, row in M.items():
            if a in sh21:
                P[:, j] += sh21[a].values * row.get(b, 0)
    rows = p22.sum(axis=1).values.astype(float)
    P = P * rows[:, None] / np.maximum(P.sum(axis=1, keepdims=True), 1e-12)
    col = p22[tgt_lists].sum().values.astype(float)
    X = ipf(P, rows, col)
    pred = pd.DataFrame(X / rows[:, None], index=idx, columns=tgt_lists)
    true = p22[tgt_lists].div(rows, axis=0)

    def camps(df):
        return pd.DataFrame({
            "C": df[["yesh_atid", "blue_white", "labor", "meretz",
                     "yisrael_beytenu"]].sum(axis=1),
            "R": df[["likud", "rzp", "shas", "utj", "jewish_home"]].sum(axis=1),
            "A": df[["raam", "hadash_taal", "balad"]].sum(axis=1)})
    cp, ct = camps(pred), camps(true)
    # uniform camp swing baseline
    c21 = pd.DataFrame({
        "C": p21[["yesh_atid", "blue_white", "labor", "meretz",
                  "yisrael_beytenu", "new_hope"]].sum(axis=1),
        "R": p21[["likud", "rzp", "shas", "utj", "yamina"]].sum(axis=1),
        "A": p21[["joint_list", "raam"]].sum(axis=1)}).div(
            p21.sum(axis=1), axis=0)
    w = rows
    nat21 = (c21.mul(p21.sum(axis=1), axis=0).sum() / p21.values.sum())
    nat22 = (ct.mul(rows, axis=0).sum() / rows.sum())
    cu = c21 + (nat22 - nat21)
    res = {}
    for k in ["C", "R", "A"]:
        res[f"mae_{k}_transfer_pp"] = round(wavg((cp[k] - ct[k]).abs(), w) * 100, 2)
        res[f"mae_{k}_uniform_pp"] = round(wavg((cu[k] - ct[k]).abs(), w) * 100, 2)
    big = w >= 5000
    res["mae_C_transfer_big_pp"] = round(wavg((cp.C - ct.C).abs()[big], w[big]) * 100, 2)
    res["mae_C_uniform_big_pp"] = round(wavg((cu.C - ct.C).abs()[big], w[big]) * 100, 2)
    party_mae = {b: round(wavg((pred[b] - true[b]).abs(), w) * 100, 2)
                 for b in tgt_lists if b != "other"}
    res["party_mae_pp"] = party_mae
    res["n_localities"] = int(len(idx))
    res["note"] = ("Flow matrix estimated by Kolot Nodedim from the same "
                   "stations: tests the local-allocation assumption, not "
                   "national accuracy.")
    return res


# ---------------------------------------------------------------- swing / openness

def resid_camp_changes(cw: pd.DataFrame, transitions, camp="R"):
    """Locality camp-share changes net of the national change, with the
    binomial sampling-noise variance of each change."""
    out = []
    for a, b in transitions:
        A = cw[cw.cycle == a].set_index("locality")
        B = cw[cw.cycle == b].set_index("locality")
        idx = A.index.intersection(B.index)
        A, B = A.loc[idx], B.loc[idx]
        sa = A[f"c_{camp}"] / A["valid"].replace(0, np.nan)
        sb = B[f"c_{camp}"] / B["valid"].replace(0, np.nan)
        na = A[f"c_{camp}"].sum() / A["valid"].sum()
        nb_ = B[f"c_{camp}"].sum() / B["valid"].sum()
        d = (sb - sa) - (nb_ - na)
        noise = sa * (1 - sa) / A["valid"].replace(0, np.nan) + \
            sb * (1 - sb) / B["valid"].replace(0, np.nan)
        out.append(pd.DataFrame({"locality": idx, "transition": f"{a}->{b}",
                                 "resid": d.values, "noise": noise.values,
                                 "valid": B["valid"].values}))
    return pd.concat(out, ignore_index=True)


def openness_features(cw: pd.DataFrame, upto: str, seg: pd.DataFrame,
                      proj_bal: pd.Series | None = None) -> pd.DataFrame:
    """Openness features from elections up to and including `upto`."""
    cyc = [c for c in ["2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]]
    keep = cyc[:cyc.index(upto) + 1]
    trans = [t for t in VOL_TRANSITIONS if t[1] in keep]
    rc = resid_camp_changes(cw, trans)
    g = rc.groupby("locality")
    vol2 = (g["resid"].apply(lambda x: np.nanmean(x ** 2))
            - g["noise"].apply(np.nanmean)).clip(lower=0)
    noise = g["noise"].apply(np.nanmean)
    f = pd.DataFrame({"vol_raw": np.sqrt(vol2), "vol_noise": noise})
    # soft-right footprint relative to national
    cs = cw[cw.cycle.isin(keep)].copy()
    natsr = cs.groupby("cycle").apply(lambda d: d["soft_right"].sum()
                                      / d["valid"].sum())
    cs["sr_rel"] = (cs["soft_right"] / cs["valid"].replace(0, np.nan)) / \
        cs["cycle"].map(natsr)
    f["footprint"] = cs.groupby("locality")["sr_rel"].mean()
    last = cw[cw.cycle == upto].set_index("locality")
    sC = last["c_C"] / last["valid"].replace(0, np.nan)
    sR = last["c_R"] / last["valid"].replace(0, np.nan)
    f["balance"] = 1 - (sC - sR).abs() / (sC + sR).replace(0, np.nan)
    f["jewish_share"] = 1 - last["c_A"] / last["valid"].replace(0, np.nan)
    # empirical-Bayes shrinkage of volatility toward the segment mean
    f = f.join(seg.set_index("locality")[["segment"]], how="left")
    seg_mean = f.groupby("segment")["vol_raw"].transform("median")
    tau2 = f.groupby("segment")["vol_raw"].transform(lambda x: np.nanvar(x))
    w = tau2 / (tau2 + f["vol_noise"])
    f["vol"] = w * f["vol_raw"] + (1 - w) * seg_mean
    return f.drop(columns="segment")


OPENNESS_SPECS = {
    "volatility only": {"vol": 1.0},
    "footprint only": {"footprint": 1.0},
    "balance only": {"balance": 1.0},
    "equal weights": {"vol": 1 / 3, "footprint": 1 / 3, "balance": 1 / 3},
    "footprint + balance": {"footprint": 0.5, "balance": 0.5},
    "footprint-led": {"vol": 0.25, "footprint": 0.5, "balance": 0.25},
}


def _openness_fold(cw, seg, upto, target):
    X = openness_features(cw, upto, seg)
    y = resid_camp_changes(cw, [target]).set_index("locality")
    d = X.join(y[["resid", "noise", "valid"]], how="inner")
    d = d[(d["jewish_share"] > 0.8) & (d["valid"] >= 400)].dropna()
    d["absres"] = d["resid"].abs()
    return d


def fit_openness(cw: pd.DataFrame, seg: pd.DataFrame) -> tuple[dict, dict]:
    """Choose the openness index by OUT-OF-SAMPLE rank validity: features
    built only from elections up to t predict the size of each locality's
    residual right-camp movement in t->t+1, for two folds (2020->2021 and
    2021->2022), Jewish-majority localities with >= 400 valid votes."""
    from scipy.stats import spearmanr
    folds = {"2020->2021": ("2020", ("2020", "2021")),
             "2021->2022": ("2021", ("2021", "2022"))}
    data = {k: _openness_fold(cw, seg, u, t) for k, (u, t) in folds.items()}
    res = {}
    for name, spec in OPENNESS_SPECS.items():
        rhos, lifts = [], []
        for k, d in data.items():
            Z = d[list(spec)].apply(lambda x: (x - x.mean()) / x.std())
            idx = sum(w * Z[f] for f, w in spec.items())
            rhos.append(spearmanr(idx, d["absres"]).correlation)
            q = pd.qcut(idx.rank(method="first"), 5, labels=False)
            lifts.append(d["absres"][q == 4].mean() / d["absres"][q == 0].mean())
        res[name] = {"spearman_by_fold": [round(float(r), 3) for r in rhos],
                     "mean_spearman": round(float(np.mean(rhos)), 3),
                     "top_bottom_quintile_ratio": [round(float(x), 2) for x in lifts]}
    best = max(res, key=lambda k: res[k]["mean_spearman"])
    val = {"specs": res, "chosen": best,
           "n_by_fold": {k: int(len(d)) for k, d in data.items()},
           "target": "absolute residual right-camp share change t->t+1 "
                     "(net of national); features from elections <= t"}
    return OPENNESS_SPECS[best], val


# ---------------------------------------------------------------- marginal-voter composition

def composition_slopes(cw: pd.DataFrame, seg: pd.DataFrame,
                       transitions) -> pd.DataFrame:
    """Within segment x transition, regress the change in each camp's votes
    per eligible voter on the change in turnout (both demeaned within the
    segment-transition, which absorbs segment-level persuasion tides): the
    slope is the camp's share of the MARGINAL voter."""
    rows = []
    sg = seg.set_index("locality")["segment"]
    for a, b in transitions:
        A = cw[cw.cycle == a].set_index("locality")
        B = cw[cw.cycle == b].set_index("locality")
        idx = A.index.intersection(B.index).intersection(sg.index)
        A, B = A.loc[idx], B.loc[idx]
        ok = (A["eligible"] >= 300) & (B["eligible"] >= 300)
        A, B = A[ok], B[ok]
        dT = B["voters"] / B["eligible"] - A["voters"] / A["eligible"]
        for camp in ["C", "R", "A", "O"]:
            dy = B[f"c_{camp}"] / B["eligible"] - A[f"c_{camp}"] / A["eligible"]
            sh = A[f"c_{camp}"] / A["valid"].replace(0, np.nan)
            rows.append(pd.DataFrame({
                "locality": A.index, "transition": f"{a}->{b}", "camp": camp,
                "dy": dy.values, "dT": dT.values, "w": B["eligible"].values,
                "share": sh.values, "segment": sg.reindex(A.index).values}))
    d = pd.concat(rows, ignore_index=True).dropna()
    out = []
    for (segm, camp), g in d.groupby(["segment", "camp"]):
        g = g.copy()
        for col in ("dy", "dT"):
            g[col] = g[col] - g.groupby("transition")[col].transform(
                lambda x: np.average(x, weights=g.loc[x.index, "w"]))
        w = np.sqrt(g["w"].values)
        x, y = g["dT"].values, g["dy"].values
        if len(g) < 12 or np.var(x) < 1e-6:
            continue
        slope = np.sum(w * x * y) / np.sum(w * x * x)
        resid = y - slope * x
        se = np.sqrt(np.sum(w * resid ** 2) / (len(g) - 1) / np.sum(w * x * x))
        avg = np.average(g["share"], weights=g["w"])
        out.append({"segment": segm, "camp": camp, "marginal": slope,
                    "se": se, "average": avg, "n": len(g)})
    return pd.DataFrame(out)


def theta_table(k: pd.DataFrame, prior_sd: float = 0.5) -> pd.Series:
    """Multiplicative turnout-propensity differential per segment x camp:
    theta = log(marginal share / average share), shrunk toward 0 by its
    delta-method precision (prior sd 0.5 on the log scale)."""
    mu = np.maximum(k["marginal"], np.maximum(0.15 * k["average"], 0.002))
    th = np.log(mu / np.maximum(k["average"], 0.002))
    var = (k["se"] / mu) ** 2
    th = th * prior_sd ** 2 / (prior_sd ** 2 + var)
    return pd.Series(th.values, index=pd.MultiIndex.from_frame(
        k[["segment", "camp"]]))


def tilt_camps(s: pd.DataFrame, segs: pd.Series, theta: pd.Series | None):
    """Marginal camp composition: m_b proportional to s_b * exp(theta_b)."""
    if theta is None:
        return s.div(s.sum(axis=1), axis=0)
    m = s.copy()
    for camp in s.columns:
        t = np.array([theta.get((sg, camp), 0.0) for sg in segs])
        m[camp] = s[camp] * np.exp(t)
    return m.div(m.sum(axis=1), axis=0)


def validate_composition(cw: pd.DataFrame, seg: pd.DataFrame) -> dict:
    """Fit on 2019s->2020 and 2020->2021; predict each locality's 2021->2022
    change in camp votes per eligible from its actual turnout change.
    Methods: naive (marginal voter = the locality's average 2021 voter) vs
    the multiplicative propensity model."""
    k = composition_slopes(cw, seg, [("2019s", "2020"), ("2020", "2021")])
    th = theta_table(k)
    sg = seg.set_index("locality")["segment"]
    A = cw[cw.cycle == "2021"].set_index("locality")
    B = cw[cw.cycle == "2022"].set_index("locality")
    idx = A.index.intersection(B.index).intersection(sg.index)
    A, B = A.loc[idx], B.loc[idx]
    A, B = A[A["eligible"] >= 300], B[A["eligible"] >= 300]
    segs = sg.reindex(A.index)
    dT = B["voters"] / B["eligible"] - A["voters"] / A["eligible"]
    s = pd.DataFrame({c: A[f"c_{c}"] / A["valid"] for c in ["C", "R", "A", "O"]})
    out = {}
    tot = {"naive": 0.0, "multiplicative": 0.0}
    for name, theta in (("naive", None), ("multiplicative", th)):
        m = tilt_camps(s, segs.values, theta)
        out[name] = {}
        for camp in ["C", "R", "A"]:
            dy = B[f"c_{camp}"] / B["eligible"] - A[f"c_{camp}"] / A["eligible"]
            tide = (dy - dT * m[camp]).groupby(segs).transform("mean")
            pred = dT * m[camp] + tide
            mae = wavg((pred - dy).abs(), B["eligible"]) * 1000
            out[name][camp] = round(mae, 2)
            tot[name] += mae
    out["chosen"] = min(tot, key=tot.get)
    out["units"] = "weighted MAE, camp votes per 1,000 eligible, 2021->2022"
    return out


# ---------------------------------------------------------------- kalpi level

def kalpi_lineage_2022() -> pd.DataFrame:
    from targeting_data import LETTERS
    for enc in ("utf-8-sig", "cp1255"):
        try:
            b = pd.read_csv(KALPI_DIR / "expb_25.csv", encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    b.columns = [c.strip() for c in b.columns]
    b = b.rename(columns={"סמל ישוב": "locality", "קלפי": "kalpi",
                          "בזב": "eligible", "מצביעים": "voters",
                          "כשרים": "valid"})
    b = b[(b["locality"] != 9999) & (b["eligible"] > 0) & (b["valid"] > 0)].copy()
    from targeting_data import META
    letters = LETTERS["2022"]
    party_cols = [c for c in b.columns if c not in META and c not in
                  ("locality", "kalpi", "eligible", "voters", "valid")]
    out = b[["locality", "kalpi", "eligible", "voters", "valid"]].copy()
    for letter, (pid, *_r) in letters.items():
        out[pid] = b[letter]
    out["other"] = b[[c for c in party_cols if c not in letters]].sum(axis=1)
    out["kalpi"] = out["kalpi"].astype(str)
    return out.reset_index(drop=True)


def project_kalpi(kal: pd.DataFrame, proj_loc: pd.DataFrame) -> pd.DataFrame:
    """Same flows (and Druze pooling) as the locality projection, then each
    list rescaled within the locality so station totals reproduce the
    raked locality projection."""
    st = project_2026.setup
    T, lists = st["T"], st["lists"]
    srcs = [c for c in kal.columns if c not in ("locality", "kalpi", "eligible",
                                                "voters", "valid")]
    tot = kal[srcs].sum(axis=1).replace(0, np.nan)
    sh = kal[srcs].div(tot, axis=0).fillna(0)
    sh = pooled_shares(sh, kal["locality"], st["pool_locs"], st["seg_mean"])
    P = sh.reindex(columns=T.index, fill_value=0).values @ T.values
    P = P / np.maximum(P.sum(axis=1, keepdims=True), 1e-12)
    P = camp_blend(P, sh, lists, st["nat_shift"])
    # rescale lists within each locality to reproduce the locality projection
    w = kal["valid"].values.astype(float)
    dfp = pd.DataFrame(P * w[:, None], columns=lists)
    dfp["locality"] = kal["locality"].values
    agg = dfp.groupby("locality")[lists].sum()
    tgt = proj_loc.reindex(agg.index).mul(agg.sum(axis=1), axis=0)
    ratio = (tgt / agg.replace(0, np.nan)).fillna(1.0)
    X = P * ratio.reindex(kal["locality"]).values
    X = X / np.maximum(X.sum(axis=1, keepdims=True), 1e-12)
    return pd.DataFrame(X, columns=lists, index=kal.index)


# ---------------------------------------------------------------- scoring

OBJECTIVES = {
    "change_govt": "P(change-led government)",
    "block_nb": "P(Netanyahu bloc < 61)",
    "change_seats": "Expected change-bloc seats",
    "change61": "P(change lists alone >= 61)",
    "change_raam61": "P(change lists + Ra'am >= 61)",
}

# Completed door conversations per canvasser-hour. ASSUMPTION anchored on
# practitioner rates (8-12 doors an hour, 25-30% answering; Green & Gerber,
# Mann & Haenschen contact rates): ~3 an hour in ordinary urban turf.
CONVERSATIONS_PER_HOUR = {"jewish_urban": 3.0, "arab_urban": 3.0, "kibbutz": 2.0,
                          "moshav": 2.0, "moshav_shitufi": 2.0, "community": 2.0,
                          "rural_other": 2.0, "institutional": 2.5,
                          "arab_rural": 2.0, "bedouin_tribe": 1.5}
DENSE_CONV_PER_HOUR = 4.0

# Double-envelope add-back, points of eligible, 2022 (Harsgor, Friedberg &
# Atmor 2025): district-wide averages; Arab localities 2.9. The Jewish rate
# per district is backed out so that each district total is preserved.
ENVELOPE_DISTRICT_ALL = {"אזור יהודה ושומרון": 0.100, "המרכז": 0.069,
                         "ירושלים": 0.079, "הדרום": 0.071, "תל אביב": 0.063,
                         "הצפון": 0.062, "חיפה": 0.063}
ENVELOPE_FIXED = {"arab_bedouin_south": 0.029, "arab_north_triangle": 0.029,
                  "arab_christian": 0.029, "druze": 0.045, "haredi": 0.035}
ENVELOPES_2022 = 462_807

ROLL_ABROAD_BY_SEGMENT = {
    # Share of the roll living abroad. National level ~8% (INSS/CBS range);
    # tilted toward segments with heavy emigration and away from haredi,
    # settler and Bedouin populations. Planning assumption.
    "russian_speaking": 0.13, "liberal_urban": 0.10, "mixed_urban": 0.09,
    "mixed_city": 0.10, "jerusalem": 0.08, "periphery_likud": 0.08,
    "kibbutz": 0.09, "moshav_rural": 0.07, "haredi": 0.04,
    "religious_zionist": 0.05, "settlement_rz": 0.04,
    "settlement_secular": 0.07, "arab_north_triangle": 0.05,
    "arab_christian": 0.08, "arab_bedouin_south": 0.03, "druze": 0.04}

# Electorate growth 2022->26 by segment (younger, faster-growing populations
# grow faster), rescaled to the K26 roll estimate. Planning assumption.
GROWTH_BY_SEGMENT = {"haredi": 1.16, "settlement_rz": 1.13,
                     "settlement_secular": 1.08, "religious_zionist": 1.09,
                     "arab_bedouin_south": 1.12, "arab_north_triangle": 1.09,
                     "arab_christian": 1.05, "druze": 1.07}
GROWTH_DEFAULT = 1.05

# Not targeted for access reasons: Golan Druze villages (most residents are
# not citizens and Knesset voting is socially sanctioned) and Ghajar.
FIELD_EXCLUDED = {4201: "Golan Druze village", 4203: "Golan Druze village",
                  4001: "Golan Druze village", 4502: "Golan Druze village",
                  4501: "Restricted border village"}
DISPLACED_CAPACITY = 0.5   # residents near the Gaza / Lebanon borders displaced
GAZA_KM, LEBANON_KM = 7.0, 5.0
# 2021->2022 abstention among 2021 change-camp voters (Kolot Nodedim K24->K25
# with abstention): Labor 19.9%, Yisrael Beytenu 20.0%, Meretz 11.6%.
ABSTAIN_21_22 = {"labor": 0.199, "yisrael_beytenu": 0.200, "meretz": 0.116}
LIST_PROGRAMMES = True     # sensitivity switch
# List programmes reach only voters the campaign has identified (supporter
# apps, earlier ID calls, modelled soft-voter lists): assume 30% of each
# target group is identified and half of those are reached by phone, text or
# a relational ask before election day. Planning assumption (planner slider).
LIST_IDENTIFIED = 0.30
LIST_CONTACT = 0.50
# Phantom roll: Jewish localities whose regular turnout sits far below their
# segment's typical level (e.g. Eilat, resort and student towns) carry
# registrants who live elsewhere; 70% of the gap beyond 8 points is treated as
# non-resident roll.
PHANTOM_SLACK, PHANTOM_SHARE = 0.08, 0.70
DRUZE_SHIFT = 0.0          # sensitivity: points moved from change to NB in Druze towns


def border_flags(loc: pd.DataFrame) -> pd.Series:
    """Distance from each locality to the Gaza Strip and to Lebanon."""
    pse = json.loads((RAW_DIR / "geo" / "pse_adm1.geojson").read_text())
    gaza = next(f for f in pse["features"] if f["properties"]["shapeName"] == "Gaza")
    g_ring = np.array(gaza["geometry"]["coordinates"][0] if gaza["geometry"]["type"] == "Polygon"
                      else gaza["geometry"]["coordinates"][0][0])
    ne = json.loads((RAW_DIR / "geo" / "ne10m_region.json").read_text())
    l_ring = np.array(ne["Lebanon"][0][0])

    def dist_km(lat, lon, ring):
        if pd.isna(lat):
            return np.nan
        x = (ring[:, 0] - lon) * 111.32 * np.cos(np.radians(lat))
        y = (ring[:, 1] - lat) * 110.57
        a, b = np.c_[x[:-1], y[:-1]], np.c_[x[1:], y[1:]]
        ab = b - a
        t = np.clip(-(a * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
        p = a + ab * t[:, None]
        return float(np.sqrt((p ** 2).sum(1)).min())
    gk = [dist_km(a, b, g_ring) for a, b in zip(loc["lat"], loc["lon"])]
    lk = [dist_km(a, b, l_ring) for a, b in zip(loc["lat"], loc["lon"])]
    return pd.DataFrame({"km_gaza": gk, "km_lebanon": lk}, index=loc.index)


def envelope_addback(loc: pd.DataFrame) -> pd.Series:
    out = pd.Series(np.nan, index=loc.index)
    fixed = loc["segment"].map(ENVELOPE_FIXED)
    out[fixed.notna()] = fixed[fixed.notna()]
    for d, a in ENVELOPE_DISTRICT_ALL.items():
        m = loc["district"] == d
        E = loc.loc[m, "eligible"]
        fm = m & fixed.notna()
        rest = m & fixed.isna()
        if rest.any():
            ra = (a * E.sum() - (loc.loc[fm, "eligible"] * fixed[fm]).sum()) / \
                loc.loc[rest, "eligible"].sum()
            out[rest] = max(ra, 0.0)
    out = out.fillna(0.068)
    scale = ENVELOPES_2022 / (out * loc["eligible"]).sum()
    return out * scale


def gotv_lift_v(p):
    return gotv_lift(np.clip(p, 0.05, 0.97))


def unit_values(comp: pd.DataFrame, p_act: np.ndarray, p_hump: np.ndarray,
                openness: np.ndarray, per_vote: pd.Series, soft: dict,
                lists: list, pers_mult) -> dict:
    """Per completed conversation, for a set of units (localities or
    stations): the value of an AREA conversation (a resident of the unit
    picked at random: turnout + persuasion + rescue in one conversation),
    and of LIST conversations with identified supporters, soft Netanyahu-
    bloc voters and sub-threshold-list voters. Values in objective units."""
    nb_lists = [l for l in lists if LIST_CAMP[l] == "nb"]
    un_lists = [l for l in lists if LIST_CAMP[l] == "un"]
    pv = per_vote.reindex(lists).fillna(0)
    p = np.clip(p_act, 0.05, 0.97)
    dp = gotv_lift_v(p_hump)
    v_mob = comp[lists].values @ pv.values
    chs = comp[CHANGE_LISTS].sum(axis=1)
    ch_mix = comp[CHANGE_LISTS].div(chs.replace(0, np.nan), axis=0).fillna(0.25)
    v_change = ch_mix.values @ pv.reindex(CHANGE_LISTS).values
    soft_nb = sum(comp[l] * soft[l] for l in nb_lists)
    src_nb = (sum(comp[l] * soft[l] * pv[l] for l in nb_lists)
              / soft_nb.replace(0, np.nan)).fillna(0).values
    pers_share = np.clip(soft_nb.values * CROSS_PRESSURE * openness * pers_mult, 0, 0.25)
    mv_alt = pv["Likud"]
    gain_p = RHO_PERSUADE * (v_change - src_nb)
    resc_share = {l: comp[l].values for l in un_lists}
    gain_r = {l: RHO_RESCUE * (RESCUE_TO_CHANGE * v_change
                               + (1 - RESCUE_TO_CHANGE) * mv_alt - pv[l]) for l in un_lists}
    area_g = dp * v_mob
    area_p = pers_share * p * gain_p
    area_r = sum(resc_share[l] * p * gain_r[l] for l in un_lists)
    dp_sup = gotv_lift_v(np.minimum(0.95, p_hump + SUPPORTER_PROPENSITY_GAP))
    if not DOOR_RESCUE:
        area_r = np.zeros_like(area_g)
    # A list persuasion call goes to an identified SOFT Netanyahu-bloc voter.
    # Per call it switches the same share as a door conversation with a soft
    # voter there: 0.3% x openness x segment multiplier (respecting the cap).
    rho_soft = RHO_PERSUADE * pers_share / np.where(soft_nb.values > 0, soft_nb.values, np.inf)
    return {
        "area_g": area_g, "area_p": area_p, "area_r": area_r,
        "area": area_g + area_p + area_r,
        # list conversations (value per contact with an identified person)
        "list_sup": dp_sup * v_change,
        "list_pers": rho_soft * (v_change - src_nb)
        + (1 - rho_soft) * PERSUASION_TURNOUT_SIDE * dp * src_nb,
        "pers_list_share": soft_nb.values,
        "list_resc": gain_r, "resc_share": resc_share,
        "dp": dp, "pers_share": pers_share, "v_mob": v_mob, "p": p,
        "ch_share": chs.values,
    }


def score(meta, cw, panel, mv, shares):
    from bayes_model import CERTAINTY

    pool_locs = set(meta.loc[meta["segment"] == "druze", "locality"])
    proj, G, trans = project_2026(panel, shares, pool_locs)
    lists = list(proj.columns)
    nb_lists = [l for l in lists if LIST_CAMP[l] == "nb"]
    un_lists = [l for l in lists if LIST_CAMP[l] == "un"]
    ar_lists = [l for l in lists if LIST_CAMP[l] == "ar"]
    l22 = cw[cw.cycle == "2022"].set_index("locality")
    loc = meta.set_index("locality").join(
        l22[["eligible", "voters", "valid", "c_C", "c_R", "c_A", "c_O"]],
        how="inner")
    loc = loc[loc["eligible"] > 0]
    proj = proj.reindex(loc.index).fillna(0)
    def shift_change_to_nb(df: pd.DataFrame, rows) -> None:
        """Sensitivity only: move DRUZE_SHIFT of the vote from change lists
        to Netanyahu-bloc lists, proportionally, in the given rows."""
        chs = df.loc[rows, CHANGE_LISTS].sum(axis=1)
        take = np.minimum(chs, DRUZE_SHIFT)
        df.loc[rows, CHANGE_LISTS] = df.loc[rows, CHANGE_LISTS].mul(
            (1 - take / chs.replace(0, np.nan)).fillna(1), axis=0)
        nbs = df.loc[rows, nb_lists].sum(axis=1).replace(0, np.nan)
        df.loc[rows, nb_lists] = df.loc[rows, nb_lists] + df.loc[rows, nb_lists].div(
            nbs, axis=0).fillna(0).mul(take, axis=0)

    if DRUZE_SHIFT:
        shift_change_to_nb(proj, loc.index[loc["segment"] == "druze"])

    # ---- turnout history (regular stations)
    th = cw.pivot_table(index="locality", columns="cycle", values="turnout").clip(upper=1)
    nat_t = cw.groupby("cycle").apply(lambda d: d.voters.sum() / d.eligible.sum())
    for c in ["2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]:
        loc[f"turnout_{c}"] = th[c].reindex(loc.index)
    rel = th / nat_t
    best_rel = rel[["2015", "2019s", "2020", "2021"]].max(axis=1)
    loc["turnout_ceiling"] = (best_rel * nat_t["2022"]).clip(upper=1).reindex(loc.index)
    loc["lapsed_rate"] = (loc["turnout_ceiling"] - loc["turnout_2022"]).clip(lower=0)
    p21 = panel[panel.cycle == "2021"].pivot_table(index="locality", columns="party",
                                                   values="votes", aggfunc="sum", fill_value=0)
    loc["change_abstained_est"] = sum(p21.get(k, 0) * r for k, r in ABSTAIN_21_22.items()) \
        .reindex(loc.index).fillna(0) if len(p21) else 0
    loc["roll_abroad"] = loc["segment"].map(ROLL_ABROAD_BY_SEGMENT).fillna(ROLL_ABROAD)
    jew = ~loc["segment"].str.startswith("arab") & (loc["segment"] != "druze")
    seg_med = loc[loc["eligible"] >= 2000].groupby("segment")["turnout_2022"].median()
    gap = (loc["segment"].map(seg_med) - loc["turnout_2022"] - PHANTOM_SLACK).clip(lower=0)
    loc["phantom_roll"] = np.where(jew & (loc["eligible"] >= 2000), PHANTOM_SHARE * gap, 0.0)
    loc["roll_abroad"] = (loc["roll_abroad"] + loc["phantom_roll"]).clip(upper=0.45)
    loc["envelope_addback"] = envelope_addback(loc)
    loc["turnout_resident"] = ((loc["turnout_2022"] + loc["envelope_addback"])
                               / (1 - loc["roll_abroad"])).clip(upper=0.97)
    loc["conv_per_hour"] = loc["settlement_type"].map(CONVERSATIONS_PER_HOUR).fillna(3.0)
    dense = (loc["settlement_type"].isin(["jewish_urban", "arab_urban"])
             & (loc["pop_density"] >= 5000))
    loc.loc[dense, "conv_per_hour"] = DENSE_CONV_PER_HOUR
    g = loc["segment"].map(GROWTH_BY_SEGMENT).fillna(GROWTH_DEFAULT)
    g = g * ELIGIBLE_2026 / (loc["eligible"] * g).sum()
    loc["eligible_2026_est"] = loc["eligible"] * g
    w_ = loc["valid"] * g
    loc["voters_2026_est"] = w_ * (4_823_026 * REGULAR_SHARE_2022 / w_.sum())
    bf = border_flags(loc)
    loc = loc.join(bf)
    loc["displaced"] = np.where(loc["km_lebanon"] <= LEBANON_KM, "Lebanon border",
                                np.where(loc["km_gaza"] <= GAZA_KM, "Gaza border", ""))
    loc["field_excluded"] = [FIELD_EXCLUDED.get(i, "") for i in loc.index]
    loc["low_confidence"] = np.where(
        loc.index.isin(CIRCASSIAN), "Circassian vote depends on 2026 list candidates",
        np.where(loc["segment"] == "druze", "Druze vote depends on 2026 list candidates", ""))
    cap_mult = np.where(loc["displaced"] != "", DISPLACED_CAPACITY, 1.0) * \
        np.where(loc["field_excluded"] != "", 0.0, 1.0)
    loc["capacity_mult"] = cap_mult

    # ---- marginal-voter composition test (naive kept unless validated)
    segdf = loc.reset_index()[["locality", "segment"]]
    comp_val = validate_composition(cw, segdf)
    kslopes = composition_slopes(cw, segdf, COMP_TRANSITIONS)
    theta = (theta_table(kslopes) if comp_val["chosen"] == "multiplicative"
             or FORCE_COMPOSITION == "multiplicative" else None)
    camp_hist = {"ch": "C", "nb": "R", "ar": "A", "un": "C", "ot": "O"}
    list_hist = {l: camp_hist[LIST_CAMP[l]] for l in lists}

    def marginal_lists(comp: pd.DataFrame, segs) -> pd.DataFrame:
        s_ = comp.T.groupby(pd.Series(list_hist)).sum().T
        for c in ["C", "R", "A", "O"]:
            if c not in s_:
                s_[c] = 0.0
        m = tilt_camps(s_[["C", "R", "A", "O"]], np.asarray(segs), theta)
        ratio = (m / s_[["C", "R", "A", "O"]].replace(0, np.nan)).fillna(1.0)
        out = comp.copy()
        for l in lists:
            out[l] = comp[l] * ratio[list_hist[l]].values
        return out.div(out.sum(axis=1), axis=0)

    # ---- openness
    w_open, val_open = fit_openness(cw, segdf)
    feats = openness_features(cw, "2022", segdf).reindex(loc.index)
    Z = feats[["vol", "footprint", "balance"]].apply(
        lambda x: (x - x.mean()) / x.std()).fillna(0)
    lin = sum(w * Z[f] for f, w in w_open.items())
    lin = lin / lin.std()
    loc["openness"] = np.clip(np.exp(0.30 * lin), 0.4, 2.5)
    loc["openness"] = loc["openness"] / wavg(loc["openness"], loc["valid"])
    for c in ["vol", "footprint", "balance"]:
        loc[f"feat_{c}"] = feats[c]
    loc["pers_mult"] = loc["segment"].map(PERSUASION_SEGMENT_MULT).fillna(1.0)
    soft = {l: 1 - CERTAINTY.get(LIST_ID[l].split("+")[0], 0.5) for l in lists}
    soft["Bennett 2026 + Yesh Atid"] = 1 - CERTAINTY["bennett_2026"]
    soft["Balad + Hadash-Ta'al"] = 1 - CERTAINTY["hadash_taal"]

    # ---- stations
    kal = kalpi_lineage_2022()
    kal = kal[kal["locality"].isin(loc.index)].reset_index(drop=True)
    kproj = project_kalpi(kal, proj)
    if DRUZE_SHIFT:
        shift_change_to_nb(kproj, kproj.index[kal["locality"].isin(
            loc.index[loc["segment"] == "druze"]).values])
    kseg = loc["segment"].reindex(kal["locality"]).values
    # stations where Arab lists lead, outside Arab localities (mixed cities,
    # Jerusalem, mixed Druze towns): no change-bloc field programme there
    k_ar = kproj[ar_lists].sum(axis=1).values
    arab_led = ((k_ar >= np.maximum(kproj[CHANGE_LISTS].sum(axis=1).values,
                                    kproj[nb_lists].sum(axis=1).values))
                & ~pd.Series(kseg).astype(str).str.startswith("arab").values)
    kmarg = marginal_lists(kproj, kseg)
    marg = marginal_lists(proj, loc["segment"].values)
    lk = lambda c: loc[c].reindex(kal["locality"]).values
    k_reg = (kal["voters"] / kal["eligible"]).clip(0, 1).values
    k_abroad = lk("roll_abroad")
    k_res = np.clip((k_reg + lk("envelope_addback")) / (1 - k_abroad), 0.03, 0.97)
    # phantom-registrant guard: a station far below its locality's turnout is
    # more likely stale roll than mobilisable abstainers
    k_hump = np.maximum(k_res, lk("turnout_resident") - 0.12)
    k_g = lk("eligible_2026_est") / lk("eligible")
    k_pool = kal["eligible"].values * k_g * (1 - k_abroad) * lk("capacity_mult")
    k_cap = k_pool * CONTACT_CAP
    l_pool = loc["eligible_2026_est"] * (1 - loc["roll_abroad"]) * loc["capacity_mult"]

    mvx = mv.set_index("list")
    nat_w = proj[CHANGE_LISTS].mul(loc["valid"], axis=0).sum()
    mv_ref = {o: float(np.average(mvx[o].reindex(CHANGE_LISTS).values,
                                  weights=nat_w.values)) / 1e4 for o in OBJECTIVES}

    kal_out = kal[["locality", "kalpi", "eligible", "voters", "valid"]].copy()
    kal_out["turnout"] = k_reg
    kal_out["turnout_resident"] = k_res
    kal_out["p26_change"] = kproj[CHANGE_LISTS].sum(axis=1).values
    kal_out["p26_nb"] = kproj[nb_lists].sum(axis=1).values
    kal_out["p26_arab"] = kproj[ar_lists].sum(axis=1).values
    kal_out["p26_unaligned"] = kproj[un_lists].sum(axis=1).values
    short_ch = {l: SHORT[l] for l in CHANGE_LISTS}
    lead = kproj[CHANGE_LISTS].idxmax(axis=1).map(short_ch)
    kal_out["lead_change_list"] = lead.values
    kal_out["p26_yb"] = kproj["Yisrael Beytenu"].values
    kal_out["arab_led"] = arab_led

    planner = {}
    for obj in OBJECTIVES:
        pv = mvx[obj].reindex(lists).fillna(0) / 1e4
        ref = mv_ref[obj]
        kv = unit_values(kproj, k_res, k_hump, lk("openness"), pv, soft, lists,
                         lk("pers_mult"))
        kv["area_g"] = (kmarg[lists].values @ pv.values) * kv["dp"]   # tilt if any
        kv["area"] = kv["area_g"] + kv["area_p"] + kv["area_r"]
        to_ve = 1000 / ref
        kal_out[f"{obj}__area_ve1k"] = kv["area"] * to_ve
        kal_out[f"{obj}__gotv_ve1k"] = kv["area_g"] * to_ve
        kal_out[f"{obj}__pers_ve1k"] = kv["area_p"] * to_ve
        kal_out[f"{obj}__resc_ve1k"] = kv["area_r"] * to_ve
        # door canvass only where one conversation has positive value and
        # Arab lists do not lead (no change-bloc field work among Arab
        # voters, mixed cities included); supporter and persuasion calls only
        # where the area is not canvassed; rescue calls in any station
        pos = (kv["area"] > 0) & ~arab_led
        neg = ~pos & ~arab_led
        n_sup = k_pool * kv["ch_share"]
        n_pers = k_pool * kv["p"] * kv["pers_list_share"]
        LR = LIST_IDENTIFIED * LIST_CONTACT
        lsup = np.where(neg & (kv["list_sup"] > 0), kv["list_sup"], 0) * LR * n_sup
        lpers = np.where(neg & (kv["list_pers"] > 0), kv["list_pers"], 0) * LR * n_pers
        lresc = np.zeros(len(kal))
        c_resc = np.zeros(len(kal))
        rv = np.zeros(len(kal)); rc = np.zeros(len(kal))
        for l in un_lists:
            n_r = k_pool * kv["p"] * kv["resc_share"][l]
            ok = ~arab_led & (kv["list_resc"][l] > 0)
            val = np.where(ok, kv["list_resc"][l], 0)
            lresc += val * LR * n_r
            c_resc += np.where(ok, LR * n_r, 0)
            rv += val * to_ve * LIST_CONTACT * n_r
            rc += np.where(ok, LIST_CONTACT * n_r, 0)
        if not LIST_PROGRAMMES:
            lsup[:] = 0; lpers[:] = 0; lresc[:] = 0; c_resc[:] = 0
        c_sup = np.where(lsup > 0, LR * n_sup, 0)
        c_pers = np.where(lpers > 0, LR * n_pers, 0)
        a = pd.DataFrame({
            "locality": kal["locality"].values,
            "area_g": np.where(pos, kv["area_g"], 0) * k_cap,
            "area_p": np.where(pos, kv["area_p"], 0) * k_cap,
            "area_r": np.where(pos, kv["area_r"], 0) * k_cap,
            "area_c": np.where(pos, k_cap, 0),
            "list_sup": lsup, "list_pers": lpers, "list_resc": lresc,
            "c_sup": c_sup, "c_pers": c_pers, "c_resc": c_resc,
            "neg_elig": kal["eligible"].values * (~pos & ~arab_led),
            "elig_na": kal["eligible"].values * ~arab_led,
            # 'every door' rate over the stations the atlas covers
            "avg_v": np.where(~arab_led, k_pool * kv["area"], 0),
            "avg_w": np.where(~arab_led, k_pool, 0)}).groupby("locality").sum()
        a = a.reindex(loc.index).fillna(0)
        for c in ["area_g", "area_p", "area_r", "list_sup", "list_pers", "list_resc"]:
            a[c] = a[c] / ref
        loc[f"{obj}__area_pot"] = a["area_g"] + a["area_p"] + a["area_r"]
        loc[f"{obj}__list_pot"] = a["list_sup"] + a["list_pers"] + a["list_resc"]
        loc[f"{obj}__gotv_pot"] = a["area_g"] + a["list_sup"]
        loc[f"{obj}__pers_pot"] = a["area_p"] + a["list_pers"]
        loc[f"{obj}__resc_pot"] = a["area_r"] + a["list_resc"]
        loc[f"{obj}__potential"] = loc[f"{obj}__area_pot"] + loc[f"{obj}__list_pot"]
        loc[f"{obj}__area_contacts"] = a["area_c"]
        loc[f"{obj}__list_contacts"] = a["c_sup"] + a["c_pers"] + a["c_resc"]
        tc = a["area_c"] + loc[f"{obj}__list_contacts"]
        loc[f"{obj}__eff1k"] = (loc[f"{obj}__potential"] / tc.replace(0, np.nan) * 1000).fillna(0)
        loc[f"{obj}__area_eff1k"] = (loc[f"{obj}__area_pot"] / a["area_c"].replace(0, np.nan)
                                     * 1000).fillna(0)
        loc[f"{obj}__list_eff1k"] = (loc[f"{obj}__list_pot"] / loc[f"{obj}__list_contacts"]
                                     .replace(0, np.nan) * 1000).fillna(0)
        loc[f"{obj}__per100h"] = loc[f"{obj}__area_eff1k"] / 1000 * loc["conv_per_hour"] * 100
        loc[f"{obj}__neg_share"] = (a["neg_elig"] / a["elig_na"].replace(0, np.nan)).fillna(0)
        # untargeted: one conversation with a random resident of the stations
        # the atlas covers (stations where Arab lists lead are left out)
        loc[f"{obj}__area_avg_ve1k"] = (a["avg_v"] / a["avg_w"].replace(0, np.nan) * to_ve).fillna(0)
        # planner tranches: area by station value; list programmes by value
        if obj in ("change_govt", "block_nb", "change_seats"):
            planner[obj] = {"area": (kal["locality"].values, kv["area"] * to_ve,
                                     np.where(pos, k_cap, 0)),
                            "sup": (kal["locality"].values, kv["list_sup"] * to_ve,
                                    np.where(neg, LIST_CONTACT * n_sup, 0)),
                            "pers": (kal["locality"].values, kv["list_pers"] * to_ve,
                                     np.where(neg, LIST_CONTACT * n_pers, 0))}
            planner[obj]["resc"] = (kal["locality"].values,
                                    np.where(rc > 0, rv / np.maximum(rc, 1e-9), 0), rc)

    # ---- objective-free metrics (net change-minus-NB votes)
    vote_pv = pd.Series({l: (1.0 if LIST_CAMP[l] == "ch" else -1.0 if LIST_CAMP[l] == "nb"
                             else 0.0) for l in lists})
    uvv = unit_values(proj, loc["turnout_resident"].values, loc["turnout_resident"].values,
                      loc["openness"].values, vote_pv, soft, lists, loc["pers_mult"].values)
    loc["gotv_lift_pp"] = uvv["dp"] * 100
    loc["persuadable_share"] = uvv["pers_share"]
    loc["rescue_share"] = sum(uvv["resc_share"].values())
    loc["rescue_bw_share"] = uvv["resc_share"].get("Blue and White", 0)
    loc["rescue_res_share"] = uvv["resc_share"].get("Reservists – Economic Party", 0)
    loc["persuadable_voters"] = loc["persuadable_share"] * loc["voters_2026_est"]
    loc["rescue_voters"] = loc["rescue_share"] * loc["voters_2026_est"]
    loc["change_supporters"] = proj[CHANGE_LISTS].sum(axis=1) * loc["voters_2026_est"]
    loc["net_change_per1k_gotv_avg"] = uvv["dp"] * (marg[lists].values @ vote_pv.values) * 1000
    kvv = unit_values(kproj, k_res, k_hump, lk("openness"), vote_pv, soft, lists, lk("pers_mult"))
    kg = kvv["dp"] * (kmarg[lists].values @ vote_pv.values)
    kal_out["net_change_gotv_1k"] = kg * 1000
    kal_out["persuadable_share"] = kvv["pers_share"]
    ag = pd.DataFrame({"locality": kal["locality"].values, "v": np.maximum(kg, 0) * k_cap,
                       "c": k_cap * (kg > 0)}).groupby("locality").sum()
    loc["net_change_votes_gotv_turf"] = ag["v"].reindex(loc.index).fillna(0)
    loc["net_change_per1k_gotv_turf"] = (ag["v"] / ag["c"].replace(0, np.nan)
                                         * 1000).reindex(loc.index).fillna(0)
    loc["n_kalpiot"] = kal.groupby("locality").size().reindex(loc.index).fillna(0)
    for l in lists:
        loc[f"p26_{SHORT[l]}"] = proj[l]
    loc["p26_change"] = proj[CHANGE_LISTS].sum(axis=1)
    loc["p26_nb"] = proj[nb_lists].sum(axis=1)
    loc["p26_arab"] = proj[ar_lists].sum(axis=1)
    loc["p26_unaligned"] = proj[un_lists].sum(axis=1)
    loc["lead_change_list"] = proj[CHANGE_LISTS].idxmax(axis=1).map(short_ch)
    second = proj[CHANGE_LISTS].apply(lambda r: r.sort_values(ascending=False).index[1], axis=1)
    loc["second_change_list"] = second.map(short_ch)
    for c in ["C", "R", "A"]:
        loc[f"s22_{c}"] = loc[f"c_{c}"] / loc["valid"]
    meta_out = {"mv_ref_per_vote": mv_ref, "composition": comp_val,
                "openness": val_open, "theta": None if theta is None else
                {f"{a}|{b}": round(float(v), 3) for (a, b), v in theta.items()},
                "flow_matrix": trans.round(4).to_dict()}
    return loc, kal_out, kslopes, meta_out, planner


TIER_NAMES = ["Turnout engine", "Supporter-list ground", "Persuasion battleground",
              "Secondary target",
              "Arab-list turf (partner-led)", "Netanyahu-bloc stronghold",
              "Low yield", "Not targeted (access)"]


def assign_tiers(loc: pd.DataFrame, obj: str = "change_govt") -> pd.Series:
    pot = loc[f"{obj}__potential"]
    eff = loc[f"{obj}__eff1k"]
    g = loc[f"{obj}__gotv_pot"]
    pp_ = loc[f"{obj}__pers_pot"]
    rr = loc[f"{obj}__resc_pot"]
    sizeable = (loc["eligible"] >= 2000) & (loc["field_excluded"] == "")
    elig = ~loc["segment"].str.startswith("arab")
    pot_hi = pot[sizeable & elig].quantile(0.85)
    pot_mid = pot[sizeable & elig].quantile(0.50)
    # efficiency only counts where there is a real programme to run
    contacts = loc[f"{obj}__area_contacts"] + loc[f"{obj}__list_contacts"]
    real = sizeable & elig & (contacts >= 1000) & (pot >= max(pot_mid, 2.0))
    eff_hi = eff[real].quantile(0.85)
    out = []
    for i in loc.index:
        if loc.at[i, "field_excluded"]:
            out.append("Not targeted (access)")
        elif loc.at[i, "segment"].startswith("arab"):
            out.append("Arab-list turf (partner-led)")
        elif real[i] and (pot[i] >= pot_hi or eff[i] >= eff_hi):
            if pp_[i] > max(g[i], rr[i]):
                out.append("Persuasion battleground")
            elif loc.at[i, f"{obj}__list_pot"] > loc.at[i, f"{obj}__area_pot"]:
                out.append("Supporter-list ground")
            else:
                out.append("Turnout engine")
        elif loc.at[i, "p26_nb"] >= 0.70 and loc.at[i, f"{obj}__neg_share"] > 0.8:
            out.append("Netanyahu-bloc stronghold")
        elif pot[i] >= pot_mid:
            out.append("Secondary target")
        else:
            out.append("Low yield")
    return pd.Series(out, index=loc.index)


def segment_summary(loc: pd.DataFrame) -> pd.DataFrame:
    g = loc.groupby("segment")
    s = pd.DataFrame({
        "label": g["segment_label"].first(),
        "localities": g.size(),
        "eligible": g["eligible"].sum(),
        "turnout_2022": g.apply(lambda d: d.voters.sum() / d.eligible.sum()),
        "s22_C": g.apply(lambda d: d.c_C.sum() / d.valid.sum()),
        "s22_R": g.apply(lambda d: d.c_R.sum() / d.valid.sum()),
        "s22_A": g.apply(lambda d: d.c_A.sum() / d.valid.sum()),
        "p26_change": g.apply(lambda d: wavg(d.p26_change, d.valid)),
        "p26_nb": g.apply(lambda d: wavg(d.p26_nb, d.valid)),
        "p26_arab": g.apply(lambda d: wavg(d.p26_arab, d.valid)),
        "persuadable_voters": g["persuadable_voters"].sum(),
        "rescue_voters": g["rescue_voters"].sum(),
        "change_abstained_est": g["change_abstained_est"].sum(),
        "openness": g.apply(lambda d: wavg(d.openness, d.valid)),
    })
    for obj in OBJECTIVES:
        for part in ("gotv_pot", "pers_pot", "resc_pot", "area_pot", "list_pot", "potential"):
            s[f"{obj}__{part}"] = g[f"{obj}__{part}"].sum()
        s[f"{obj}__share"] = s[f"{obj}__potential"] / s[f"{obj}__potential"].sum()
    return s.reset_index()


def backtest_holdout(panel: pd.DataFrame, seeds=(1, 2, 3)) -> dict:
    """A real held-out test of the allocation assumption (one transfer rate
    per party pair, applied everywhere): fit the transfer matrix by
    non-negative least squares on a random half of localities, project the
    other half from its own earlier vote, rake to that half's true list
    totals, and score camp shares. Uniform camp swing gets the same totals."""
    from scipy.optimize import nnls
    out = {}
    for a, b in [("2020", "2021"), ("2021", "2022")]:
        A = panel[panel.cycle == a].pivot_table(index="locality", columns="party",
                                                values="votes", aggfunc="sum", fill_value=0)
        B = panel[panel.cycle == b].pivot_table(index="locality", columns="party",
                                                values="votes", aggfunc="sum", fill_value=0)
        idx = A.index.intersection(B.index)
        A, B = A.loc[idx], B.loc[idx]
        keep = B.sum(axis=1) >= 200
        A, B = A[keep], B[keep]
        camp_b = {p: camp_of(b, p, panel[(panel.cycle == b) & (panel.party == p)]["family"].iloc[0])
                  for p in B.columns}
        camp_a = {p: camp_of(a, p, panel[(panel.cycle == a) & (panel.party == p)]["family"].iloc[0])
                  for p in A.columns}
        res = {"transfer": {"C": [], "R": [], "A": []}, "uniform": {"C": [], "R": [], "A": []},
               "blend": {"C": [], "R": [], "A": []}}
        for sd in seeds:
            rng = np.random.default_rng(sd)
            tr = rng.random(len(A)) < 0.5
            Xa, Xb = A.values.astype(float), B.values.astype(float)
            Tm = np.zeros((Xa.shape[1], Xb.shape[1]))
            for j in range(Xb.shape[1]):
                Tm[:, j], _ = nnls(Xa[tr], Xb[tr, j])
            te = ~tr
            P = Xa[te] @ Tm
            rows = Xb[te].sum(axis=1)
            P = P * rows[:, None] / np.maximum(P.sum(axis=1, keepdims=True), 1e-9)
            P = ipf(P, rows, Xb[te].sum(axis=0))
            true = Xb[te] / rows[:, None]
            pred = P / rows[:, None]
            w = rows
            sa = A.values[te] / A.values[te].sum(axis=1, keepdims=True)
            for c in ["C", "R", "A"]:
                cb = [k for k, p in enumerate(B.columns) if camp_b[p] == c]
                ca = [k for k, p in enumerate(A.columns) if camp_a[p] == c]
                t_c, p_c = true[:, cb].sum(1), pred[:, cb].sum(1)
                a_c = sa[:, ca].sum(1)
                nat_b = np.average(t_c, weights=w)
                nat_a = np.average(a_c, weights=w)
                u_c = a_c + (nat_b - nat_a)
                res["transfer"][c].append(wavg(np.abs(p_c - t_c), w) * 100)
                res["uniform"][c].append(wavg(np.abs(u_c - t_c), w) * 100)
                res["blend"][c].append(wavg(np.abs(0.5 * (p_c + u_c) - t_c), w) * 100)
        out[f"{a}->{b}"] = {m: {c: round(float(np.mean(v)), 2) for c, v in d.items()}
                            for m, d in res.items()}
    out["note"] = ("Transfer matrix fitted by NNLS on a random half of localities and "
                   "scored on the other half (3 splits); both methods are given the "
                   "held-out half's true national totals.")
    return out


def main() -> None:
    panel, lc, meta, nat, mv, shares = load()
    cw = camp_wide(panel, lc)
    seg = assign_segments(meta, cw, panel)
    loc, kal, kslopes, mmeta, planner = score(seg, cw, panel, mv, shares)
    for obj in OBJECTIVES:
        loc[f"{obj}__tier"] = assign_tiers(loc, obj)
        loc[f"{obj}__rank"] = loc[f"{obj}__potential"].rank(
            ascending=False, method="first").astype(int)
    loc["tier"] = loc["change_govt__tier"]
    loc["tier_block"] = loc["block_nb__tier"]
    pct = lambda s_: (s_.rank(pct=True) * 100).round(0)
    loc["swing_index"] = pct(loc["persuadable_share"] + loc["rescue_share"])
    loc["turnout_index"] = pct(loc["net_change_per1k_gotv_turf"])
    loc["rescue_index"] = pct(loc["rescue_share"])
    loc["impact_index"] = pct(loc["change_govt__potential"])

    val = {"projection_in_sample_2021_2022": backtest_projection(panel),
           "projection_holdout": backtest_holdout(panel),
           "projection_method": {
               "camp_blend": CAMP_BLEND, "druze_pool": DRUZE_POOL,
               "note": ("Lists projected by the coherent 2022->2026 flow matrix, then each "
                        "locality's camp totals pulled halfway toward uniform camp swing "
                        "(lists scaled within camp), then raked to the forecast. The 50/50 "
                        "blend had the lowest or near-lowest held-out error in both folds; "
                        "pure transfer failed badly in 2020->21 (C 2.5 pts) and pure swing "
                        "in 2021->22 (A 1.2 pts).")},
           "openness_out_of_sample": mmeta["openness"],
           "composition_out_of_sample": mmeta["composition"],
           "theta": mmeta["theta"],
           "mv_ref_per_vote": mmeta["mv_ref_per_vote"]}
    kslopes.to_csv(OUT / "composition_slopes.csv", index=False)
    loc.reset_index().to_csv(OUT / "localities.csv", index=False)
    big = loc[loc["n_kalpiot"] >= 8].index
    kal[kal["locality"].isin(big)].to_csv(OUT / "kalpi.csv", index=False)
    kal.to_parquet(OUT / "kalpi_all.parquet")
    cw[["cycle", "locality", "eligible", "voters", "valid", "c_C", "c_R",
        "c_A", "c_O", "turnout"]].to_parquet(OUT / "camp_history.parquet")
    segment_summary(loc).to_csv(OUT / "segments.csv", index=False)
    (OUT / "flow_matrix.json").write_text(json.dumps(mmeta["flow_matrix"], ensure_ascii=False))
    import pickle
    with open(OUT / "planner_units.pkl", "wb") as fh:
        pickle.dump(planner, fh)
    (OUT / "validation.json").write_text(json.dumps(val, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in val.items() if k not in ("theta",)},
                     indent=1, ensure_ascii=False)[:3000])
    cols = ["name_he", "segment", "eligible", "p26_change", "p26_nb",
            "change_govt__area_pot", "change_govt__list_pot", "change_govt__gotv_pot",
            "change_govt__pers_pot", "change_govt__resc_pot", "change_govt__potential",
            "change_govt__eff1k", "change_govt__per100h", "tier"]
    pd.set_option("display.width", 260)
    ranked = loc[loc.eligible >= 1000]
    print(ranked.sort_values("change_govt__potential", ascending=False)[cols].head(30).round(2).to_string())
    print(ranked.sort_values("change_govt__per100h", ascending=False)[cols].head(12).round(2).to_string())
    for o in ("change_govt", "block_nb", "change_seats"):
        print(o, {p: round(loc[f"{o}__{p}"].sum()) for p in
                  ("area_pot", "list_pot", "gotv_pot", "pers_pot", "resc_pot", "potential",
                   "area_contacts", "list_contacts")})
    print(loc["tier"].value_counts())
    print(loc["tier_block"].value_counts())


if __name__ == "__main__":
    main()
