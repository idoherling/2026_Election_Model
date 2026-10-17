"""Election night: the live CEC count -> seats, a sector-weighted nowcast,
a threshold watch, and the forecast beside it.

    python src/election_night.py --check                probe the CEC feed, build nothing
    python src/election_night.py --build                fetch once, cache the snapshot, write the page
    python src/election_night.py --watch 180            fetch + build every 180 s until Ctrl-C
    python src/election_night.py --build --manual night.csv [--valid N] [--pct-counted P]
    python src/election_night.py --build --snapshot data/raw/election_night/<stamp>
    python src/election_night.py --replay 2022          rehearsal on the real 2022 count
    python src/election_night.py --fetch-archive 2022   download the archived 2022 night files

Output: output/site/election-night.html, a standalone page that re-reads
output/site/election-night.json every two minutes when it is served over
http(s). The rehearsal writes election-night-rehearsal.{html,json} so the
live page is never overwritten by 2022 numbers.

RUNBOOK, 27 Oct 2026 (polls close 22:00 Israel time)
  before   python tests/test_election_night.py; python src/election_night.py --check
           (404 everywhere until the CEC publishes; 200 + "ok": true once it does).
           Confirm the surplus agreements against the CEC's published list; if they
           differ from simulate.SURPLUS_PAIRS, pass --pairs "מחל-ט,רק-ל,...".
  22:00    python src/election_night.py --watch 180   (Ctrl-C to stop). Each cycle
           fetches expb/expc/national, caches data/raw/election_night/<stamp>/, and
           rewrites election-night.{html,json}. Republish the page with the JSON
           beside it, or let the open page re-read the JSON.
  if the files move: --base-url https://<new host>/<dir>/ (and --national-url).
  if the format breaks: the page keeps the last good count and says "Feed
           problem". Type the national table into a CSV (list,votes; letters or
           names; a "small parties" row or --valid N) and run
           --build --manual night.csv --pct-counted P.
  rebuild offline from any cached stamp: --build --snapshot data/raw/election_night/<stamp>
  envelopes: counted from about 28 Oct; keep --watch running until the final count.

DATA SOURCE (researched 17 Oct 2026)
------------------------------------
2022, the 25th Knesset. The Central Elections Committee published the live
count as two flat CSV files, refreshed every few minutes through the night:
    https://media25.bechirot.gov.il/files/expb.csv    one row per polling station
    https://media25.bechirot.gov.il/files/expc.csv    one row per locality
Columns: סמל ועדה, [ברזל, קלפי, ריכוז, שופט: stations only], שם ישוב,
סמל ישוב, בזב (eligible), מצביעים (ballots), פסולים (invalid), כשרים (valid),
then one integer column per ballot letter (40 in 2022). UTF-8 with a BOM
(windows-1255 up to 2021). Only counted units appear: 276 stations at 01:38
Israel time, 11,707 regular stations at the end. The double envelopes are one
pseudo-locality, 9999 'מעטפות חיצוניות', in count units of about 600 ballots
(838 units in 2022: 458,714 valid votes, 9.6%), counted after the regular
stations. The Wayback Machine holds about twenty snapshots of each file
from 01:15 Israel time on 2 Nov 2022 to certification
(web.archive.org/cdx/search/cdx?url=media25.bechirot.gov.il/files/*);
--fetch-archive 2022 downloads them and --replay 2022 steps through them.
The HTML results site https://votes25.bechirot.gov.il/ served / and
/nationalresults (table.TableData: name, letters, %, votes in td.Last; seats
were not shown during the count), /cityresults?cityID=<סמל ישוב> and
/ballotresults?cityID=<code>&BallotNumber=<n.m>. No JSON API was found.

2026, the 26th Knesset. Assumed from the 2019-2022 pattern:
media26.bechirot.gov.il/files/expb.csv and expc.csv, with the national page
at votes26.bechirot.gov.il. On 17 Oct 2026 both hosts resolve to CloudFront
and S3 and answer 404, so they are provisioned but empty; votes27 and media27
do not resolve. The 2019-2022 hosts now answer HTTP 200 with a gov.il
"site not found" page, so a status code proves nothing: every response is
validated as a results file before it is used.
Uncertain for 2026: the paths and file names, the encoding, extra columns,
the refresh cadence, CloudFront geo- or bot-blocking, and whether the HTML
page keeps table.TableData. Hence a configurable base URL (--base-url or
EN_BASE_URL), content validation, three source levels (station, then
locality, then the national page) and a manual CSV.

THE SEAT LAW (a)
----------------
The threshold is 3.25% of ALL valid votes, tested in exact integer arithmetic
(Knesset Elections Law s.81(a)). Surplus agreements pool two lists only when
both pass. Seats go by Bader-Ofer. The pooling and division reuse the
project's own allocator, simulate.resolve_pairs / form_factions / dhondt (the
same calls official_forecast.allocate_central makes). The 2026 pairs are
simulate.SURPLUS_PAIRS, mapped to ballot letters through the forecast's
components. With validate_model.REGISTERED_PAIRS the engine reproduces the
official allocation of every cycle from 2009 to 2022 from
data/cec_final_counts.csv (tests/test_election_night.py).

THE NOWCAST (b)
---------------
Early counts are not representative. Small Jewish localities report first,
Arab and haredi localities report at their own pace, and the double
envelopes come days later. (b) is a simple reweighting by expected remaining
votes:
  * Each locality's expected final valid vote is its previous-election valid
    vote, times register growth (TRN-F07: Arab localities +10.2%, others
    +8.1%), times the forecast's Arab turnout term (Arab localities only).
  * Its remaining votes (expected minus counted) are cast at its own counted
    shares, shrunk (K_LOCAL votes) toward a prediction: its prior
    composition times its sector's ratio swing. The prior composition is the
    locality's previous result carried to the current lists. For 2026 that
    is the 2022 result through kalpi_model.LINEAGE_2026 at the forecast's
    national shares, the forecast's own poststratification. For the 2022
    replay it is the 2021 result through MAP_2021_TO_2022, a lineage table
    written without the 2022 outcome. The ratio swing is counted votes over
    prior-predicted votes in the sector's reported localities, shrunk to no
    swing with K_SECTOR votes. Sectors come from the kalpi_model clustering
    (seven sectors). The locality layer matters: in 2022 the Negev's
    Ra'am-heavy localities reported last, and a sector-only adjustment put
    Balad over the line at 63% counted. The locality prior did not.
  * The double-envelope pool is sized at the previous election's share. It is
    cast at the counted envelope shares once envelopes report, and at the
    projected regular-station shares before that. Its list lean is NOT
    applied numerically; the threshold watch gives the direction (TRN-F03).
Not modelled: uncertainty bands on (b); reporting-order bias among one
locality's stations; turnout swings by sector other than the Arab term; and
localities absent from the previous election, which add only what they
report. With only a national table (the HTML page or a manual CSV), (b) is
not computed: the page shows (a) and the threshold margins in votes.

THE THRESHOLD WATCH (c)
-----------------------
Every list within 0.5 percentage points of 3.25%, on the raw count or on (b),
is shown with its margin in votes and the likely direction of the
double-envelope count. Per TRN-F03 (IDI, Anabi and Kenig, 2 Nov 2022, as
corrected by the verifier), the envelope lean is by list, not by bloc:
Religious Zionism up, Shas and UTJ down, the Arab lists down. Lists descended
from those lists are marked "inferred". IDI expects a negligible effect on
bloc seats except through the threshold.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import simulate as _sim                       # the project's seat-law pieces
from kalpi_model import META as _KALPI_META
from scrape_polls import PROCESSED_DIR, RAW_DIR

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "site"
SITE_TEMPLATE = ROOT / "site" / "template.html"
PAGE_TEMPLATE = ROOT / "site" / "election_night.html"
SITE_DATA = OUT_DIR / "site_data.json"
COUNTS = ROOT / "data" / "cec_final_counts.csv"
CACHE_DIR = Path(os.environ.get("EN_CACHE_DIR", str(RAW_DIR / "election_night")))
KALPI_DIR = Path(os.environ.get("EN_KALPI_DIR", str(RAW_DIR / "kalpi")))

FEED = {
    "2026": {"base": "https://media26.bechirot.gov.il/files/",
             "national": "https://votes26.bechirot.gov.il/"},
    "2022": {"base": "https://media25.bechirot.gov.il/files/",
             "national": "https://votes25.bechirot.gov.il/"},
}
FILES = (("station", "expb.csv"), ("locality", "expc.csv"))
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 KnessetModel-election-night")

THRESHOLD = Fraction(13, 400)      # 3.25% of all valid votes, s.81(a)
SEATS = 120
WATCH_PP = 0.5                     # threshold-watch band, percentage points
ENVELOPE_CODE = 9999               # 'מעטפות חיצוניות'
REST = "_rest"                     # unitemised votes (manual input): in the denominator, never a list
K_SECTOR = 10_000                  # nowcast shrinkage: sector shares toward the prior (votes)
K_LOCAL = 1_000                    # locality shares toward the sector (votes)
LETTER_RE = re.compile(r"^[א-ת]{1,4}$")
META = set(_KALPI_META) | {"ת. עדכון", "ת.עדכון", "תאריך עדכון", "שעת עדכון"}
NUM_META = ("בזב", "מצביעים", "פסולים", "כשרים")

# Register and stations (TRN-F01 verified: Ynet; TRN-F02: Knesset fact sheet 24 Oct 2022)
ELIGIBLE = {"2026": 7_331_981, "2022": 6_788_804, "2021": 6_578_084}
REGULAR_STATIONS = {"2026": 12_018, "2022": 11_707}
# Register growth 2022 -> 2026 by locality type (TRN-F07 verified, Stat-Net from CEC
# station lists of 31 May 2026: Arab localities +10.2%, Jewish localities +8.1%)
GROWTH_2026 = {"arab": 1.102, "_other": 1.081}
GROWTH_2022 = 6_788_804 / 6_578_084            # national, TRN-F02 (no sector split)

TRN_F03 = {"id": "TRN-F03", "url": "https://en.idi.org.il/articles/46196",
           "cite": "Anabi & Kenig, IDI, 2 Nov 2022"}
# envelope lean by 2026 list: (direction, basis, family); see THE THRESHOLD WATCH
LEAN_2026 = {
    "Religious Zionist Party": ("up", "direct", "rz"),
    "Otzma Yehudit": ("up", "lineage", "rz"),          # inside the 2021/2022 RZ list
    "Noam": ("up", "lineage", "rz"),
    "Shas": ("down", "direct", "haredi"),
    "United Torah Judaism": ("down", "direct", "haredi"),
    "The Haredi Public": ("down", "lineage", "haredi"),
    "Code Black – Shield of the Torah World": ("down", "lineage", "haredi"),
    "Ra'am": ("down", "direct", "arab"),
    "Balad + Hadash-Ta'al": ("down", "direct", "arab"),
}
LEAN_2022 = {"rzp": ("up", "direct", "rz"), "shas": ("down", "direct", "haredi"),
             "utj": ("down", "direct", "haredi"), "raam": ("down", "direct", "arab"),
             "hadash_taal": ("down", "direct", "arab"), "balad": ("down", "direct", "arab")}

# 2022 replay: era blocs (National Unity was an opposition list then) and display
BLOC_2022 = {"likud": "nb", "rzp": "nb", "shas": "nb", "utj": "nb", "jewish_home": "nb",
             "yesh_atid": "anti", "blue_white": "anti", "yisrael_beytenu": "anti",
             "labor": "anti", "meretz": "anti",
             "raam": "arab", "hadash_taal": "arab", "balad": "arab"}
HE_2022 = {"likud": "הליכוד", "yesh_atid": "יש עתיד", "rzp": "הציונות הדתית",
           "blue_white": "המחנה הממלכתי", "shas": "ש״ס", "utj": "יהדות התורה",
           "yisrael_beytenu": "ישראל ביתנו", "raam": "רע״ם", "hadash_taal": "חד״ש–תע״ל",
           "labor": "העבודה", "meretz": "מרצ", "balad": "בל״ד", "jewish_home": "הבית היהודי"}
EN_2022 = {"blue_white": "National Unity"}
PVAR_2022 = {"likud": "likud", "yesh_atid": "yashar", "rzp": "rzp", "blue_white": "bw",
             "shas": "shas", "utj": "utj", "yisrael_beytenu": "yb", "raam": "raam",
             "hadash_taal": "jl", "balad": "jl", "labor": "dems", "meretz": "together",
             "jewish_home": "zh"}
# 2021 lineage -> 2022 ballot letters, the replay's sector prior. Written as a
# pre-election judgement, not fitted to 2022: Yamina's electorate split across
# Shaked's Jewish Home, RZP, Likud and National Unity; the 2021 Joint List
# split evenly into Hadash-Ta'al and Balad; New Hope went into National Unity.
MAP_2021_TO_2022 = {
    "likud": {"מחל": 1.0}, "yesh_atid": {"פה": 1.0}, "blue_white": {"כן": 1.0},
    "new_hope": {"כן": 1.0}, "rzp": {"ט": 1.0},
    "rz_family": {"ב": 0.40, "ט": 0.30, "מחל": 0.20, "כן": 0.10},
    "labor": {"אמת": 1.0}, "meretz": {"מרצ": 1.0},
    "joint_list": {"ום": 0.5, "ד": 0.5}, "raam": {"עם": 1.0},
    "shas": {"שס": 1.0}, "utj": {"ג": 1.0}, "yisrael_beytenu": {"ל": 1.0},
}
REST_ALIASES = {"_rest", "rest", "small parties", "small lists", "other", "others",
                "המפלגות הקטנות", "אחרים", "שאר הרשימות"}


# ---------------------------------------------------------------- lexicon
_LEX: Optional[dict] = None


def _js_object(src: str, name: str) -> dict:
    m = re.search(r"const\s+" + re.escape(name) + r"\s*=\s*(\{.*?\});", src, re.S)
    if not m:
        raise ValueError(f"site/template.html: const {name} not found")
    return json.loads(m.group(1))


def site_lexicon() -> dict:
    """Names, letters, blocs, colours and design tokens, read from the main
    site's template so this page always matches it (one source of truth)."""
    global _LEX
    if _LEX is not None:
        return _LEX
    src = SITE_TEMPLATE.read_text(encoding="utf-8")
    lex = {k: _js_object(src, k) for k in ("BLOC", "HEB", "HE_PARTY", "SHORT", "PVAR")}
    i = src.find(":root{")
    j = src.find("*{box-sizing:border-box}", i)
    if i < 0 or j < 0:
        raise ValueError("site/template.html: design tokens not found")
    lex["tokens"] = src[i:j].strip()
    m = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', src)
    lex["fonts"] = m.group(1) if m else ""
    m = re.search(r'<link rel="icon"[^>]*>', src)
    lex["icon"] = m.group(0) if m else ""
    _LEX = lex
    return lex


