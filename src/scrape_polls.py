"""Scrape published Knesset polls into the tidy poll database.

Sources are Wikipedia's per-cycle polling pages. Seat-projection tables sit
under year section headings ("2026", "2024", ...) or a "Polls" heading;
hypothetical-scenario tables ("New parties and mergers", "Alternative
leadership") are excluded.

Tables are parsed directly from the HTML grid (not pandas.read_html) so that
colspan cells are read as what they are: a joint electoral list published as
one number. Those become one observation with a composite party_id
("balad+hadash_taal+raam"), which is also the semantically correct unit —
Israel's 3.25% threshold applies to lists, not component parties.

Output (data/processed/polls.csv), one row per poll-list pair:
    poll_id, cycle, pollster, publisher, fieldwork_end, sample_size,
    party_id, seats, vote_pct, sums_ok, page, section

Below-threshold results published as "(x.y%)" become seats=0 with vote_pct
recorded — raw material for threshold modeling later.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import lxml.html
import pandas as pd

from normalize import canonical_pollster, party_lookup

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

USER_AGENT = "IsraelElectionModel/0.1 (contact: idoherling98@gmail.com)"

# page key -> (url, default year for dates without an explicit year)
PAGES: dict[str, tuple[str, int]] = {
    "2026_main": (
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Israeli_legislative_election",
        2026,
    ),
    "2026_2025": (
        "https://en.wikipedia.org/wiki/2025_opinion_polling_for_the_2026_Israeli_legislative_election",
        2025,
    ),
    "2026_2024": (
        "https://en.wikipedia.org/wiki/2024_opinion_polling_for_the_2026_Israeli_legislative_election",
        2024,
    ),
    "2026_2223": (
        "https://en.wikipedia.org/wiki/2022%E2%80%932023_opinion_polling_for_the_2026_Israeli_legislative_election",
        2023,
    ),
}

CYCLE = "2026"

POLL_SECTION = re.compile(r"^(\d{4}|Polls)$")
META_LABELS = {"Fieldwork date", "Date", "Polling firm", "Publisher", "Sample size"}
NON_PARTY_LABELS = {"Others", "Other", "Gov.", "Opp.", "Lead", "Don't know"}
RESULT_ROW = re.compile(r"election", re.I)

MONTHS = {
    m: i + 1
    for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())
}
FOOTNOTE = re.compile(r"\[[^\]]*\]")
DATE_RE = re.compile(
    r"(?:\d{1,2}\s*[–—-]\s*)?(\d{1,2})\s+([A-Za-z]{3})[a-z]*(?:\s+(\d{4}))?"
)
PCT_RE = re.compile(r"\(?\s*(\d+(?:\.\d+)?)\s*%\s*\)?$")


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", FOOTNOTE.sub("", s)).strip()


def fetch(page_key: str, url: str) -> str:
    cache = RAW_DIR / f"{page_key}.html"
    if cache.exists():
        return cache.read_text()
    import requests

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(resp.text)
    return resp.text


class Cell:
    __slots__ = ("text", "is_header", "origin", "cols")

    def __init__(self, text: str, is_header: bool, origin: tuple[int, int]):
        self.text = text
        self.is_header = is_header
        self.origin = origin
        self.cols: list[int] = []


def expand_grid(table_el) -> list[list[Cell | None]]:
    """Expand an HTML table into a dense grid, honoring col- and rowspans.

    A merged cell appears as the SAME Cell object at every grid position it
    covers, so spans can be recovered downstream via identity.
    """
    grid: dict[tuple[int, int], Cell] = {}
    trs = [tr for tr in table_el.iter("tr")]
    for r, tr in enumerate(trs):
        c = 0
        for el in tr:
            if el.tag not in ("td", "th"):
                continue
            while (r, c) in grid:
                c += 1
            cell = Cell(clean_text(" ".join(el.itertext())), el.tag == "th", (r, c))
            try:
                cs = max(1, int(el.get("colspan") or 1))
                rs = max(1, int(el.get("rowspan") or 1))
            except ValueError:
                cs = rs = 1
            for dr in range(rs):
                for dc in range(cs):
                    grid[(r + dr, c + dc)] = cell
            c += cs
    if not grid:
        return []
    nrows = 1 + max(r for r, _ in grid)
    ncols = 1 + max(c for _, c in grid)
    return [[grid.get((r, c)) for c in range(ncols)] for r in range(nrows)]


def column_labels(rows: list[list[Cell | None]]) -> tuple[list[str], int]:
    """Per-column label (deepest named header level) and body start index."""
    n_header = 0
    for row in rows:
        if row and all(cell is None or cell.is_header for cell in row):
            n_header += 1
        else:
            break
    ncols = len(rows[0]) if rows else 0
    labels = []
    for c in range(ncols):
        label = ""
        for r in range(n_header):
            cell = rows[r][c]
            if cell and cell.text:
                label = cell.text
        labels.append(label)
    return labels, n_header


def poll_tables(html: str):
    doc = lxml.html.fromstring(html)
    heading = None
    for el in doc.iter():
        if el.tag in ("h2", "h3"):
            heading = clean_text(el.text_content())
        elif el.tag == "table" and "wikitable" in (el.get("class") or ""):
            if heading and POLL_SECTION.match(heading):
                yield heading, el


def parse_date(raw: str, default_year: int) -> pd.Timestamp | None:
    m = DATE_RE.search(str(raw))
    if not m:
        return None
    day, mon, year = m.groups()
    mon_num = MONTHS.get(mon[:3].title())
    if not mon_num:
        return None
    return pd.Timestamp(int(year) if year else default_year, mon_num, int(day))


def parse_seats(text: str) -> tuple[int | None, float | None]:
    """Return (seats, vote_pct). (None, None) means no observation."""
    if text in ("", "nan") or re.fullmatch(r"[–—\-]+|—?N/a|n/a", text, re.I):
        return None, None
    pct = PCT_RE.search(text)
    if pct:
        return 0, float(pct.group(1))
    try:
        return int(float(text)), None
    except ValueError:
        return None, None


def parse_sample(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def scrape() -> pd.DataFrame:
    lookup = party_lookup()
    unknown_parties: set[str] = set()
    unknown_pollsters: set[str] = set()
    rows = []

    for page_key, (url, default_year) in PAGES.items():
        html = fetch(page_key, url)
        for table_i, (section, table_el) in enumerate(poll_tables(html)):
            grid = expand_grid(table_el)
            if not grid:
                continue
            labels, body_start = column_labels(grid)
            # Real seat tables have a Gov. column; quoted labels and
            # "Don't know" mark hypothetical/percentage tables.
            if (
                "Gov." not in labels
                or "Don't know" in labels
                or any('"' in l for l in labels)
            ):
                continue
            col_of = {l: i for i, l in enumerate(labels)}
            date_col = col_of.get("Fieldwork date", col_of.get("Date"))
            firm_col = col_of.get("Polling firm")
            if date_col is None or firm_col is None:
                continue
            party_cols = [
                i
                for i, l in enumerate(labels)
                if l and l not in META_LABELS | NON_PARTY_LABELS
            ]
            # A year section heading dates its polls; the page default only
            # covers pages whose sections aren't years ("Polls").
            year_default = int(section) if section.isdigit() else default_year
            # Tables run newest-first, so dates must descend down the rows;
            # a date that jumps forward past the row above belongs to the
            # previous year (tables straddle New Year without repeating it).
            prev_end: pd.Timestamp | None = None

            for r in range(body_start, len(grid)):
                row = grid[r]
                if len(row) <= max(party_cols or [0]):
                    continue
                firm_cell = row[firm_col]
                date_cell = row[date_col]
                if firm_cell is None or date_cell is None:
                    continue
                # Event rows: one cell spans the party columns with prose.
                first_party = row[party_cols[0]] if party_cols else None
                if first_party is not None and firm_cell is first_party:
                    continue
                pollster_raw = firm_cell.text
                fieldwork_end = parse_date(date_cell.text, year_default)
                if not pollster_raw or fieldwork_end is None:
                    continue
                has_explicit_year = bool(re.search(r"\d{4}", date_cell.text))
                if not has_explicit_year:
                    while (
                        prev_end is not None
                        and fieldwork_end > prev_end + pd.Timedelta(days=14)
                    ):
                        fieldwork_end = fieldwork_end.replace(
                            year=fieldwork_end.year - 1
                        )
                prev_end = fieldwork_end
                if RESULT_ROW.search(pollster_raw):
                    continue
                try:
                    pollster = canonical_pollster(pollster_raw)
                except KeyError:
                    unknown_pollsters.add(pollster_raw)
                    pollster = pollster_raw

                publisher = None
                if "Publisher" in col_of and row[col_of["Publisher"]] is not None:
                    publisher = row[col_of["Publisher"]].text or None
                sample = None
                if "Sample size" in col_of and row[col_of["Sample size"]] is not None:
                    sample = parse_sample(row[col_of["Sample size"]].text)

                # Walk distinct cells (by identity) across party columns;
                # a merged cell = one joint-list observation.
                seen: set[tuple[int, int]] = set()
                parsed = []
                for c in party_cols:
                    cell = row[c]
                    if cell is None or cell.origin in seen:
                        continue
                    seen.add(cell.origin)
                    covered = [
                        labels[cc]
                        for cc in party_cols
                        if row[cc] is not None and row[cc].origin == cell.origin
                    ]
                    seats, pct = parse_seats(cell.text)
                    if seats is None and pct is None:
                        continue
                    ids = []
                    for label in covered:
                        pid = lookup.get(label.casefold())
                        if pid is None:
                            unknown_parties.add(label)
                            pid = f"RAW:{label}"
                        ids.append(pid)
                    parsed.append(("+".join(sorted(set(ids))), seats, pct))

                if not parsed:
                    continue
                for party_id, seats, pct in parsed:
                    rows.append(
                        {
                            "page": page_key,
                            "section": section,
                            "source_row": f"{page_key}:{table_i}:{r}",
                            "pollster": pollster,
                            "publisher": publisher,
                            "fieldwork_end": fieldwork_end,
                            "sample_size": sample,
                            "party_id": party_id,
                            "seats": seats,
                            "vote_pct": pct,
                        }
                    )

    polls = pd.DataFrame(rows)
    if unknown_pollsters:
        print(f"UNKNOWN POLLSTERS ({len(unknown_pollsters)}): {sorted(unknown_pollsters)}")
    if unknown_parties:
        print(f"UNKNOWN PARTIES ({len(unknown_parties)}): {sorted(unknown_parties)}")
    return polls


def finalize(polls: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate across pages, assign poll ids, flag bad seat sums."""
    sig = (
        polls.sort_values("party_id")
        .groupby("source_row", sort=False)
        .apply(lambda g: tuple(zip(g["party_id"], g["seats"])))
        .rename("signature")
    )
    polls = polls.merge(sig, on="source_row")
    keep = (
        polls.drop_duplicates("source_row")
        .drop_duplicates(["pollster", "fieldwork_end", "signature"])["source_row"]
    )
    polls = polls[polls["source_row"].isin(keep)].drop(columns="signature")

    polls["poll_id"] = (
        CYCLE
        + "_"
        + polls["fieldwork_end"].dt.strftime("%Y%m%d")
        + "_"
        + polls["pollster"].str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)
    )
    # Same pollster, same day, different seat lines: suffix a/b/c. These are
    # usually alternate list-configuration variants published with one poll.
    firsts = polls.drop_duplicates(["poll_id", "source_row"])
    rank = firsts.groupby("poll_id")["source_row"].rank(method="dense").astype(int)
    ranks = dict(zip(firsts["source_row"], rank))
    needs_suffix = polls.groupby("poll_id")["source_row"].transform("nunique") > 1
    suffix = polls["source_row"].map(ranks).map(lambda x: chr(ord("a") + x - 1))
    polls.loc[needs_suffix, "poll_id"] = (
        polls.loc[needs_suffix, "poll_id"] + suffix[needs_suffix]
    )
    polls["cycle"] = CYCLE

    seat_sums = polls.groupby("poll_id")["seats"].sum()
    polls["sums_ok"] = polls["poll_id"].map(seat_sums == 120)

    n_polls = polls["poll_id"].nunique()
    bad = seat_sums[seat_sums != 120]
    print(f"{n_polls} unique polls, {len(polls)} party rows")
    print(f"seat sums != 120: {len(bad)} polls")
    if len(bad):
        print(bad.value_counts().sort_index().to_string())

    order = [
        "poll_id", "cycle", "pollster", "publisher", "fieldwork_end",
        "sample_size", "party_id", "seats", "vote_pct", "sums_ok",
        "page", "section", "source_row",
    ]
    return polls[order].sort_values(["fieldwork_end", "poll_id", "party_id"])


if __name__ == "__main__":
    polls = finalize(scrape())
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "polls.csv"
    polls.to_csv(out, index=False)
    print(f"wrote {out}")
    sys.exit(0)
