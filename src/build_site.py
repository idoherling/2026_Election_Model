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
  kalpi     kalpi_sectors.csv + kalpi_poststrat_2026.csv x expected seats (mixture mean)
  val       recomputed every build from the harness outputs:
            simple   model_validation.csv (8 cycles, eve)
            bayes    model_validation_ablation.csv, ablation == "shipped"
                     (eve, shipped list mask, one seed; dossier s.41 restates
                     the 3-seed baseline at 1.735 / 1.630 / 0.970 / 0.051)
            horizon  model_validation_horizon.csv, mode == "calendar"
                     (D-56 / D-21 / D-7 refits, the shipped calendar)
  below     share of the forecast vote below 3.25% (the mixture's median
            vector, renormalised as allocate_central does)
  fit.u_*   the certainty layer's undecided pool and expected per-side
            transfer, from bayes_model's own constants
  fit       fit_summary.json (written by bayes_model.main) + CEC filing count
  ledger    site_ledger.build_ledger — every 2026 poll with its sources
  ratings   site_ledger.build_ratings — per-firm track record
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
PM_RENAME = {"none (repeat election)": "No one — repeat election",
             "rotation / Likud successor": "Rotation / Likud successor"}


def build_val() -> dict:
    """Validation table, recomputed from the harness CSVs every build."""
    order = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
    out = {"cycles": order}
    sp = PROCESSED / "model_validation.csv"
    if sp.exists():
        m = pd.read_csv(sp, dtype={"cycle": str}).set_index("cycle").reindex(order)
        out["simple"] = {"mae": round(float(m.seat_mae.mean()), 2),
                         "cov": round(float(m.coverage_90.mean()) * 100, 1),
                         "brier": round(float(m.threshold_brier.mean()), 3),
                         "per": [round(float(x), 2) for x in m.seat_mae]}
    ap = PROCESSED / "model_validation_ablation.csv"
    if ap.exists():
        a = pd.read_csv(ap, dtype={"cycle": str})
        a = a[a["ablation"] == "shipped"].set_index("cycle").reindex(order)
        out["bayes"] = {"mae": round(float(a.seat_mae.mean()), 2),
                        "mae_med": round(float(a.seat_mae_median.mean()), 2),
                        "cov": round(float(a.coverage_90.mean()) * 100, 1),
                        "brier": round(float(a.threshold_brier.mean()), 3),
                        "per": [round(float(x), 2) for x in a.seat_mae],
                        "src": "model_validation_ablation.csv (shipped, eve, one seed)"}
    hp = PROCESSED / "model_validation_horizon.csv"
    if hp.exists():
        h = pd.read_csv(hp, dtype={"cycle": str})
        h = h[h["mode"] == "calendar"]
        out["horizon"] = {f"D{int(k)}": {"mae": round(float(g.seat_mae.mean()), 2),
                                         "mae_med": round(float(g.seat_mae_median.mean()), 2),
                                         "cov": round(float(g.coverage_90.mean()) * 100, 1),
                                         "brier": round(float(g.threshold_brier.mean()), 3)}
                          for k, g in h.groupby("horizon")}
    return out