# ---------------------------------------------------------------- parsing
class FeedFormatError(ValueError):
    """A response that is not a CEC results file."""


def decode_bytes(raw: bytes) -> tuple:
    """CEC files: UTF-8 with a BOM in 2022, windows-1255 up to 2021."""
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="replace"), "utf-8-bom"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1255"), "windows-1255"
    except UnicodeDecodeError:
        return raw.decode("iso-8859-8", errors="replace"), "iso-8859-8"


def _to_int(s) -> Optional[int]:
    t = re.sub(r"[,\s‎‏]", "", str(s))
    return int(t) if re.fullmatch(r"\d+", t) else None


def parse_results_csv(text: str) -> pd.DataFrame:
    """A station (expb) or locality (expc) results file -> DataFrame.
    Raises FeedFormatError for anything else (gov.il error pages come with HTTP 200)."""
    head = text.lstrip()[:600].lower()
    if head.startswith("<") or "<html" in head or "<!doctype" in head:
        raise FeedFormatError("an HTML page, not a results CSV")
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, skipinitialspace=True)
    except Exception as e:                                 # noqa: BLE001
        raise FeedFormatError(f"unreadable CSV: {e}") from e
    df.columns = [str(c).strip().strip('"') for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not c.startswith("Unnamed")]]
    missing = {"סמל ישוב", "כשרים"} - set(df.columns)
    if missing:
        raise FeedFormatError(f"missing columns {sorted(missing)}")
    letters = [c for c in df.columns if c not in META and LETTER_RE.match(c)]
    unknown = [c for c in df.columns if c not in META and c not in letters]
    if not letters:
        raise FeedFormatError("no ballot-letter columns")
    for c in letters + [c for c in NUM_META if c in df.columns]:
        df[c] = (pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(),
                               errors="coerce").fillna(0).astype(np.int64))
    df["סמל ישוב"] = pd.to_numeric(df["סמל ישוב"], errors="coerce").fillna(-1).astype(int)
    if "שם ישוב" in df.columns:
        df["שם ישוב"] = df["שם ישוב"].fillna("").astype(str).str.strip()
    df = df[df["סמל ישוב"] >= 0].reset_index(drop=True)
    df.attrs["level"] = "station" if "קלפי" in df.columns else "locality"
    df.attrs["letters"] = letters
    df.attrs["unknown_columns"] = unknown
    df.attrs["row_mismatch"] = int((df[letters].sum(axis=1) != df["כשרים"]).sum())
    return df


def parse_national_html(text: str) -> tuple:
    """The 2019-2022 national page (table.TableData; letters cell, votes in the
    last cell). Returns ({letter: votes}, cec_pct or None, {letter: name})."""
    from lxml import html as lhtml
    try:
        doc = lhtml.fromstring(text)
    except Exception as e:                                 # noqa: BLE001
        raise FeedFormatError(f"unparseable HTML: {e}") from e
    tables = doc.xpath('//table[contains(concat(" ", normalize-space(@class), " "), " TableData ")]')
    if not tables:
        raise FeedFormatError("no table.TableData on the page")
    votes, names = {}, {}
    for tr in tables[0].xpath(".//tr"):
        cells = [" ".join(td.text_content().split()) for td in tr.xpath("./td")]
        if len(cells) < 3:
            continue
        letter = next((c for c in cells[:3] if LETTER_RE.match(c)), None)
        n = _to_int(cells[-1])
        if letter is None or n is None:
            continue
        votes[letter] = votes.get(letter, 0) + n
        names[letter] = cells[0]
    if not votes:
        raise FeedFormatError("table.TableData has no list rows")
    return votes, find_pct_counted(doc.text_content()), names


def find_pct_counted(text: str) -> Optional[float]:
    """A 'percent counted' figure near the CEC's wording, if the page shows one."""
    t = " ".join(text.split())
    pats = [r"(?:נספרו|ספירת|אחוז\s+ה?קלפיות|קלפיות\s+שנספרו|הקולות\s+שנספרו)[^0-9%]{0,40}(\d{1,3}(?:\.\d+)?)\s*%",
            r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:מהקלפיות|מהקולות|מן\s+הקלפיות)"]
    for p in pats:
        m = re.search(p, t)
        if m:
            v = float(m.group(1))
            if 0 <= v <= 100:
                return v
    return None


