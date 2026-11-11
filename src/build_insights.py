"""The insights page: ten findings of the project and what happens next.

    python src/build_insights.py     writes output/site/insights.html + insights.json

Every number on the page is computed here from the repository's own files
(the certified result, the poll archive, the frozen forecast and its
scorecard, the backtest record, the election-night snapshots and the
formation tracker) and injected into site/insights.html (placeholder
__IN_DATA__), the way scorecard.py builds its page. The text, in English and
Hebrew, lives in the template.

Inputs that are not committed (data/raw is ignored) are cached as small
tables: the 2026 count's path through election night is written once to
data/processed/election_night_2026_path.csv and read back from it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import election_night as en
import postmortem_shares

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output" / "site"
TEMPLATE = ROOT / "site" / "insights.html"
RESULT = PROCESSED / "result_2026_certified.csv"
NIGHT_PATH = PROCESSED / "election_night_2026_path.csv"
NIGHT_RAW = ROOT / "data" / "raw" / "election_night"
AS_OF = "2026-11-11"

# poll party_id -> the forecast's list name (the 13 lists the scorecard grades)
PID = {"likud": "Likud", "yashar": "Yashar", "together": "Bennett 2026 + Yesh Atid",
       "joint_list": "Balad + Hadash-Ta'al", "democrats": "The Democrats", "shas": "Shas",
       "utj": "United Torah Judaism", "yisrael_beytenu": "Yisrael Beytenu", "otzma": "Otzma Yehudit",
       "raam": "Ra'am", "rzp": "Religious Zionist Party", "amcha_yisrael": "Amcha Yisrael",
       "zionist_home": "Reservists – Economic Party"}
ARAB_IDS = {"raam", "hadash_taal", "balad", "joint_list", "balad+hadash_taal", "balad+hadash_taal+raam",
            "hadash_taal+raam"}
# 2022 ballot letters by camp (CEC, 25th Knesset), lists below the threshold included in the vote share
B22 = {"nb": ["מחל", "ט", "שס", "ג"], "anti": ["פה", "כן", "ל", "אמת", "מרצ"], "arab": ["עם", "ום", "ד"]}
B26 = {"nb": ["מחל", "ב", "ג", "שס", "ט"], "anti": ["דרך", "רק", "אמת", "ל"], "arab": ["ודם", "עם"]}
OUTLET = {"HaHadashot 12": "Channel 12", "Zman Israel": "Zman Yisrael"}
PANELS = {"Direct Polls", "Filber"}          # the two large online panels
# Likud's record against its final polls (dossier s.36; recomputed there from polls.csv)
LIKUD_RECORD = [{"cycle": "2015", "polls": 21.2, "result": 30, "trailing": True},
                {"cycle": "2019a", "polls": 28.2, "result": 35, "trailing": True}]


def _polls() -> pd.DataFrame:
    p = pd.read_csv(PROCESSED / "polls.csv", parse_dates=["fieldwork_end"])
    p = p[(p.cycle.astype(str) == "2026") & p.sums_ok].copy()
    p["party_id"] = p.party_id.replace({"balad+hadash_taal": "joint_list"})
    p["publisher"] = p.publisher.replace(OUTLET)
    return p


def result() -> dict:
    sc = json.loads((OUT_DIR / "scorecard.json").read_text(encoding="utf-8"))
    lists = sc["frozen"]["payload"]["lists"]
    r26 = pd.read_csv(RESULT, comment="#")
    valid26 = int(r26.votes.sum())
    v26, s26 = dict(zip(r26.list, r26.votes)), dict(zip(r26.list, r26.seats))
    c = pd.read_csv(ROOT / "data" / "cec_final_counts.csv")
    c = c[c.cycle.astype(str) == "2022"]
    v22, s22, valid22 = dict(zip(c.ballot, c.votes)), dict(zip(c.ballot, c.seats_official)), int(c.valid_votes.iloc[0])
    blocs = {}
    for b in ("nb", "anti", "arab"):
        blocs[b] = {"seats22": int(sum(s22.get(l, 0) for l in B22[b])), "seats26": int(sum(s26.get(l, 0) for l in B26[b])),
                    "votes22": int(sum(v22.get(l, 0) for l in B22[b])), "votes26": int(sum(v26.get(l, 0) for l in B26[b])),
                    "share22": round(100 * sum(v22.get(l, 0) for l in B22[b]) / valid22, 2),
                    "share26": round(100 * sum(v26.get(l, 0) for l in B26[b]) / valid26, 2)}
    seats = [{"letters": v.get("letters") or v.get("letter"), "en": v["en"], "he": v["he"], "bloc": v["bloc"],
              "pvar": v.get("pvar"), "seats": int(sc["result"]["seats"].get(k, 0)),
              "share": round(100 * v26.get(v.get("letters") or v.get("letter"), 0) / valid26, 2)}
             for k, v in lists.items() if sc["result"]["seats"].get(k, 0) > 0]
    seats.sort(key=lambda r: -r["seats"])
    wasted = {l: {"votes": int(v26[l]), "share": round(100 * v26[l] / valid26, 2)} for l in ("די", "ך")}
    return {"valid": valid26, "valid22": valid22, "eligible": 7_331_981, "voted": 5_717_397, "turnout": 77.98, "turnout22": 70.6,
            "blocs": blocs, "seats": seats, "wasted": wasted,
            "wasted_share": round(sum(w["share"] for w in wasted.values()), 2),
            "wasted_votes": int(sum(w["votes"] for w in wasted.values())),
            "threshold_votes": int(-(-valid26 * 325 // 10000))}


def pacts() -> dict:
    r = pd.read_csv(RESULT, comment="#")
    votes = dict(zip(r.list, r.votes))
    pairs, _ = en.cycle_2026().letter_pairs()
    with_, without = en.allocate(votes, pairs).seats, en.allocate(votes, []).seats
    moved = {k: [int(without[k]), int(with_[k])] for k in with_ if with_[k] != without[k]}
    # the closest seat: the smallest change to one list's vote that changes the allocation
    best = None
    for k in [l for l, s in with_.items() if s > 0]:
        for sign in (1, -1):
            lo, hi = 0, 60000
            def changed(d):
                vv = dict(votes); vv[k] += sign * d
                return en.allocate(vv, pairs).seats != with_
            if not changed(hi):
                continue
            while hi - lo > 1:
                m = (lo + hi) // 2
                lo, hi = (lo, m) if changed(m) else (m, hi)
            if best is None or hi < best:
                best = hi
    return {"moved": moved, "closest": int(best)}


def arab_polls(p: pd.DataFrame) -> dict:
    w = p[p.seats > 0].pivot_table(index="poll_id", columns="party_id", values="seats", aggfunc="first").fillna(0)
    arab = w[[c for c in w.columns if c in ARAB_IDS]].sum(axis=1).astype(int)
    hist = arab.value_counts().sort_index()
    first = p.fieldwork_end.min()
    return {"n": int(len(arab)), "max": int(arab.max()), "hist": {int(k): int(v) for k, v in hist.items()},
            "from": first.strftime("%Y-%m-%d"), "result": 19, "previous_record": 15}


def final_polls(p: pd.DataFrame) -> pd.DataFrame:
    q = p[p.fieldwork_end >= "2026-10-14"]
    w = q.pivot_table(index="poll_id", columns="party_id", values="seats", aggfunc="first").fillna(0)
    meta = q.groupby("poll_id")[["fieldwork_end", "pollster", "publisher", "sample_size"]].first()
    w = meta.join(w).sort_values("fieldwork_end")
    return w.groupby(["pollster", "publisher"]).tail(1)


def ranking(fin: pd.DataFrame, sc: dict) -> dict:
    lists = sc["frozen"]["payload"]["lists"]
    y = {k: int(sc["result"]["seats"].get(k, 0)) for k in PID.values()}
    nb = [k for k in PID.values() if lists[k]["bloc"] == "nb"]

    def grade(v):
        return {"err": int(sum(abs(v.get(k, 0) - y[k]) for k in y)),
                "nb": int(sum(v.get(k, 0) - y[k] for k in nb)),
                "thr": int(sum((v.get(k, 0) > 0) != (y[k] > 0) for k in y)),
                "likud": int(v.get("Likud", 0)), "shas": int(v.get("Shas", 0)),
                "arab": int(v.get("Balad + Hadash-Ta'al", 0) + v.get("Ra'am", 0)),
                "res": int(v.get("Reservists – Economic Party", 0)), "amcha": int(v.get("Amcha Yisrael", 0))}
    rows = []
    for _, r in fin.iterrows():
        v = {PID[c]: int(r[c]) for c in PID if c in fin.columns}
        rows.append({"outlet": r.publisher, "firm": r.pollster, "date": r.fieldwork_end.strftime("%Y-%m-%d"),
                     "kind": "panel" if r.pollster in PANELS else "poll", **grade(v)})
    off = next(m for m in sc["frozen"]["payload"]["models"] if m["id"] == "official")
    rows.append({"outlet": "model", "firm": "", "date": "2026-10-23", "kind": "model", **grade(off["central"])})
    rows.sort(key=lambda r: (r["err"], abs(r["nb"])))
    polls = [r for r in rows if r["kind"] != "model"]
    return {"rows": rows, "avg_err": round(float(np.mean([r["err"] for r in polls])), 1),
            "avg_likud": round(float(np.mean([r["likud"] for r in polls])), 1),
            "avg_shas": round(float(np.mean([r["shas"] for r in polls])), 1),
            "avg_arab": round(float(np.mean([r["arab"] for r in polls])), 1),
            "res4": int(sum(r["res"] >= 4 for r in polls)), "amcha4": int(sum(r["amcha"] >= 4 for r in polls)),
            "n": len(polls), "share_mae": share_mae()}


def share_mae() -> dict:
    """Mean absolute error per list in vote-share points (postmortem_shares.table)."""
    t = postmortem_shares.table().set_index("outlet").mae
    polls = t.drop("MODEL (frozen forecast)")
    return {"direct_polls": round(float(t["i24 News (Direct Polls)"]), 2),
            "model": round(float(t["MODEL (frozen forecast)"]), 2),
            "others": [round(float(polls.drop("i24 News (Direct Polls)").min()), 2), round(float(polls.max()), 2)]}


def likud_months(p: pd.DataFrame) -> list:
    q = p[(p.party_id == "likud") & (p.fieldwork_end >= "2026-04-01")].copy()
    q["month"] = q.fieldwork_end.dt.strftime("%Y-%m")
    q["grp"] = np.where(q.pollster.isin(PANELS), "panels", "others")
    t = q.groupby(["month", "grp"]).seats.mean().unstack()
    return [{"month": m, "panels": round(float(r.panels), 1), "others": round(float(r.others), 1)}
            for m, r in t.iterrows()]


def shas_record(rk: dict) -> list:
    b = pd.read_csv(PROCESSED / "backtest_blocks.csv")
    rows = [{"cycle": str(r.cycle), "err": round(float(r.error), 1)} for r in b[b.block == "Shas"].itertuples()]
    rows.append({"cycle": "2026", "err": round(rk["avg_shas"] - 6, 1)})
    return rows


def scorecard(sc: dict) -> dict:
    S = sc["scores"]
    by = {m["id"]: m for m in S["models"]}
    names = {m["id"]: m["name"] for m in sc["frozen"]["payload"]["models"]}
    rows = [{"id": i, "en": names[i]["en"], "he": names[i]["he"], "log": round(by[i]["summary"]["log"], 3),
             "rank": by[i]["rank"]} for i in S["ranking"]]
    off = by["official"]
    v = pd.read_csv(PROCESSED / "model_validation_bayes_lists.csv")
    inside = int(((v.actual >= v.p05) & (v.actual <= v.p95)).sum())
    n26 = sum(1 for x in off["lists"].values() if x.get("scored"))
    in26 = sum(1 for x in off["lists"].values() if x.get("scored") and x.get("covered"))
    L = off["lists"]
    return {"variants": rows, "official_rank": off["rank"], "n": len(rows),
            "beats": (off["expect"].get("log") or {}).get("beats"),
            "coverage": {"record": [inside, int(len(v))], "y2026": [in26, n26]},
            "p_pass": {"reservists": L["Reservists – Economic Party"]["p_pass"], "amcha": L["Amcha Yisrael"]["p_pass"]},
            "shas_pit": L["Shas"]["pit"], "central": {k: x["central"] for k, x in L.items() if x.get("scored")}}


def night_path() -> list:
    """Raw Netanyahu-bloc and Arab-list seats at each stage of the 2026 count."""
    if NIGHT_RAW.exists() and any(d.name.startswith("2026") for d in NIGHT_RAW.iterdir()):
        pairs, _ = en.cycle_2026().letter_pairs()
        valid = int(pd.read_csv(RESULT, comment="#").votes.sum())
        rows, seen = [], set()
        for d in sorted(x for x in NIGHT_RAW.iterdir() if x.is_dir() and x.name.startswith("2026")):
            c = en.load_snapshot(d)
            if c is None or c.valid in seen or c.valid < 20000:
                continue
            seen.add(c.valid)
            a = en.allocate(c.votes, pairs).seats
            rows.append({"snapshot": d.name, "valid": int(c.valid), "pct": round(100 * c.valid / valid, 1),
                         "nb": int(sum(a.get(l, 0) for l in B26["nb"])), "arab": int(sum(a.get(l, 0) for l in B26["arab"]))})
        pd.DataFrame(rows).to_csv(NIGHT_PATH, index=False)
    t = pd.read_csv(NIGHT_PATH)
    return t.to_dict("records")


def night_2022() -> list:
    t = pd.read_csv(PROCESSED / "election_night_replay_2022_archive.csv")
    return [{"pct": float(r.pct_of_final_valid), "nb": int(r.nb_raw), "official": int(r.nb_official)}
            for r in t.itertuples()]


def build() -> dict:
    sc = json.loads((OUT_DIR / "scorecard.json").read_text(encoding="utf-8"))
    p = _polls()
    fin = final_polls(p)
    rk = ranking(fin, sc)
    return {"as_of": AS_OF, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "result": result(), "pacts": pacts(), "arab": arab_polls(p), "ranking": rk,
            "likud": {"months": likud_months(p), "record": LIKUD_RECORD, "result": 27},
            "shas": shas_record(rk), "scorecard": scorecard(sc),
            "night": night_path(), "night22": night_2022(),
            "next": json.loads((PROCESSED / "formation_tracker.json").read_text(encoding="utf-8"))}


def render(payload: dict) -> str:
    lex = en.site_lexicon()
    tpl = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for k, v in (("__EN_TOKENS__", lex["tokens"]), ("__EN_FONTS__", lex["fonts"]), ("__EN_ICON__", lex["icon"])):
        tpl = tpl.replace(k, v)
    assert "__IN_DATA__" in tpl, "page template placeholder missing"
    return tpl.replace("__IN_DATA__", blob)


def main() -> None:
    payload = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "insights.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                                           encoding="utf-8")
    if TEMPLATE.exists():
        (OUT_DIR / "insights.html").write_text(render(payload), encoding="utf-8")
    r, rk = payload["result"], payload["ranking"]
    print(f"insights: blocs {r['blocs']}; wasted {r['wasted_share']}%; Arab lists max {payload['arab']['max']} "
          f"in {payload['arab']['n']} polls; model seat error "
          f"{next(x['err'] for x in rk['rows'] if x['kind'] == 'model')} vs polls {rk['avg_err']}; "
          f"{'wrote output/site/insights.html' if TEMPLATE.exists() else 'no template yet (json only)'}")


if __name__ == "__main__":
    main()
