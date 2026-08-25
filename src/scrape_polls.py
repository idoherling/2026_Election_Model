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

WIKI = "https://en.wikipedia.org/wiki"

# page key -> (url, default year for dates without an explicit year, cycle)
PAGES: dict[str, tuple[str, int, str]] = {
    "2026_main": (f"{WIKI}/Opinion_polling_for_the_2026_Israeli_legislative_election", 2026, "2026"),
    "2026_2025": (f"{WIKI}/2025_opinion_polling_for_the_2026_Israeli_legislative_election", 2025, "2026"),
    "2026_2024": (f"{WIKI}/2024_opinion_polling_for_the_2026_Israeli_legislative_election", 2024, "2026"),
    "2026_2223": (f"{WIKI}/2022%E2%80%932023_opinion_polling_for_the_2026_Israeli_legislative_election", 2023, "2026"),
    "2022": (f"{WIKI}/Opinion_polling_for_the_2022_Israeli_legislative_election", 2022, "2022"),
    "2021": (f"{WIKI}/Opinion_polling_for_the_2021_Israeli_legislative_election", 2021, "2021"),
    "2020": (f"{WIKI}/Opinion_polling_for_the_2020_Israeli_legislative_election", 2020, "2020"),
    "2019s": (f"{WIKI}/Opinion_polling_for_the_September_2019_Israeli_legislative_election", 2019, "2019s"),
    "2019a": (f"{WIKI}/Opinion_polling_for_the_April_2019_Israeli_legislative_election", 2019, "2019a"),
    "2015": (f"{WIKI}/Opinion_polling_for_the_2015_Israeli_legislative_election", 2015, "2015"),
    "2013": (f"{WIKI}/Opinion_polling_for_the_2013_Israeli_legislative_election", 2013, "2013"),
    "2009": (f"{WIKI}/Opinion_polling_for_the_2009_Israeli_legislative_election", 2009, "2009"),
}

ELECTION_DAY = {
    "2009": "2009-02-10",
    "2013": "2013-01-22",
    "2015": "2015-03-17",
    "2019a": "2019-04-09",
    "2019s": "2019-09-17",
    "2020": "2020-03-02",
    "2021": "2021-03-23",
    "2022": "2022-11-01",
    "2026": None,  # by 2026-10-27
}

# Official-result baseline rows, e.g. "April 2019 legislative election".
RESULT_CYCLE = {
    "2009 election results": "2009",
    "2013 election results": "2013",
    "April 2019 legislative election": "2019a",
    "September 2019 legislative election": "2019s",
    "2020 legislative election": "2020",
    "2021 legislative election": "2021",
    "2022 legislative election": "2022",
}

# Rows whose "Polling firm" is really just the publisher (old-page format).
PUBLISHER_ONLY = {
    "channel 2", "channel 10", "channel 13", "channel 22",
    "maariv", "news company", "ten news", "walla", "walla news",
    # 2009-2015-era rows crediting only the outlet
    "channel 1", "globes", "haaretz", "israel army radio (galatz)",
    "israel radio", "reshet bet", "times of israel", "yedioth ahronoth",
    "yisrael hayom", "knesset channel/nrg", "yisrael post/sof hashavua",
}

# "Contents" covers the 2015-page layout where the poll table is the first
# element after the TOC, before any section heading.
POLL_SECTION = re.compile(
    r"^(\d{4}|Polls|Polling|By party|Contents|Seat projections|\d+(st|nd|rd|th) Knesset)$"
)
META_LABELS = {
    "Fieldwork date", "Date", "Polling firm", "Poll", "Pollster", "Media",
    "Publisher", "Sample size",
}
# Bloc totals (C/O = coalition/opposition, Netanyahu bloc), leads, residuals.
NON_PARTY_LABELS = {
    "others", "other", "gov.", "opp.", "lead", "don't know", "none",
    "c", "o", "l", "r", "netanyahu",
}
RESULT_ROW = re.compile(r"election", re.I)

MONTHS = {
    m: i + 1
    for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())
}
FOOTNOTE = re.compile(r"\[[^\]]*\]")
DATE_RE = re.compile(
    r"(?:\d{1,2}\s*[–—-]\s*)?(\d{1,2})\s+([A-Za-z]{3})[a-z]*(?:\s+(\d{4}))?"
)
# US-style "Feb 10, 2009" (the 2009-page format).
DATE_US_RE = re.compile(
    r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})(?:\s*[–—-]\s*\d{1,2})?,?\s*(\d{4})?"
)
# Trailing two-digit year after day-month ("19 Mar 20", "6-7 Aug 20").
TWO_DIGIT_YEAR = re.compile(r"\b\d{1,2}\s+[A-Za-z]{3}[a-z]*\.?\s+(\d{2})\s*$")


