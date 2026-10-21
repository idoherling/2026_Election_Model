"""Forecast history: every published build of the forecast, read back from git.

Reads every committed version of output/site/site_data.json (``git show
<hash>:output/site/site_data.json`` along the first-parent history of the
checked-out branch), plus the working copy when its headline differs from
HEAD's, and writes data/processed/forecast_history.csv with one row per build.
history_payload (below, called by src/build_site.py) turns the CSV into the
site's "history" key.

Run: PYTHONPATH=src python src/build_history.py && PYTHONPATH=src python src/build_site.py

Columns
  commit, commit_date  short hash and committer date (ISO 8601); the working
                       copy is "working", dated by the file's mtime
  asof                 the build's data date (official_forecast.csv asof)
  subject              first line of the commit message (CSV only, never
                       shown on the site)
  kind                 what moved the forecast in this build:
      polls  new inputs only: polls, CEC filings, or real-world events
             (withdrawals, court rulings, surplus pacts) and a refit
      model  a methodology change with no new inputs, including the owner's
             rulings on how a list is counted
      both   new inputs and a methodology change in the same build, or a
             build that cannot be split; the default whenever unsure
      site   the headline did not change: site, annex or validation work
  moved                1 when any headline field differs from the previous
                       build (the first build counts as moved)
  sections             decision-log sections (docs/priors_dossier.md "## N.")
                       the build implements, ";"-separated
  label_en, label_he   the short label the site shows (same content)
  nb, anti, anti_raam, neither, nb_mean   the bloc headline
  pm_<name>            P(PM) per name (pm_repeat = no one, repeat election;
                       pm_likud_successor was "rotation / Likud successor"
                       before 16 Oct and the unity-government successor after)
  seats_, lo_, hi_, p_pass_<list>         central seats, 90% interval, P(pass)

The classification is curated per commit below (CURATED), from the commit
message and the decision log's section titles and dates. A commit that is
not curated yet is classified by a keyword rule that defaults to "both", and
gets a generic label. Early payloads lack some fields; a missing field is
left empty, never inferred (no per-list number is derived from bloc totals).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = "output/site/site_data.json"
OUT = ROOT / "data" / "processed" / "forecast_history.csv"
DOSSIER = ROOT / "docs" / "priors_dossier.md"

LIST_SLUG = {
    "Likud": "likud", "Yashar": "yashar", "Bennett 2026 + Yesh Atid": "together",
    "The Democrats": "democrats", "Yisrael Beytenu": "yisrael_beytenu", "Shas": "shas",
    "United Torah Judaism": "utj", "Otzma Yehudit": "otzma",
    "Religious Zionist Party": "rzp_zehut", "Ra'am": "raam",
    "Balad + Hadash-Ta'al": "joint_list", "Balad (alone)": "balad",
    "Reservists – Economic Party": "reservists_economic", "Blue and White": "blue_white",
    "Amcha Yisrael": "amcha", "Unity": "unity", "Zehut": "zehut", "Noam": "noam",
    "The Haredi Public": "haredi_public", "Israel First": "israel_first",
    "New Economic Party": "new_economic", "A Place for All of Us": "makom_lekulanu",
    # the registry renamed this row on filing day (s.31); kept as its own column
    "Zionist Home – The Reservists": "zionist_home_reservists",
    "Ahi – Back to the Roots": "ahi", "Tzomet Beit Yisrael": "beit_yisrael",
    "Code Black – Shield of the Torah World": "code_black", "El HaDegel": "el_hadegel",
    "Fiery Youth": "fiery_youth", "The Fourth Quarter": "fourth_quarter",
}
PM_SLUG = {
    "netanyahu": "netanyahu", "eisenkot": "eisenkot", "bennett": "bennett",
    "liberman": "liberman", "no one — repeat election": "repeat",
    "none (repeat election)": "repeat", "rotation / likud successor": "likud_successor",
    "a likud successor (unity government)": "likud_successor",
    "likud successor (unity)": "likud_successor", "another leader": "another_leader",
}
PM_ORDER = ["netanyahu", "eisenkot", "bennett", "repeat", "likud_successor", "liberman",
            "another_leader"]
BLOC_KEYS = [("nb", "nb"), ("anti", "anti"), ("antiRaam", "anti_raam"),
             ("neither", "neither"), ("nb_mean", "nb_mean")]

# The site tracks these lists (the eight largest) and these PM outcomes.
TRACK = ["Likud", "Yashar", "Bennett 2026 + Yesh Atid", "Balad + Hadash-Ta'al", "Shas",
         "United Torah Judaism", "Otzma Yehudit", "Religious Zionist Party"]
PM_TRACK = ["netanyahu", "eisenkot", "bennett", "repeat"]

# hash -> (kind, decision-log sections, label EN, label HE). Classified from
# the commit message and the decision log; "both" wherever a build mixed new
# inputs with a method change or the split is unclear.
CURATED = {
    "16ee58e": ("model", [], "First published build: the small parties itemised in the model",
                "הבנייה הראשונה שפורסמה: המפלגות הקטנות פורטו במודל"),
    "ff6f563": ("site", [], "Small-party ledger: Zehut no longer listed beside RZP–Zehut",
                "רשימת המפלגות הקטנות: זהות אינה מופיעה עוד לצד הציונות הדתית–זהות"),
    "27021b3": ("model", [], "Fiery Youth removed from the modelled lists",
                "צעירים בוערים הוסרה מהרשימות הממודלות"),
    "79ea94a": ("site", [], "Technical annex rewritten",
                "הנספח הטכני נכתב מחדש"),
    "661b25a": ("model", [15], "Small parties forecast at their expected actual vote",
                "המפלגות הקטנות נחזות לפי הקולות הצפויים להן בפועל"),
    "c5abb7c": ("both", [16], "2 Sept poll wave; pre-registered tripwires fired (RZP–Zehut, the Ra'am slate)",
                "גל הסקרים של 2 בספטמבר; כללים שנרשמו מראש הופעלו (הציונות הדתית–זהות, רשימת רע״ם)"),
    "82cbc16": ("both", [17], "Afkar Arab-sector poll; Makom Lekulanu added to the board",
                "סקר אפקאר במגזר הערבי; מקום לכולנו נוספה ללוח"),
    "06dd0bc": ("model", [], "Audit fixes: the RZP–Zehut series backcast across the merger",
                "תיקוני ביקורת: סדרת הציונות הדתית–זהות שוחזרה לאחור מעבר לאיחוד"),
    "a5c7c5d": ("site", [], "Poll ledger and pollster ratings added to the annex",
                "יומן הסקרים ודירוג המכונים נוספו לנספח"),
    "4283bfe": ("model", [18], "Certainty layer: soft support and the undecided pool",
                "שכבת הוודאות: תמיכה רכה ומאגר המתלבטים"),
    "8ccc7a1": ("model", [19, 20, 21], "Sector polls, time-varying house effects, conditional formation gates",
                "סקרים מגזריים, אפקטי בית משתנים בזמן ושערי הרכבה מותנים"),
    "969085d": ("model", [22], "Blue and White and Unity counted as unaligned",
                "כחול לבן והאחדות נספרות כלא משויכות"),
    "49b1acb": ("model", [23], "Pollster weighting audit, first pass",
                "ביקורת שקלול הסוקרים, סבב ראשון"),
    "206e875": ("model", [23], "Weighting audit resolved: the sampling floor rejected",
                "ביקורת השקלול הוכרעה: רצפת הדגימה נדחתה"),
    "51a7d29": ("model", [24], "Arab lists audit: filing shares renormalised, unified-list turnout",
                "ביקורת הרשימות הערביות: נרמול הנתחים בהגשות והשתתפות ברשימה מאוחדת"),
    "5fd403d": ("model", [25], "Stage-by-stage deep dive: fixes applied",
                "בדיקה שלב אחר שלב: התיקונים הוחלו"),
    "ff42eec": ("model", [26], "Central seats allocated on the mixture's mean shares",
                "המנדטים המרכזיים חולקו לפי נתחי הקולות הממוצעים של התערובת"),
    "4853abe": ("model", [27], "Round two: undecided pool, Arab turnout, measured transfers, calibrated width",
                "סבב שני: מאגר המתלבטים, ההשתתפות הערבית, מעברים מדודים ורוחב מכויל"),
    "2f0175c": ("site", [], "The small parties get their own section",
                "המפלגות הקטנות קיבלו מדור משלהן"),
    "30d7fa3": ("model", [28], "Accuracy round three: anchors retired, median centres",
                "סבב דיוק שלישי: העוגנים הוסרו, מרכזים חציוניים"),
    "82e4f67": ("polls", [29], "Three new polls; 13 new CEC filings; a filing-parser fix",
                "שלושה סקרים חדשים; 13 הגשות חדשות לוועדת הבחירות; תיקון במפענח ההגשות"),
    "b305ca9": ("polls", [30], "Unity withdraws; a Maariv poll",
                "האחדות פורשת; סקר של מעריב"),
    "9dd5e0d": ("polls", [31], "Filing day: 38 lists filed, open events closed; 6 polls and 7 filings",
                "יום הגשת הרשימות: 38 רשימות הוגשו והאירועים הפתוחים נסגרו; 6 סקרים ו־7 הגשות"),
    "4a6a19f": ("model", [32], "Editorial ruling: the Reservists–Economic list is unaligned",
                "הכרעת עריכה: המילואימניקים והכלכלית היא רשימה לא משויכת"),
    "9cb58be": ("model", [33], "Editorial ruling: Segalovitz's seat counts only with Ra'am",
                "הכרעת עריכה: המנדט של סגלוביץ׳ נספר רק יחד עם רע״ם"),
    "f91bcb2": ("site", [], "Ground game: every list's expected seats shown",
                "השטח: מוצגים המנדטים הצפויים של כל רשימה"),
    "904b147": ("model", [35], "Formation: unaligned lists close coalitions explicitly",
                "הרכבה: רשימות לא משויכות סוגרות קואליציות במפורש"),
    "89707a0": ("both", [36], "Accuracy round four shipped; polls to 10 Sept",
                "סבב הדיוק הרביעי נכנס לתחזית; סקרים עד 10 בספטמבר"),
    "e65b69d": ("both", [37], "Polls to 15 Sept; disqualification petitions added as open events",
                "סקרים עד 15 בספטמבר; עתירות הפסילה נוספו כאירועים פתוחים"),
    "dbc5555": ("polls", [37], "Polls to 16 Sept; refit",
                "סקרים עד 16 בספטמבר; התאמה מחדש"),
    "003af92": ("both", [38], "8 Oct catch-up: 22 polls, court rulings, surplus pacts, a Blue and White withdrawal event",
                "ההשלמה של 8 באוקטובר: 22 סקרים, פסיקות, הסכמי עודפים ואירוע פרישה של כחול לבן"),
    "b179245": ("polls", [40], "Six polls to 8 Oct; refit",
                "שישה סקרים עד 8 באוקטובר; התאמה מחדש"),
    "502a0a5": ("both", [41], "Accuracy round five shipped; polls to 12 Oct",
                "סבב הדיוק החמישי נכנס לתחזית; סקרים עד 12 באוקטובר"),
    "6da87ea": ("model", [42], "Every polled list modelled the same way (a 21-list fit)",
                "כל רשימה שנסקרה ממודלת באותה דרך (התאמה של 21 רשימות)"),
    "594d8ee": ("polls", [45], "Kantar, Channel 12 and Channel 13 polls; refit",
                "סקרים של קנטאר, חדשות 12 וערוץ 13; התאמה מחדש"),
    "a5bf54e": ("model", [43], "Arab turnout term graded and shipped",
                "איבר ההשתתפות הערבית נבחן ונכנס לתחזית"),
    "806c6f4": ("both", [46], "Centred-log-ratio latent shipped; the Otzma–Amcha pact dropped after Ben-Gvir's refusal",
                "המשתנה החבוי עבר ליחס לוגריתמי ממורכז; הסכם העודפים עוצמה–עמך הוסר אחרי סירוב בן גביר"),
    "f150aa1": ("both", [47, 49, 51], "Two polls; seat-law fidelity, formation calibration and the haredi family term",
                "שני סקרים; נאמנות לחוק חלוקת המנדטים, כיול ההרכבה ואיבר המשפחה החרדית"),
    "63b74b8": ("model", [52], "Formation outputs rebuilt; the pledge-break outcome split out",
                "פלטי ההרכבה נבנו מחדש; הפרת התחייבות הופרדה לתוצאה נפרדת"),
    "2ac0e41": ("site", [50], "Track record re-run on leave-one-out scorecards",
                "ביצועי העבר חושבו מחדש על כרטיסי דירוג בהשמטת־מחזור"),
    "9657905": ("site", [53, 54], "Checkpoint: filings parsed, two candidates graded and not shipped",
                "נקודת ביניים: הגשות פוענחו, שני מועמדים נבחנו ולא נכנסו"),
    "bad4469": ("both", [], "Evening refit with four filed or restored polls; the Agudah share set by the filed slate",
                "התאמה מחדש בערב עם ארבעה סקרים שהוגשו או שוחזרו; חלקה של אגודה נקבע לפי הרשימה שהוגשה"),
    "09ba1e9": ("polls", [], "Late refit with Kantar/Israel Hayom and a Channel 14 filing",
                "התאמה מחדש מאוחרת עם קנטאר/ישראל היום והגשה של ערוץ 14"),
    "e9a15a5": ("model", [58], "Event risk tied to the unpolled days before the blackout",
                "סיכון האירועים נקשר לימים שבלי סקרים לפני איסור הפרסום"),
    "cb4d1a6": ("site", [56], "A record-based formation split tested and not shipped",
                "חלוקת הרכבה לפי נתוני העבר נבחנה ולא נכנסה"),
    "5bdf849": ("site", [], "Forecast history section added",
                "נוסף פרק היסטוריית התחזית"),
    "590bd89": ("site", [], "Accessibility and design fixes",
                "תיקוני נגישות ועיצוב"),
    "1ca6c85": ("model", [59], "Pledge-break gate recalibrated on the formation record",
                "שער הפרת ההתחייבות כויל מחדש על נתוני ההרכבה"),
    "651b955": ("site", [], "Redesign: answer-first top of the page",
                "עיצוב מחדש: התשובה בראש העמוד"),
    "91bc933": ("model", [62], "Residual index bug fixed; stacking tested and not shipped",
                "תוקן באג האינדקס בזעזוע השיורי; ערבוב המודלים נבחן ולא נכנס"),
    "f2eccf3": ("site", [61, 63], "Model explorer added: the official forecast beside its alternatives",
                "נוסף בוחר המודלים: התחזית הרשמית לצד החלופות"),
    "0c525fe": ("site", [], "Final-week runbook written",
                "נכתב נוהל השבוע האחרון"),
    "c2fe2f3": ("site", [], "Scorecard page added: how the forecast will be graded",
                "נוסף עמוד הציונים: איך התחזית תיבדק"),
    "5d183bf": ("site", [], "Provisional freeze of the 15 Oct forecast",
                "הקפאה זמנית של תחזית 15 באוקטובר"),
    "0a216c4": ("polls", [], "Channel 12 and Channel 13 polls, nine filings; Blue and White withdraws",
                "סקרי ערוץ 12 וערוץ 13, תשע הגשות; כחול לבן פורשת"),
    "089efdf": ("model", [64], "Owner ruling: Blue and White's voters lean to the unity side",
                "הכרעת הבעלים: מצביעי כחול לבן נוטים לצד האחדות"),
    "d401811": ("both", [65, 66], "i24, Channel 14 and Walla polls; Channel 14's weighting tested; Reservists' pledge restated",
                "סקרי i24, ערוץ 14 ווואלה; השקלול של ערוץ 14 נבחן; התחייבות המילואימניקים חודשה"),
    "daed6f0": ("polls", [], "Channel 14 and Channel 16 polls of 20 Oct; five new filings",
                "סקרי ערוץ 14 וערוץ 16 מ־20 באוקטובר; חמש הגשות חדשות"),
}
GENERIC = {
    "polls": ("New polls or events and a refit", "סקרים או אירועים חדשים והתאמה מחדש"),
    "model": ("A model change (see the decision log)", "שינוי במודל (ראו את יומן ההחלטות)"),
    "both": ("New polls or events and a model change", "סקרים או אירועים חדשים ושינוי במודל"),
    "site": ("Site change only; the forecast did not move", "שינוי באתר בלבד; התחזית לא זזה"),
}
LATEST = ("Latest build (not yet in the repository)", "הבנייה האחרונה (טרם נשמרה במאגר)")

POLL_WORDS = re.compile(r"\bpolls?\b|refit|filings?\b|wave|catch-up|\bupdate\b|withdraw|(?<!owner )ruling|"
                        r"petition", re.I)
MODEL_WORDS = re.compile(r"accuracy|\bship(ped| set)?\b|layer|harness|calibrat|taxonomy|audit|latent|"
                         r"\bterm\b|method|prior|\bgates?\b|retire|backcast|unaligned|owner ruling|"
                         r"model(l)?ed|allocat", re.I)
SECTION_REF = re.compile(r"(?:dossier\s+)?\bs\.(\d+)", re.I)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, text=True).stdout


def dossier_sections() -> dict[int, str]:
    if not DOSSIER.exists():
        return {}
    out = {}
    for line in DOSSIER.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (\d+)\.\s*(.+)$", line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def _num(x):
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)) and math.isfinite(x):
        return x
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _slug(name: str, table: dict) -> str:
    if name in table:
        return table[name]
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unnamed"


def headline(d: dict) -> dict:
    """Flat headline fields of one payload; missing fields stay missing."""
    out = {"asof": d.get("asof")}
    b = d.get("blocs") or {}
    for k, col in BLOC_KEYS:
        out[col] = _num(b.get(k))
    for p in d.get("parties") or []:
        name = p.get("name")
        if not name:
            continue
        s = _slug(name, LIST_SLUG)
        lo, hi = p.get("lo"), p.get("hi")
        if (lo is None or hi is None) and isinstance(p.get("interval"), str) and "-" in p["interval"]:
            lo, hi = p["interval"].split("-", 1)
        out[f"seats_{s}"] = _num(p.get("seats"))
        out[f"lo_{s}"] = _num(lo)
        out[f"hi_{s}"] = _num(hi)
        out[f"p_pass_{s}"] = _num(p.get("p_pass"))
    for r in d.get("pm") or []:
        if isinstance(r, (list, tuple)) and len(r) >= 2:
            name, p = r[0], r[1]
        elif isinstance(r, dict):
            name, p = r.get("pm") or r.get("name"), r.get("p", r.get("probability"))
        else:
            continue
        if not name:
            continue
        key = f"pm_{_slug(str(name).lower(), PM_SLUG)}"
        v = _num(p)
        if v is not None:
            out[key] = round((out.get(key) or 0) + v, 4)
    return out


def _numeric_part(h: dict) -> dict:
    return {k: v for k, v in h.items() if k != "asof" and v is not None}


def same_headline(a: dict, b: dict, tol: float = 1e-9) -> bool:
    x, y = _numeric_part(a), _numeric_part(b)
    if set(x) != set(y) or a.get("asof") != b.get("asof"):
        return False
    return all(abs(float(x[k]) - float(y[k])) <= tol for k in x)


def classify_fallback(subject: str, moved: bool) -> str:
    if not moved:
        return "site"
    p, m = bool(POLL_WORDS.search(subject)), bool(MODEL_WORDS.search(subject))
    if p and not m:
        return "polls"
    if m and not p:
        return "model"
    return "both"


def builds() -> list[dict]:
    log = git("log", "--first-parent", "--reverse", "--format=%H%x1f%h%x1f%cI%x1f%s", "--", REL)
    out = []
    for line in log.splitlines():
        if not line.strip():
            continue
        full, short, date, subject = line.split("\x1f", 3)
        try:
            d = json.loads(git("show", f"{full}:{REL}"))
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"  skip {short}: unreadable payload ({type(e).__name__})", file=sys.stderr)
            continue
        out.append({"commit": short, "full": full, "commit_date": date, "subject": subject,
                    "h": headline(d)})
    wp = ROOT / REL
    if wp.exists():
        try:
            w = headline(json.loads(wp.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            w = None
        if w is not None and (not out or not same_headline(w, out[-1]["h"])):
            mt = dt.datetime.fromtimestamp(wp.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            out.append({"commit": "working", "full": "", "commit_date": mt,
                        "subject": "(working copy, not committed)", "h": w})
    return out


def build_rows() -> list[dict]:
    secs = dossier_sections()
    rows, prev = [], None
    for b in builds():
        h = b["h"]
        moved = prev is None or not same_headline(h, prev)
        cur = next((v for k, v in CURATED.items() if b["full"].startswith(k) or b["commit"] == k), None)
        if b["commit"] == "working":
            kind, sections, en, he = ("both" if moved else "site"), [], *LATEST
        elif cur is not None:
            kind, sections, en, he = cur
            if kind == "site" and moved:
                print(f"  {b['commit']}: curated as site but the headline moved; recorded as both",
                      file=sys.stderr)
                kind = "both"
        else:
            kind = classify_fallback(b["subject"], moved)
            sections = sorted({int(n) for n in SECTION_REF.findall(b["subject"])})
            en, he = GENERIC[kind]
        missing = [s for s in sections if secs and s not in secs]
        if missing:
            print(f"  {b['commit']}: sections {missing} not in the decision log; dropped", file=sys.stderr)
        sections = [s for s in sections if not secs or s in secs]
        rows.append({"commit": b["commit"], "commit_date": b["commit_date"], "asof": h.get("asof"),
                     "subject": b["subject"], "kind": kind, "moved": int(moved),
                     "sections": ";".join(str(s) for s in sections),
                     "label_en": en, "label_he": he, **{k: v for k, v in h.items() if k != "asof"}})
        prev = h
    return rows


def columns(rows: list[dict]) -> list[str]:
    head = ["commit", "commit_date", "asof", "kind", "moved", "sections", "label_en",
            "label_he"] + [c for _, c in BLOC_KEYS]
    keys = set().union(*(r.keys() for r in rows)) if rows else set()
    pms = sorted((k for k in keys if k.startswith("pm_")),
                 key=lambda k: (PM_ORDER.index(k[3:]) if k[3:] in PM_ORDER else 99, k))
    # lists ordered by their seats in the latest build, then the rest by name
    last = rows[-1] if rows else {}
    slugs = sorted({k[len("seats_"):] for k in keys if k.startswith("seats_")},
                   key=lambda s: (-(last.get(f"seats_{s}") or -1), s))
    per = [f"{p}_{s}" for s in slugs for p in ("seats", "lo", "hi", "p_pass")]
    return head + pms + per + ["subject"]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e6:
        return str(int(v))
    return str(v)


def main() -> None:
    rows = build_rows()
    cols = columns(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in cols])
    n = {k: sum(r["kind"] == k for r in rows) for k in ("polls", "model", "both", "site")}
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} builds: {n['polls']} polls, {n['model']} model, "
          f"{n['both']} both, {n['site']} site; {len({r['asof'] for r in rows})} data dates)")


# ---------------------------------------------------------------- site payload

def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if not math.isfinite(x) else (int(x) if x.is_integer() and abs(x) > 1.5 else round(x, 4))


def history_payload(current: dict | None = None) -> dict:
    """Compact rows for the site's "history" key (read by build_site).

    One row per build: c commit, t commit date, a asof, k kind, m moved,
    s sections, l / lh labels, b [nb, anti, antiRaam, neither, nb_mean],
    se / lo / hi / pp per tracked list (TRACK order), pm per PM_TRACK name.
    When ``current`` (the payload being built) has a headline that differs
    from the CSV's last build, it is appended as the latest, uncommitted build.
    """
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as f:
        recs = list(csv.DictReader(f))
    if current is not None:
        h = headline(current)
        last = {k: _f(v) for k, v in recs[-1].items()} if recs else None
        if last is not None:
            last["asof"] = recs[-1].get("asof")
            last = {k: v for k, v in last.items()
                    if k == "asof" or k in {c for _, c in BLOC_KEYS} or k.startswith(("pm_", "seats_", "lo_", "hi_", "p_pass_"))}
        if last is None or not same_headline(h, last, tol=1e-6):
            recs.append({"commit": "", "commit_date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                         "asof": h.get("asof"), "kind": "both", "moved": "1", "sections": "",
                         "label_en": LATEST[0], "label_he": LATEST[1],
                         **{k: ("" if v is None else v) for k, v in h.items() if k != "asof"}})
    slugs = [_slug(n, LIST_SLUG) for n in TRACK]
    rows = []
    for r in recs:
        g = lambda k: _f(r.get(k))
        rows.append({
            "c": "" if r.get("commit") in (None, "working") else r["commit"],
            "t": (r.get("commit_date") or "")[:16].replace("T", " "),
            "a": r.get("asof") or "", "k": r.get("kind") or "both", "m": int(g("moved") or 0),
            "s": [int(x) for x in (r.get("sections") or "").split(";") if x.strip().isdigit()],
            "l": r.get("label_en") or "", "lh": r.get("label_he") or "",
            "b": [g(c) for _, c in BLOC_KEYS],
            "se": [g(f"seats_{s}") for s in slugs], "lo": [g(f"lo_{s}") for s in slugs],
            "hi": [g(f"hi_{s}") for s in slugs], "pp": [g(f"p_pass_{s}") for s in slugs],
            "pm": [g(f"pm_{p}") for p in PM_TRACK],
        })
    return {"lists": TRACK, "pmNames": PM_TRACK, "rows": rows}


if __name__ == "__main__":
    main()
