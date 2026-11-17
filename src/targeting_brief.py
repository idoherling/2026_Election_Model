"""Targeting layer: the model brief for content writers and reviewers.

Writes data/processed/targeting/research/MODEL_BRIEF_v2.md from the current pipeline outputs:
forecast headline, exchange rates, saturation and realistic budgets, tiers, segments, top
localities, robustness, validation and the strategic levers. Run after the pipeline.
"""

from __future__ import annotations

import datetime as dt
import json

import pandas as pd

import targeting_planner as tp
from scrape_polls import PROCESSED_DIR

P = PROCESSED_DIR
T = P / "targeting"
SHORT = {"Bennett 2026 + Yesh Atid": "Together", "The Democrats": "Democrats", "United Torah Judaism": "UTJ",
         "Balad + Hadash-Ta'al": "Joint List", "Yisrael Beytenu": "YB", "Otzma Yehudit": "Otzma",
         "Religious Zionist Party": "RZP-Zehut", "Amcha Yisrael": "Amcha",
         "Reservists – Economic Party": "Reservists", "Blue and White": "Blue and White"}
CHANGE_OUT = ["Change coalition (without Ra'am)", "Change coalition with unaligned / Amcha",
              "Change coalition with a haredi party", "Centre minority backed by the Joint List",
              "Change coalition with Ra'am"]


