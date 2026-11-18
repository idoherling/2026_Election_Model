"""The final polls and the model against the official result, in vote shares (dossier s.74).

Israeli pollsters publish seat tables; the raw percentages behind them are in
the reports they file with the Central Elections Committee
(data/processed/postmortem_cec_*.csv: the filings as re-parsed after the
election, with the final polls' filings added). Each outlet is scored on its
last poll, the model on the frozen forecast's vote shares:

  - every poll and the result are rescaled to the 13 graded lists, summing
    to 100 (evens out undecideds, small parties and lists that withdrew);
  - mae is the mean absolute error per list in percentage points; bloc is
    the summed absolute error of the four camps;
  - an outlet whose last poll has no national percentages on file (Channel
    13 files sub-samples only; Direct Polls did not file its 22 Oct poll) is
    scored on the shares its published seat table implies: lists with seats
    share 100 - U in proportion to seats, a list at 0 seats takes the
    outlet's own figure for it when there is one, else the mean of the
    other outlets' final raw figures. On the outlets that have both, the
    conversion moves the mae by -0.06 to +0.05.

    python src/postmortem_shares.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
PID = {"likud": "Likud", "yashar": "Yashar", "together": "Bennett 2026 + Yesh Atid",
       "balad+hadash_taal": "Balad + Hadash-Ta'al", "democrats": "The Democrats", "shas": "Shas",
       "utj": "United Torah Judaism", "yisrael_beytenu": "Yisrael Beytenu", "otzma": "Otzma Yehudit",
       "raam": "Ra'am", "rzp": "Religious Zionist Party", "amcha_yisrael": "Amcha Yisrael",
       "zionist_home": "Reservists – Economic Party"}
SEAT_ID = {"joint_list": "balad+hadash_taal"}
MAIN = list(PID.values())
PUB = {"חדשות 12": "Channel 12", "וואלה": "Walla", "ערוץ 14": "Channel 14", "ערוץ 16": "Channel 16",
       "מעריב": "Maariv", "ישראל היום": "Israel Hayom", "זמן ישראל": "Zman Yisrael", "כאן": "Kan 11",
       "המזרח התיכון 24": "i24 News"}
SINCE = "2026-10-14"


def _norm(s) -> pd.Series:
    s = pd.Series(s, dtype=float).reindex(MAIN).fillna(0)
    return 100 * s / s.sum()


def table(with_average: bool = False) -> pd.DataFrame:
    """One row per outlet and the model: basis, date, mae, bloc, Netanyahu-bloc and Likud error.
    with_average adds a row for the mean of the outlets' rescaled shares (the scorecard's
    reference row), "AVERAGE (final polls)"."""
    reg = json.loads((PROCESSED / "frozen_forecast_2026-10-23.json").read_text(encoding="utf-8"))["payload"]["lists"]
    camps = {g: [k for k in MAIN if reg[k]["bloc"] == g] for g in ("nb", "anti", "arab", "una")}
    by_letter = {(v.get("letters") or v.get("letter")): k for k, v in reg.items()}
    res = pd.read_csv(PROCESSED / "result_2026_certified.csv", comment="#")
    y = _norm({by_letter[r.list]: r.votes for r in res.itertuples() if by_letter.get(r.list) in MAIN})

    def score(v) -> dict:
        e = _norm(v) - y
        return {"mae": float(e.abs().mean()), "bloc": float(sum(abs(e[camps[g]].sum()) for g in camps)),
                "nb": float(e[camps["nb"]].sum()), "likud": float(e["Likud"])}

    f = pd.read_csv(PROCESSED / "postmortem_cec_filings.csv", parse_dates=["fieldwork_end"])
    c = pd.read_csv(PROCESSED / "postmortem_cec_party_pcts.csv")
    f = f[(f.fieldwork_end >= SINCE) & f.national_table].copy()
    f["outlet"] = f.publisher_he.map(lambda he: next((v for k, v in PUB.items() if k in str(he)), he)) + " (" + f.pollster + ")"
    raw = {}
    for out, g in f.sort_values("fieldwork_end").groupby("outlet"):
        raw[out] = [(r.fieldwork_end, {PID[q]: c[c.ref == r.ref].set_index("party_id").raw_pct.get(q, 0.0) for q in PID})
                    for r in g.itertuples()]
    p = pd.read_csv(PROCESSED / "polls.csv", parse_dates=["fieldwork_end"])
    p = p[(p.cycle.astype(str) == "2026") & p.sums_ok & (p.fieldwork_end >= SINCE)].copy()
    p["publisher"] = p.publisher.replace({"Zman Israel": "Zman Yisrael", "HaHadashot 12": "Channel 12"})
    fallback = {k: float(np.mean([L[-1][1][k] for L in raw.values()])) for k in MAIN}

    def implied(poll, own=None) -> dict:
        ids = [SEAT_ID.get(q, q) for q in poll.party_id]
        seats = {PID[q]: s for q, s in zip(ids, poll.seats) if q in PID}
        pct = {PID[q]: v for q, v in zip(ids, poll.vote_pct) if q in PID and pd.notna(v)}
        zero = {k: pct.get(k, (own or {}).get(k, fallback[k])) for k in MAIN if seats.get(k, 0) == 0}
        u = sum(zero.values())
        return {k: (seats[k] / 120 * (100 - u) if seats.get(k, 0) > 0 else zero[k]) for k in MAIN}

    rows, vecs = [], []
    for (pub, firm), g in p.groupby(["publisher", "pollster"]):
        out = f"{pub} ({firm})"
        last = g[g.fieldwork_end == g.fieldwork_end.max()]
        when = last.fieldwork_end.iloc[0]
        filed = raw.get(out, [])
        if filed and (when - filed[-1][0]).days <= 1:
            v = filed[-1][1]
            rows.append({"outlet": out, "basis": "filing", "date": filed[-1][0], **score(v)})
        elif filed or firm == "Midgam Project":
            own = next((v for d, v in filed if abs((d - when).days) <= 1), None)
            v = implied(last, own)
            rows.append({"outlet": out, "basis": "seats", "date": when, **score(v)})
        else:
            continue
        vecs.append(_norm(v))
    if with_average and vecs:
        rows.append({"outlet": "AVERAGE (final polls)", "basis": "average",
                     "date": max(r["date"] for r in rows), **score(pd.concat(vecs, axis=1).mean(axis=1))})
    rows.append({"outlet": "MODEL (frozen forecast)", "basis": "forecast shares", "date": pd.Timestamp("2026-10-23"),
                 **score({k: 100 * reg[k]["share"] for k in MAIN})})
    return pd.DataFrame(rows).sort_values("mae").reset_index(drop=True)


if __name__ == "__main__":
    t = table()
    t["date"] = t.date.dt.strftime("%d %b")
    print(t.round(2).to_string(index=False))