def explicit_year(raw: str) -> int | None:
    m = re.search(r"\b(\d{4})\b", raw)
    if m:
        return int(m.group(1))
    m = TWO_DIGIT_YEAR.search(raw)
    if m:
        return 2000 + int(m.group(1))
    return None
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
    if m:
        day, mon, year = m.groups()
    else:
        m = DATE_US_RE.search(str(raw))
        if not m:
            return None
        mon, day, year = m.groups()
    mon_num = MONTHS.get(mon[:3].title())
    if not mon_num:
        return None
    year_in_cell = explicit_year(str(raw))
    y = year_in_cell if year_in_cell is not None else default_year
    try:
        return pd.Timestamp(y, mon_num, int(day))
    except ValueError:
        # 29 Feb parsed under a non-leap default year: the poll belongs to
        # the leap year before (tables straddle New Year without repeating it).
        try:
            return pd.Timestamp(y - 1, mon_num, int(day))
        except ValueError:
            return None


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


def scrape() -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = party_lookup()
    unknown_parties: set[str] = set()
    unknown_pollsters: set[str] = set()
    rows = []
    result_rows = []

    for page_key, (url, default_year, cycle) in PAGES.items():
        html = fetch(page_key, url)
        for table_i, (section, table_el) in enumerate(poll_tables(html)):
            grid = expand_grid(table_el)
            if not grid:
                continue
            labels, body_start = column_labels(grid)
            # Quoted labels and "Don't know" mark hypothetical/percentage
            # tables; real seat tables carry many party columns.
            if "Don't know" in labels or any('"' in l for l in labels):
                continue
            col_of = {l: i for i, l in enumerate(labels)}
            date_col = col_of.get("Fieldwork date", col_of.get("Date"))
            firm_col = col_of.get(
                "Polling firm", col_of.get("Poll", col_of.get("Pollster"))
            )
            if date_col is None or firm_col is None:
                continue
            party_cols = [
                i
                for i, l in enumerate(labels)
                if l and l not in META_LABELS and l.casefold() not in NON_PARTY_LABELS
            ]
            if len(party_cols) < 6:
                continue
            # A year section heading dates its polls; the page default only
            # covers pages whose sections aren't years ("Polls").
            year_default = int(section) if section.isdigit() else default_year
            # Tables run newest-first, so dates must descend down the rows;
            # a date that jumps forward past the row above belongs to the
            # previous year (tables straddle New Year without repeating it).
            prev_end: pd.Timestamp | None = None
            # Buffer the table so topical sub-tables (a few parties only,
            # row sums nowhere near 120) can be dropped as a unit.
            table_rows: list[dict] = []
            table_result_rows: list[dict] = []
            row_sums: list[tuple[int, int]] = []

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
                if not pollster_raw:
                    continue
                key = pollster_raw.strip().casefold()
                # Old pages label their own election's outcome "Election
                # results"; baseline rows name historical elections explicitly.
                # Result rows often merge the date cell into the label, so
                # detect them before date parsing and stamp election day.
                result_cycle = RESULT_CYCLE.get(pollster_raw) or (
                    cycle if key in ("election results", "final results") else None
                )
                is_result = result_cycle is not None
                if is_result:
                    # A generically labeled "Election results" row identifies
                    # its election by its own date when it carries one — old
                    # pages' period tables end with the PREVIOUS election's
                    # results under the same generic label.
                    if RESULT_CYCLE.get(pollster_raw) is None:
                        dated = parse_date(date_cell.text, year_default)
                        if dated is not None:
                            near = [
                                c for c, d in ELECTION_DAY.items()
                                if d and abs((pd.Timestamp(d) - dated).days) <= 10
                            ]
                            if not near:
                                continue  # an election outside our range
                            result_cycle = near[0]
                    fieldwork_end = pd.Timestamp(ELECTION_DAY[result_cycle])
                else:
                    fieldwork_end = parse_date(date_cell.text, year_default)
                    if fieldwork_end is None:
                        continue
                    has_explicit_year = explicit_year(date_cell.text) is not None
                    if not has_explicit_year:
                        # No poll on a cycle's page is fielded after that
                        # cycle's election day — this anchors period tables
                        # whose newest row is from an earlier year (e.g. a
                        # "23rd Knesset" table ending in December 2020 on
                        # the 2021 page).
                        page_eday = ELECTION_DAY.get(cycle)
                        if page_eday is not None:
                            while fieldwork_end > pd.Timestamp(page_eday):
                                fieldwork_end = fieldwork_end.replace(
                                    year=fieldwork_end.year - 1
                                )
                        while (
                            prev_end is not None
                            and fieldwork_end > prev_end + pd.Timedelta(days=14)
                        ):
                            fieldwork_end = fieldwork_end.replace(
                                year=fieldwork_end.year - 1
                            )
                    prev_end = fieldwork_end
                if not is_result and RESULT_ROW.search(pollster_raw):
                    continue  # pre-election seats, municipal baselines etc.
                if "exit poll" in key:
                    continue  # exit polls are a different data class
                if key == "current composition":
                    continue  # sitting-Knesset baseline row, not a poll
                # Older pages pack "Firm/Publisher" into one cell (in either
                # order); the first segment that canonicalizes is the firm.
                pollster = pollster_raw
                inline_publisher = None
                if not is_result:
                    segments = [s for s in re.split(r"\s*/\s*", pollster_raw) if s]
                    for seg in segments:
                        try:
                            pollster = canonical_pollster(seg)
                        except KeyError:
                            continue
                        inline_publisher = (
                            "/".join(s for s in segments if s is not seg) or None
                        )
                        break
                    else:
                        if key in PUBLISHER_ONLY:
                            pollster = "Unattributed"
                            inline_publisher = pollster_raw
                        else:
                            unknown_pollsters.add(pollster_raw)

                publisher = inline_publisher if not is_result else None
                for pub_label in ("Publisher", "Media"):
                    if pub_label in col_of and row[col_of[pub_label]] is not None:
                        publisher = row[col_of[pub_label]].text or publisher
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
                if not is_result:
                    row_sums.append(
                        (sum(s for _, s, _ in parsed), len(parsed))
                    )
                for party_id, seats, pct in parsed:
                    if is_result:
                        table_result_rows.append(
                            {
                                "cycle": result_cycle,
                                "party_id": party_id,
                                "seats": seats,
                                "vote_pct": pct,
                                "source_row": f"{page_key}:{table_i}:{r}",
                            }
                        )
                        continue
                    table_rows.append(
                        {
                            "page": page_key,
                            "section": section,
                            "source_row": f"{page_key}:{table_i}:{r}",
                            "cycle": cycle,
                            "pollster": pollster,
                            "publisher": publisher,
                            "fieldwork_end": fieldwork_end,
                            "sample_size": sample,
                            "party_id": party_id,
                            "seats": seats,
                            "vote_pct": pct,
                        }
                    )

            complete = sorted(s for s, n in row_sums if n >= 6)
            median_sum = complete[len(complete) // 2] if complete else 120
            if median_sum >= 100:
                rows.extend(table_rows)
                result_rows.extend(table_result_rows)

    polls = pd.DataFrame(rows)
    if unknown_pollsters:
        print(f"UNKNOWN POLLSTERS ({len(unknown_pollsters)}): {sorted(unknown_pollsters)}")
    if unknown_parties:
        print(f"UNKNOWN PARTIES ({len(unknown_parties)}): {sorted(unknown_parties)}")
    return polls, pd.DataFrame(result_rows)


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

    # A poll belongs to the cycle of the next election after its fieldwork,
    # regardless of which page listed it (pages carry post-election rows).
    boundaries = sorted(
        (pd.Timestamp(day), cyc) for cyc, day in ELECTION_DAY.items() if day
    )

    def cycle_of(ts: pd.Timestamp) -> str:
        for day, cyc in boundaries:
            if ts <= day:
                return cyc
        return "2026"

    polls["cycle"] = polls["fieldwork_end"].map(cycle_of)

    polls["poll_id"] = (
        polls["cycle"]
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


def finalize_results(results: pd.DataFrame) -> pd.DataFrame:
    """One official-result line per cycle: prefer the copy summing to 120."""
    picked = []
    for cyc, g in results.groupby("cycle"):
        candidates = []
        for src, rows_ in g.groupby("source_row"):
            # Prefer the copy summing to 120, then the one with MORE party
            # lines (baseline rows of the same election are often condensed).
            candidates.append((abs(rows_["seats"].sum() - 120), -len(rows_), src))
        best_src = min(candidates)[2]
        picked.append(g[g["source_row"] == best_src])
    out = pd.concat(picked, ignore_index=True)
    sums = out.groupby("cycle")["seats"].sum()
    print(f"results captured for cycles: {dict(sums)}")
    return out.sort_values(["cycle", "party_id"])


if __name__ == "__main__":
    polls_raw, results_raw = scrape()
    polls = finalize(polls_raw)
    results = finalize_results(results_raw)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    polls.to_csv(PROCESSED_DIR / "polls.csv", index=False)
    results.to_csv(PROCESSED_DIR / "results.csv", index=False)
    print(f"wrote {PROCESSED_DIR / 'polls.csv'} and results.csv")
    sys.exit(0)