def main() -> None:
    fc = pd.read_csv(P / "official_forecast.csv")
    bl = pd.read_csv(P / "mixture_blocs.csv").iloc[0]
    gov = pd.read_csv(P / "government_formation.csv")
    pm = pd.read_csv(P / "pm_probabilities.csv")
    cg = gov.set_index("outcome")["probability"]
    change = sum(cg.get(k, 0) for k in CHANGE_OUT)
    loc = pd.read_csv(T / "localities.csv").sort_values("locality").reset_index(drop=True)
    seg = pd.read_csv(T / "segments.csv")
    val = json.loads((T / "validation.json").read_text())
    sens = json.loads((T / "sensitivity_summary.json").read_text())
    mv = pd.read_csv(T / "marginal_values.csv")
    lev = json.loads((T / "levers.json").read_text())
    today = dt.date.today()
    out = []
    w = out.append

    w("# MODEL BRIEF for content writers (Change Bloc Victory Guide)\n")
    w(f"Context: Israel's 26th Knesset election is Tue 27 Oct 2026 (brief generated {today:%a %d %b %Y}, "
      f"D-{(dt.date(2026, 10, 27) - today).days}). The change bloc: Yashar (Eisenkot), Together (Bennett 2026 + "
      "Yesh Atid; ballot letters רק), The Democrats (Golan), Yisrael Beytenu (Liberman). Netanyahu bloc (NB) = "
      "Likud, Shas, UTJ, Otzma, RZP-Zehut, Amcha, Noam, Haredi Public. Arab lists = Ra'am, Joint List (Balad + "
      "Hadash-Ta'al). Reservists-Economic (Hendel/Zelekha) is a right-of-centre, reservist-branded list near the "
      "threshold. Blue and White (Gantz) withdrew on 19 Oct without an endorsement; the forecast routes its vote.")
    w("Forecast (polls to " + str(fc["asof"].iloc[0]) + "): " + ", ".join(
        f"{SHORT.get(r.list, r.list)} {int(r.central_seats)}" + (f" (pass {r.p_pass:.2f})" if r.p_pass < 0.95 else "")
        for r in fc.itertuples() if r.p_pass >= 0.005 or r.central_seats > 0)
      + f". P(NB>=61) {bl.p_nb_61:.1%}; P(change bloc alone >=61) {bl.p_anti_61:.1%}; with Ra'am "
        f"{bl.p_anti_raam_61:.1%}; neither {bl.p_neither:.1%}.")
    w("Government outcomes (formation model): " + "; ".join(f"{r.outcome} {r.probability:.1%}" for r in gov.itertuples())
      + f". Change-led government (sum of change outcomes) {change:.1%}. PM: "
      + "; ".join(f"{r.pm} {r.probability:.1%}" for r in pm.itertuples()) + ".")
    w("Key dates: final published polls Fri 23 Oct (poll-publication ban from the end of Friday: Sat 24 - Tue 27 "
      "Oct); election day Tue 27 Oct, polls 07:00-22:00; double-envelope votes counted centrally afterwards.\n")
    w("Every model number in the site's prose is a live token filled from the pipeline (src/targeting_facts.py); "
      "check any number with `cd src && ../.venv/bin/python targeting_facts.py get <key>`.\n")

    w("## Exchange rate per 10,000 extra votes (pp of probability; seats for change_seats)\n")
    m = mv[mv.share_mean > 0.003].copy()
    for c in ["change_govt", "block_nb", "change61", "change_raam61"]:
        m[c] = (m[c] * 100).round(2)
    m["change_seats"] = m["change_seats"].round(3)
    w(m[["list", "share_mean", "p_pass", "change_govt", "block_nb", "change_seats"]].to_csv(index=False))
    vps = 1 / val["mv_ref_per_vote"]["change_seats"]
    w(f"One net vote for an average change list = {val['mv_ref_per_vote']['change_seats']:.3g} expected change-bloc "
      f"seats (about {round(vps, -3):,.0f} votes per expected seat).\n")

    w("## Saturation potential (net votes; every positive station area at 35%, plus list programmes at 30% identified)\n")
    for o in ["change_govt", "block_nb", "change_seats"]:
        s = {p: round(loc[f"{o}__{p}"].sum()) for p in ["potential", "area_pot", "list_pot", "gotv_pot", "pers_pot",
                                                        "resc_pot", "area_contacts", "list_contacts"]}
        w(f"- {o}: {s}")
    w("\n## Realistic budgets (Arab localities, Arab-led stations, access-excluded and low-confidence Druze towns "
      "excluded; ranges = min-max across sensitivity scenarios)\n")
    U = tp.load_units()
    tr = tp.tranches(U, loc["locality"])
    core = set(loc.index[loc.segment.str.startswith("arab") | loc.field_excluded.notna() | loc.low_confidence.notna()])
    arab_only = set(loc.index[loc.segment.str.startswith("arab") | loc.field_excluded.notna()])
    sb = sens.get("budgets", {})
    for o in ["change_govt", "block_nb", "change_seats"]:
        for b in [150_000, 400_000]:
            for ident in [0.0, 0.3]:
                r = tp.allocate(tr[o], b, ident, exclude=core)
                k = f"{b}_{ident if ident else '0.0'}"
                v = [d[o][k] for n, d in sb.items() if n not in ("base", "lists_off", "druze_minus20", "persuasion_no_side")]
                eff = r["ve"] * val["mv_ref_per_vote"][o] * (100 if o != "change_seats" else 1)
                dz = tp.allocate(tr[o], b, ident, exclude=arab_only)["ve"] - r["ve"]
                top = sorted(r["alloc"].items(), key=lambda kv: -kv[1]["ve"])[:8]
                w(f"- {o}, {b:,} contacts, {int(ident * 100)}% identified: {r['ve']:,.0f} net votes "
                  f"(range {min(v):,.0f}-{max(v):,.0f}; {eff:.3f} {'pp' if o != 'change_seats' else 'seats'}); "
                  f"Druze towns would add {dz:,.0f}; {r['localities']} localities; top: "
                  + ", ".join(f"{loc.at[i, 'name_en']} {a['ve']:.0f}" for i, a in top))

    w("\n## Tiers (change_govt)\n")
    w(str(loc["change_govt__tier"].value_counts().to_dict()))
    for t in ["Turnout engine", "Supporter-list ground", "Persuasion battleground"]:
        sub = loc[loc["change_govt__tier"] == t].sort_values("change_govt__potential", ascending=False)
        w(f"- {t}: " + (", ".join(f"{r.name_en} ({r.change_govt__potential:.0f})" for r in sub.itertuples()) or "none"))
    w("\n## Segments\n")
    cols = ["segment", "label", "localities", "eligible", "turnout_2022", "p26_change", "p26_nb", "p26_arab",
            "persuadable_voters", "rescue_voters", "change_govt__potential", "change_govt__share", "block_nb__potential"]
    w(seg[cols].round(3).to_csv(index=False))
    w("## Top 30 localities by change_govt potential (non-Arab)\n")
    c2 = ["name_en", "segment", "eligible", "turnout_resident", "p26_change", "p26_nb", "lead_change_list",
          "change_govt__potential", "change_govt__area_pot", "change_govt__list_pot", "change_govt__eff1k",
          "change_govt__tier", "low_confidence"]
    na = loc[~loc.segment.str.startswith("arab")]
    w(na.sort_values("change_govt__potential", ascending=False).head(30)[c2].round(3).to_csv(index=False))
    w("## Robustness (sensitivity; Spearman vs base / top-25 overlap)\n")
    for o, d in sens["objectives"].items():
        w(f"- {o}: " + "; ".join(f"{sens['labels'][k]}: {v['spearman']} / {v['top25_overlap']}"
                                 for k, v in d["scenarios"].items() if k != "base"))
    w("\n## Strategic levers (exact scenario engine; effect if the lever happens)\n")
    w(f"Base: P(change-led govt) {lev['base']['change_govt']:.1%}, P(NB<61) {lev['base']['block_nb']:.1%}, "
      f"expected change seats {lev['base']['change_seats']:.1f}.")
    for x in lev["scenarios"]:
        d = x["delta"]
        w(f"- [{x['group']}] {x['title']}: {x['votes']:,} votes. Change-led govt {100 * d['change_govt']:+.2f} pts; "
          f"deny-61 {100 * d['block_nb']:+.2f} pts; change seats {d['change_seats']:+.2f}. ({x['what']})")
    (T / "research" / "MODEL_BRIEF_v2.md").write_text("\n".join(out))
    print("wrote", T / "research" / "MODEL_BRIEF_v2.md")


if __name__ == "__main__":
    main()
