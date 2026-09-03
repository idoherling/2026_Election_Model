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
from scrape_polls import PAGES, PROCESSED_DIR, RAW_DIR, poll_tables

ELECTION_DAY = {"2009": "2009-02-10", "2013": "2013-01-22", "2015": "2015-03-17",
                "2019a": "2019-04-09", "2019s": "2019-09-17", "2020": "2020-03-02",
                "2021": "2021-03-23", "2022": "2022-11-01"}
CEC_RESULTS = "https://www.bechirot.gov.il/election/Pages/AllElectionResults.aspx"
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
            if h.startswith("http"):
                out.setdefault(m.group(1), h)
                break
    return out


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
    name_he = dict(zip(reg["party_id"], reg["name_he"]))
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    p = polls[polls["cycle"].astype(str) == "2026"].copy()

    counts = p["party_id"].value_counts()
    ids = [i for i in counts.index if counts[i] >= 25]
    recent = p[p["fieldwork_end"] >= p["fieldwork_end"].max() - pd.Timedelta(days=120)]
    rc = recent["party_id"].value_counts()
    ids.sort(key=lambda i: (-(rc.get(i, 0)), -counts[i]))
    col_ix = {i: k for k, i in enumerate(ids)}
    cols = [{"id": i, "en": " + ".join(name_en.get(c, c) for c in i.split("+")),
             "he": " + ".join(name_he.get(c, c) for c in i.split("+"))} for i in ids]

    srcs = poll_sources()
    # CEC filings: gov.il blob per ref, matched to polls by firm + date (<=3d)
    idx = pd.read_csv(CEC_DATA / "cec_filings_index.psv", sep="|", header=None,
                      names=["ref", "urlname", "fname", "editor", "publisher",
                             "survey_date", "transfer_date", "notes"], dtype={"ref": str})
    fil = pd.read_csv(PROCESSED_DIR / "cec_filings.csv", parse_dates=["fieldwork_end"],
                      dtype={"ref": str}).merge(idx[["ref", "urlname", "fname"]], on="ref")
    fil["url"] = [BLOB.format(urlname=u, fname=requests.utils.quote(f))
                  for u, f in zip(fil["urlname"], fil["fname"])]
    weights = fit.get("firm_weights", {})

    rows = []
    for pid, g in p.groupby("poll_id", sort=False):
        f0 = g.iloc[0]
        seats = [None] * len(ids)
        for r in g.itertuples():
            if r.party_id in col_ix and pd.notna(r.seats):
                seats[col_ix[r.party_id]] = float(r.seats)
        cand = fil[(fil["pollster"] == f0.pollster)
                   & ((fil["fieldwork_end"] - f0.fieldwork_end).abs() <= pd.Timedelta(days=3))]
        rows.append({
            "d": f0.fieldwork_end.date().isoformat(), "f": f0.pollster,
            "p": f0.publisher if isinstance(f0.publisher, str) else "",
            "n": int(f0.sample_size) if pd.notna(f0.sample_size) else None,
            "s": seats, "w": weights.get(f0.pollster),
            "cec": cand["url"].iloc[0] if len(cand) else None,
            "src": srcs.get(f0.source_row),
            "pg": f0.page,
        })
    rows.sort(key=lambda r: r["d"], reverse=True)

    he = pd.read_csv(PROCESSED_DIR / "house_effects_lists_2026.csv")
    rev = {v: k for k, v in name_en.items()}
    rev.update(COMPOSITE_NAMES)
    house = {}
    for r in he.itertuples():
        i = rev.get(r.list)
        if i in col_ix:
            house.setdefault(r.pollster, {})[i] = round(float(r.house_effect), 2)
    return {"cols": cols, "rows": rows, "house": house,
            "archive": {k: v[0] for k, v in PAGES.items() if k.startswith("2026")}}


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
        pc = polls[(polls["cycle"].astype(str) == cyc)
                   & (polls["fieldwork_end"] <= pd.Timestamp(eday))]
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
    sources = {c: {"archive": PAGES[c][0], "election": ELECTION_DAY[c]}
               for c in ELECTION_DAY if c in PAGES}
    sources["2009"] = {"archive": PAGES.get("2009", (None,))[0], "election": ELECTION_DAY["2009"]}
    return {"firms": out, "cycles": sources, "cec_results": CEC_RESULTS}
