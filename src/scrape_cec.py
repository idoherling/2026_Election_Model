"""Download and parse the CEC poll filings (section 16E disclosure reports).

Every poll published in the election period must be filed with the Central
Elections Committee with full methodology. The filings index lives at
data/cec_filings_index.psv — harvested from the gov.il DynamicCollector API
(template b043127d-d79d-472e-ac10-5567bc9e8d3d), which sits behind
Cloudflare bot protection, so the index is refreshed via a real browser
(see docs/pollsters.md workflow note); the PDF blobs themselves are openly
downloadable and fetched here.

Each PDF yields what published seat tables destroy:
  * RAW support percentages per list, including sub-threshold lists
  * sample size, margin of error, initial sample, refusal/non-response
  * undecided share where reported

Hebrew text extraction is RTL-scrambled, so parsing is keyword-based per
line: a line naming a known party keyword plus a percentage is a party
line; methodology numbers are matched by their labels' key tokens.

Outputs:
    data/raw/cec_pdfs/<ref>.pdf              cached filings
    data/processed/cec_filings.csv           one row per filing (metadata +
                                             methodology fields)
    data/processed/cec_party_pcts.csv        filing x party raw percentages

Usage:
    python src/scrape_cec.py                       download + parse the index
    python src/scrape_cec.py --discover [--append] probe gov.il for filings the
                                                   index does not list yet (see
                                                   the discovery section below)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import requests

from scrape_polls import PROCESSED_DIR

DATA = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA / "raw" / "cec_pdfs"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0"}
BLOB = "https://www.gov.il/BlobFolder/dynamiccollectorresultitem/{urlname}/he/{fname}"

# Hebrew editor label -> our canonical pollster (normalize.py names).
EDITOR_MAP = {
    "מדגם יעוץ ומחקר": "Midgam",
    "נקסט דאטה": "Filber",
    "נקסט דאטה - שלמה פילבר": "Filber",
    "שלמה פילבר": "Filber",
    "דיירקט פולס בע\"מ": "Direct Polls",
    "דיירקט פולס בעמ": "Direct Polls",   # spelling without gershayim (4199)
    "קנטאר ישראל": "Kantar",
    "ד\"ר מנחם לזר": "Lazar",
    "מנחם לזר": "Lazar",
    "שמואל רוזנר": "Midgam Project & StatNet",  # the HaMadad/Ch13 consortium
    "טאטיקה מחקרים ומדיה": "Tatika",
    "מאגר מוחות": "Maagar Mochot",
    "דיאלוג": "Dialog",
    "אפקאר מחקרים וידע": "Afkar",     # Arab-sector specialist (sector stream)
}

# Keyword (appears intact even in scrambled lines) -> party_id.
PARTY_KEYWORDS = [
    # "ישר" alone is a substring of "ישראל" (filing 4192: "ישראל הרשאים
    # לבחור" + the next line's response rate parsed as Yashar 7.3%); match
    # the list name as a token or the leader's name in either spelling.
    ("ישר ", "yashar"), ("ישר!", "yashar"), ("!ישר", "yashar"),
    ("אייזנקוט", "yashar"), ("איזנקוט", "yashar"),
    ("הליכוד", "likud"), ("ליכוד", "likud"),
    ("ביחד", "together"), ("בנט", "together"), ("יחד בראשות", "together"),
    ("ביתנו", "yisrael_beytenu"),
    ("ש\"ס", "shas"), ("ס\"ש", "shas"), ("שס", "shas"),
    ("התורה", "utj"),
    ("הדמוקרטים", "democrats"), ("דמוקרטים", "democrats"),
    ("חד\"ש", "balad+hadash_taal"), ("ש\"חד", "balad+hadash_taal"),
    ("המשותפת", "balad+hadash_taal"), ("בל״ד", "balad+hadash_taal"),
    ("בל\"ד", "balad+hadash_taal"),
    ("עוצמה", "otzma"),
    ("הציונות הדתית", "rzp"), ("הדתית הציונות", "rzp"),
    # Filings spell Ra'am several ways: רע"ם (final mem), רע"מ (regular mem),
    # unquoted רעמ, plus scrambled-RTL reversals; the leader's name is the
    # most robust anchor and appears intact in every variant seen.
    ("רע\"ם", "raam"), ("ם\"רע", "raam"), ("רעם", "raam"),
    ("רע\"מ", "raam"), ("מ\"ער", "raam"), ("רעמ", "raam"),
    ("עבאס", "raam"), ("מנסור", "raam"),
    # Hadash-Ta'al lines often drop the gershayim ("חדש תעל"); Tibi/Jabareen
    # anchor those.
    ("תע\"ל", "balad+hadash_taal"), ("ל\"עת", "balad+hadash_taal"),
    ("תעל", "balad+hadash_taal"),
    ("ג׳בארין", "balad+hadash_taal"), ("ג'בארין", "balad+hadash_taal"),
    # Some filings label YB only by its leader.
    ("ליברמן", "yisrael_beytenu"),
    ("ציוני בית", "zionist_home"), ("בית ציוני", "zionist_home"),
    ("הנדל", "zionist_home"), ("טרופר", "zionist_home"),
    ("כחול", "blue_white"), ("גנץ", "blue_white"),
    ("אחודות", "unity"), ("אחדות", "unity"), ("ארדן", "unity"),
    ("אדלשטיין", "unity"),
    ("עמך", "amcha_yisrael"), ("וינטר", "amcha_yisrael"),
    # "זהות" is NOT a keyword: since the Sept 2 technical bloc it names the
    # RZP-Zehut list (matched by its RZP tokens above) or a merger
    # SCENARIO line ("if RZP + Amcha + Zehut united ... 8.9%"), never a
    # list of its own.
    ("נעם", "noam"), ("נועם", "noam"),
    # Filing-day lists (Sept 8): the Reservists-Economic list (Hendel +
    # Zelekha) continues the zionist_home series; pre-merger NEP lines map
    # to the absorbed id so they are not mistaken for the merged list.
    ("המילואימניקים", "zionist_home"), ("המילואמיניקים", "zionist_home"),
    ("הכלכלית החדשה", "nep"), ("המפלגה הכלכלית", "nep"),
    ("הציבור החרדי", "haredi_public"), ("ישראל תחילה", "israel_first"),
    ("אח\"י", "ahi"), ("חוזרים לשורשים", "ahi"),
    ("צומת בית ישראל", "beit_yisrael"), ("צבע שחור", "code_black"),
    ("מקום לכולנו", "makom_lekulanu"), ("לכולנו מקום", "makom_lekulanu"),
]
# Lines that pose a hypothetical ("if X and Y united ...") are scenario
# tables, not the vote-intention table.
SCENARIO_TOKENS = ("איחוד", "יתאחדו", "אם יהיה", "אם  יהיה", "להצטרף")
UNDECIDED_TOKENS = ("לא החליט", "טרם החליט", "יודע לא", "לא יודע", "מתלבט", "החלטתי לא", "לא החלטתי")
# Leader names also appear in PM-suitability tables ("גדי איזנקוט 32%"); a
# leader-only keyword counts as a party line only when the line names a
# list ("בראשות" / "בהובלת" / "בהנהגת").
LEADER_KEYWORDS = {"אייזנקוט", "איזנקוט", "עבאס", "מנסור", "ליברמן", "הנדל",
                   "טרופר", "גנץ", "ארדן", "אדלשטיין", "וינטר", "ג׳בארין",
                   "ג'בארין", "בנט"}
LIST_MARKERS = ("בראשות", "בהובלת", "בהנהגת")

PCT = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)%")
# The full digit run in front of a percent sign. Several filings glue a
# respondent count or a seat count onto the percentage ("224.40%6" =
# 22 respondents, 4.40%, 6 seats; "139.7%" = 13 seats, 9.7%), so the
# split between prefix and percentage has to be resolved, not assumed.
PCT_RUN = re.compile(r"(\d+(?:\.\d{1,2})?)%")
# Filings whose party table is NOT a national distribution: the Midgam
# Project consortium files the seat column plus four raw UNWEIGHTED
# sub-sample columns (Jewish adults / young / haredi / Arab), none of
# which is a national share; a sector-only sample (e.g. Dialog's
# reservists poll for Yedioth) is a different universe altogether.
NON_NATIONAL_MARKERS = (r"גולמיים\s+לא\s+משוקללים", r"משרתי\s+מילואים")
# Editors whose filings never carry a national raw-share table (the
# Midgam Project consortium files seats + raw sub-samples in every format
# it has used).
NON_NATIONAL_EDITORS = {"Midgam Project & StatNet"}
# Filings that are not polls the model should learn from: a self-
# commissioned "institute" with no publisher, no published series and a
# report whose party names are RTL-scrambled (DRI, filed 2026-09-08 with
# Likud 25 / Yashar 20 / Blue and White 4). Parsed for the record only.
EXCLUDED_EDITORS = {"מכון די אר איי",
                    # aChord (Hebrew University social-psychology centre): one
                    # self-commissioned survey of non-haredi Jews aged 22-34 -
                    # not a national sample, no series
                    "מרכז אקורד"}


def split_pct(run: str, n_resp, seats_after):
    """Resolve a glued digit run into (prefix, pct).

    Candidates: the last 1 or 2 integer digits are the percentage's
    integer part, the rest is a prefix. A candidate is chosen by whichever
    is corroborated: prefix / n_resp x 100 ~ pct (Tatika files respondent
    counts), or pct ~ seats / 1.2 (a seat count glued in front). With no
    corroboration and no ambiguity (<= 2 integer digits) the run is the
    percentage itself; ambiguous runs with nothing to test against are
    rejected (None).
    """
    ip, _, dp = run.partition(".")
    if len(ip) <= 2 and float(run) <= 40:
        return "", float(run)
    cands = []
    for k in (1, 2):
        if k >= len(ip):
            continue
        pre, pct_i = ip[:-k], ip[-k:]
        if pct_i.startswith("0") and k == 2:
            continue
        pct = float(pct_i + ("." + dp if dp else ""))
        if pct > 40:
            continue
        cands.append((pre, pct))
    best, best_err = None, 1.5
    for pre, pct in cands:
        errs = []
        if n_resp and pre:
            errs.append(abs(int(pre) / n_resp * 100 - pct))
        if seats_after is not None:
            errs.append(abs(seats_after / 1.2 - pct))
        # a seat count glued BEFORE the percentage ("2116.4%" = 21 seats,
        # 16.4%; Filber 4176): about 1.28 seats per percent of the vote
        # (120 / the ~93% of the vote that passes); error in seats
        if pre and 0 < int(pre) <= 45:
            errs.append(abs(int(pre) - pct * 1.28) / 1.28)   # back to pct units
        if errs and min(errs) < best_err:
            best, best_err = (pre, pct), min(errs)
    return best


def download_all(index: pd.DataFrame) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for r in index.itertuples():
        out = PDF_DIR / f"{r.ref}.pdf"
        if out.exists():
            continue
        url = BLOB.format(urlname=r.urlname, fname=requests.utils.quote(r.fname))
        resp = requests.get(url, headers=UA, timeout=60)
        if resp.ok and resp.content[:4] == b"%PDF":
            out.write_bytes(resp.content)
            print(f"  downloaded {r.ref} ({len(resp.content)//1024} KB)")
        else:
            print(f"  FAILED {r.ref}: HTTP {resp.status_code}")


def parse_pdf(path: Path):
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        return {"parse_error": str(e)}, []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    meta = {}
    national = not any(re.search(m, text) for m in NON_NATIONAL_MARKERS)
    meta["national_table"] = national

    for ln in lines:
        # respondents: "משיבים 500" / "השיבו לו"
        if "משיבים" in ln and ("השיבו" in ln or "נערך" in ln) and "n" not in meta:
            m = re.search(r"(\d{3,4})", ln.replace(",", ""))
            if m:
                meta["n"] = int(m.group(1))
        if ("טעות" in ln or "תקן" in ln) and "moe" not in meta:
            m = PCT.search(ln)
            if m:
                meta["moe"] = float(m.group(1))
        if "התחלתי" in ln and "initial_sample" not in meta:
            m = re.search(r"([\d,]{3,7})", ln)
            if m:
                meta["initial_sample"] = int(m.group(1).replace(",", ""))
        if ("סירבו" in ln or "השתתפו שלא" in ln) and "refused_pct" not in meta:
            m = PCT.search(ln)
            if m:
                meta["refused_pct"] = float(m.group(1))
        if any(t in ln for t in UNDECIDED_TOKENS) and "undecided_pct" not in meta:
            m = PCT.search(ln)
            if m:
                meta["undecided_pct"] = float(m.group(1))
        # Sample composition (sector coverage), where the filing reports it.
        # sample composition only: the Haredi Public list's vote line ("הציבור
        # החרדי 0 1.0%") is a party line, not the sample's haredi share
        if ("חרדי" in ln and "haredi_sample_pct" not in meta
                and not any(kw in ln for kw, _ in PARTY_KEYWORDS)):
            m = PCT.search(ln)
            if m and float(m.group(1)) <= 25:
                meta["haredi_sample_pct"] = float(m.group(1))
        if "מוסלמי" in ln and "arab_muslim_sample_pct" not in meta:
            m = PCT.search(ln)
            if m and float(m.group(1)) <= 25:
                meta["arab_muslim_sample_pct"] = float(m.group(1))
        if "נוצרי" in ln and "ערבי" in ln and "arab_christian_sample_pct" not in meta:
            m = PCT.search(ln)
            if m and float(m.group(1)) <= 10:
                meta["arab_christian_sample_pct"] = float(m.group(1))
        if "דרוזי" in ln and "druze_sample_pct" not in meta:
            m = PCT.search(ln)
            if m and float(m.group(1)) <= 10:
                meta["druze_sample_pct"] = float(m.group(1))

    # Party lines: a known keyword + a percentage; keep the FIRST match per
    # party (the main vote-intention table precedes crosstabs).
    parties = {}
    if not national:
        return meta, []
    for i, ln in enumerate(lines):
        if any(t in ln for t in SCENARIO_TOKENS):
            continue
        # methodology lines: "שיעור האנשים שסרבו ... 77%" contains the token
        # "שס" inside "שסרבו"
        if "סרבו" in ln or "סירבו" in ln:
            continue
        # government-preference rows ("ממשלת אחדות 21.8%" in Next Data 4212,
        # a which-government question, not the Unity list)
        if "ממשלת" in ln or "ממשלה" in ln:
            continue
        # "lists below 1%: Blue and White, Code Black, Noam" (Direct Polls
        # 4211) names several lists with no percentage of their own
        if re.search(r"מתחת\s*ל[-־]?\s*\d", ln):
            continue
        runs = PCT_RUN.findall(ln)
        if not runs:
            # A long list name wraps: the keyword sits on this line and the
            # percentage on the next, which names no party of its own.
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            # a name wrapped over THREE lines ("המילואימניקים" / "והכלכלית" /
            # "2.2%", Direct Polls 4211): skip one keyword-free middle line
            if (not PCT_RUN.findall(nxt) and i + 2 < len(lines)
                    and not any(kw in nxt for kw, _ in PARTY_KEYWORDS if kw not in LEADER_KEYWORDS)
                    and PCT_RUN.findall(lines[i + 2])
                    and not any(kw in lines[i + 2] for kw, _ in PARTY_KEYWORDS if kw not in LEADER_KEYWORDS)):
                nxt = nxt + " " + lines[i + 2]
            # the continuation line may carry the leader's name (Maagar:
            # "הרשימה המשותפת בראשות פרופ' יוסף" / "ג׳בארין 6% ...")
            if (any(kw in ln for kw, _ in PARTY_KEYWORDS)
                    and not any(kw in nxt for kw, _ in PARTY_KEYWORDS if kw not in LEADER_KEYWORDS)
                    and not any(t in nxt for t in SCENARIO_TOKENS)):
                runs = PCT_RUN.findall(nxt)
                if runs:
                    ln = ln + " " + nxt
            if not runs:
                continue
        for kw, pid in PARTY_KEYWORDS:
            if kw in ln and pid not in parties:
                if kw in LEADER_KEYWORDS and not any(m in ln for m in LIST_MARKERS):
                    continue
                # a seat count glued after the first percentage ("4.40%6")
                m_after = re.search(r"%(\d{1,2})(?!\d|\.)", ln)
                seats_after = int(m_after.group(1)) if m_after else None
                res = split_pct(runs[0], meta.get("n"), seats_after)
                if res is None:
                    break
                val = res[1]
                # party tables carry small percents; skip demographic rows
                if val <= 40:
                    passed = ("עבר לא" not in ln and "לא עבר" not in ln)
                    parties[pid] = {"raw_pct": val, "shown_passing": passed}
                break
    rows = [{"party_id": pid, **v} for pid, v in parties.items()]
    return meta, rows


def main() -> None:
    index = pd.read_csv(DATA / "cec_filings_index.psv", sep="|", header=None,
                        names=["ref", "urlname", "fname", "editor",
                               "publisher", "survey_date", "transfer_date",
                               "notes"], dtype={"ref": str})
    # gov.il dates are UTC-midnight-shifted: local date = date + 1 day.
    for c in ("survey_date", "transfer_date"):
        index[c] = (pd.to_datetime(index[c]) + pd.Timedelta(days=1))

    print(f"{len(index)} filings in index; downloading PDFs...")
    download_all(index)

    meta_rows, pct_rows = [], []
    for r in index.itertuples():
        path = PDF_DIR / f"{r.ref}.pdf"
        if not path.exists():
            continue
        meta, parties = parse_pdf(path)
        if (EDITOR_MAP.get(r.editor, r.editor) in NON_NATIONAL_EDITORS
                or r.editor in EXCLUDED_EDITORS):
            meta["national_table"] = False
            parties = []
        meta_rows.append({
            "ref": r.ref, "pollster": EDITOR_MAP.get(r.editor, r.editor),
            "editor_he": r.editor, "publisher_he": r.publisher,
            "fieldwork_end": r.survey_date.date(),
            "filed": r.transfer_date.date(),
            "cec_notes": r.notes if isinstance(r.notes, str) else "",
            "n_parties_parsed": len(parties), **meta,
        })
        for p in parties:
            pct_rows.append({"ref": r.ref,
                             "pollster": EDITOR_MAP.get(r.editor, r.editor),
                             "fieldwork_end": r.survey_date.date(), **p})

    filings = pd.DataFrame(meta_rows)
    pcts = pd.DataFrame(pct_rows)
    filings.to_csv(PROCESSED_DIR / "cec_filings.csv", index=False)
    pcts.to_csv(PROCESSED_DIR / "cec_party_pcts.csv", index=False)

    print(f"\nparsed {len(filings)} filings, "
          f"{len(pcts)} party-percentage rows")
    print(filings[["ref", "pollster", "fieldwork_end", "n", "moe",
                   "initial_sample", "refused_pct", "n_parties_parsed"]]
          .to_string(index=False))

    # Coverage audit vs our poll database.
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    win = polls[(polls["cycle"] == "2026")
                & (polls["fieldwork_end"] >= "2026-07-25")]
    ours = set(zip(win["pollster"], win["fieldwork_end"].dt.date))
    filings["matched_in_db"] = [
        (p, d) in ours or (p, d - pd.Timedelta(days=1).to_pytimedelta()) in ours
        for p, d in zip(filings["pollster"], filings["fieldwork_end"])
    ]
    missing = filings[~filings["matched_in_db"]]
    print(f"\nfilings NOT matched to any poll in our database: "
          f"{len(missing)}/{len(filings)}")
    if len(missing):
        print(missing[["ref", "pollster", "publisher_he", "fieldwork_end"]]
              .to_string(index=False))


# ---------------------------------------------------------------------------
# Filing discovery (python src/scrape_cec.py --discover [--append])
#
# The gov.il index behind data/cec_filings_index.psv lags the filings (it
# sits behind Cloudflare and is refreshed by hand in a browser), while the
# PDF blobs are openly downloadable at a predictable address:
#   BLOB with urlname knesset_election{IDX} and fname Survey_{REF}.pdf
#   (some filings drop the underscore: Survey{REF}.pdf, e.g. 4190, 4209).
# Discovery probes IDX beyond the last indexed one and REF beyond the last
# indexed ref, downloads what it finds into data/raw/cec_pdfs/, and reads
# the editor, publisher and fieldwork date from the PDF text - the steps
# done by hand on 16 Oct for 4202, 4207 and 4209-4212 (index rows marked
# "index row added 16 Oct"). Proposed index rows go to stdout for review;
# --append adds them to the index.
# ---------------------------------------------------------------------------
INDEX_COLUMNS = ["ref", "urlname", "fname", "editor", "publisher",
                 "survey_date", "transfer_date", "notes"]
INDEX_PATH = DATA / "cec_filings_index.psv"


def _with_reversed(labels):
    """Labels plus their character-reversed forms (some filings extract
    RTL-scrambled: "רקסה ןימזמ" is "מזמין הסקר")."""
    return tuple(labels) + tuple(lb[::-1] for lb in labels)


EDITOR_LABELS = _with_reversed(("עורך הסקר", "עורכת הסקר", "שערך את הסקר", "הסקר את שערך",
                                "הגורם שערך", "הגוף שערך"))
PUBLISHER_LABELS = _with_reversed(("מזמין הסקר", "מזמינת הסקר", "שהזמין את הסקר",
                                   "הסקר את שהזמין", "הגוף המזמין"))
DATE_LABELS = _with_reversed(("מועד איסוף", "איסוף הנתונים", "איסוף נתונים", "תאריך ביצוע",
                              "תאריכי ביצוע", "ביצוע הסקר", "הסקר ביצוע", "תאריך הביצוע",
                              "בוצע הסקר", "נערך הסקר", "בתאריכים", "מועד ביצוע",
                              "מועד עריכת", "תאריך עריכת", "תאריכי הסקר", "מועד הסקר"))
# Editor names as some filings write them -> the index's spelling
EDITOR_ALIASES = {"next data": "נקסט דאטה", "direct polls": 'דיירקט פולס בע"מ',
                  "kantar": "קנטאר ישראל", "קאנטר": "קנטאר ישראל",
                  "tatika": "טאטיקה מחקרים ומדיה", "טאטיקה": "טאטיקה מחקרים ומדיה",
                  "אפקאר": "אפקאר מחקרים וידע", "מכון dri": "מכון די אר איי"}
HE_MONTHS = {"ינואר": 1, "פברואר": 2, "מרץ": 3, "מרס": 3, "אפריל": 4, "מאי": 5,
             "יוני": 6, "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10,
             "נובמבר": 11, "דצמבר": 12}
PUB_STOP = {'בע"מ', "בעמ", "חברת", ",", "-", "ltd", "ltd."}


def load_index(path: Path = INDEX_PATH) -> pd.DataFrame:
    """The filings index as written (dates left as strings, gov.il-shifted)."""
    return pd.read_csv(path, sep="|", header=None, names=INDEX_COLUMNS,
                       dtype=str, keep_default_na=False)


def _norm_he(s: str) -> str:
    return (s or "").replace("״", '"').replace("׳", "'").replace("“", '"').replace("”", '"')


def pdf_lines(path: Path) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    return [_norm_he(ln.strip()) for ln in text.splitlines() if ln.strip()]


def _labelled(lines: list[str], labels, exclude=(), wrap: bool = True) -> str:
    """The first line carrying one of the labels (plus the next line, for
    values that wrap), or ''."""
    for i, ln in enumerate(lines[:60]):
        if any(lb in ln for lb in labels) and not any(x in ln for x in exclude):
            nxt = lines[i + 1] if wrap and i + 1 < len(lines) else ""
            return (ln + " " + nxt).strip()
    return ""


def _default_year(lines: list[str]) -> int:
    years = [int(y) for y in re.findall(r"(?<!\d)(20[2-3]\d)(?!\d)", " ".join(lines[:40]))]
    return max(years) if years else pd.Timestamp.today().year


def _parse_dates(s: str, default_year: int) -> list:
    """Every date on a line: d/m/yyyy, d.m.yyyy, d-m-yyyy (two-digit years
    are 20yy), yyyy-mm-dd, "13 באוקטובר2026"; with none of those, dates
    without a year ("11 באוקטובר", "26/8") take default_year."""
    out = []
    for d, m, y in re.findall(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})(?!\d)", s):
        out.append((int(y) + (2000 if len(y) == 2 else 0), int(m), int(d)))
    for y, m, d in re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", s):
        out.append((int(y), int(m), int(d)))
    months = "|".join(HE_MONTHS)
    for d, mon, y in re.findall(rf"(?<!\d)(\d{{1,2}})\s*ב?({months})\s*(\d{{4}})", s):
        out.append((int(y), HE_MONTHS[mon], int(d)))
    if not out:
        for d, mon in re.findall(rf"(?<!\d)(\d{{1,2}})\s*ב?({months})", s):
            out.append((default_year, HE_MONTHS[mon], int(d)))
        for d, m in re.findall(r"(?<![\d/.])(\d{1,2})/(\d{1,2})(?![\d/%])", s):
            out.append((default_year, int(m), int(d)))
    dates = []
    for y, m, d in out:
        try:
            dates.append(pd.Timestamp(year=y, month=m, day=d))
        except ValueError:
            continue
    return dates


def fieldwork_dates(lines: list[str]):
    """(first, last) date on the fieldwork-date line - or on the two lines
    after it when the value wraps - or (None, None)."""
    yr = _default_year(lines)
    for i, ln in enumerate(lines[:80]):
        if any(lb in ln for lb in DATE_LABELS):
            for j in range(i, min(i + 3, len(lines))):
                ds = _parse_dates(lines[j], yr)
                if ds:
                    return min(ds), max(ds)
    return None, None


def fieldwork_end(lines: list[str]):
    """The last fieldwork date (a multi-day survey is dated by its last day,
    the convention of the poll archive's fieldwork_end)."""
    return fieldwork_dates(lines)[1]


def _editor_spelling(index: pd.DataFrame) -> dict:
    """canonical pollster -> the index's most frequent Hebrew editor name."""
    if index.empty:
        return {}
    pol = index["editor"].map(lambda e: EDITOR_MAP.get(e, e))
    return {p: g.value_counts().index[0] for p, g in index["editor"].groupby(pol)}


def _name_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[\s,\-–]+", name) if len(t) >= 3 and '"' not in t]


def resolve_editor(lines: list[str], index: pd.DataFrame):
    """(editor as the index spells it, flags). On the editor line: a known
    editor name, an alias, or every word of a known name (word order is
    scrambled in some extractions); failing that, a name or alias anywhere
    in the first 40 lines (flagged)."""
    known = sorted(set(EDITOR_MAP) | set(index["editor"]) | EXCLUDED_EDITORS, key=len, reverse=True)
    known = [k for k in known if k]
    spelling = _editor_spelling(index)
    line = _labelled(lines, EDITOR_LABELS, exclude=PUBLISHER_LABELS)
    full = " ".join(lines[:40])

    def alias(scope):
        low = scope.lower()
        return next((he for k, he in EDITOR_ALIASES.items() if k in low), None)

    for scope, on_line in ((line, True), (full, False)):
        if not scope:
            continue
        hit = next((k for k in known if k in scope), None) or alias(scope)
        if hit is None and on_line:
            hit = next((k for k in sorted(known, key=lambda k: -len(_name_tokens(k)))
                        if _name_tokens(k) and all(t in scope for t in _name_tokens(k))), None)
        if hit is not None:
            return (spelling.get(EDITOR_MAP.get(hit, hit), hit),
                    [] if on_line else ["editor found outside the editor line"])
    raw = line
    for lb in EDITOR_LABELS:
        raw = raw.replace(lb, "")
    return raw.strip(" :"), ["CHECK editor: no known editor matched"]


def _token_hit(tok: str, text: str) -> bool:
    if tok.isdigit():
        return re.search(rf"(?<!\d){tok}(?!\d)", text) is not None
    return len(tok) >= 2 and tok.lower() in text.lower()


def resolve_publisher(lines: list[str], index: pd.DataFrame, editor: str):
    """(publisher as the index spells it, flags). Each publisher already in
    the index is scored on the PDF's commissioner line (label removed): the
    share of its words found there, +0.25 if it appears verbatim, plus half
    the share of this editor's past filings it accounts for. A publisher
    with under half its words on the line is not taken; the line's own text
    is proposed instead, flagged for review."""
    line = _labelled(lines, PUBLISHER_LABELS)
    for lb in PUBLISHER_LABELS:
        line = line.replace(lb, " ")
    pubs = [p for p in index["publisher"].unique() if p]
    hist = index.loc[index["editor"] == editor, "publisher"].value_counts(normalize=True)
    best, best_score, best_overlap = None, 0.0, 0.0
    for p in pubs:
        toks = [t.strip("-–.:()'") for t in re.split(r"[\s,]+", _norm_he(p))]
        toks = [t for t in toks if t and t.lower() not in PUB_STOP]
        overlap = (sum(_token_hit(t, line) for t in toks) / len(toks)) if toks and line.strip() else 0.0
        score = overlap + (0.25 if line.strip() and _norm_he(p) in line else 0.0) \
            + 0.5 * float(hist.get(p, 0.0))
        if score > best_score:
            best, best_score, best_overlap = p, score, overlap
    if best is not None and best_overlap >= 0.5:
        return best, []
    if not line.strip() and best is not None:
        return best, ["CHECK publisher: no commissioner line; guessed from the editor's earlier filings"]
    raw = _labelled(lines, PUBLISHER_LABELS, wrap=False)
    for lb in PUBLISHER_LABELS:
        raw = raw.replace(lb, " ")
    return " ".join(raw.split()).strip(" :"), ["CHECK publisher: not matched to a known publisher"]


def propose_row(ref: str, urlname: str, fname: str, lines: list[str],
                index: pd.DataFrame, today=None) -> dict:
    """An index row read from a filing's text, in the index's conventions:
    survey_date is the fieldwork date minus one day (gov.il's UTC-midnight
    shift, which main() adds back) and transfer_date is the day after it,
    marked approximate - as the 16 Oct rows were entered. A multi-day survey
    is dated by its last day (gov.il's own rows usually carry the first)."""
    editor, flags = resolve_editor(lines, index)
    publisher, pflags = resolve_publisher(lines, index, editor)
    first, fw = fieldwork_dates(lines)
    flags = flags + pflags
    if fw is None:
        flags.append("CHECK fieldwork date: not found")
    else:
        if first is not None and first != fw:
            flags.append(f"fieldwork {first.date()} to {fw.date()}, dated by its last day")
        dates = pd.to_datetime(index["survey_date"], errors="coerce").dropna()
        if len(dates) and fw < dates.max() - pd.Timedelta(days=14):
            flags.append("CHECK fieldwork date: over two weeks before the latest indexed filing")
    survey = (fw - pd.Timedelta(days=1)) if fw is not None else None
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today()
    note = (f"index row proposed by scrape_cec --discover on {today.date()} from the PDF "
            f"({'file named without the underscore; ' if not fname.startswith('Survey_') else ''}"
            f"gov.il index not refreshed); transfer date approximate")
    if flags:
        note += "; " + "; ".join(flags)
    return {"ref": str(ref), "urlname": urlname, "fname": fname, "editor": editor,
            "publisher": publisher,
            "survey_date": survey.date().isoformat() if survey is not None else "",
            "transfer_date": (survey + pd.Timedelta(days=1)).date().isoformat() if survey is not None else "",
            "notes": note, "flags": flags,
            "fieldwork_end": fw.date().isoformat() if fw is not None else ""}


def row_psv(row: dict) -> str:
    return "|".join(str(row[c]).replace("|", "/").replace("\n", " ") for c in INDEX_COLUMNS)


def fetch_pdf(url: str, timeout: int = 30):
    """The blob's bytes if it is a PDF, else None (404s and HTML pages)."""
    try:
        resp = requests.get(url, headers=UA, timeout=timeout)
    except requests.RequestException as e:
        print(f"  probe error {url}: {e}", file=sys.stderr)
        return None
    if resp.ok and resp.content[:4] == b"%PDF":
        return resp.content
    return None


def last_indexed(index: pd.DataFrame) -> tuple[int, int]:
    """(last IDX in knesset_election{IDX}, last numeric ref)."""
    idx = []
    for u in index["urlname"]:
        m = re.search(r"knesset_election(\d+)$", str(u))
        if m:
            idx.append(int(m.group(1)))
    refs = [int(r) for r in index["ref"] if str(r).isdigit()]
    return max(idx), max(refs)


def discover(index: pd.DataFrame, fetch=fetch_pdf, idx_span: int = 12, ref_span: int = 25,
             max_misses: int = 2, idx_from=None, ref_from=None, out_dir: Path = PDF_DIR,
             today=None, log=None) -> list[dict]:
    """Probe IDX = idx_from.. (default last indexed + 1) against REF in a
    window above the last indexed ref (both file-name forms); stop after
    max_misses consecutive IDX with no filing. Each hit is saved to
    out_dir/<ref>.pdf and turned into a proposed index row."""
    log = log or (lambda msg: print(msg, file=sys.stderr))
    last_idx, last_ref = last_indexed(index)
    idx0 = int(idx_from) if idx_from is not None else last_idx + 1
    ref0 = int(ref_from) if ref_from is not None else last_ref + 1
    known = set(index["ref"].astype(str))
    out_dir = Path(out_dir)
    found_max = ref0 - 1
    rows, misses, n_probe = [], 0, 0
    for idx in range(idx0, idx0 + idx_span):
        urlname = f"knesset_election{idx}"
        hit = None
        for ref in range(ref0, max(ref0, found_max + 1) + ref_span):
            if str(ref) in known:
                continue
            for fname in (f"Survey_{ref}.pdf", f"Survey{ref}.pdf"):
                n_probe += 1
                data = fetch(BLOB.format(urlname=urlname, fname=fname))
                if data:
                    hit = (ref, fname, data)
                    break
            if hit:
                break
        if hit is None:
            misses += 1
            log(f"  {urlname}: no filing for refs {ref0}-{max(ref0, found_max + 1) + ref_span - 1}")
            if misses >= max_misses:
                break
            continue
        misses = 0
        ref, fname, data = hit
        known.add(str(ref))
        found_max = max(found_max, ref)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ref}.pdf"
        if not path.exists():
            path.write_bytes(data)
        row = propose_row(str(ref), urlname, fname, pdf_lines(path), index, today=today)
        meta, parties = parse_pdf(path)
        row["parsed"] = (f"{len(parties)} lists, sum {sum(p['raw_pct'] for p in parties):.1f}%"
                         if parties else "no party table parsed")
        log(f"  {urlname}: {fname} ({len(data) // 1024} KB) -> {row['editor']} / "
            f"{row['publisher']} / fieldwork {row['fieldwork_end'] or '?'}; {row['parsed']}")
        rows.append(row)
    log(f"{n_probe} URLs probed, {len(rows)} new filing(s)")
    return rows


