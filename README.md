# 2026 Israeli Election Model

A poll aggregation and seat-projection model for the October 2026 election of the 26th Knesset.

## Architecture

The pipeline, in order:

1. **Poll database** (`src/scrape_polls.py`) — ingest published polls for the 2026 cycle
   (Wikipedia's polling tables) and the five backtest cycles (Apr 2019 – Nov 2022),
   normalized to one tidy format: one row per poll–party pair.
2. **Party registry** (`data/party_registry.csv`) — canonical party IDs and bloc
   assignments across mergers, splits, and renames. Every poll row must join to this.
3. **Aggregation** (`src/polling_average.py`) — weighted average for the live
   cycle: each pollster's latest poll, weighted by recency (half-life
   sharpens toward election day), sample size, backtested accuracy, and a
   correlation-group discount so related firms don't count twice; poll values
   are trendline-adjusted to today's level before averaging.
4. **Seat simulation** (`src/simulate.py`) — Monte Carlo over vote shares with
   correlated errors calibrated on the backtest (bloc swing, Arab/haredi
   family shocks, debut-list widening): 3.25% threshold survival → Bader–Ofer
   with surplus pairs → per-list seat distributions and P(bloc ≥ 61).
5. **Registration mixture** (`src/registration_scenarios.py`) — the headline
   forecast is a mixture over list-registration scenarios (Balad split, RZP
   merges, centre folds, new entries), each with a precedent-based prior and
   transfer rule, sampled per draw; on filing day the `RESOLVED` dict
   collapses the mixture to the true configuration (scheduled refit).
6. **Evaluation** (`src/backtest.py`, `src/bias_audit.py`,
   `src/validate_model.py`) — final-poll averages vs official results per
   cycle (2009-2022); seven systematic-bias tests; and full-model
   retro-validation: the entire pipeline rerun as-of each past election eve
   with leave-one-cycle-out calibration (pooled 90% interval coverage ~96%,
   bloc-majority Brier ~0.03).

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
