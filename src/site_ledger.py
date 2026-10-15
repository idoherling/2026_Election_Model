"""Site payloads for the poll ledger and the pollster ratings.

ledger   every 2026-cycle poll: date, firm, publisher, sample size, seats
         per list, the firm's posterior precision weight, its CEC legal
         filing (gov.il blob) and the publication the polling archive
         cites for it — resolved from the cached Wikipedia page rows the
         scraper recorded as source_row (page:table:row).
ratings  per firm: institutional facts (pollster_meta.csv), cycles graded,
         final-poll error and final-month error against the official
         result (polls.csv x results.csv), Netanyahu-bloc lean per cycle
         (house_effects_blocs.csv), 2026 activity and model weight.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import lxml.html
import numpy as np
import pandas as pd
import requests

from normalize import load_party_registry
from scrape_cec import BLOB, DATA as CEC_DATA
from scrape_polls import PAGES, POLL_SECTION, PROCESSED_DIR, RAW_DIR, clean_text, poll_tables

ELECTION_DAY = {"2009": "2009-02-10", "2013": "2013-01-22", "2015": "2015-03-17",
                "2019a": "2019-04-09", "2019s": "2019-09-17", "2020": "2020-03-02",
                "2021": "2021-03-23", "2022": "2022-11-01"}
# Official results. The old bechirot.gov.il/election/Pages/AllElectionResults.aspx
# page is dead (302 to a gov.il "page not found", checked 14 Oct 2026). The
# CEC's per-Knesset results sites answer for the 21st-25th Knessets
# (votes21..votes25, HTTP 200 on 14 Oct 2026); votes18-20 do not, so 2009,
# 2013 and 2015 link the CEC's official results dataset on data.gov.il.
CEC_RESULTS = "https://data.gov.il/he/datasets/central-election-committee/votes-knesset"
CEC_RESULTS_CYCLE = {"2019a": "https://votes21.bechirot.gov.il/",
                     "2019s": "https://votes22.bechirot.gov.il/",
                     "2020": "https://votes23.bechirot.gov.il/",
                     "2021": "https://votes24.bechirot.gov.il/",
                     "2022": "https://votes25.bechirot.gov.il/"}
COMPOSITE_NAMES = {"Bennett 2026 + Yesh Atid": "together",
                   "Balad + Hadash-Ta'al": "balad+hadash_taal"}


def _note_bodies(doc) -> dict:
    """cite_note id -> first external URL in the note (Parsoid or classic)."""
    out = {}
    for el in doc.iter("span", "li"):
        i = el.get("id") or ""
        m = re.match(r"(?:mw-reference-text-)?(cite_note-.+)", i)
        if not m:
            continue
        for a in el.iter("a"):
            h = a.get("href") or ""
            # skip the cite template's author / wikilinks (Parsoid renders
            # them as absolute en.wikipedia.org URLs ahead of the |url=)
            if (h.startswith("http") and "wikipedia.org" not in h
                    and "mw:WikiLink" not in (a.get("rel") or "")):
                out.setdefault(m.group(1), h)
                break
    return out


def section_anchors() -> dict:
    """page_key:table_index -> the archive section that holds the table
    (its heading id), so a poll with no usable citation can still link its
    own place in the archive instead of the page top."""
    out = {}
    for page_key in [k for k in PAGES if k.startswith("2026")]:
        path = RAW_DIR / f"{page_key}.html"
        if not path.exists():
            continue
        html = path.read_text()
        doc = lxml.html.fromstring(html)
        # the same walk as scrape_polls.poll_tables, so table indices agree
        heading, heading_id, ti = None, None, 0
        for el in doc.iter():
            if el.tag in ("h2", "h3"):
                heading = clean_text(el.text_content())
                heading_id = el.get("id")
            elif el.tag == "table" and "wikitable" in (el.get("class") or ""):
                if heading and POLL_SECTION.match(heading):
                    if heading_id:
                        # The per-year archive pages were restructured after
                        # the cache was taken: the live 2024 page's year
                        # heading (#2024) is gone and its table now sits under
                        # "Polls", as on the 2025 and 2022-2023 pages (live
                        # section ids checked 15 Oct 2026). A bare-year id on
                        # a per-year page falls back to that stable heading.
                        if page_key != "2026_main" and re.fullmatch(r"\d{4}(_\d+)?", heading_id):
                            heading_id = "Polls"
                        out[f"{page_key}:{ti}"] = heading_id
                    ti += 1
    return out


# A cited URL that the archive attaches to two different surveys can be
# right for at most one of them. Owners verified by publication date
# (14 Oct 2026 audit); any other URL shared by two surveys is dropped and
# those rows fall back to their archive section.
SRC_OWNER = {
    "https://www.israelhayom.co.il/news/politics/article/21444759": "2026_20260917_kantar",  # published 2026-09-17
    "https://www.maariv.co.il/news/politics/article-1254155": "2026_20251120_lazar",  # published 2025-11-21
    "https://www.mako.co.il/news-politics/2025_q2/Article-2e765d42d380791026.htm": "2026_20250525_midgam",  # published 2025-05-25
    "https://www.youtube.com/watch?v=Kouy2YqVJ90": "2026_20240704_directpolls",  # uploaded 2024-07-04
}
# Channel 16 retired its vod.html player: every such link returns 404
# (checked 14 Oct 2026), and its new player answers 200 for any id, so the
# old ids cannot be mapped. These rows keep their CEC filing and link the
# archive section.
DEAD_SRC = ("ch16.co.il/vod.html",)
# Polls.csv publisher -> the CEC filing's publisher (Hebrew, substring)
PUB_HE = {"Channel 14": "ערוץ 14", "Kan 11": "תאגיד השידור", "Israel Hayom": "ישראל היום",
          "Maariv": "מעריב", "Walla": "וואלה", "HaHadashot 12": "חדשות 12",
          "Channel 13": "ערוץ 13", "Channel 16": "ערוץ 16", "i24 News": "חדשות המזרח התיכון",
          "Zman Yisrael": "זמן ישראל", "Zman Israel": "זמן ישראל"}
# Archive firm name -> the CEC filing's firm name
FIRM_CEC = {"Midgam Project": "Midgam Project & StatNet"}


def fitted_polls(p: pd.DataFrame, asof) -> dict:
    """poll_id -> None if the current fit consumes the survey, else the
    reason it does not. Mirrors bayes_model.prepare_data's poll filters, in
    its order (read-only: the model code is not touched): sums check,
    Unattributed, Ra'am composites, the fit window ("window" before it,
    "after" past its asof), same-day a/b variants
    (keep the configuration with the most list rows), excluded firms."""
    from bayes_model import WINDOW_DAYS, EXCLUDE_POLLSTERS
    why = {}
    for pid, g in p.groupby("poll_id", sort=False):
        if not bool(g["sums_ok"].all()):
            why[pid] = "sums"
        elif g["pollster"].iloc[0] == "Unattributed":
            why[pid] = "unattributed"
        elif g["party_id"].astype(str).str.contains(r"raam.*\+|\+.*raam").any():
            why[pid] = "composite"
    ok = p[~p["poll_id"].isin(set(why))]
    asof = pd.Timestamp(asof) if asof is not None else ok["fieldwork_end"].max()
    # newer than the fit's data date: inside the window, just not fitted yet
    for pid in ok.loc[ok["fieldwork_end"] > asof, "poll_id"].unique():
        why[pid] = "after"
    for pid in ok.loc[ok["fieldwork_end"] <= asof - pd.Timedelta(days=WINDOW_DAYS), "poll_id"].unique():
        why[pid] = "window"
    inwin = (ok["fieldwork_end"] > asof - pd.Timedelta(days=WINDOW_DAYS)) & (ok["fieldwork_end"] <= asof)
    win = ok[inwin]
    rows_per = win.groupby("poll_id").size()
    order = (win.drop_duplicates("poll_id")[["poll_id", "pollster", "fieldwork_end"]]
             .assign(n=lambda d: d["poll_id"].map(rows_per))
             .sort_values(["pollster", "fieldwork_end", "n", "poll_id"],
                          ascending=[True, True, False, True]))
    keep = set(order.drop_duplicates(["pollster", "fieldwork_end"])["poll_id"])
    for pid in set(win["poll_id"]) - keep:
        why[pid] = "variant"
    for pid in win.loc[win["pollster"].isin(EXCLUDE_POLLSTERS), "poll_id"].unique():
        why.setdefault(pid, "excluded")
    out = {pid: why.get(pid) for pid in p["poll_id"].unique()}
    return _late_polls(p, out)


# The mirror above reads polls.csv as it is now. A poll scraped after the
# fit ran (dated on or before its asof) would pass the mirror though the
# fit never saw it. The fit records no poll list, so this module keeps one:
# whenever polls.csv is not newer than the fit's posterior (m3_idata.nc),
# the poll_ids on disk are the fit's input and are snapshotted, keyed by the
# posterior's mtime; when polls.csv is newer, polls absent from the matching
# snapshot are tagged "late" (not yet fitted).
FIT_IDATA = PROCESSED_DIR / "m3_idata.nc"
FIT_POLLS_SNAPSHOT = PROCESSED_DIR / "site_fit_poll_ids.json"


def _late_polls(p: pd.DataFrame, why: dict) -> dict:
    import sys
    polls_csv = PROCESSED_DIR / "polls.csv"
    if not FIT_IDATA.exists() or not polls_csv.exists():
        return why
    fit_t = FIT_IDATA.stat().st_mtime
    if polls_csv.stat().st_mtime <= fit_t:
        FIT_POLLS_SNAPSHOT.write_text(json.dumps(
            {"fit_mtime": fit_t, "poll_ids": sorted(map(str, p["poll_id"].unique()))}))
        return why
    snap = None
    if FIT_POLLS_SNAPSHOT.exists():
        try:
            snap = json.loads(FIT_POLLS_SNAPSHOT.read_text())
        except ValueError:
            snap = None
    if not snap or abs(snap.get("fit_mtime", 0) - fit_t) > 1:
        print("site_ledger: WARNING polls.csv is newer than the fit and no poll "
              "snapshot matches it; 'in the fit' tags may include polls the fit "
              "has not seen", file=sys.stderr)
        return why
    seen = set(snap["poll_ids"])
    for pid in why:
        if why[pid] is None and str(pid) not in seen:
            why[pid] = "late"
    return why


def poll_sources() -> dict:
    """source_row -> publication URL, from the cached archive pages."""
    urls = {}
    for page_key in [k for k in PAGES if k.startswith("2026")]:
        path = RAW_DIR / f"{page_key}.html"
        if not path.exists():
            continue
        html = path.read_text()
        doc = lxml.html.fromstring(html)
        notes = _note_bodies(doc)
        for ti, (_, table) in enumerate(poll_tables(html)):
            trs = table.findall(".//tr")
            for r, tr in enumerate(trs):
                url = None
                for a in tr.iter("a"):
                    h = a.get("href") or ""
                    if h.startswith("#cite_note-") and h[1:] in notes:
                        url = notes[h[1:]]
                        break
                    if h.startswith("http") and "wikipedia.org" not in h:
                        url = h
                        break
                if url:
                    urls[f"{page_key}:{ti}:{r}"] = url
    return urls


def build_ledger(fit: dict) -> dict:
    reg = load_party_registry()
    name_en = dict(zip(reg["party_id"], reg["name_en"]))
    # registry cells write ASCII double quotes (ש"ס); the page writes gershayim
    name_he = {k: (v.replace('"', "\u05f4") if isinstance(v, str) else v)
               for k, v in zip(reg["party_id"], reg["name_he"])}
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    p = polls[polls["cycle"].astype(str) == "2026"].copy()

    counts = p["party_id"].value_counts()
    ids = [i for i in counts.index if counts[i] >= 25]
    recent = p[p["fieldwork_end"] >= p["fieldwork_end"].max() - pd.Timedelta(days=120)]
    rc = recent["party_id"].value_counts()
    ids.sort(key=lambda i: (-(rc.get(i, 0)), -counts[i]))
    col_ix = {i: k for k, i in enumerate(ids)}
    # Header names: the ledger's RZP column carries the RZP-Zehut technical
    # bloc from 2 Sept (the party_id is unchanged).
    HE_HEAD = {"rzp": "הציונות הדתית–זהות"}
    cols = [{"id": i, "en": " + ".join(name_en.get(c, c) for c in i.split("+")),
             "he": HE_HEAD.get(i) or " + ".join(name_he.get(c, c) for c in i.split("+"))}
            for i in ids]

    srcs = poll_sources()
    anchors = section_anchors()
    archive = {k: v[0] for k, v in PAGES.items() if k.startswith("2026")}
    # CEC filings: gov.il blob per ref
    idx = pd.read_csv(CEC_DATA / "cec_filings_index.psv", sep="|", header=None,
                      names=["ref", "urlname", "fname", "editor", "publisher",
                             "survey_date", "transfer_date", "notes"], dtype={"ref": str})
    fil = pd.read_csv(PROCESSED_DIR / "cec_filings.csv", parse_dates=["fieldwork_end"],
                      dtype={"ref": str}).merge(idx[["ref", "urlname", "fname"]], on="ref")
    fil["url"] = [BLOB.format(urlname=u, fname=requests.utils.quote(f))
                  for u, f in zip(fil["urlname"], fil["fname"])]
    fil["n_cec"] = fil["initial_sample"].fillna(fil["n"])
    weights = fit.get("firm_weights", {})

    # Each survey is matched to ITS OWN filing: same firm, same publisher
    # (filtered, not ranked), fieldwork within 3 days; the nearest date
    # wins, then the closest sample size; a filing serves one survey only.
    # Ledger rows of one survey (a/b scenario variants: same firm, date,
    # publisher and n) share that survey's filing.
    heads = p.groupby("poll_id", sort=False).first()
    heads["skey"] = list(zip(heads["pollster"], heads["fieldwork_end"],
                             heads["publisher"].fillna(""), heads["sample_size"].fillna(-1)))
    pairs = []
    for firm, d, pub, n in heads["skey"].unique():
        c = fil[(fil["pollster"] == FIRM_CEC.get(firm, firm))
                & ((fil["fieldwork_end"] - d).abs() <= pd.Timedelta(days=3))]
        if pub in PUB_HE:
            c = c[c["publisher_he"].fillna("").str.contains(PUB_HE[pub], regex=False)]
        else:
            c = c.iloc[0:0]
        for r in c.itertuples():
            nd = abs(r.n_cec - n) / r.n_cec if pd.notna(r.n_cec) and n > 0 else 1.0
            pairs.append((abs((r.fieldwork_end - d).days), nd, (firm, d, pub, n), r.ref, r.url))
    pairs.sort(key=lambda t: (t[0], t[1], t[3]))
    cec_of, used = {}, set()
    for _dd, _nd, sk, ref, url in pairs:
        if sk in cec_of or ref in used:
            continue
        cec_of[sk] = url
        used.add(ref)

    fitted = fitted_polls(p, fit.get("asof"))

    rows = []
    for pid, g in p.groupby("poll_id", sort=False):
        f0 = g.iloc[0]
        seats = [None] * len(ids)
        for r in g.itertuples():
            if r.party_id in col_ix and pd.notna(r.seats):
                seats[col_ix[r.party_id]] = float(r.seats)
        src = (f0.source_row if isinstance(f0.source_row, str) and f0.source_row.startswith("http")
               else srcs.get(f0.source_row))
        if src and ("wikipedia.org" in src or any(x in src for x in DEAD_SRC)):
            src = None
        sec = None
        if isinstance(f0.source_row, str) and not f0.source_row.startswith("http"):
            sec = anchors.get(":".join(f0.source_row.split(":")[:2]))
        rows.append({
            "pid": pid,
            "d": f0.fieldwork_end.date().isoformat(), "f": f0.pollster,
            "p": f0.publisher if isinstance(f0.publisher, str) else "",
            "n": int(f0.sample_size) if pd.notna(f0.sample_size) else None,
            "s": seats, "w": weights.get(f0.pollster),
            "cec": cec_of.get(heads.loc[pid, "skey"]),
            "src": src,
            "pg": f0.page,
            "a": (archive.get(f0.page) + "#" + sec) if sec and archive.get(f0.page) else None,
            "x": fitted.get(pid),
        })
    # one cited URL, two different surveys: keep it only where it belongs
    survey_of = {r["pid"]: (r["f"], r["d"]) for r in rows}
    by_src = {}
    for r in rows:
        if r["src"]:
            by_src.setdefault(r["src"], set()).add(survey_of[r["pid"]])
    for r in rows:
        if r["src"] and len(by_src[r["src"]]) > 1:
            owner = SRC_OWNER.get(r["src"])
            if owner is None or survey_of.get(owner) != survey_of[r["pid"]]:
                r["src"] = None
    for r in rows:
        del r["pid"]
    rows.sort(key=lambda r: r["d"], reverse=True)

    he = pd.read_csv(PROCESSED_DIR / "house_effects_lists_2026.csv")
    rev = {v: k for k, v in name_en.items()}
    rev.update(COMPOSITE_NAMES)
    house = {}
    for r in he.itertuples():
        i = rev.get(r.list)
        if i in col_ix:
            house.setdefault(r.pollster, {})[i] = round(float(r.house_effect), 2)
    return {"cols": cols, "rows": rows, "house": house, "archive": archive,
            "fitted": sum(1 for r in rows if r["x"] is None)}


def build_ratings(fit: dict) -> dict:
    meta = pd.read_csv(CEC_DATA / "pollster_meta.csv")
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    hb = pd.read_csv(PROCESSED_DIR / "house_effects_blocs.csv")
    hb = hb[hb["unit"] == "Netanyahu bloc"]
    weights = fit.get("firm_weights", {})
    p26 = polls[polls["cycle"].astype(str) == "2026"]

    firms = {}
    for cyc, eday in ELECTION_DAY.items():
        res = results[results["cycle"].astype(str) == cyc].dropna(subset=["seats"])
        res_map = dict(zip(res["party_id"], res["seats"]))
        # strictly BEFORE election day: day-0 rows are exit polls, not
        # pre-election polls (Kantar/Kan 11, Midgam/Ch12, Fuchs/Ch13)
        pc = polls[(polls["cycle"].astype(str) == cyc)
                   & (polls["fieldwork_end"] < pd.Timestamp(eday))]
        for firm, g in pc.groupby("pollster"):
            last = g[g["fieldwork_end"] == g["fieldwork_end"].max()]
            last = last[last["party_id"].isin(res_map)]
            month = g[(g["fieldwork_end"] >= pd.Timestamp(eday) - pd.Timedelta(days=30))
                      & g["party_id"].isin(res_map)]
            if len(last) < 5:
                continue
            e_last = float(np.mean([abs(r.seats - res_map[r.party_id]) for r in last.itertuples()]))
            e_month = (float(np.mean([abs(r.seats - res_map[r.party_id]) for r in month.itertuples()]))
                       if len(month) >= 5 else None)
            lean = hb[(hb["pollster"] == firm) & (hb["cycle"].astype(str) == cyc)]["house_effect"]
            firms.setdefault(firm, {})[cyc] = {
                "final_mae": round(e_last, 2),
                "month_mae": round(e_month, 2) if e_month is not None else None,
                "lean": round(float(lean.iloc[0]), 1) if len(lean) else None,
                "final_gap": int((pd.Timestamp(eday) - last["fieldwork_end"].max()).days),
            }

    out = []
    all_firms = set(firms) | set(p26["pollster"].unique())
    for firm in sorted(all_firms):
        cyc = firms.get(firm, {})
        m = meta[meta["pollster"] == firm]
        lean26 = hb[(hb["pollster"] == firm) & (hb["cycle"].astype(str) == "2026")]["house_effect"]
        finals = [c["final_mae"] for c in cyc.values()]
        months = [c["month_mae"] for c in cyc.values() if c["month_mae"] is not None]
        leans = [abs(c["lean"]) for c in cyc.values() if c["lean"] is not None]
        out.append({
            "f": firm,
            "principal": m["principal"].iloc[0] if len(m) else "",
            "outlet": m["outlet_2026"].iloc[0] if len(m) else "",
            "group": m["correlation_group"].iloc[0] if len(m) else "",
            "cycles": cyc,
            "n_cycles": len(cyc),
            "final_mae": round(float(np.mean(finals)), 2) if finals else None,
            "month_mae": round(float(np.mean(months)), 2) if months else None,
            "lean_abs": round(float(np.mean(leans)), 1) if leans else None,
            "lean26": round(float(lean26.iloc[0]), 1) if len(lean26) else None,
            "n26": int(p26[p26["pollster"] == firm]["poll_id"].nunique()),
            "w": weights.get(firm),
        })
    out.sort(key=lambda r: (r["final_mae"] is None, r["final_mae"] or 0))
    sources = {c: {"archive": PAGES[c][0], "election": ELECTION_DAY[c],
                   "cec": CEC_RESULTS_CYCLE.get(c, CEC_RESULTS)}
               for c in ELECTION_DAY if c in PAGES}
    sources["2009"] = {"archive": PAGES.get("2009", (None,))[0], "election": ELECTION_DAY["2009"],
                       "cec": CEC_RESULTS}
    return {"firms": out, "cycles": sources, "cec_results": CEC_RESULTS}
