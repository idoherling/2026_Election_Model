"""Scrape published Knesset polls into the tidy poll database.

Sources are Wikipedia's per-cycle polling pages, which carry pollster,
commissioning outlet, fieldwork dates, sample size, and projected seats per
party for every published poll.

Output schema (data/processed/polls.csv), one row per poll-party pair:
    poll_id, cycle, pollster, sponsor, fieldwork_start, fieldwork_end,
    sample_size, method, party_id, seats

Invariant: seats within a poll_id sum to 120.
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# The 2026 cycle is split across yearly pages; earlier cycles are one page each.
CYCLE_PAGES: dict[str, list[str]] = {
    "2026": [
        "https://en.wikipedia.org/wiki/2022%E2%80%932023_opinion_polling_for_the_2026_Israeli_legislative_election",
        "https://en.wikipedia.org/wiki/2024_opinion_polling_for_the_2026_Israeli_legislative_election",
        "https://en.wikipedia.org/wiki/2025_opinion_polling_for_the_2026_Israeli_legislative_election",
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Israeli_legislative_election",
    ],
    # Backtest cycles — fill in once the 2026 path works end to end:
    # "2022": [...], "2021": [...], "2020": [...], "2019_sep": [...], "2019_apr": [...],
}


def fetch_tables(url: str) -> list[pd.DataFrame]:
    """Fetch every wikitable on the page, caching raw HTML under data/raw/."""
    raise NotImplementedError  # step 2 of the build plan


def tidy_poll_tables(tables: list[pd.DataFrame], cycle: str) -> pd.DataFrame:
    """Reshape wide seat tables to the tidy schema and canonicalize labels."""
    raise NotImplementedError  # step 2 of the build plan


def validate(polls: pd.DataFrame) -> None:
    seat_sums = polls.groupby("poll_id")["seats"].sum()
    bad = seat_sums[seat_sums != 120]
    if not bad.empty:
        raise ValueError(f"{len(bad)} polls do not sum to 120 seats:\n{bad}")


if __name__ == "__main__":
    frames = []
    for cycle, urls in CYCLE_PAGES.items():
        for url in urls:
            frames.append(tidy_poll_tables(fetch_tables(url), cycle))
    polls = pd.concat(frames, ignore_index=True)
    validate(polls)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    polls.to_csv(PROCESSED_DIR / "polls.csv", index=False)
    print(f"Wrote {len(polls)} rows for {polls['poll_id'].nunique()} polls")
