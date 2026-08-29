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
    ("רע\"ם", "raam"), ("ם\"רע", "raam"), ("רעם", "raam"),
    ("ציוני בית", "zionist_home"), ("בית ציוני", "zionist_home"),
    ("הנדל", "zionist_home"), ("טרופר", "zionist_home"),
    ("כחול", "blue_white"), ("גנץ", "blue_white"),
    ("אחודות", "unity"), ("אחדות", "unity"), ("ארדן", "unity"),
    ("אדלשטיין", "unity"),
    ("עמך", "amcha_yisrael"), ("וינטר", "amcha_yisrael"),
    ("זהות", "zehut"), ("נעם", "noam"),
]
UNDECIDED_TOKENS = ("יודע לא", "לא יודע", "מתלבט", "החלטתי לא", "לא החלטתי")

PCT = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)%")


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

    # Party lines: a known keyword + a percentage; keep the FIRST match per
    # party (the main vote-intention table precedes crosstabs).
    parties = {}
    for ln in lines:
        pcts = PCT.findall(ln)
        if not pcts:
            continue
        for kw, pid in PARTY_KEYWORDS:
            if kw in ln and pid not in parties:
                # party tables carry small percents; skip demographic rows
                val = float(pcts[0])
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
