# Final-week runbook (18–27 Oct 2026, and the count after)

Everything runs through `src/pipeline.py`; every published build passes its
checks and the test suite first. Publish target:
https://claude.ai/artifact/Vzs8UP91RRkVnELspHmzUM, page
`output/publish/knesset-model-site.html` plus the supporting files the
pipeline copies (`decision-log.html`, `annex-data.json`,
`election-night.html`, `election-night.json`, and `scorecard.*` once that
module lands).

## Each evening, Sunday 18 – Thursday 22 Oct (polls land 19:00–22:00)

1. New polls and filings:
   `mv data/raw/2026_main.html <scratch>/` (forces a fresh archive read), then
   `PYTHONPATH=src .venv/bin/python src/scrape_cec.py --discover --append`
   (gov.il posts filings on working days only; the index is behind
   Cloudflare, so the discovery probes the blob URLs directly).
2. Any poll missing from the archive and without a filing: enter it in
   `data/manual_polls.csv` from the publisher's own article, one row per list,
   with the source URL; seats must sum to 120. Do not add a manual row for a
   poll that has a CEC filing: the filing enters on its own, and the
   one-to-one matcher displaces the archive row.
3. `PYTHONPATH=src .venv/bin/python src/pipeline.py --refresh --refit --publish-check`
   (about 45 minutes: the refit gates are 0 divergences, r-hat <= 1.02,
   ESS >= 300 and the CLR holdout no worse than ALR, with one reseed and
   then an ALR fallback).
4. Add a `CURATED` entry for the new commit in `src/build_history.py` (kind
   "polls" unless the model changed), rebuild the history (`build_history.py`,
   `build_site.py`), publish, and commit. When committing `src/bayes_model.py`,
   stage a filtered blob without the targeting project's 4-line
   `project.last_shares` / `project.last_pairs` hook.

No model change in the final week unless it passes the s.53/s.55 rule on
three seeds and is written into the decision log first.

## Friday 23 Oct: the final pre-blackout build

- The last legal polls come in two waves: the Friday papers (Maariv,
  Israel Hayom) in the morning, and the TV channels' final polls in the
  Friday evening newscasts (Kan 11, Channels 12 and 13, i24; 2026: aired
  20:40-21:20 on 23 Oct). The freeze of record waits for the evening wave
  (s.73: a 13:43 freeze had to be re-taken twice). Last fieldwork D-4 in
  seven of eight cycles, DYN-F08. Ingest them as above and refit.
- With the asof at D-4 the event allowance is exactly 1.0 (s.58). Check
  that the site's annex shows it.
- Re-check the surplus agreements against the CEC's published list
  (EVT-F01 could not reach it on 16 Oct). The five pairs are in
  `simulate.SURPLUS_PAIRS`; if the CEC list differs, correct them and refit.
- Freeze the forecast for grading: `python src/scorecard.py --freeze`
  (once that module lands), commit the frozen JSON with its sha256, and
  publish. This is the forecast of record.

## Saturday 24 – Monday 26 Oct: the blackout

- No new polls. Do not republish forecast numbers. Site fixes only (text,
  accessibility), each through the pipeline's checks.
- Election-night dry run: `python src/election_night.py --check` (expect a
  404 until the CEC publishes) and `--replay 2022` for a full rehearsal.

## Tuesday 27 Oct: election night

- From 22:00: `python src/election_night.py --watch 180`. Each cycle caches a
  snapshot under `data/raw/election_night/` and rewrites
  `output/site/election-night.html` and `.json`; republish both with the page
  every few cycles.
- If the files move, use `--base-url` / `--national-url`. If the format breaks,
  type the national table into a CSV and run
  `--build --manual night.csv --pct-counted P`. The page keeps the last good
  count and says so.
- Expect the raw count to overstate the Netanyahu bloc early on. In the 2022
  replay the raw count said 72 at 25% counted, the adjusted count 64 (the
  official result was 64). Report the adjusted count; show the raw one too.

## 28 Oct onwards: envelopes and the official result

- Double envelopes (soldiers, hospitals, prisons, diplomats; about 10% of
  valid votes) are counted from 28 Oct. They lean by list: RZP up, the
  haredi and Arab lists down (TRN-F03). Keep the watch running until the
  final count.
- When the CEC publishes the official result:
  `python src/scorecard.py --score --result <official csv>`, then publish
  the scorecard page. One election is one draw: the page compares each
  score with what the eight-cycle record says such scores look like.
- Then, and only then, revisit the shipping rule for uncertainty-layer
  changes (three candidates, s.57, s.60 and s.61, failed only the per-fold
  median test), and grade the judgment layers (event risk s.58, the
  formation gates s.59) on the outcome.
- Grade the corrected new-straddler record (s.70, arm nstrad_fixed: Yachad
  2015 and Zehut 2019a in, 2009 and renamed parties out, vote shares,
  non-runners out; failed only on single horizon folds and D-7 coverage)
  on the Amcha Yisrael and Reservists-Economic results beside the shipped
  layer, and decide whether it replaces the seat-implied constant.