def build_payload() -> dict:
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
        {"name": names.get(pid, pid), "kind": "micro",
         "polled": round(MICRO_POLLED[pid][0] * 100, 1),
         "src": "sector" if pid in SECTOR_POLLED else "national",
         "share": round(mean * 100, 1),
         "pass": round(float(ppass.get(names.get(pid, pid), 0.0)), 3)}
        for pid, (mean, _sd) in MICRO_PRIORS.items() if pid not in merged_away
    ]
    # Every modeled list the forecast leaves below the threshold joins the
    # section too, with its forecast vote share (the mixture's mean share)
    # and its polled share over the last 14 days (seat-derived, or the
    # below-threshold percentage where a pollster published one).
    ms = pd.read_csv(PROCESSED / "mixture_shares.csv")
    # the median share: the same vector the central seat count is built on
    # (s.42 - the mean of a list polled under 1% is lifted by the residual
    # shock's clip at zero, so it overstates the list's own polling)
    mshare = dict(zip(ms["list"], ms["share_median"]))
    # vote below the threshold on the vector the central seats use
    # (official_forecast.allocate_central renormalises the median vector)
    v = ms["share_median"] / ms["share_median"].sum()
    below = round(float(v[v < 0.0325].sum()) * 100, 1)
    polls_all = pd.read_csv(PROCESSED / "polls.csv", parse_dates=["fieldwork_end"])
    p26 = polls_all[polls_all["cycle"].astype(str) == "2026"]
    recent = p26[p26["fieldwork_end"] >= p26["fieldwork_end"].max() - pd.Timedelta(days=14)]
    name_of_id = dict(zip(reg["party_id"], reg["name_en"]))
    comp_name = {"together": "Bennett 2026 + Yesh Atid", "balad+hadash_taal": "Balad + Hadash-Ta'al"}
    recent = recent.assign(list_name=recent["party_id"].map(lambda i: comp_name.get(i, name_of_id.get(i, i))))
    already = {x["name"] for x in sub}
    for r in off.itertuples():
        if r.central_seats > 0 or r.list in already or r.list not in mshare:
            continue
        g = recent[recent["list_name"] == r.list]
        vals = []
        for q in g.itertuples():
            if pd.notna(q.seats) and q.seats > 0:
                vals.append(q.seats / 120 * 100)
            elif pd.notna(q.vote_pct):
                vals.append(float(q.vote_pct))
        sub.append({"name": r.list, "kind": "list",
                    "polled": round(float(np.mean(vals)), 1) if vals else None,
                    "src": "national", "share": round(float(mshare[r.list]) * 100, 1),
                    "pass": round(float(r.p_pass), 3)})
    # columns a resolved event zeroes in every draw (e.g. a split that did
    # not happen) are not contenders
    sub = [x for x in sub if x["share"] > 0]
    sub.sort(key=lambda x: (-x["share"], -(x["polled"] or 0)))

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
    # certainty layer: today's undecided pool (median of the last 45 days of
    # the genuine-undecided filings) and the expected per-side transfer at
    # the posterior mean lean (the magnitude draw has mean one), exactly as
    # bayes_model._certainty_layer computes it
    import bayes_model as bm
    a_, b_ = bm.U_LEAN_BETA
    excess = (a_ / (a_ + b_) - bm.U_PROP_ANTI) / (bm.U_LEAN_BASE - bm.U_PROP_ANTI)
    side = bm.U_POOL * bm.U_TURNOUT * (bm.U_EXCESS_PER_SIDE if bm.U_LEAN_PER_SIDE
                                       else bm.U_EXCESS_ANTI) * excess * 120
    fit["u_pool_pct"] = round(bm.U_POOL * 100)
    fit["u_side_seats"] = round(side, 1)
    fit["u_gap_seats"] = round(2 * side, 1) if bm.U_LEAN_PER_SIDE else round(side, 1)
    fit["u_leaned_n"] = round(a_ + b_ - bm.U_PRIOR_N)
    # a tie prints as "-0.0" otherwise
    if isinstance(fit.get("trail_margin_seats"), (int, float)):
        fit["trail_margin_seats"] = round(float(fit["trail_margin_seats"]), 1) + 0.0

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

    # Expected seats (the mixture mean), not the central count: a list at
    # 0 central seats but a real pass probability (Amcha, the Reservists,
    # Blue and White) still lives somewhere, and the micro-lists too.
    seats_by = dict(zip(mix["list"], mix["mean"]))
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
            "examples": [" ".join(str(x).split()) for x in g.nlargest(3, "eligible")["name"]],
        })
    kalpi.sort(key=lambda k: -k["eligible"])

    from site_ledger import build_ledger, build_ratings
    ledger = build_ledger(fit)
    ratings = build_ratings(fit)

    return {
        "asof": str(off["asof"].iloc[0]), "parties": parties, "sub": sub,
        "ledger": ledger, "ratings": ratings,
        "blocs": blocs, "formation": formation, "pm": pm, "events": events,
        "house": house, "val": build_val(), "below": below, "counts": counts, "fit": fit,
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
