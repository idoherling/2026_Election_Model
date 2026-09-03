"""Build the published site from the processed model outputs.

Injects a JSON payload into site/template.html (placeholder __SITE_DATA__)
and writes output/site/index.html. The payload is also persisted at
output/site/site_data.json so data refreshes are diffable in git.

Key -> source:
  asof      official_forecast.csv
  parties   official_forecast.csv (seats/interval/p_pass/p_largest)
            + bayes_forecast_mixture.csv (mixture mean)
  sub       bayes_model.MICRO_POLLED x MICRO_REALIZE — the small parties
            (polled support and forecast vote), with pass probabilities
            from official_forecast.csv
  blocs     mixture_blocs.csv
  formation government_formation.csv
  pm        pm_probabilities.csv
  events    registration_effects.csv
  house     house_effects_blocs.csv (Netanyahu-bloc unit, 2026, n >= 10)
  counts    polls.csv
  draws     mixture_draws.parquet (2,500-row sample; columns with any seats)
  kalpi     kalpi_sectors.csv + kalpi_poststrat_2026.csv x current seats
  val       carried forward from the previous payload (backtest numbers
            change only when the harness is re-run)
  fit       fit_summary.json (written by bayes_model.main) + CEC filing count
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
TEMPLATE = ROOT / "site" / "template.html"
OUT_DIR = ROOT / "output" / "site"

SECTOR_LABELS = {
    "centre_left": "Centre-left localities", "mixed": "Mixed cities",
    "secular_right": "Secular-right localities", "arab": "Arab localities",
    "haredi": "Haredi localities",
    "religious_zionist": "Religious-Zionist localities",
    "russian_leaning": "Druze & YB strongholds",
}
PM_RENAME = {"none (repeat election)": "No one — repeat election"}


def build_payload() -> dict:
    prev = {}
    prev_path = OUT_DIR / "site_data.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text(encoding="utf-8"))

    off = pd.read_csv(PROCESSED / "official_forecast.csv")
    mix = pd.read_csv(PROCESSED / "bayes_forecast_mixture.csv")
    mmean = dict(zip(mix["list"], mix["mean"]))
    parties = []
    for r in off.itertuples():
        lo, hi = (int(x) for x in r.interval_90.split("-"))
        parties.append({
            "name": r.list, "seats": int(r.central_seats), "lo": lo, "hi": hi,
            "mean": round(float(mmean.get(r.list, r.central_seats)), 1),
            "p_pass": round(float(r.p_pass), 3),
            "p_largest": round(float(r.p_largest), 3),
        })

    from bayes_model import MICRO_POLLED, MICRO_PRIORS
    from normalize import load_party_registry
    from registration_scenarios import RESOLVED
    reg = load_party_registry()
    names = dict(zip(reg["party_id"], reg["name_en"]))
    ppass = dict(zip(off["list"], off["p_pass"]))
    # A micro-list absorbed by a RESOLVED merger is not a separate small
    # party: its support already sits inside the absorbing list's seat row,
    # and listing it again would count the same voters twice.
    merged_away = set()
    if RESOLVED.get("rzp_fate") == "merge_zehut":
        merged_away.add("zehut")
    # Support measured only in a sector poll (not a national itemization)
    # is labelled as such on the site.
    SECTOR_POLLED = {"makom_lekulanu"}
    sub = [
        {"name": names.get(pid, pid),
         "polled": round(MICRO_POLLED[pid][0] * 100, 1),
         "src": "sector" if pid in SECTOR_POLLED else "national",
         "share": round(mean * 100, 1),
         "pass": round(float(ppass.get(names.get(pid, pid), 0.0)), 3)}
        for pid, (mean, _sd) in MICRO_PRIORS.items() if pid not in merged_away
    ]
    sub.sort(key=lambda x: (-x["share"], -x["polled"]))

    b = pd.read_csv(PROCESSED / "mixture_blocs.csv").iloc[0]
    blocs = {"nb": round(float(b.p_nb_61), 3),
             "anti": round(float(b.p_anti_61), 3),
             "antiRaam": round(float(b.p_anti_raam_61), 3),
             "neither": round(float(b.p_neither), 3),
             "nb_mean": round(float(b.nb_mean), 1)}

    gf = pd.read_csv(PROCESSED / "government_formation.csv")
    formation = [{"o": r.outcome, "p": round(float(r.probability), 3)}
                 for r in gf.itertuples()]

    pm_df = pd.read_csv(PROCESSED / "pm_probabilities.csv")
    pm = [[PM_RENAME.get(r.pm, r.pm), round(float(r.probability), 3),
           round(float(r.p05), 3), round(float(r.p95), 3)]
          for r in pm_df.itertuples()]

    ev = pd.read_csv(PROCESSED / "registration_effects.csv")
    events = [{"e": r.event, "o": str(r.outcome),
               "p": round(float(r.probability), 3),
               "nb61": round(float(r.p_nb_61), 3),
               "nbm": round(float(r.nb_mean), 1)} for r in ev.itertuples()]

    he = pd.read_csv(PROCESSED / "house_effects_blocs.csv")
    he = he[(he["unit"] == "Netanyahu bloc") & (he["n_polls"] >= 10)
            & (he["cycle"].astype(str) == "2026")]
    house = [{"p": r.pollster, "he": round(float(r.house_effect), 1),
              "n": int(r.n_polls)}
             for r in he.sort_values("house_effect").itertuples()]

    fit = {}
    fs = PROCESSED / "fit_summary.json"
    if fs.exists():
        fit = json.loads(fs.read_text())
    fit["cec_filings_parsed"] = int(len(pd.read_csv(PROCESSED / "cec_filings.csv")))

    polls = pd.read_csv(PROCESSED / "polls.csv")
    p26 = polls[polls.cycle.astype(str) == "2026"]
    counts = {"polls": int(polls.poll_id.nunique()), "rows": int(len(polls)),
              "cycles": int(polls.cycle.nunique()),
              "polls26": int(p26.poll_id.nunique()),
              "firms26": int(p26.pollster.nunique())}

    dr = pd.read_parquet(PROCESSED / "mixture_draws.parquet")
    dr = dr[[c for c in dr.columns if dr[c].max() > 0]]
    samp = dr.sample(n=min(2500, len(dr)), random_state=1).astype(int)
    draw_cols = list(samp.columns)
    draws = samp.values.tolist()

    seats_by = dict(zip(off["list"], off["central_seats"]))
    ps = pd.read_csv(PROCESSED / "kalpi_poststrat_2026.csv")
    ps["seats_now"] = ps["list"].map(seats_by).fillna(0) * ps["share_of_list"]
    loc = pd.read_csv(PROCESSED / "kalpi_sectors.csv")
    kalpi = []
    for sector, g in loc.groupby("sector"):
        elig = int(g.eligible.sum())
        seats = ps[ps.sector == sector].groupby("list")["seats_now"].sum()
        seats = {k: round(float(v), 1) for k, v in seats.items() if v >= 0.05}
        kalpi.append({
            "sector": sector, "eligible": elig,
            "turnout": round(float((g.turnout * g.eligible).sum() / elig), 3),
            "n": int(len(g)), "seats": seats,
            "examples": g.nlargest(3, "eligible")["name"].tolist(),
        })
    kalpi.sort(key=lambda k: -k["eligible"])

    return {
        "asof": str(off["asof"].iloc[0]), "parties": parties, "sub": sub,
        "blocs": blocs, "formation": formation, "pm": pm, "events": events,
        "house": house, "val": prev.get("val", {}), "counts": counts, "fit": fit,
        "drawCols": draw_cols, "draws": draws, "kalpi": kalpi,
    }


def main() -> None:
    payload = build_payload()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    (OUT_DIR / "site_data.json").write_text(blob, encoding="utf-8")
    tpl = TEMPLATE.read_text(encoding="utf-8")
    assert "__SITE_DATA__" in tpl, "template placeholder missing"
    html = '<!doctype html>\n<html lang="en">\n' + tpl.replace("__SITE_DATA__", blob)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"built output/site/index.html "
          f"({len(html)//1024} KB, {len(payload['parties'])} lists, "
          f"{len(payload['sub'])} sub-threshold, asof {payload['asof']})")


if __name__ == "__main__":
    main()
