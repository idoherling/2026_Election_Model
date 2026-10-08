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
"""

from __future__ import annotations

import re
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
    ("ישר", "yashar"), ("אייזנקוט", "yashar"),
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
    ("נעם", "noam"),
    # Filing-day lists (Sept 8): the Reservists-Economic list (Hendel +
    # Zelekha) continues the zionist_home series; pre-merger NEP lines map
    # to the absorbed id so they are not mistaken for the merged list.
    ("המילואימניקים", "zionist_home"), ("המילואמיניקים", "zionist_home"),
    ("הכלכלית החדשה", "nep"), ("המפלגה הכלכלית", "nep"),
    ("הציבור החרדי", "haredi_public"), ("ישראל תחילה", "israel_first"),
    ("מקום לכולנו", "makom_lekulanu"), ("לכולנו מקום", "makom_lekulanu"),
]
# Lines that pose a hypothetical ("if X and Y united ...") are scenario
# tables, not the vote-intention table.
SCENARIO_TOKENS = ("איחוד", "יתאחדו", "אם יהיה", "אם  יהיה", "להצטרף")
UNDECIDED_TOKENS = ("יודע לא", "לא יודע", "מתלבט", "החלטתי לא", "לא החלטתי")

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
    if len(ip) <= 2:
        return "", float(run)
    cands = []
    for k in (1, 2):
        pre, pct_i = ip[:-k], ip[-k:]
        if pct_i.startswith("0") and k == 2:
            continue
        pct = float(pct_i + ("." + dp if dp else ""))
        cands.append((pre, pct))
    best, best_err = None, 1.5
    for pre, pct in cands:
        errs = []
        if n_resp and pre:
            errs.append(abs(int(pre) / n_resp * 100 - pct))
        if seats_after is not None:
            errs.append(abs(seats_after / 1.2 - pct))
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
        if "חרדי" in ln and "haredi_sample_pct" not in meta:
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
        runs = PCT_RUN.findall(ln)
        if not runs:
            # A long list name wraps: the keyword sits on this line and the
            # percentage on the next, which names no party of its own.
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if (any(kw in ln for kw, _ in PARTY_KEYWORDS)
                    and not any(kw in nxt for kw, _ in PARTY_KEYWORDS)
                    and not any(t in nxt for t in SCENARIO_TOKENS)):
                runs = PCT_RUN.findall(nxt)
                if runs:
                    ln = ln + " " + nxt
            if not runs:
                continue
        for kw, pid in PARTY_KEYWORDS:
            if kw in ln and pid not in parties:
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


if __name__ == "__main__":
    main()