# ---------------------------------------------------------------- the count
@dataclass
class Count:
    votes: dict                         # letter -> valid votes (all lists; REST allowed)
    level: str                          # station | locality | national | manual
    source: str
    fetched_utc: str
    units: Optional[pd.DataFrame] = None   # per locality (index: code)
    eligible: Optional[int] = None
    voters: Optional[int] = None
    invalid: Optional[int] = None
    stations: Optional[int] = None         # regular stations reported
    envelope_units: Optional[int] = None
    envelope_valid: Optional[int] = None
    cec_pct: Optional[float] = None        # 'percent counted' as the CEC shows it
    manual_pct: Optional[float] = None
    snapshot: Optional[str] = None
    names: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def valid(self) -> int:
        return int(sum(self.votes.values()))


def count_from_frame(df: pd.DataFrame, source: str, fetched_utc: str,
                     snapshot: Optional[str] = None) -> Count:
    letters = df.attrs["letters"]
    env = df["סמל ישוב"] == ENVELOPE_CODE
    cols = letters + [c for c in NUM_META if c in df.columns]
    g = df.groupby("סמל ישוב")
    units = g[cols].sum()
    units["name"] = g["שם ישוב"].first() if "שם ישוב" in df.columns else ""
    units["n_rows"] = g.size()
    c = Count(votes={l: int(df[l].sum()) for l in letters}, level=df.attrs["level"],
              source=source, fetched_utc=fetched_utc, units=units, snapshot=snapshot)
    if "בזב" in df.columns:
        c.eligible = int(df.loc[~env, "בזב"].sum())
    if "מצביעים" in df.columns:
        c.voters = int(df["מצביעים"].sum())
    if "פסולים" in df.columns:
        c.invalid = int(df["פסולים"].sum())
    c.envelope_valid = int(df.loc[env, letters].to_numpy().sum())
    if c.level == "station":
        c.stations = int((~env).sum())
        c.envelope_units = int(env.sum())
    else:
        c.stations = None
        c.envelope_units = int(df.loc[env, "n_rows"].sum()) if "n_rows" in df.columns else None
    if df.attrs.get("row_mismatch"):
        c.warnings.append(f"{df.attrs['row_mismatch']} rows where the letters do not sum to כשרים")
    if df.attrs.get("unknown_columns"):
        c.warnings.append("ignored columns: " + ", ".join(df.attrs["unknown_columns"]))
    return c


def _norm(s: str) -> str:
    s = str(s).strip().casefold()
    s = s.replace('"', "״").replace("''", "״").replace("׳׳", "״").replace("’", "'")
    return re.sub(r"\s+", " ", s)


def parse_manual_csv(path, cycle: "Cycle", valid: Optional[int] = None,
                     pct: Optional[float] = None) -> Count:
    """Manual fallback: a CSV with a list column (ballot letters, English or
    Hebrew name, or component id) and a votes column. A 'small parties' row,
    or --valid N, carries unitemised votes into the threshold's denominator."""
    df = pd.read_csv(path, dtype=str, comment="#", skipinitialspace=True)
    cols = {_norm(c): c for c in df.columns}
    lcol = next((cols[k] for k in ("list", "letters", "party", "name", "רשימה", "אותיות") if k in cols), None)
    vcol = next((cols[k] for k in ("votes", "קולות") if k in cols), None)
    if lcol is None or vcol is None:
        raise ValueError(f"{path}: need a 'list' and a 'votes' column, got {list(df.columns)}")
    votes, bad = {}, []
    for name, v in zip(df[lcol], df[vcol]):
        if pd.isna(name) or str(name).strip() == "":
            continue
        n = _to_int(v)
        key = cycle.resolve_list(name)
        if n is None or key is None:
            bad.append(str(name))
            continue
        votes[key] = votes.get(key, 0) + n
    if bad:
        raise ValueError(f"{path}: unrecognised rows {bad}; known: letters "
                         f"{sorted(cycle.names)} or names, or 'small parties'")
    if valid is not None:
        rest = int(valid) - sum(votes.values())
        if rest < 0:
            raise ValueError(f"--valid {valid} is smaller than the listed votes")
        votes[REST] = votes.get(REST, 0) + rest
    return Count(votes=votes, level="manual", source=str(path), fetched_utc=utc_iso(),
                 manual_pct=pct)


# ---------------------------------------------------------------- seat engine
@dataclass
class Allocation:
    seats: dict
    passed: list
    pooled: list          # surplus pairs pooled (both passed)
    unresolved: list      # pairs whose letters are not in the count
    valid: int
    needed: int           # votes needed to pass: ceil(3.25% x valid)


