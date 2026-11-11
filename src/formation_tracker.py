"""What happens next: the formation tree after the vote (dossier s.74).

Before the election, government_formation.py ran every seat draw through a
tree of behavioural gates (will UTJ cross, will Liberman sit with the
haredim, ...). After it, two things are known that the tree could only
assume: the Knesset, and what the parties have since said and done. This
module changes those two inputs and nothing else:

  1. the seats are the certified result
     (data/processed/result_2026_certified.csv);
  2. each behavioural assumption is updated through an EVIDENCE LEDGER: a
     dated, sourced observation, tied to one parameter, with a direction and
     one of three strengths that multiply the odds (weak x1.5, moderate
     x2.5, strong x5). The parameter's posterior is the prior of the forecast
     of record moved by the product of its items;
  3. the same tree is run on (1): the same gates, and the same deadlock
     stage, which takes WHETHER a government forms from the Israeli record
     (2 repeat elections in 7 deadlocks) and lets the gates decide WHICH.

Two additions, both stated on the page:
  - the two haredi parties do not decide independently. The tree drew Shas
    and UTJ separately; a conscription arrangement UTJ accepts removes
    Shas's main reason to refuse, so Shas enters as "joins, given UTJ does"
    (SHAS_FOLLOWS), with a prior from the record of Shas and non-Likud
    premiers (three joined of six asked: 1992, 1999, 2006 against 1990,
    2008, 2021) rather than the tree's unconditional 0.10;
  - the mandate: a government the change bloc forms inside Eisenkot's
    mandate is led by Eisenkot (MANDATE_PM).

Like the layer it extends, this is scenario analysis: coalition behaviour
has no likelihood, the strengths are judgment, and the output is only as
good as the ledger. The frozen forecast of record is not touched.

    python src/formation_tracker.py        writes data/processed/formation_tracker.json
    python src/formation_tracker.py --print  the tables, no write
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import build_variants as bv
import government_formation as gf
from scrape_polls import PROCESSED_DIR

OUT = PROCESSED_DIR / "formation_tracker.json"
RESULT = PROCESSED_DIR / "result_2026_certified.csv"
FROZEN = PROCESSED_DIR / "frozen_forecast_2026-10-23.json"
AS_OF = "2026-11-11"
N_ROWS = 4000            # identical rows of the certified Knesset: Monte Carlo over behaviour only
VECTORS = 200            # parameter vectors (government_formation.main's production count)
STRENGTH = {"weak": 1.5, "moderate": 2.5, "strong": 5.0}

# Sources (each fetched and read on 11 Nov 2026)
SRC = {
    "toi_mandate": "https://www.timesofisrael.com/eisenkot-gets-nod-to-form-government-vows-unconventional-acts-in-time-of-emergency/",
    "jns_recs": "https://www.jns.org/news/israel-news/herzog-67-mks-recommend-eisenkot-46-netanyahu-mandate-to-be-assigned-sunday",
    "jpost_arab": "https://www.jpost.com/israel-election-2026/article-913448",
    "jpost_liberman": "https://www.jpost.com/israel-election-2026/article-914045",
    "jpost_shas": "https://www.jpost.com/israel-election-2026/article-914154",
    "jpost_recs": "https://www.jpost.com/israel-news/article-913842",
    "ynet_liberman": "https://www.ynetnews.com/article/rjya9vaaml",
    "ynet_fades": "https://www.ynetnews.com/article/bjnjwzw0gx",
    "jpost_cancel": "https://www.jpost.com/israel-news/politics-and-diplomacy/article-914502",
    "toi_utj": "https://www.timesofisrael.com/haredi-utj-says-it-wont-vote-to-replace-knesset-speaker-rejecting-opposition-push/",
    "toi_talks": "https://www.timesofisrael.com/liveblog_entry/report-eisenkot-liberman-agree-to-open-talks-with-haredi-parties-eyeing-draft-law-concessions/",
    "walla_utj": "https://www.walla.co.il/news/politics/383959645",
    "polymarket": "https://polymarket.com/event/who-will-be-the-next-prime-minister-of-israel-after-the-next-election",
    "cec": "https://votes26.bechirot.gov.il/nationalresults?lang=he",
}

# Tracker-only priors (not parameters of the pre-election tree): (mean, effective n, why)
SHAS_FOLLOWS = (0.45, 6, "Shas and non-Likud premiers who needed it: joined 1992, 1999, 2006; "
                         "refused 1990, 2008, 2021 (government_formation.COND's record)")
# PM inside a change-led government formed under Eisenkot's mandate:
#            Eisenkot  Bennett  Liberman  Lapid  other
MANDATE_PM = [0.92, 0.03, 0.03, 0.00, 0.02]

# The ledger. param: a key of government_formation.BEHAVIOR, or "shas_follows".
# dir +1 raises the parameter, -1 lowers it.
LEDGER = [
    # --- Liberman and the haredi parties
    dict(param="liberman_haredi_ok", date="2026-11-06", dir=+1, strength="strong", src="jpost_liberman",
         en="Liberman says he will \"be flexible and compromise\" on the draft law; Channel 12 reports he has dropped his veto on sitting with haredi parties.",
         he="ליברמן הודיע שיהיה מוכן \"להתגמש ולהתפשר\" בחוק הגיוס; בחדשות 12 דווח שהסיר את הווטו על ישיבה עם המפלגות החרדיות."),
    dict(param="liberman_haredi_ok", date="2026-11-09", dir=+1, strength="moderate", src="toi_talks",
         en="Eisenkot and Liberman agree to open talks with Shas and UTJ (Kan).",
         he="איזנקוט וליברמן סיכמו לפתוח במגעים עם ש\"ס ויהדות התורה (כאן)."),
    # --- Liberman and a government that leans on Arab abstention
    dict(param="liberman_minority_ok", date="2026-11-06", dir=-1, strength="moderate", src="jpost_liberman",
         en="Liberman's third red line: no government that relies on the Joint List or Ra'am abstaining.",
         he="הקו האדום השלישי של ליברמן: לא לממשלה שנשענת על הימנעות של הרשימה המשותפת או של רע\"ם."),
    dict(param="liberman_minority_ok", date="2026-11-08", dir=-1, strength="weak", src="ynet_liberman",
         en="He repeats it after the mandate (\"That will not happen\") and threatens to vote against.",
         he="אחרי הטלת המנדט חזר על כך (\"זה לא יקרה\") ואיים להצביע נגד."),
    dict(param="liberman_minority_ok", date="2026-11-06", dir=+1, strength="weak", src="jpost_liberman",
         en="His first two red lines pull the other way: Netanyahu's premiership must end, and no further election.",
         he="שני הקווים האדומים הראשונים שלו מושכים לכיוון ההפוך: כהונת נתניהו חייבת להסתיים, ואין ללכת לבחירות נוספות."),
    # --- United Torah Judaism
    dict(param="utj_defects", date="2026-11-05", dir=+1, strength="weak", src="jns_recs",
         en="UTJ recommends nobody to the President: its seven MKs are the only ones outside both tallies (67 for Eisenkot, 46 for Netanyahu). Reports had pointed to this since September, so it moves the prior only a little.",
         he="יהדות התורה לא המליצה על אף מועמד: שבעת חבריה הם היחידים מחוץ לשני המניינים (67 לאיזנקוט, 46 לנתניהו). הדיווחים צפו זאת מאז ספטמבר, ולכן ההשפעה קטנה."),
    dict(param="utj_defects", date="2026-11-06", dir=+1, strength="moderate", src="jpost_liberman",
         en="A UTJ source: with a satisfactory conscription law \"we'll go with them for sure\"; chair Asher welcomes \"the flexibility displayed by all political players\".",
         he="גורם ביהדות התורה: עם חוק גיוס מניח את הדעת \"נלך איתם בוודאות\"; היו\"ר אשר בירך על \"הגמישות שמפגינים כל השחקנים הפוליטיים\"."),
    dict(param="utj_defects", date="2026-11-09", dir=+1, strength="moderate", src="toi_talks",
         en="A softened draft law is reported on offer: a transitional arrangement of 12 to 18 months with no sanctions (Channel 12).",
         he="לפי הדיווחים מוצע חוק גיוס מרוכך: הסדר מעבר של 12 עד 18 חודשים בלי סנקציות (חדשות 12)."),
    dict(param="utj_defects", date="2026-11-09", dir=-1, strength="weak", src="toi_talks",
         en="The talks are at an early stage and UTJ has not been approached officially (Channel 12, Kan).",
         he="המגעים בשלב מוקדם, ואל יהדות התורה עדיין לא פנו רשמית (חדשות 12, כאן)."),
    dict(param="utj_defects", date="2026-11-09", dir=-1, strength="weak", src="toi_utj",
         en="UTJ declines to help replace the Knesset speaker now; Eisenkot's principles include national service for all, which the haredi parties oppose.",
         he="יהדות התורה סירבה לסייע בהחלפת יו\"ר הכנסת כעת; עקרונות איזנקוט כוללים שירות לאומי לכולם, שהמפלגות החרדיות מתנגדות לו."),
    # --- Shas, given UTJ joins
    dict(param="shas_follows", date="2026-11-04", dir=-1, strength="weak", src="jpost_recs",
         en="Shas recommends Netanyahu.",
         he="ש\"ס המליצה על נתניהו."),
    dict(param="shas_follows", date="2026-11-07", dir=-1, strength="moderate", src="jpost_shas",
         en="Shas calls reports that it will join Eisenkot \"complete fake news\" and says its Council of Torah Sages keeps it in the right-wing bloc.",
         he="ש\"ס כינתה את הדיווחים על הצטרפותה לאיזנקוט \"פייק ניוז מוחלט\" והודיעה שמועצת חכמי התורה מותירה אותה בגוש הימין."),
    dict(param="shas_follows", date="2026-11-07", dir=+1, strength="weak", src="jpost_shas",
         en="Channel 12: Shas would not obstruct a coalition that includes UTJ, and is expected to back the softer draft law under pressure from UTJ's Rabbi Lando.",
         he="חדשות 12: ש\"ס לא תכשיל קואליציה שכוללת את יהדות התורה, וצפויה לתמוך בחוק הגיוס המרוכך בלחץ הרב לנדו."),
    # --- the Arab lists
    dict(param="raam_supports", date="2026-11-05", dir=+1, strength="strong", src="jpost_arab",
         en="Ra'am recommends Eisenkot.",
         he="רע\"ם המליצה על איזנקוט."),
    dict(param="jl_supports", date="2026-11-05", dir=+1, strength="strong", src="jpost_arab",
         en="The Joint List recommends Eisenkot.",
         he="הרשימה המשותפת המליצה על איזנקוט."),
    # --- a change-bloc list joins a Netanyahu-led government (the 2020 path)
    dict(param="centre_defects", date="2026-11-08", dir=-1, strength="weak", src="toi_mandate",
         en="Eisenkot, now holding the mandate, repeats that he will not serve in a Netanyahu government.",
         he="איזנקוט, שהמנדט בידיו, חזר והודיע שלא יכהן בממשלת נתניהו."),
    dict(param="centre_defects", date="2026-11-10", dir=-1, strength="weak", src="jpost_cancel",
         en="Yashar cancels its first meeting with Likud after Netanyahu's Knesset speech; Bennett heckles the speech.",
         he="ישר ביטלה את פגישתה הראשונה עם הליכוד אחרי נאום נתניהו בכנסת; בנט קרא קריאות ביניים במהלך הנאום."),
    dict(param="centre_defects", date="2026-11-09", dir=+1, strength="weak", src="ynet_fades",
         en="Netanyahu courts a unity government daily and says he will talk \"right now with any party\".",
         he="נתניהו מחזר מדי יום אחר ממשלת אחדות ואומר שהוא מוכן לשוחח \"כבר עכשיו עם כל מפלגה\"."),
    # --- Likud without Netanyahu at the head
    dict(param="likud_sans_bibi", date="2026-11-04", dir=-1, strength="moderate", src="cec",
         en="Likud won 27 seats, six more than its final polls. A leader who has just beaten the polls is harder to remove, and no Likud figure has broken ranks.",
         he="הליכוד זכה ב־27 מנדטים, שישה יותר מהסקרים האחרונים. קשה יותר להדיח מנהיג שזה עתה גבר על הסקרים, ואיש בליכוד לא שבר שורות."),
    dict(param="likud_sans_bibi", date="2026-11-10", dir=-1, strength="weak", src="ynet_fades",
         en="Netanyahu offers no rotation and insists Likud must lead.",
         he="נתניהו אינו מציע רוטציה ועומד על כך שהליכוד יוביל."),
    dict(param="likud_sans_bibi", date="2026-11-08", dir=+1, strength="weak", src="toi_mandate",
         en="President Herzog floats a unity government that includes both Eisenkot and Netanyahu.",
         he="הנשיא הרצוג העלה אפשרות של ממשלת אחדות שכוללת גם את איזנקוט וגם את נתניהו."),
]

# The legal calendar (Basic Law: The Government), from the mandate of 8 Nov.
TIMELINE = [
    dict(date="2026-11-08", en="Herzog gives Eisenkot the mandate (67 recommendations to 46, UTJ's 7 for nobody).",
         he="הרצוג הטיל את המנדט על איזנקוט (67 ממליצים מול 46; שבעת חברי יהדות התורה לא המליצו).", src="toi_mandate"),
    dict(date="2026-12-06", en="Eisenkot's 28 days end.", he="תום 28 הימים של איזנקוט.", src="toi_mandate"),
    dict(date="2026-12-20", en="The latest date if the President adds the full 14 days.",
         he="המועד האחרון אם הנשיא יאריך ב־14 הימים המלאים.", src="toi_mandate"),
    dict(date="2027-01", en="If he fails: a second nominee, in practice Netanyahu, gets 28 days.",
         he="אם ייכשל: מועמד שני, בפועל נתניהו, יקבל 28 ימים.", src="toi_mandate"),
    dict(date="2027-02", en="If that fails too: 21 days in which 61 MKs can name anyone.",
         he="אם גם הוא ייכשל: 21 ימים שבהם 61 חברי כנסת יכולים להציע כל מועמד.", src="toi_mandate"),
    dict(date="2027-05", en="If nobody does: the Knesset dissolves and Israel votes again within about 90 days.",
         he="אם אף אחד לא יצליח: הכנסת מתפזרת ובחירות חדשות נערכות בתוך כ־90 יום.", src="toi_mandate"),
]

# Prediction market, read 11 Nov 2026 08:44 UTC (gamma-api.polymarket.com). Its question differs
# from ours: it pays on the next PM sworn in by the end of 2027, AFTER a repeat election too.
MARKET = dict(name="Polymarket", url=SRC["polymarket"], read_utc="2026-11-11T08:44:26Z", volume_usd=91_330_049,
              prices={"Eisenkot": 0.575, "Netanyahu": 0.2395, "Liberman": 0.0495, "Bennett": 0.0305},
              note_en="Pays on the next prime minister sworn in by the end of 2027, including after a repeat election; a caretaker does not count.",
              note_he="השוק משלם לפי ראש הממשלה הבא שיושבע עד סוף 2027, גם אחרי בחירות חוזרות; ראש ממשלת מעבר אינו נחשב.")


def _logit(p: float) -> float:
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def priors() -> dict:
    """{param: (mean, effective n)} for every parameter the ledger touches."""
    out = {k: (gf.BEHAVIOR[k], gf.BEHAVIOR_NEFF[k]) for k in {e["param"] for e in LEDGER} if k in gf.BEHAVIOR}
    out["shas_follows"] = SHAS_FOLLOWS[:2]
    return out


def posterior(ledger=LEDGER, pri=None) -> dict:
    """Each parameter's prior moved on the odds scale by its ledger items.
    {param: {prior, n, posterior, items, log_odds_shift}}; n is unchanged (the
    strengths are judgment, so the spread is not narrowed)."""
    pri = pri or priors()
    out = {}
    for k, (p0, n) in pri.items():
        items = [e for e in ledger if e["param"] == k]
        shift = sum(e["dir"] * math.log(STRENGTH[e["strength"]]) for e in items)
        out[k] = {"prior": p0, "n": n, "posterior": round(_sigmoid(_logit(p0) + shift), 4),
                  "items": len(items), "log_odds_shift": round(shift, 4)}
    return out


def knesset() -> dict:
    """The certified Knesset as {list name of the forecast: seats}."""
    reg = json.loads(FROZEN.read_text(encoding="utf-8"))["payload"]["lists"]
    by_letter = {(v.get("letters") or v.get("letter")): k for k, v in reg.items()}
    res = pd.read_csv(RESULT, comment="#")
    return {by_letter[r.list]: int(r.seats) for r in res.itertuples() if r.seats > 0}


def knesset_frame(seats: dict, n: int = N_ROWS) -> pd.DataFrame:
    cols = list(dict.fromkeys(list(seats) + gf.NB_CORE + gf.CENTRE + [gf.JOINT_LIST, gf.RAAM, gf.AMCHA]))
    return pd.DataFrame([{c: seats.get(c, 0) for c in cols}] * n)


@contextlib.contextmanager
def tree(behavior: dict = None, neff: dict = None, pm_alloc: dict = None, resolution: str = None):
    """government_formation's module state for the block, restored after it."""
    keep = (dict(gf.BEHAVIOR), dict(gf.BEHAVIOR_NEFF), {k: list(v) for k, v in gf.PM_ALLOC.items()},
            gf.STAGE_RESOLUTION)
    try:
        if behavior:
            gf.BEHAVIOR.update(behavior)
        if neff:
            gf.BEHAVIOR_NEFF.update(neff)
        if pm_alloc:
            gf.PM_ALLOC.update(pm_alloc)
        if resolution:
            gf.STAGE_RESOLUTION = resolution
        yield
    finally:
        for live, old in ((gf.BEHAVIOR, keep[0]), (gf.BEHAVIOR_NEFF, keep[1]), (gf.PM_ALLOC, keep[2])):
            live.clear()
            live.update(old)
        gf.STAGE_RESOLUTION = keep[3]


