# 2026 Israeli Election Model

A poll aggregation and seat-projection model for the October 2026 election of the 26th Knesset.

## Architecture

The pipeline, in order:

1. **Poll database** (`src/scrape_polls.py`) — ingest published polls for the 2026 cycle
   (Wikipedia's polling tables) and the five backtest cycles (Apr 2019 – Nov 2022),
   normalized to one tidy format: one row per poll–party pair.
2. **Party registry** (`data/party_registry.csv`) — canonical party IDs and bloc
   assignments across mergers, splits, and renames. Every poll row must join to this.
3. **Aggregation** (planned) — weighted polling average: recency decay, sample size,
   then pollster house effects estimated hierarchically.
4. **Seat simulation** (planned) — Monte Carlo over vote shares: 3.25% threshold
   survival → Bader–Ofer apportionment with surplus agreements → P(bloc ≥ 61).
5. **Evaluation** (`src/backtest.py`) — final-poll averages vs official results
   per cycle (2009-2022), aggregated to the finest common partition of party
   components; per-cycle MAE and a per-pollster scorecard seed. Calibration
   and Brier scoring arrive with the simulation layer.

## Layout

```
data/
  raw/          # scraped HTML/tables, cached as fetched (not committed)
  processed/    # tidy CSVs: polls.csv, results.csv (committed)
  party_registry.csv
src/            # pipeline code
notebooks/      # exploration and chart drafts
output/figures/ # generated charts
```

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Conventions

- Every poll row: `poll_id, pollster, sponsor, fieldwork_start, fieldwork_end,
  sample_size, method, party_id, seats`. Seat rows per poll must sum to 120.
- Pollster names are canonical (see `POLLSTER_ALIASES` in `src/normalize.py`).
- Dates are ISO 8601. All processed data is UTF-8 CSV.