def allocate(votes: dict, pairs=(), threshold=THRESHOLD, seats: int = SEATS) -> Allocation:
    """Threshold on all valid votes (exact), surplus pairs, Bader-Ofer.
    The pooling and the d'Hondt division are the project's own
    (simulate.resolve_pairs / form_factions / dhondt)."""
    keys = list(votes)
    v = np.array([int(votes[k]) for k in keys], dtype=np.int64)
    valid = int(v.sum())
    thr = Fraction(threshold)
    needed = -(-thr.numerator * valid // thr.denominator)
    passed = (v * thr.denominator >= thr.numerator * valid) & (v > 0)
    for i, k in enumerate(keys):
        if k == REST:
            passed[i] = False
    pair_idx, _, unresolved = _sim.resolve_pairs(list(pairs), [{k} for k in keys], fixed=True)
    out = {k: 0 for k in keys}
    pooled = []
    if valid > 0 and passed.any():
        fvotes, fmembers = _sim.form_factions(pair_idx, passed, v.astype(float), fixed=True)
        alloc = _sim.dhondt(np.array(fvotes, dtype=float), seats)
        for members, k in zip(fmembers, alloc):
            if len(members) == 1:
                out[keys[members[0]]] = int(k)
                continue
            a, b = members
            inner = _sim.dhondt(np.array([v[a], v[b]], dtype=float), int(k))
            out[keys[a]], out[keys[b]] = int(inner[0]), int(inner[1])
            pooled.append((keys[a], keys[b]))
    return Allocation(out, [k for i, k in enumerate(keys) if passed[i]], pooled,
                      list(unresolved), valid, int(needed))


# ---------------------------------------------------------------- cycles
@dataclass
class Cycle:
    key: str
    names: dict                     # letter -> canonical name (forecast vocabulary)
    comps: dict                     # letter -> component ids (pair resolution)
    pair_ids: list                  # surplus pairs as component ids
    aliases: dict
    bloc: dict                      # letter -> nb / anti / arab / una
    lean: dict                      # letter -> (direction, basis, family)
    display: dict                   # letter -> {en, he, pvar}
    raam: Optional[str]             # Ra'am's letter: the "+Ra'am" bloc line
    eligible: int
    regular_stations: int
    baseline: Optional[pd.DataFrame] = None   # index code: expected, sector, name
    sector_prior: dict = field(default_factory=dict)
    locality_prior: Optional[pd.DataFrame] = None   # index code x letters: prior shares
    reference: Optional[dict] = None
    feed: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    params: dict = field(default_factory=dict)
    pair_override: Optional[list] = None

    def letter_pairs(self) -> tuple:
        """Surplus pairs as ballot-letter pairs, via simulate.resolve_pairs."""
        if self.pair_override is not None:
            return list(self.pair_override), []
        letters = list(self.comps)
        idx, _, dropped = _sim.resolve_pairs(self.pair_ids, [self.comps[l] for l in letters],
                                             aliases=self.aliases, fixed=True)
        return [(letters[a], letters[b]) for a, b in idx], list(dropped)

    def resolve_list(self, name) -> Optional[str]:
        n = _norm(name)
        if n in REST_ALIASES:
            return REST
        table = {}
        for l, canon in self.names.items():
            d = self.display.get(l, {})
            for alias in (l, canon, d.get("en"), d.get("he"), *self.comps.get(l, ())):
                if alias:
                    table.setdefault(_norm(alias), l)
        if n in table:
            return table[n]
        raw = str(name).strip()
        return raw if LETTER_RE.match(raw) else None


def _kalpi_sectors_baseline(growth: dict, turnout: dict) -> pd.DataFrame:
    """2022 localities (data/processed/kalpi_sectors.csv) -> expected 2026 valid votes."""
    sec = pd.read_csv(PROCESSED_DIR / "kalpi_sectors.csv")
    cnt = pd.read_csv(COUNTS, dtype={"cycle": str})
    valid22 = int(cnt.loc[cnt["cycle"] == "2022", "valid_votes"].iloc[0])
    ratio = valid22 / sec["voters"].sum()                   # valid / ballots, 2022
    sec["sector"] = np.where(sec["locality"] == ENVELOPE_CODE, "envelopes", sec["sector"])
    g = sec["sector"].map(lambda s: growth.get(s, growth["_other"]))
    t = sec["sector"].map(lambda s: turnout.get(s, 1.0))
    out = pd.DataFrame({"expected": sec["voters"] * ratio * g * t, "sector": sec["sector"],
                        "name": sec["name"]})
    out.index = sec["locality"].astype(int)
    return out


def cycle_2026(site_data: Optional[dict] = None) -> Cycle:
    lex = site_lexicon()
    if site_data is None and SITE_DATA.exists():
        site_data = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    names = {letter: name for name, letter in lex["HEB"].items()}
    shares = pd.read_csv(PROCESSED_DIR / "mixture_shares.csv")
    comp_of = dict(zip(shares["list"], shares["components"].astype(str)))
    comps = {l: set(comp_of.get(n, n).split("+")) for l, n in names.items()}
    display = {l: {"en": lex["SHORT"].get(n, n), "he": lex["HE_PARTY"].get(n, n),
                   "pvar": lex["PVAR"].get(n)} for l, n in names.items()}
    params = (site_data or {}).get("params", {})
    try:
        arab_t = float(params["arab_mean_pct"]) / float(params["arab_base_pct"])
    except (KeyError, ValueError, ZeroDivisionError):
        arab_t = 1.0
    cyc = Cycle(
        key="2026", names=names, comps=comps, pair_ids=list(_sim.SURPLUS_PAIRS),
        aliases=dict(_sim.PAIR_ALIASES_2026),
        bloc={l: lex["BLOC"].get(n, "una") for l, n in names.items()},
        lean={l: LEAN_2026[n] for l, n in names.items() if n in LEAN_2026},
        display=display, raam=lex["HEB"].get("Ra'am"),
        eligible=ELIGIBLE["2026"], regular_stations=REGULAR_STATIONS["2026"],
        feed=dict(FEED["2026"]),
        params={"growth": GROWTH_2026, "arab_turnout_factor": round(arab_t, 4),
                "prior": "forecast poststratification by sector (site_data.kalpi)",
                "baseline": "2022 locality ballots (kalpi_sectors.csv)"})
    cyc.baseline = _kalpi_sectors_baseline(GROWTH_2026, {"arab": arab_t})
    try:
        cyc.locality_prior = _locality_prior_2026(names, comp_of, shares)
        cyc.params["prior"] = ("each locality's 2022 result carried to the 2026 lists through "
                               "kalpi_model.LINEAGE_2026 at the forecast's national shares")
    except (OSError, KeyError, ValueError) as e:
        cyc.notes.append(f"locality prior unavailable ({type(e).__name__}); sector prior used")
    # sector prior (fallback): the forecast's own poststratification by sector
    for row in (site_data or {}).get("kalpi", []):
        sh = {lex["HEB"][n]: float(s) for n, s in row.get("seats", {}).items()
              if n in lex["HEB"] and s > 0}
        tot = sum(sh.values())
        if tot > 0:
            cyc.sector_prior[row["sector"]] = {l: s / tot for l, s in sh.items()}
    if site_data:
        cyc.reference = reference_2026(site_data, cyc)
    return cyc


def _locality_prior_2026(names: dict, comp_of: dict, shares: pd.DataFrame) -> pd.DataFrame:
    """Each 2022 locality's expected 2026 composition: the forecast's national
    share of each list spread over localities in proportion to its lineage's
    2022 vote base (kalpi_model.LINEAGE_2026, as in poststratify_2026). Lists
    without a lineage are spread uniformly."""
    from kalpi_model import LINEAGE_2026
    panel = pd.read_parquet(PROCESSED_DIR / "kalpi_localities.parquet")
    p22 = panel[(panel["cycle"] == "2022") & (panel["locality"] != ENVELOPE_CODE)]
    w22 = p22.pivot_table(index="locality", columns="party", values="share", fill_value=0)
    v22 = p22.groupby("locality")["voters"].first().reindex(w22.index).fillna(0).astype(float)
    nat = dict(zip(shares["list"], shares["share_mean"]))
    cols = {}
    for l, n in names.items():
        s = float(nat.get(n, 0.0))
        if s <= 0:
            continue
        lin = LINEAGE_2026.get(comp_of.get(n, ""))
        if lin:
            base = sum(w22[src] * wgt for src, wgt in lin.items() if src in w22.columns) * v22
        else:
            base = v22.copy()
        tot = float(base.sum())
        if tot > 0:
            cols[l] = s * base / tot
    V = pd.DataFrame(cols)
    V = V.div(V.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    V.index = V.index.astype(int)
    return V


def reference_2026(sd: dict, cyc: Cycle) -> dict:
    letter_of = {n: l for l, n in cyc.names.items()}
    lists = {}
    for p in sd.get("parties", []):
        l = letter_of.get(p["name"])
        if l:
            lists[l] = {"seats": p["seats"], "lo": p["lo"], "hi": p["hi"],
                        "p_pass": p["p_pass"], "mean": p.get("mean")}
    blocs = {}
    cols, draws = sd.get("drawCols"), sd.get("draws")
    if cols and draws:
        D = np.asarray(draws, dtype=float)
        bl = [cyc.bloc.get(letter_of.get(c), "una") for c in cols]
        sums = {k: D[:, [i for i, b in enumerate(bl) if b == k]].sum(axis=1)
                for k in ("nb", "anti", "arab", "una")}
        ri = [i for i, c in enumerate(cols) if letter_of.get(c) == cyc.raam]
        sums["antiRaam"] = sums["anti"] + (D[:, ri].sum(axis=1) if ri else 0)
        for k, s in sums.items():
            blocs[k] = {"lo": int(np.percentile(s, 5)), "hi": int(np.percentile(s, 95))}
    for k in ("nb", "anti", "arab", "una", "antiRaam"):
        members = [l for l in lists if cyc.bloc.get(l) == k] if k != "antiRaam" else \
            [l for l in lists if cyc.bloc.get(l) == "anti" or l == cyc.raam]
        blocs.setdefault(k, {})["central"] = int(sum(lists[l]["seats"] for l in members))
    b = sd.get("blocs", {})
    blocs["nb"]["p61"] = b.get("nb")
    blocs["anti"]["p61"] = b.get("anti")
    blocs["antiRaam"]["p61"] = b.get("antiRaam")
    return {"kind": "forecast", "asof": sd.get("asof"), "lists": lists, "blocs": blocs,
            "p_neither": b.get("neither"),
            "label": {"en": f"Forecast, {sd.get('asof')}", "he": f"התחזית, {sd.get('asof')}"}}


def _read_cec_file(path: Path) -> pd.DataFrame:
    text, _ = decode_bytes(Path(path).read_bytes())
    return parse_results_csv(text)


def cycle_2022() -> Cycle:
    """The rehearsal cycle: 2022 lists, registered pairs, a 2021-based nowcast
    baseline (no 2022 outcome used), the harness's 2022 eve forecast as the
    reference and the official result beside it."""
    from validate_model import REGISTERED_PAIRS
    d = pd.read_csv(COUNTS, dtype={"cycle": str})
    d = d[d["cycle"] == "2022"].reset_index(drop=True)
    names, comps, display, bloc, lean, official = {}, {}, {}, {}, {}, {}
    for r in d.itertuples():
        l = str(r.ballot).strip()
        pid = r.party_id if isinstance(r.party_id, str) and r.party_id else None
        nm = r.list_name if isinstance(r.list_name, str) and r.list_name else f"List {l}"
        names[l] = nm
        comps[l] = {pid} if pid else {f"_letter_{l}"}
        display[l] = {"en": EN_2022.get(pid, nm), "he": HE_2022.get(pid, f"רשימה {l}"),
                      "pvar": PVAR_2022.get(pid)}
        bloc[l] = BLOC_2022.get(pid, "una")
        if pid in LEAN_2022:
            lean[l] = LEAN_2022[pid]
        official[l] = int(r.seats_official)
    cyc = Cycle(key="2022", names=names, comps=comps, pair_ids=list(REGISTERED_PAIRS["2022"]),
                aliases={}, bloc=bloc, lean=lean, display=display, raam="עם",
                eligible=ELIGIBLE["2022"], regular_stations=REGULAR_STATIONS["2022"],
                feed=dict(FEED["2022"]))
    try:
        base, prior, info, loc = _baseline_from_2021()
        cyc.baseline, cyc.sector_prior, cyc.locality_prior = base, prior, loc
        cyc.params = info
    except FileNotFoundError:
        cyc.baseline = _kalpi_sectors_baseline({"_other": 1.0}, {})
        cyc.params = {"baseline": "2022 localities (LOOK-AHEAD: raw 2021 files missing)"}
        cyc.notes.append("raw 2021 locality file missing: the replay's nowcast baseline uses "
                         "2022 locality sizes (look-ahead)")
    cyc.reference = reference_2022(cyc, official)
    return cyc


def _baseline_from_2021():
    """Expected 2022 votes per locality (2021 valid x register growth), the
    2021-based sector map, and the 2021 sector prior mapped to 2022 letters."""
    from kalpi_model import LETTERS, cluster_sectors
    d = _read_cec_file(KALPI_DIR / "expc_24.csv")
    lin = {l: pid for l, (pid, _) in LETTERS["2021"].items() if l in d.columns}
    valid = d["כשרים"].replace(0, np.nan)
    long = []
    for l, pid in lin.items():
        p = {"joint_list": "hadash_taal"}.get(pid, pid)
        long.append(pd.DataFrame({"cycle": "2022", "locality": d["סמל ישוב"].astype(int),
                                  "name": d["שם ישוב"], "eligible": d["בזב"],
                                  "voters": d["מצביעים"], "party": p,
                                  "share": (d[l] / valid).fillna(0.0)}))
    sectors = cluster_sectors(pd.concat(long, ignore_index=True)).set_index("locality")["sector"]
    sectors[sectors.index == ENVELOPE_CODE] = "envelopes"
    base = pd.DataFrame({"expected": d["כשרים"].values * GROWTH_2022,
                         "name": d["שם ישוב"].values}, index=d["סמל ישוב"].astype(int).values)
    base["sector"] = sectors.reindex(base.index).fillna("mixed")
    # sector prior: 2021 lineage votes by sector -> 2022 letters
    prior = {}
    sec_of = base["sector"]
    for s in sec_of.unique():
        if s == "envelopes":
            continue
        m = (sec_of == s).values
        acc = {}
        for l, pid in lin.items():
            tot = float(d.loc[m, l].sum())
            for l22, w in MAP_2021_TO_2022.get(pid, {}).items():
                acc[l22] = acc.get(l22, 0.0) + w * tot
        t = sum(acc.values())
        if t > 0:
            prior[s] = {k: v / t for k, v in acc.items()}
    # locality prior: each locality's 2021 result through the same map
    regm = (d["סמל ישוב"] != ENVELOPE_CODE).values
    loc = {}
    for l, pid in lin.items():
        for l22, w in MAP_2021_TO_2022.get(pid, {}).items():
            loc[l22] = loc.get(l22, 0.0) + w * d.loc[regm, l].astype(float).values
    loc = pd.DataFrame(loc, index=d.loc[regm, "סמל ישוב"].astype(int).values)
    loc = loc.div(loc.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    env_share = float(d.loc[d["סמל ישוב"] == ENVELOPE_CODE, "כשרים"].sum() / d["כשרים"].sum())
    info = {"baseline": "2021 locality valid votes x national register growth "
                        f"{GROWTH_2022:.3f} (TRN-F02)",
            "sectors": "2021-based clustering (kalpi_model.cluster_sectors)",
            "prior": "each locality's 2021 result through MAP_2021_TO_2022",
            "envelope_share_prev": round(env_share, 4), "growth": {"_other": round(GROWTH_2022, 4)},
            "arab_turnout_factor": 1.0}
    return base, prior, info, loc


def reference_2022(cyc: Cycle, official: dict) -> Optional[dict]:
    path = PROCESSED_DIR / "model_validation_bayes_lists.csv"
    lists = {}
    if path.exists():
        h = pd.read_csv(path, dtype={"cycle": str})
        h = h[h["cycle"] == "2022"]
        letter_of = {next(iter(c)): l for l, c in cyc.comps.items()}
        for r in h.itertuples():
            l = letter_of.get(r.components)
            if l:
                lists[l] = {"seats": int(round(r.pred_median)), "lo": int(math.ceil(r.p05 - 1e-9)),
                            "hi": int(math.floor(r.p95 + 1e-9)), "p_pass": float(r.p_pass),
                            "mean": float(r.pred)}
    p61 = None
    pb = PROCESSED_DIR / "model_validation_bayes.csv"
    if pb.exists():
        b = pd.read_csv(pb, dtype={"cycle": str})
        b = b[b["cycle"] == "2022"]
        if len(b):
            p61 = float(b["p_bloc_61"].iloc[0])
    blocs = {}
    for k in ("nb", "anti", "arab", "una", "antiRaam"):
        mem = [l for l in cyc.names if (cyc.bloc.get(l) == k if k != "antiRaam"
                                        else cyc.bloc.get(l) == "anti" or l == cyc.raam)]
        blocs[k] = {"central": int(sum(lists.get(l, {}).get("seats", 0) for l in mem)),
                    "official": int(sum(official.get(l, 0) for l in mem))}
    blocs["nb"]["p61"] = p61
    return {"kind": "harness", "asof": "2022-10-31", "lists": lists, "blocs": blocs,
            "official": official,
            "label": {"en": "Model's 2022 eve forecast (leave-one-out harness)",
                      "he": "תחזית המודל לערב הבחירות 2022 (מבחן השמטה)"}}


# ---------------------------------------------------------------- nowcast (b)
@dataclass
class Nowcast:
    votes: dict
    alloc: Allocation
    expected_valid: float
    pct_votes: float
    sectors: list
    envelope: dict


def nowcast(count: Count, cycle: Cycle, pairs=()) -> Optional[Nowcast]:
    if count.units is None or cycle.baseline is None:
        return None
    L = [l for l in count.votes if l != REST]
    U = count.units
    base = cycle.baseline
    codes = U.index.union(base.index)
    C = U.reindex(codes)[L].fillna(0.0).astype(float)
    Ctot = C.sum(axis=1)
    sector = base["sector"].reindex(codes).fillna("unknown")
    sector[codes == ENVELOPE_CODE] = "envelopes"
    E = base["expected"].reindex(codes).fillna(Ctot)
    E = np.maximum(E, Ctot)
    R = E - Ctot
    reg = (sector != "envelopes").values
    nat_c = C[reg].sum()
    nat = nat_c / nat_c.sum() if nat_c.sum() > 0 else pd.Series(1.0 / len(L), index=L)

    def sector_prior(s):
        p = pd.Series(cycle.sector_prior.get(s, {}), dtype=float).reindex(L).fillna(0.0)
        return p / p.sum() if p.sum() > 0 else nat

    # prior composition of every locality: its previous result carried to the
    # current lists (locality_prior); its sector's prior where it has none
    Pi = pd.DataFrame(0.0, index=codes, columns=L)
    if cycle.locality_prior is not None:
        lp = cycle.locality_prior.reindex(index=codes, columns=L).fillna(0.0)
        Pi = lp
    missing = Pi.sum(axis=1) <= 0
    for s in pd.unique(sector[missing.values]):
        m = missing.values & (sector == s).values
        Pi.loc[m, :] = sector_prior(s).values
    Pi = Pi.div(Pi.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)

    # per sector: ratio swing of the counted localities against their prior,
    # shrunk to no swing with K_SECTOR votes; lists the prior lacks take the
    # sector's counted share
    q = pd.DataFrame(0.0, index=codes, columns=L)
    rows = []
    for s in pd.unique(sector[reg]):
        m = reg & (sector == s).values
        cs, Es = C[m].sum(), float(E[m].sum())
        Cs = float(cs.sum())
        pred = Pi[m].mul(Ctot[m], axis=0).sum()
        pbar = Pi[m].mul(E[m], axis=0).sum() / Es if Es > 0 else Pi[m].mean()
        rho = (cs + K_SECTOR * pbar) / (pred + K_SECTOR * pbar)
        rho = rho.where(pbar > 0, 1.0).fillna(1.0)
        fresh = (pbar <= 0) & (cs > 0)
        qs = Pi[m] * rho
        if fresh.any() and Cs > 0:
            qs.loc[:, fresh] = (cs[fresh] / (Cs + K_SECTOR)).values
        q.loc[m, :] = qs.div(qs.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0).values
        rows.append({"sector": s, "counted": int(Cs), "expected": int(round(Es)),
                     "pct": float(Cs / Es) if Es > 0 else None,
                     "localities": int(m.sum()), "reporting": int(((Ctot > 0).values & m).sum())})
    empty = reg & (q.sum(axis=1) <= 0).values
    if empty.any():
        q.loc[empty, :] = nat.values
    Q = (C + q.mul(K_LOCAL)).div(Ctot + K_LOCAL, axis=0)
    rem_reg = Q[reg].mul(R[reg], axis=0).sum()
    proj_reg = nat_c + rem_reg
    neutral = proj_reg / proj_reg.sum() if proj_reg.sum() > 0 else nat
    envm = ~reg
    c_env = C[envm].sum()
    C_env = float(c_env.sum())
    E_env = float(E[envm].sum()) if envm.any() else 0.0
    q_env = (c_env + K_SECTOR * neutral) / (C_env + K_SECTOR)
    rem_env = q_env * max(E_env - C_env, 0.0)
    proj = C.sum() + rem_reg + rem_env
    votes = {l: int(round(proj[l])) for l in L}
    if REST in count.votes:
        votes[REST] = count.votes[REST]
    expected = float(E[reg].sum()) + max(E_env, C_env)
    rows.append({"sector": "envelopes", "counted": int(C_env), "expected": int(round(E_env)),
                 "pct": (C_env / E_env) if E_env > 0 else None, "localities": 1,
                 "reporting": int(C_env > 0)})
    order = ["centre_left", "mixed", "secular_right", "arab", "haredi",
             "religious_zionist", "russian_leaning", "unknown", "envelopes"]
    rows.sort(key=lambda r: order.index(r["sector"]) if r["sector"] in order else 99)
    return Nowcast(votes, allocate(votes, pairs), expected,
                   count.valid / expected if expected > 0 else 0.0, rows,
                   {"counted": int(C_env), "expected": int(round(E_env))})


# ---------------------------------------------------------------- threshold watch (c)
def threshold_watch(count: Count, raw: Allocation, nc: Optional[Nowcast], cycle: Cycle) -> list:
    out = []
    valid = count.valid
    tot_p = sum(nc.votes.values()) if nc else None
    need_p = nc.alloc.needed if nc else None
    for l, v in count.votes.items():
        if l == REST or valid <= 0:
            continue
        sh = 100.0 * v / valid
        shp = 100.0 * nc.votes.get(l, 0) / tot_p if nc and tot_p else None
        near = abs(sh - 3.25) <= WATCH_PP or (shp is not None and abs(shp - 3.25) <= WATCH_PP)
        if not near:
            continue
        lean = cycle.lean.get(l)
        out.append({"letter": l, "votes": int(v), "share": round(sh, 3),
                    "margin": int(v - raw.needed), "passes": l in raw.passed,
                    "share_adj": None if shp is None else round(shp, 3),
                    "margin_adj": None if shp is None else int(nc.votes.get(l, 0) - need_p),
                    "passes_adj": None if nc is None else l in nc.alloc.passed,
                    "lean": None if lean is None else {"dir": lean[0], "basis": lean[1],
                                                       "family": lean[2]}})
    out.sort(key=lambda r: -r["share"])
    return out


# ---------------------------------------------------------------- payload
def utc_iso(t: Optional[float] = None) -> str:
    return datetime.fromtimestamp(t if t is not None else time.time(), tz=timezone.utc) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _in(x, ref) -> Optional[bool]:
    if x is None or not ref or ref.get("lo") is None or ref.get("hi") is None:
        return None
    return bool(ref["lo"] <= x <= ref["hi"])


def build_payload(count: Optional[Count], cycle: Cycle, *, mode: str = "live",
                  check: Optional[list] = None, replay: Optional[dict] = None,
                  stale: Optional[dict] = None, refresh: int = 120,
                  json_name: str = "election-night.json") -> dict:
    """Everything the page renders, as one small JSON document."""
    pairs, dropped = cycle.letter_pairs()
    ref = cycle.reference or {}
    rlists = ref.get("lists", {})
    official = ref.get("official")
    raw = allocate(count.votes, pairs) if count else None
    nc = nowcast(count, cycle, pairs) if count else None
    valid = count.valid if count else 0
    tot_p = sum(nc.votes.values()) if nc else None
    letters = list(dict.fromkeys(list(rlists) + (list(count.votes) if count else [])))
    rows, small = [], {"votes": 0, "n": 0}
    for l in letters:
        if l == REST:
            continue
        v = count.votes.get(l, 0) if count else None
        share = (v / valid) if count and valid else None
        sr = raw.seats.get(l, 0) if raw else None
        sa = nc.alloc.seats.get(l, 0) if nc else None
        r = rlists.get(l)
        keep = (r and (r.get("seats", 0) > 0 or (r.get("p_pass") or 0) >= 0.005)) or \
            (sr or 0) > 0 or (sa or 0) > 0 or (share or 0) >= 0.01 or \
            (official and official.get(l, 0) > 0)
        if not keep:
            if count:
                small["votes"] += int(v or 0)
                small["n"] += int((v or 0) > 0)
            continue
        disp = cycle.display.get(l, {})
        nm = cycle.names.get(l)
        rows.append({
            "letter": l, "name": nm or f"List {l}",
            "en": disp.get("en") or nm or f"List {l}",
            "he": disp.get("he") or f"רשימה {l}",
            "pvar": disp.get("pvar"), "bloc": cycle.bloc.get(l, "una"),
            "votes": v, "share": None if share is None else round(share, 6),
            "seats_raw": sr, "seats_adj": sa,
            "votes_adj": nc.votes.get(l) if nc else None,
            "share_adj": round(nc.votes.get(l, 0) / tot_p, 6) if nc and tot_p else None,
            "ref": r, "in_raw": _in(sr, r), "in_adj": _in(sa, r),
            "official": official.get(l) if official else None,
            "lean": cycle.lean.get(l)})
    if count and REST in count.votes:
        small["votes"] += count.votes[REST]
    small["share"] = (small["votes"] / valid) if count and valid else None

    def key(r):
        s = r["seats_adj"] if r["seats_adj"] is not None else r["seats_raw"]
        if s is None:
            s = (r["ref"] or {}).get("seats", 0)
        return (-(s or 0), -((r["votes"] or 0)), -((r["ref"] or {}).get("p_pass") or 0))
    rows.sort(key=key)

    blocs = []
    for k in ("nb", "anti", "antiRaam", "arab", "una"):
        mem = [r for r in rows if (r["bloc"] == k if k != "antiRaam"
                                   else r["bloc"] == "anti" or r["letter"] == cycle.raam)]
        rb = (ref.get("blocs") or {}).get(k, {})
        b = {"key": k,
             "raw": sum(r["seats_raw"] or 0 for r in mem) if raw else None,
             "adj": sum(r["seats_adj"] or 0 for r in mem) if nc else None,
             "ref": rb or None}
        b["in_raw"] = _in(b["raw"], rb)
        b["in_adj"] = _in(b["adj"], rb)
        blocs.append(b)

    prog = {"valid": valid if count else None,
            "invalid": count.invalid if count else None,
            "stations": count.stations if count else None,
            "stations_expected": cycle.regular_stations,
            "envelope_units": count.envelope_units if count else None,
            "envelope_valid": count.envelope_valid if count else None,
            "cec_pct": count.cec_pct if count else None,
            "manual_pct": count.manual_pct if count else None,
            "expected_valid": None, "pct_votes": None, "envelope_expected": None}
    if nc:
        prog.update(expected_valid=int(round(nc.expected_valid)), pct_votes=round(nc.pct_votes, 5),
                    envelope_expected=nc.envelope["expected"])
    elif count and cycle.baseline is not None:
        ev = float(cycle.baseline["expected"].sum())
        prog.update(expected_valid=int(round(ev)), pct_votes=round(valid / ev, 5) if ev else None)
    if prog["stations"] is not None and cycle.regular_stations:
        prog["pct_stations"] = round(prog["stations"] / cycle.regular_stations, 5)

    watch = threshold_watch(count, raw, nc, cycle) if count else []
    for w in watch:
        d = cycle.display.get(w["letter"], {})
        w.update(en=d.get("en") or cycle.names.get(w["letter"]) or f"List {w['letter']}",
                 he=d.get("he") or f"רשימה {w['letter']}", pvar=d.get("pvar"))
    payload = {
        "version": 1, "mode": mode, "cycle": cycle.key,
        "generated_utc": utc_iso(),
        "fetched_utc": count.fetched_utc if count else None,
        "source": {"level": count.level if count else None,
                   "url": count.source if count else None,
                   "snapshot": _rel(count.snapshot) if count and count.snapshot else None,
                   "feed": cycle.feed, "check": check or [],
                   "warnings": count.warnings if count else []},
        "progress": prog,
        "lists": rows, "small": small, "blocs": blocs, "watch": watch,
        "sectors": nc.sectors if nc else [],
        "pairs": [{"a": a, "b": b, "pooled_raw": bool(raw and (a, b) in raw.pooled),
                   "pooled_adj": bool(nc and (a, b) in nc.alloc.pooled)} for a, b in pairs],
        "pairs_unresolved": [list(p) for p in dropped],
        "threshold_votes": raw.needed if raw else None,
        "threshold_votes_adj": nc.alloc.needed if nc else None,
        "reference": {k: ref.get(k) for k in ("kind", "asof", "label", "p_neither")} if ref else None,
        "method": {"k_sector": K_SECTOR, "k_local": K_LOCAL, "watch_pp": WATCH_PP,
                   **{k: v for k, v in cycle.params.items()}},
        "notes": cycle.notes, "trn_f03": TRN_F03,
        "refresh_seconds": refresh, "json_name": json_name,
        "replay": replay, "stale": stale,
    }
    return payload


def _rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except (ValueError, OSError):
        return str(p)


# ---------------------------------------------------------------- page
def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def render_page(payload: dict) -> str:
    lex = site_lexicon()
    tpl = PAGE_TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    blob = blob.replace("</", "<\\/")
    for k, v in (("__EN_TOKENS__", lex["tokens"]), ("__EN_FONTS__", lex["fonts"]),
                 ("__EN_ICON__", lex["icon"])):
        tpl = tpl.replace(k, v)
    assert "__EN_DATA__" in tpl, "page template placeholder missing"
    return tpl.replace("__EN_DATA__", blob)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


def write_page(payload: dict, html_path: Path) -> tuple:
    json_path = html_path.with_name(payload["json_name"])
    _atomic_write(json_path, json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                                        default=_json_default))
    _atomic_write(html_path, render_page(payload))
    return html_path, json_path


# ---------------------------------------------------------------- fetching
@dataclass
class Fetched:
    url: str
    status: Optional[int]
    content: bytes
    headers: dict
    error: Optional[str]
    attempts: int


def http_get(url: str, timeout: float = 20.0, retries: int = 4, backoff: float = 2.0,
             session=None, headers: Optional[dict] = None) -> Fetched:
    """GET with retries on network errors, 429 and 5xx; 404 returns at once."""
    import requests
    s = session or requests.Session()
    h = {"User-Agent": USER_AGENT, "Accept": "text/csv,text/html;q=0.9,*/*;q=0.8",
         "Accept-Language": "he-IL,he;q=0.9,en;q=0.8", "Cache-Control": "no-cache",
         **(headers or {})}
    err = None
    for attempt in range(1, retries + 1):
        try:
            r = s.get(url, timeout=timeout, headers=h)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                err = f"HTTP {r.status_code}"
                time.sleep(backoff ** attempt)
                continue
            return Fetched(url, r.status_code, r.content or b"", dict(r.headers), None, attempt)
        except requests.RequestException as e:
            err = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(backoff ** attempt)
    return Fetched(url, None, b"", {}, err, retries)


def _latest_dirs(root: Path) -> list:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d{8}T\d{6}Z", p.name)],
                  reverse=True)


def take_snapshot(base: str, national: Optional[str], root: Path = CACHE_DIR,
                  files=FILES, stamp: Optional[str] = None, fetch=http_get) -> Path:
    """Fetch the station file, the locality file and the national page; cache
    each response under data/raw/election_night/<UTC stamp>/ (gzip, with
    meta.json). A body identical to the previous snapshot's is not stored
    twice (meta records same_as)."""
    stamp = stamp or _stamp()
    d = root / stamp
    d.mkdir(parents=True, exist_ok=True)
    prev = next((p for p in _latest_dirs(root) if p.name < stamp), None)
    prev_meta = json.loads((prev / "meta.json").read_text()) if prev and (prev / "meta.json").exists() else {}
    prev_sha = {i["file"]: (i.get("same_as") or prev.name, i.get("sha256"))
                for i in prev_meta.get("items", []) if i.get("sha256")}
    items = []
    targets = [(lvl, base.rstrip("/") + "/" + fn, fn) for lvl, fn in files]
    if national:
        targets.append(("national", national, "national.html"))
    for level, url, fname in targets:
        f = fetch(url)
        item = {"level": level, "url": url, "file": fname, "status": f.status, "error": f.error,
                "attempts": f.attempts, "bytes": len(f.content),
                "etag": f.headers.get("ETag") or f.headers.get("etag"),
                "last_modified": f.headers.get("Last-Modified") or f.headers.get("last-modified"),
                "server": f.headers.get("Server") or f.headers.get("server")}
        if f.status == 200 and f.content:
            sha = hashlib.sha256(f.content).hexdigest()
            item["sha256"] = sha
            src_dir, psha = prev_sha.get(fname, (None, None))
            if psha == sha and src_dir and (root / src_dir / (fname + ".gz")).exists():
                item["same_as"] = src_dir
            else:
                (d / (fname + ".gz")).write_bytes(gzip.compress(f.content))
            item.update(validate_body(level, f.content))
        else:
            item["ok"] = False
            item["problem"] = ("not published yet (404)" if f.status == 404 else
                               f.error or f"HTTP {f.status}")
        items.append(item)
    meta = {"fetched_utc": utc_iso(), "base": base, "national": national, "items": items}
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def validate_body(level: str, content: bytes) -> dict:
    text, enc = decode_bytes(content)
    try:
        if level == "national":
            votes, pct, _ = parse_national_html(text)
            return {"ok": True, "encoding": enc, "lists": len(votes), "valid": sum(votes.values()),
                    "cec_pct": pct}
        df = parse_results_csv(text)
        return {"ok": True, "encoding": enc, "rows": len(df), "format": df.attrs["level"],
                "valid": int(df[df.attrs["letters"]].to_numpy().sum()),
                "letters": len(df.attrs["letters"])}
    except FeedFormatError as e:
        return {"ok": False, "encoding": enc, "problem": str(e)}


def load_snapshot(d: Path, root: Optional[Path] = None) -> Optional[Count]:
    """Best count in a snapshot directory: station > locality > national."""
    d = Path(d)
    root = root or d.parent
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    by = {i["level"]: i for i in meta.get("items", []) if i.get("ok")}
    page_pct = by.get("national", {}).get("cec_pct")
    for level in ("station", "locality", "national"):
        it = by.get(level)
        if not it:
            continue
        src = (root / it["same_as"] if it.get("same_as") else d) / (it["file"] + ".gz")
        if not src.exists():
            continue
        text, _ = decode_bytes(gzip.decompress(src.read_bytes()))
        fetched = it.get("fetched_utc") or meta.get("fetched_utc")
        if level == "national":
            votes, pct, names = parse_national_html(text)
            return Count(votes=votes, level="national", source=it["url"], fetched_utc=fetched,
                         cec_pct=pct, snapshot=str(d), names=names)
        c = count_from_frame(parse_results_csv(text), it["url"], fetched, snapshot=str(d))
        c.cec_pct = page_pct
        return c
    return None


def last_good_snapshot(root: Path = CACHE_DIR, before: Optional[str] = None) -> Optional[Path]:
    for p in _latest_dirs(root):
        if before and p.name >= before:
            continue
        try:
            meta = json.loads((p / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if any(i.get("ok") for i in meta.get("items", [])):
            return p
    return None


def check_feed(base: str, national: Optional[str]) -> list:
    """Probe each endpoint once and say what it serves (no caching)."""
    out = []
    targets = [(lvl, base.rstrip("/") + "/" + fn) for lvl, fn in FILES]
    if national:
        targets.append(("national", national))
    for level, url in targets:
        f = http_get(url, retries=2)
        r = {"level": level, "url": url, "status": f.status, "bytes": len(f.content),
             "server": f.headers.get("Server") or f.headers.get("server"), "checked_utc": utc_iso()}
        if f.status == 200 and f.content:
            r.update(validate_body(level, f.content))
        else:
            r["ok"] = False
            r["problem"] = "not published yet (404)" if f.status == 404 else (f.error or f"HTTP {f.status}")
        out.append(r)
    return out


# ---------------------------------------------------------------- the 2022 archive
ARCHIVE_CDX = "https://web.archive.org/cdx/search/cdx"
ARCHIVE_DIR = CACHE_DIR / "archive_2022"


def fetch_archive(year: str = "2022", root: Path = None, pause: float = 4.0,
                  limit: Optional[int] = None) -> list:
    """Download the Wayback Machine's election-night snapshots of the 2022
    expb.csv / expc.csv into data/raw/election_night/archive_2022/<stamp>/
    (the live snapshot layout, so load_snapshot reads them)."""
    if year != "2022":
        raise SystemExit("only the 2022 archive is known")
    root = root or ARCHIVE_DIR
    import requests
    s = requests.Session()
    got = []
    for level, fn in FILES:
        url = FEED["2022"]["base"] + fn
        q = f"{ARCHIVE_CDX}?url={url}&output=json&fl=timestamp,statuscode,mimetype&from=20221101200000&to=20221110235959"
        f = http_get(q, timeout=90, retries=6, backoff=3.0, session=s)
        if f.status != 200:
            print(f"CDX {fn}: {f.status} {f.error}")
            continue
        rows = json.loads(f.content.decode("utf-8"))[1:]
        stamps = sorted({r[0] for r in rows if r[1] == "200"})
        for ts in stamps[:limit]:
            stamp = f"{ts[:8]}T{ts[8:14]}Z"
            d = root / stamp
            if (d / (fn + ".gz")).exists():
                continue
            wb = f"https://web.archive.org/web/{ts}id_/{url}"
            r = http_get(wb, timeout=180, retries=5, backoff=3.0, session=s)
            if r.status != 200 or not r.content:
                print(f"  {stamp} {fn}: {r.status} {r.error}")
                continue
            save_archive_item(d, level, fn, url, wb, r.content, stamp)
            got.append((stamp, fn))
            print(f"  {stamp} {fn}: {len(r.content):,} bytes")
            time.sleep(pause)
    return got


def save_archive_item(d: Path, level: str, fname: str, url: str, wayback: str,
                      content: bytes, stamp: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    item = {"level": level, "url": url, "wayback": wayback, "file": fname, "status": 200,
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "fetched_utc": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"}
    item.update(validate_body(level, content))
    (d / (fname + ".gz")).write_bytes(gzip.compress(content))
    mp = d / "meta.json"
    meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {"items": []}
    meta["items"] = [i for i in meta["items"] if i["file"] != fname] + [item]
    meta["fetched_utc"] = item["fetched_utc"]
    meta["source"] = "Wayback Machine snapshot of the CEC live file"
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- rehearsal
# Simulated reporting order (used when the archive is absent): each regular
# station draws a report time U(0,1) plus its sector's delay; envelopes come
# last. The delays are fitted by eye to the archived 2022 night (share of each
# sector's final valid vote counted at 04:41 / 07:43 Israel time): mixed big
# cities .44/.78, haredi .27/.87, Arab .20/.49, the rest about .22-.26/.61-.69.
# So: cities first, haredi localities fast by the morning, Arab localities last.
SIM_DELAY = {"mixed": -0.12, "haredi": -0.15, "russian_leaning": -0.08, "arab": 0.20}
SIM_FRACTIONS = (0.05, 0.15, 0.30, 0.50, 0.70, 0.85, 0.95, 1.00)


def _final_2022() -> pd.DataFrame:
    return _read_cec_file(KALPI_DIR / "expb_25.csv")


def simulated_steps(final_df: pd.DataFrame, cycle: Cycle, fractions=SIM_FRACTIONS,
                    seed: int = 20221101) -> list:
    rng = np.random.default_rng(seed)
    code = final_df["סמל ישוב"]
    reg = final_df[code != ENVELOPE_CODE]
    sector = reg["סמל ישוב"].map(cycle.baseline["sector"]).fillna("mixed")
    t = sector.map(lambda s: SIM_DELAY.get(s, 0.0)).values + rng.uniform(0, 1, len(reg))
    order = reg.iloc[np.argsort(t, kind="stable")]
    out = []
    for f in fractions:
        part = order.iloc[: int(round(f * len(order)))].copy()
        part.attrs.update(final_df.attrs)
        out.append(((f"simulated: {f:.0%} of regular stations, no envelopes",
                     f"הדמיה: {f:.0%} מהקלפיות הרגילות, בלי המעטפות"), part))
    out.append((("simulated: final, envelopes counted", "הדמיה: סופי, כולל המעטפות"), final_df))
    return out


def archive_steps(root: Path = None) -> list:
    root = root or ARCHIVE_DIR
    steps = []
    for d in sorted(_latest_dirs(root)):
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        if any(i.get("ok") and i["level"] == "station" for i in meta.get("items", [])):
            steps.append(d)
    return steps


def _israel_time(iso: str, fmt: str = "%d %b %H:%M") -> str:
    try:
        from zoneinfo import ZoneInfo
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return t.astimezone(ZoneInfo("Asia/Jerusalem")).strftime(fmt)
    except Exception:                                      # noqa: BLE001
        return iso


def replay(year: str = "2022", mode: str = "auto", out: Optional[Path] = None,
           step_seconds: float = 0.0, max_steps: Optional[int] = None,
           stop_at: Optional[int] = None) -> pd.DataFrame:
    if year != "2022":
        raise SystemExit("--replay supports 2022")
    out = Path(out) if out else OUT_DIR / "election-night-rehearsal.html"
    cyc = cycle_2022()
    official = cyc.reference["official"]
    pairs, _ = cyc.letter_pairs()
    have_final = (KALPI_DIR / "expb_25.csv").exists()
    arch = archive_steps() if mode in ("auto", "archive") else []
    if mode == "archive" and not arch:
        raise SystemExit("no archived 2022 snapshots: run --fetch-archive 2022 first")
    seq = []
    if arch:
        # thin the archive to distinct steps (the files stop changing after certification)
        seen = set()
        for d in arch:
            c = load_snapshot(d)
            if c is None or c.valid == 0 or c.valid in seen:   # header-only files at 22:00
                continue
            seen.add(c.valid)
            seq.append(((f"archived CEC file, {_israel_time(c.fetched_utc)} Israel time",
                         f"קובץ ועדת הבחירות מהארכיון, {_israel_time(c.fetched_utc, '%d.%m %H:%M')} שעון ישראל"), c))
        src = "archive"
    elif have_final:
        fdf = _final_2022()
        for label, part in simulated_steps(fdf, cyc):
            seq.append((label, count_from_frame(part, "simulated subsample of expb_25.csv",
                                                "2022-11-02T00:00:00Z")))
        src = "simulated"
    else:
        raise SystemExit(f"no 2022 station data: {KALPI_DIR / 'expb_25.csv'} missing and no archive")
    if max_steps and len(seq) > max_steps:
        keep = np.unique(np.linspace(0, len(seq) - 1, max_steps).round().astype(int))
        seq = [seq[i] for i in keep]
    of = len(seq)
    if stop_at:
        seq = seq[:stop_at]          # leave the page on a mid-count step
    final_valid = sum(int(v) for v in pd.read_csv(COUNTS, dtype={"cycle": str})
                      .query("cycle == '2022'")["votes"])
    nb_letters = [l for l, b in cyc.bloc.items() if b == "nb"]
    rows = []
    for i, (label, c) in enumerate(seq, 1):
        label, label_he = label
        info = {"step": i, "of": of, "label": label, "label_he": label_he, "source": src,
                "pct_of_final": round(c.valid / final_valid, 5)}
        payload = build_payload(c, cyc, mode="rehearsal", replay=info,
                                json_name=out.with_suffix(".json").name)
        write_page(payload, out)
        raw = {r["letter"]: r["seats_raw"] or 0 for r in payload["lists"]}
        adj = {r["letter"]: r["seats_adj"] or 0 for r in payload["lists"]}
        mis = lambda s: sum(abs(s.get(l, 0) - official.get(l, 0)) for l in set(s) | set(official)) // 2
        rows.append({
            "step": i, "label": label, "pct_of_final_valid": round(100 * c.valid / final_valid, 1),
            "pct_est": round(100 * (payload["progress"]["pct_votes"] or 0), 1),
            "stations": c.stations, "envelopes_valid": c.envelope_valid,
            "misalloc_raw": mis(raw), "misalloc_adj": mis(adj) if payload["sectors"] else None,
            "nb_raw": sum(raw.get(l, 0) for l in nb_letters),
            "nb_adj": sum(adj.get(l, 0) for l in nb_letters) if payload["sectors"] else None,
            "nb_official": sum(official.get(l, 0) for l in nb_letters),
            "watch": " ".join(f"{w['letter']}:{w['share']:.2f}%" for w in payload["watch"]),
            "seats_raw": " ".join(f"{l}{raw[l]}" for l in raw if raw[l]),
            "seats_adj": " ".join(f"{l}{adj[l]}" for l in adj if adj[l]),
        })
        print(f"[{i}/{of}] {label}: {rows[-1]['pct_of_final_valid']}% of final valid "
              f"(est {rows[-1]['pct_est']}%), misallocated raw {rows[-1]['misalloc_raw']} / "
              f"adj {rows[-1]['misalloc_adj']}, NB raw {rows[-1]['nb_raw']} adj {rows[-1]['nb_adj']} "
              f"(official {rows[-1]['nb_official']})")
        if step_seconds and i < len(seq):
            time.sleep(step_seconds)
    table = pd.DataFrame(rows)
    note = ""
    if not stop_at and not max_steps:
        table.to_csv(PROCESSED_DIR / f"election_night_replay_{year}_{src}.csv", index=False)
        note = f"; summary data/processed/election_night_replay_{year}_{src}.csv"
    print(f"\nwrote {_rel(out)} (+ .json) at each step{note}")
    return table


# ---------------------------------------------------------------- CLI
def parse_pairs(s: str) -> list:
    out = []
    for part in s.split(","):
        a, _, b = part.strip().partition("-")
        if a and b:
            out.append((a.strip(), b.strip()))
    return out


def build_once(args, cyc: Cycle, out: Path) -> dict:
    base = args.base_url or cyc.feed["base"]
    national = args.national_url if args.national_url is not None else cyc.feed["national"]
    stale, check, count, mode = None, [], None, "live"
    if args.manual:
        count = parse_manual_csv(args.manual, cyc, valid=args.valid, pct=args.pct_counted)
    elif args.snapshot:
        count = load_snapshot(Path(args.snapshot))
        if count is None:
            raise SystemExit(f"{args.snapshot}: no usable file in the snapshot")
    elif args.no_fetch:
        mode = "waiting"
    else:
        d = take_snapshot(base, national or None)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        check = [{k: i.get(k) for k in ("level", "url", "status", "ok", "problem", "rows", "valid")}
                 for i in meta["items"]]
        count = load_snapshot(d)
        if count is None:
            prev = last_good_snapshot(before=d.name)
            if prev is not None:
                count = load_snapshot(prev)
                probs = "; ".join(f"{i['level']}: {i.get('problem')}" for i in meta["items"])
                stale = {"since": meta["fetched_utc"], "problem": probs,
                         "showing": count.fetched_utc if count else None}
            elif all(i.get("status") == 404 for i in meta["items"]):
                mode = "waiting"
            else:
                mode = "waiting"
                stale = {"since": meta["fetched_utc"], "showing": None,
                         "problem": "; ".join(f"{i['level']}: {i.get('problem')}" for i in meta["items"])}
    if count is not None and args.pct_counted is not None:
        count.manual_pct = args.pct_counted
    payload = build_payload(count, cyc, mode=mode, check=check, stale=stale,
                            refresh=args.refresh_seconds, json_name=out.with_suffix(".json").name)
    write_page(payload, out)
    return payload


def _summary(p: dict) -> str:
    if p["mode"] == "waiting":
        return "waiting: no count yet" + (f" ({p['stale']['problem']})" if p.get("stale") else "")
    pr = p["progress"]
    nb = next(b for b in p["blocs"] if b["key"] == "nb")
    pct = pr["manual_pct"] / 100 if pr.get("manual_pct") is not None else pr.get("pct_votes")
    return (f"{p['source']['level']} count, {pr['valid']:,} valid"
            + (f" (~{100 * pct:.1f}% counted"
               + (", as entered" if pr.get("manual_pct") is not None else " of expected") + ")"
               if pct else "")
            + f"; NB raw {nb['raw']} adj {nb['adj']}; watch "
            + (", ".join(f"{w['letter']} {w['share']:.2f}%" for w in p["watch"]) or "none")
            + (f"; STALE since {p['stale']['since']}" if p.get("stale") else ""))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true", help="fetch (or read) once and write the page")
    ap.add_argument("--watch", type=int, metavar="SECONDS", help="fetch + build in a loop")
    ap.add_argument("--check", action="store_true", help="probe the feed and print what it serves")
    ap.add_argument("--replay", metavar="YEAR", help="rehearsal on a past count (2022)")
    ap.add_argument("--replay-mode", choices=("auto", "archive", "simulated"), default="auto")
    ap.add_argument("--step-seconds", type=float, default=0.0, help="pause between rehearsal steps")
    ap.add_argument("--max-steps", type=int, default=None, help="thin the rehearsal to N steps")
    ap.add_argument("--stop-at", type=int, default=None, help="stop the rehearsal after step N")
    ap.add_argument("--fetch-archive", metavar="YEAR", help="download the archived night files")
    ap.add_argument("--base-url", default=os.environ.get("EN_BASE_URL"),
                    help="directory holding expb.csv / expc.csv (default media26.bechirot.gov.il/files/)")
    ap.add_argument("--national-url", default=os.environ.get("EN_NATIONAL_URL"),
                    help="national results page ('' to skip)")
    ap.add_argument("--manual", metavar="CSV", help="manual vote table: list,votes")
    ap.add_argument("--valid", type=int, help="total valid votes for a partial manual table")
    ap.add_argument("--pct-counted", type=float, help="percent counted to display (manual)")
    ap.add_argument("--snapshot", metavar="DIR", help="rebuild from a cached snapshot directory")
    ap.add_argument("--pairs", help='override surplus pairs as letters, e.g. "מחל-ט,רק-ל"')
    ap.add_argument("--no-fetch", action="store_true", help="write the pre-count page without network")
    ap.add_argument("--refresh-seconds", type=int, default=120)
    ap.add_argument("--out", default=str(OUT_DIR / "election-night.html"))
    args = ap.parse_args(argv)

    if args.fetch_archive:
        got = fetch_archive(args.fetch_archive)
        print(f"downloaded {len(got)} archived files into {_rel(ARCHIVE_DIR)}")
        return
    if args.replay:
        out = Path(args.out) if args.out != str(OUT_DIR / "election-night.html") else None
        table = replay(args.replay, mode=args.replay_mode, out=out,
                       step_seconds=args.step_seconds, max_steps=args.max_steps,
                       stop_at=args.stop_at)
        with pd.option_context("display.width", 200, "display.max_colwidth", 60):
            print(table.drop(columns=["seats_raw", "seats_adj"]).to_string(index=False))
        return
    cyc = cycle_2026()
    if args.pairs:
        cyc.pair_override = parse_pairs(args.pairs)
    if args.check:
        base = args.base_url or cyc.feed["base"]
        nat = args.national_url if args.national_url is not None else cyc.feed["national"]
        for r in check_feed(base, nat or None):
            print(json.dumps(r, ensure_ascii=False))
        return
    out = Path(args.out)
    if args.watch:
        print(f"watching every {args.watch}s -> {_rel(out)} (Ctrl-C to stop)")
        while True:
            t0 = time.time()
            try:
                p = build_once(args, cyc, out)
                print(f"{utc_iso()} {_summary(p)}", flush=True)
            except Exception as e:                         # noqa: BLE001 - keep the loop alive
                print(f"{utc_iso()} build failed: {type(e).__name__}: {e}", flush=True)
            time.sleep(max(5.0, args.watch - (time.time() - t0)))
    if args.build or args.manual or args.snapshot or args.no_fetch:
        p = build_once(args, cyc, out)
        print(f"wrote {_rel(out)} + {p['json_name']}: {_summary(p)}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