def updated_behavior(post: dict) -> tuple:
    """The tree's inputs after the ledger: (behaviour means, effective n).
    shas_follows enters as the tree's Shas gate: a change + haredi government
    needs both parties at these seats, so the gate is read conditionally."""
    b = {k: v["posterior"] for k, v in post.items() if k in gf.BEHAVIOR}
    b["shas_defects"] = post["shas_follows"]["posterior"]
    return b, {"shas_defects": post["shas_follows"]["n"]}


def run(frame: pd.DataFrame, **state) -> dict:
    """The tree's summary on a seat frame under the given state (see tree())."""
    with tree(**state), contextlib.redirect_stdout(io.StringIO()):
        s = bv.formation_summary(frame, M=VECTORS)
    return {"groups": s["groups"], "pm": s["pm"], "outcomes": s["outcomes"]}


def pm_table(r: dict) -> dict:
    return {row[0]: {"p": row[1], "lo": row[2], "hi": row[3]} for row in r["pm"]}


def build() -> dict:
    seats = knesset()
    frame = knesset_frame(seats)
    post = posterior()
    b, n = updated_behavior(post)
    mandate = {4: MANDATE_PM, 5: MANDATE_PM, 8: MANDATE_PM}
    base = run(frame)                                              # the frozen tree on the certified seats
    now = run(frame, behavior=b, neff=n, pm_alloc=mandate)        # + the ledger
    # sensitivities: one input back to its prior at a time, and the tree's independent Shas
    sens = {}
    for k in ("utj_defects", "liberman_haredi_ok", "likud_sans_bibi", "centre_defects"):
        bb = dict(b, **{k: post[k]["prior"]})
        sens[f"{k} at its prior"] = pm_table(run(frame, behavior=bb, neff=n, pm_alloc=mandate))
    bb = dict(b, shas_defects=gf.BEHAVIOR["shas_defects"])
    sens["Shas drawn independently (the tree's 0.10)"] = pm_table(
        run(frame, behavior=bb, neff={"shas_defects": gf.BEHAVIOR_NEFF["shas_defects"]}, pm_alloc=mandate))
    bb = dict(b, utj_defects=round(_sigmoid(_logit(b["utj_defects"]) + math.log(2.5)), 4))
    sens["UTJ one moderate step likelier"] = pm_table(run(frame, behavior=bb, neff=n, pm_alloc=mandate))
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))["payload"]["models"][0]
    rec = gf.deadlock_posterior()
    return {
        "as_of": AS_OF, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "knesset": seats, "strength": STRENGTH,
        "ledger": [dict(e, url=SRC[e["src"]]) for e in LEDGER],
        "parameters": post, "shas_follows_prior": SHAS_FOLLOWS[2], "mandate_pm": MANDATE_PM,
        "record": {"repeat_mean": round(float(rec[0] / (rec[0] + rec[1])), 3), "beta": [float(rec[0]), float(rec[1])],
                   "text": "2 repeat elections in 7 deadlocked Knessets (1984-2021)"},
        "pre_election": {"pm": frozen.get("pm"), "groups": frozen.get("groups")},
        "result_only": {"groups": base["groups"], "pm": pm_table(base), "outcomes": base["outcomes"]},
        "now": {"groups": now["groups"], "pm": pm_table(now), "outcomes": now["outcomes"]},
        "sensitivity": sens, "timeline": [dict(t, url=SRC[t["src"]]) for t in TIMELINE],
        "market": MARKET, "sources": SRC,
    }