def append_rows(rows: list[dict], path: Path = INDEX_PATH) -> None:
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    text += "".join(row_psv(r) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8")


def discover_main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Probe gov.il for CEC filings not yet in the index.")
    ap.add_argument("--discover", action="store_true", required=True)
    ap.add_argument("--append", action="store_true",
                    help="append the proposed rows to data/cec_filings_index.psv")
    ap.add_argument("--idx-span", type=int, default=12, help="IDX values to probe (default 12)")
    ap.add_argument("--ref-span", type=int, default=25,
                    help="refs to try above the last indexed / last found ref (default 25)")
    ap.add_argument("--max-misses", type=int, default=2,
                    help="stop after this many consecutive IDX with no filing (default 2)")
    ap.add_argument("--idx-from", type=int, default=None)
    ap.add_argument("--ref-from", type=int, default=None)
    args = ap.parse_args(argv)
    index = load_index()
    last_idx, last_ref = last_indexed(index)
    print(f"last indexed: knesset_election{last_idx}, ref {last_ref}; probing...", file=sys.stderr)
    rows = discover(index, idx_span=args.idx_span, ref_span=args.ref_span,
                    max_misses=args.max_misses, idx_from=args.idx_from, ref_from=args.ref_from)
    for r in rows:
        print(row_psv(r))
    if rows and args.append:
        append_rows(rows)
        print(f"appended {len(rows)} row(s) to {INDEX_PATH}; run python src/scrape_cec.py to parse",
              file=sys.stderr)
    elif rows:
        print("review the rows above; rerun with --append to add them, then run "
              "python src/scrape_cec.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if "--discover" in sys.argv[1:]:
        sys.exit(discover_main(sys.argv[1:]))
    main()