def _print(d: dict) -> None:
    print(f"as of {d['as_of']}; Knesset {d['knesset']}")
    print("\nparameter                  prior -> posterior  (items, log-odds shift)")
    for k, v in d["parameters"].items():
        print(f"  {k:24s} {v['prior']:.3f} -> {v['posterior']:.3f}   ({v['items']}, {v['log_odds_shift']:+.2f})")
    for lab, key in (("the frozen tree on the certified seats", "result_only"), ("with the ledger", "now")):
        r = d[key]
        print(f"\n{lab}\n  groups " + ", ".join(f"{g} {v[0]:.3f}" for g, v in r["groups"].items()))
        print("  PM     " + ", ".join(f"{n} {v['p']:.3f} [{v['lo']:.2f}-{v['hi']:.2f}]" for n, v in r["pm"].items()))
        print("  types  " + ", ".join(f"{o} {p:.3f}" for o, p in r["outcomes"] if p > 0.0005))
    print("\nsensitivity (P next PM)")
    for lab, r in d["sensitivity"].items():
        print(f"  {lab:44s} " + ", ".join(f"{n} {v['p']:.2f}" for n, v in list(r.items())[:5]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--print", action="store_true", help="print the tables without writing")
    a = ap.parse_args(argv)
    d = build()
    _print(d)
    if not a.print:
        OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
