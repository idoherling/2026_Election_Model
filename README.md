# The Knesset Model: 2026 Israeli election forecast

A probabilistic forecast of the 27 October 2026 election to the 26th Knesset,
published as a bilingual (English and Hebrew) website. It gives every list's
seat distribution, the probability that each bloc reaches 61 seats, and the
odds of each government that could form.

The production path is a Bayesian state-space model of every published 2026
poll and every CEC poll filing (PyMC). Its posterior is projected to election
day through a stack of shocks calibrated on eight past elections, mixed over
the open list-registration events, and passed through the real seat law
(3.25% threshold, Bader-Ofer with surplus agreements). The resulting seat
draws feed a coalition-formation tree. A simpler weighted-average pipeline
is kept as a benchmark. Every modelling decision and its measurements are in
the decision log, `docs/priors_dossier.md`, cited below as "s.N".

```
Wikipedia poll archive ─┐                      ┌─ registration mixture ─ official forecast
manual_polls.csv ───────┼─ prepare_data ─ fit ─┤  (registration_scenarios) (official_forecast)
CEC poll filings ───────┤  (bayes_model)       │            │
sector polls ───────────┘                      │     formation tree ─ kalpi poststrat
                                               │  (government_formation) (kalpi_model)
                                  projection shock stack + seat law            │
                                       (bayes_model.project)                   │
research desks ─ evidence registry (build_sources) ─┬─ site build (build_site) ┘
docs/priors_dossier.md ─ decision log page ─────────┘   └─ checks (site_checks)
```

## How to run

Setup (Python 3.9; the Bayesian stack is pinned for it):

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The whole build is one command, run from the repository root:

```
python src/pipeline.py [--refresh] [--refit | --project-only] [--publish-check]
```

| flag | what it adds |
|---|---|
| `--refresh` | moves `data/raw/2026_main.html` to `data/raw/previous/` so the 2026 archive page is downloaded again, then runs `scrape_polls.py` and `scrape_cec.py` |
| `--refit` | `bayes_model.py`: 14-day holdout fits, the NUTS fit, the refit gates, the posterior save and the projection (the only slow step) |
| `--project-only` | `BAYES_PROJECT_ONLY=1 bayes_model.py`: re-projects the saved posterior `data/processed/m3_idata.nc` |
| (neither) | no model step. The chain still re-projects the saved posterior through the mixture |
| `--publish-check` | runs the test suite too, and writes the publish copy to `output/publish/` |
| `--skip STEP` | skips one named step (repeatable). The skip is logged |
| `-v` | echoes every output line |

The steps run in this order:

1. refresh (with `--refresh`)
2. model (with `--refit` or `--project-only`)
3. chain: `registration_scenarios`, `government_formation`, `official_forecast`, `kalpi_model`
4. site: `build_sources`, `build_decision_log`, `build_history`, `build_site`
5. checks: `src/site_checks.py`, always
6. headline

Each step's command, full output and timing go to `logs/pipeline_<timestamp>.log`
(gitignored). The run stops at the first step that exits non-zero or fails to
rewrite its output files. It then names the step, shows the last output lines
and exits 1. When every step passes, it prints P(bloc ≥ 61), the
government-group odds and the central seat count.

The publish copy is `output/publish/knesset-model-site.html` plus the
supporting file `decision-log.html`. The copy is `index.html` without the
first two lines (`<!doctype html>` and `<html lang="en">`), which the artifact
host adds itself. This is what `publish_checkpoint.sh` did by hand.

Two inputs are not in git. `data/raw/` holds the scrape caches and the kalpi
files. `data/processed/m3_idata.nc` is the posterior, written atomically by
`--refit`. Without a posterior the pipeline stops before the chain;
`registration_scenarios.py` run by hand would fit a smaller posterior itself
(600/600 draws).

**Finding new CEC filings.** The gov.il index lags the filings:

```
python src/scrape_cec.py --discover            # proposed index rows to stdout
python src/scrape_cec.py --discover --append   # ... and appended to data/cec_filings_index.psv
python src/scrape_cec.py                       # then download + parse
```

Discovery probes `https://www.gov.il/BlobFolder/dynamiccollectorresultitem/knesset_election{IDX}/he/Survey_{REF}.pdf`
and `Survey{REF}.pdf` (some filings drop the underscore). It tries each IDX
above the last indexed one against REFs above the last indexed ref, and stops
after two IDXs in a row with nothing (`--idx-span`, `--ref-span`,
`--max-misses`, `--idx-from` and `--ref-from` change this). Each PDF it finds
is saved to `data/raw/cec_pdfs/`. The tool reads the editor, publisher and
fieldwork date from the PDF text, in the conventions of the 16 Oct hand-added
rows:

- `survey_date` is the fieldwork date minus one day (gov.il's UTC shift, which `main()` adds back);
- the transfer date is the next day, marked approximate;
- a multi-day survey is dated by its last day.

Rows it cannot resolve are flagged `CHECK ...` in their notes.

Individual stages can still be run directly with `PYTHONPATH=src python src/<module>.py`.

## How to test

```
python -m pytest            # pytest.ini adds src/ to the path; about 10 s, no MCMC, no network
```

| file | what it pins |
|---|---|
| `tests/test_seat_law.py` | The official 2022 counts and registered pairs reproduce the official 2022 Knesset list by list, and all eight graded cycles reproduce too. Seats sum to 120 under the full shock stack. A list below 3.25% gets 0. A pair with a failing partner changes nothing. A pair moves its combined seats by 0 or +1. No list is pooled twice. The harness allocator equals production. `allocate_central` obeys the law |
| `tests/test_projection.py` | `bayes_model.project` on a synthetic CLR posterior, in the current and mixture configurations: 120 seats in every draw, all five 2026 pairs resolve, seeded |
| `tests/test_cec_parser.py` | `parse_pdf` gives exact values on filings 4202, 4207, 4211 and 4212 (fixtures in `tests/fixtures/cec/`): the three-line wrap, the "below 1%" line, the נועם spelling, the "ממשלת אחדות" line that is not Unity, and undecided 8.1. The discovery helper rebuilds the 16 Oct hand rows from the PDFs and probes both file names |
| `tests/test_merge_cec.py` | `_merge_cec` on synthetic frames: a filing displaces at most one table poll, and a poll is displaced at most once. Same-day pairs match first. A poll 2 days apart with a gap over 3 points is kept. The tolerances are pinned |
| `tests/test_formation.py` | `simulate_formation` on 500 synthetic Knessets, with the stage off, on (gates) and on the s.56 record path: outcome codes 0-9 and every branch reachable. Yisrael Beytenu never sits in outcome 4 without `lib_haredi`. Likud sits in outcomes 0, 1, 9 and 6 and nowhere else. The outcome-9 pledge-breaker is never named. P(repeat) and every non-{1,9} outcome are identical to the pre-s.52 tree. `main()` writes consistent membership rows |
| `tests/test_site.py` | the checks of `src/site_checks.py` on `output/site/index.html`, each with a negative control |
| `tests/test_registry.py` | every finding behind a cited source is verified or corrected, agreeing with its desk verdict, and the DL-n citations point at dossier sections |
| `tests/test_pipeline.py` | step order, stop on first failure, logging, `--skip`, and the refresh move-aside and restore |

Known bugs are pinned as strict `xfail` tests, which turn red when the bug is fixed:

- `scrape_cec.parse_pdf` fills `haredi_sample_pct` from the Haredi Public list's vote line. No model code reads the column.
- `build_sources.py` raises `IndexError` when more than ten sources share an author-year label. Today 11 share "CEC 2026".
- Because of that crash, the 30 verified `polls_beyond_vote` findings are missing from the registry.
- On the unshipped s.56 record-resolution path, Liberman's haredi veto has no effect: a deadlock that needs Yisrael Beytenu for a change + haredi government seats it even at `liberman_haredi_ok = 0`.

## Architecture

### 1. Data

- **Poll archive** (`src/scrape_polls.py`): the Wikipedia polling pages for the 2026 cycle and the eight graded cycles (2009, 2013, 2015, April and September 2019, 2020, 2021, 2022).
  - Tables are parsed from the HTML grid, so a joint list printed in one spanned cell becomes one composite observation (`balad+hadash_taal`).
  - "(x.y%)" cells become 0 seats with the vote share recorded, and footnote itemisations of small lists are added.
  - Pages are cached in `data/raw/<page>.html`, and a cached page is never re-fetched.
  - `data/manual_polls.csv` adds sourced press polls the archive lacks, and replaces archive rows whose seats do not sum to 120.
  - Output: `data/processed/polls.csv` (one row per poll and list) and `results.csv` (official results from the pages' result rows).
- **Names** (`src/normalize.py`): canonical pollster names and party labels. An unknown label raises an error.
- **Party registry** (`data/party_registry.csv`): canonical ids, Hebrew names, blocs and lineage notes across mergers and splits.
- **Pollster registry** (`data/pollster_meta.csv`): each firm's principal, outlet, fieldwork panel and correlation group. Firms that share an operation share a group, such as Filber and Direct Polls, or Lazar and Panels Politics. Background is in `docs/pollsters.md`.
- **CEC filings** (`src/scrape_cec.py`): every poll published in the election period is filed with the Central Elections Committee.
  - The index `data/cec_filings_index.psv` comes from the gov.il DynamicCollector, which sits behind Cloudflare and is refreshed in a browser.
  - The PDFs download openly.
  - Parsing is keyword-based per line, because the Hebrew extraction is RTL-scrambled.
  - Output: `cec_filings.csv` (sample size, margin of error, refusals, undecided share) and `cec_party_pcts.csv` (the raw share of every list, including sub-threshold lists).
  - Filings that are not national tables, and excluded editors, are kept for the record only: the Midgam Project consortium's raw sub-samples, sector-only samples, DRI and aChord.
- **Official counts** (`data/cec_final_counts.csv`): CEC final vote counts for every list, 2009-2022, with a source per row. `validate_seat_law.py` checks the seat law against them.
- **Sector polls** (`data/sector_polls.csv`, `src/sector_stream.py`): Afkar's Arab-sector shares, converted to national shares through kalpi-measured sector weights. They enter the fit as a firm of their own, with a noise multiplier.
- **Undecided leans** (`data/undecided_leans.csv`): the published measurements of how undecided voters lean, used by the certainty layer.
- **Kalpi panel** (`src/kalpi_model.py`): locality and polling-station results from the 2019a-2022 elections (`data/raw/kalpi/`). The panel feeds sector clustering, the sector-swing decomposition and the 2026 poststratification.

### 2. The state-space model (`bayes_model.prepare_data`, `bayes_model.fit`)

**Observations.**

- A seat row becomes the share `seats / 120 × (1 − wasted − 0.01)`, where "wasted" is the poll's itemised sub-threshold vote. A "(x.y%)" row is a direct share.
- The window is the last 240 days before the as-of date.
- One poll is kept per firm per fieldwork date: the variant with the most lists.
- Lists absorbed into another list are removed (Zehut into RZP, NEP into the Reservists), as are lists not on the ballot.
- A list needs at least 3 polls (filings count). The firm "S.M.L.T." is excluded.
- Mid-campaign mergers polled without a column get a structural break (RZP + 0.9 × Zehut's share before 2 Sept).
- Re-formed lists carry a noise multiplier on their earlier observations (`REFORMED_NOISE`).

**Latent.** The latent is a centred log-ratio (CLR) random walk, shipped in s.46 (`BAYES_CLR=1` is the default; `0` fits the old ALR latent).

- The grid is non-uniform: weekly bins to D-28, then 2-day bins.
- Every list b has its own start `z0_b ~ N(log early share, 0.5)`, innovation scale `tau_b ~ HalfNormal(0.06)` and steps `N(0,1) × tau_b × sqrt(dt)`.
- The walk is row-centred (`zc`), and the shares are `softmax(zc)`.

**House effects.** House effects are nested in correlation groups:

- `gamma_{g,b} ~ N(0, sigma_g)` and `delta_{f,b} ~ N(gamma_{g(f),b}, sigma_f)`;
- `delta_c` is centred across firms for each list;
- each firm also gets a linear drift over the window, `slope_c`, centred the same way.

The centring encodes that polls cannot identify how wrong the whole industry
is. That error enters at projection.

**Likelihood.** The likelihood is Student-t(4):

- mean: `share[week, list] + delta_c + slope_c × t`;
- scale: `(s_obs_b + 0.002) × lam_f × noise_mult × exp(beta_u × u_c)`.

The terms of the scale:

- `lam_f ~ LogNormal(log 1/q_f², 0.20)` is a per-firm precision. Its prior comes from the results-graded accuracy scorecard (`polling_average.quality_map`; the harness uses the leave-one-cycle-out scorecard, s.50).
- `u_c` is the filing's centred undecided share, and `beta_u ~ HalfNormal(3)` is estimated.
- A binomial sampling floor exists but is off (`BAYES_FLOOR=1`). The harness rejected it in s.23.

**Sampling.** NUTS with 4 chains, 800 tuning draws and 800 draws, target_accept 0.92.

**Checks.** `main()` refits on the data without the last 14 days, in CLR and in ALR, and scores the frozen prediction on the held-out polls. The simple pipeline is scored on the same holdout. The production build then has to pass the refit gates (`REFIT_GATES`, s.46):

- 0 divergences;
- r-hat ≤ 1.02 and bulk ESS ≥ 300, over the scale parameters and the endpoint shares;
- a CLR holdout error no worse than ALR's.

One reseed is allowed. Otherwise the build ships ALR. The outcome goes to `fit_summary.json` (`latent`, `refit_gates`). The posterior is written to a temporary file and renamed over `m3_idata.nc`.

### 3. CEC filings merge (`bayes_model._merge_cec`)

A filing's raw shares are better observations than shares inverted from a
seat table. `_merge_cec` applies these rules:

- A filing line for an absorbed list is dropped from the absorption date. A "unity" line after Unity withdrew is a which-government question.
- The same firm filing an identical vector within 3 days counts once.
- A filing is trusted when its parties sum to 90-105%, or when they reach at least 80% and, with the filed undecided share, 95-105%.
- Shares are renormalised by the party sum. The sample size is the filing's own (n, else the initial sample).
- **Matching** (16 Oct): a filing displaces at most one table poll, and a table poll is displaced at most once.
  - The first pass matches same-day polls of the same firm (tolerance 0.04, or fewer than 4 common lists).
  - The second pass matches polls 1-3 days apart, whose normalised vectors must agree within `CEC_MATCH_TOL = 0.03`.
- A displaced poll keeps its rows for lists the filing does not report.
- An unmatched filing enters as a new poll.
- The counts go to `fit_summary.json` (`cec_filings_merged`, `polls_displaced`).

### 4. Projection shock stack (`bayes_model.project`)

`project()` turns 8,000 posterior endpoint draws into election-day seat draws.
The layers apply in order. Every election-day shock comes from the sequential
decomposition of the eight-cycle error record (`error_decomposition.py`):
e0 is the raw error, e1 is after the bloc swing, e2 is after the family
totals and e3 is the per-list residual. No component is counted twice.

1. **Forward random walk.** The walk is run to election day with a campaign-volatility calendar: weight 0.64 within 35 days, 1.25 at 36-77 days, 1.13 before that (`campaign_vol_weight`).
2. **Withdrawn lists.** A list unpolled for 14 days inside the final 28 days, or for 35 days otherwise, leaves the race. Lists on the ballot never do. A dropped list stays at zero.
3. **Per-list residual.** The residual is Gaussian, with sd = the decomposition's line × `RESID_SCALE` 0.9. It is ×1.35 (`NEW_LIST_MULT`) for the new lists in `NEW_LIST_IDS`.
4. **Configuration.** In the published run this is the registration mixture (section 5).
5. **Bloc swing.** A Student-t(5) draw × the record's sd, moving the Netanyahu bloc against the rest. Since 17 Oct (s.58, `EVENT_RISK_HORIZON`) the old constant `EVENT_RISK` 1.2 multiplier is replaced by a compound-Poisson walk of bloc jumps. The jumps come from this cycle's verified event record, cover the days between the as-of date and the D-4 blackout (`event_walk`), and draw on a child generator. The walk is equivalent to a multiplier of about 1.03 at h = 8 days and exactly 1 at the final build.
6. **Certainty layer.**
   - Soft supporters churn at a Beta(mean 0.25, sd 0.12) rate with list-level LogNormal noise.
   - They are routed within the bloc, across it or into abstention by the Kolot Nodedim 2021→2022 transition matrix.
   - The undecided pool is the median filed undecided share over 45 days for Lazar, Midgam Project and Maagar Mochot, × 0.65 turnout. It breaks per side by the Beta posterior over `undecided_leans.csv` (s.18, s.41).
7. **Family shocks.** The haredi and Arab family shocks share a correlated t draw (rho 0.5, from the kalpi panel).
   - The haredi mean is the raw e0 mean (s.51).
   - The Arab term is a turnout mechanism: T ~ mean 0.580, sd 0.05, pass-through k 0.247 and intercept −0.634 seats (s.43).
8. **Anchors.** The fixed Likud and leader anchors are off (s.28).
9. **New-straddler desertion.** First-cycle lists projected within −0.75/+1.5 points of the threshold lose N(−1.6, 2.6) points (s.36).
10. **Trailing-Likud conditional.** When Likud trails or ties the largest non-bloc list (0.5-seat margin), it gains N(5.0, 4.9) × 0.5 seats. The seats come from its bloc's satellites, capped at 75% (s.36, s.41).
11. **Churn terms.** A gevalt coupling moves seats between Likud and its satellites (sd 2 seats). Centre churn moves seats between Yashar and Bennett 2026 + Yesh Atid (sd 1.5) and between Yashar and the Democrats (sd 0.8).
12. **Loyal-list shrinkage.** Shas, UTJ, YB, Likud, the Joint List, Yashar and Ra'am are shrunk to their measured total sd (`LOYAL_SD`).
13. **Kalpi capacity truncation.** Arab lists jointly ≤ 16.3% of the vote, Shas + UTJ jointly ≥ 6.6%.
14. **Seat law** (section 6).

Candidate layers that were graded and not shipped stay in the code behind
flags at their shipped values. Examples are `TRAIL_RAMP_ON`,
`THRESHOLD_ALL_VALID`, `HOUSE_CENTRE`, `HAREDI_ALLOC`, `ARAB_INTERCEPT_ALLOC`,
`T_UNIT_VAR`, `RESID_REL_CAP`, `RESID_SPACE` (s.48, s.60) and `NEW_STRADDLER_RECORD` (s.57). Each flag's comment cites its dossier
section.

### 5. Registration mixture (`src/registration_scenarios.py`)

The published forecast is a mixture over list-registration events, sampled
per draw (`apply_registration_events`), so every event's marginal effect is
read off the same simulations (`registration_effects.csv`).

- Each event has a stated prior and a transfer rule. Folds route votes by measured or declared vectors.
- `RESOLVED` collapses an event once it is decided. After filing day, the court rulings and Unity's withdrawal, every event is resolved except `blue_white_folds`: Blue and White withdrawing before election day, prior 0.25, its votes routed 0.60 to Yashar and 0.25 to Bennett 2026 + Yesh Atid.
- Outputs: `bayes_forecast_mixture.csv`, `mixture_shares.csv` (mean and median share vectors), `mixture_draws.parquet` (the seat draws the formation layer reads) and `mixture_blocs.csv`.
- The bloc probabilities count Ra'am with the change bloc in "neither" and in the "with Ra'am" figure.

### 6. Seat law (`src/simulate.py`)

The same code serves the simple simulator, `bayes_model.project` and
`official_forecast.allocate_central`:

1. Lists below the threshold (3.25%; 2% in 2009 and 2013) get no seats.
2. The surplus pairs are resolved (`resolve_pairs`): the first occurrence of an id wins, and the 2026 aliases map `together` to `bennett_2026+yesh_atid` and `joint_list` to `balad+hadash_taal` (s.40).
3. A pair is pooled only when both partners pass, and a list is never pooled twice (`form_factions`).
4. D'Hondt over the factions gives the seats (Bader-Ofer).
5. D'Hondt inside each pooled pair splits its seats.

`SURPLUS_PAIRS` for 2026: Likud and RZP, Together and Yisrael Beytenu, Yashar
and the Democrats, Shas and UTJ, and the Joint List and Ra'am. Otzma and
Amcha were dropped when Ben-Gvir refused, 13 Oct.

The threshold is tested against the modelled pie. Testing against all valid
votes (`THRESHOLD_ALL_VALID`, s.47) was graded and is off.

`validate_model.REGISTERED_PAIRS` holds the agreements actually registered in
2009-2022, with sources. `validate_seat_law.py` shows that they reproduce the
official seats from the CEC counts, in exact statutory arithmetic, in every
cycle.

### 7. Official forecast (`src/official_forecast.py`)

The central seat count is the mixture's median share vector, renormalised and
passed once through the seat law. It sums to 120 by construction. Intervals,
pass probabilities and bloc odds are read off the mixture draws. Output:
`official_forecast.csv`.

### 8. The formation tree (`src/government_formation.py`)

Coalition behaviour has no likelihood, so this layer is scenario analysis
with stated parameters. Each seat draw is run through a formation tree.

**Branches.**

- Netanyahu's bloc alone (0), or closed by kingmakers or Amcha (1).
- The change lists alone (2), or with kingmakers or Amcha (3).
- With a haredi defection (4). Liberman sits with haredim only if `liberman_haredi_ok` fires.
- A centre minority government backed by the Joint List (5).
- Unity, Likud without Netanyahu (6).
- With Ra'am inside (8).
- A change-bloc list breaking its pledge to join Netanyahu (9). Its membership is not attributed to any list (s.52).
- Otherwise a repeat election (7).

**Kingmakers.** Blue and White, Unity and the Reservists send their seats right, centre or nowhere, by their side priors. The Reservists' centre seats count only in coalitions with no haredi or Arab partner (`ZIONIST_ONLY`).

**Uncertainty.**

- Each `BEHAVIOR` probability is a Beta draw with an evidence-quality concentration (`BEHAVIOR_NEFF`), over 200 parameter vectors.
- Gate probabilities shift with the seat configuration through logistic covariates (`COND`).
- PM allocation within a coalition is a Dirichlet over `PM_ALLOC`.

**Post-deadlock stage** (s.49). In a deadlock, whether any government forms is drawn from the Israeli record: a Beta posterior on `DEADLOCK_RECORD`, 2 repeats in 7 parliamentary-era deadlocks, under a Jeffreys prior. Which government forms comes from re-drawing the gates (`STAGE_RESOLUTION = "gates"`). A variant that draws the government type from the record's resolutions (`"record"`, s.56) was graded and not shipped.

**Outputs.**

- `government_formation.csv` (outcomes)
- `government_groups.csv` (who leads)
- `government_membership.csv` (P(in government) by list)
- `government_by_nb.csv`
- `pm_probabilities.csv`
- `government_deadlock.csv`
- `government_sensitivity.csv`

`validate_formation.py` grades the shipped tree on the seventeen Knessets of
1977-2022.

### 9. Kalpi layer (`src/kalpi_model.py`)

- Localities are clustered into seven sectors by vote profile.
- Each locality's swing is decomposed into national, sector and local parts, and validated leave-one-transition-out against uniform swing.
- The central 2026 forecast is poststratified to sectors through each list's 2022 lineage (`kalpi_poststrat_2026.csv`, shown on the site).
- The sector-tide correlation (0.92) is the source of the family-shock rho, shrunk to 0.5.

### 10. Validation harness and the shipping rule

Nothing reaches production without grading on the eight past elections.

**Harnesses.**

- `src/validate_bayes.py` refits the model as of each election eve on that cycle's polls alone. It projects with leave-one-cycle-out shocks through the cycle's threshold and its registered pairs (`HARNESS_REG_PAIRS`, s.47). It grades median and mean seat MAE, 90% coverage, the threshold Brier score and the interval score.
  - Ablation arms are named in `ABLATIONS` (`HARNESS_ABLATIONS=shipped,arm` limits a run).
  - The ballot-fidelity windows are the default (`HARNESS_FIDELITY`, s.46).
  - Firm priors use the leave-one-out scorecard (`HARNESS_SCORECARD=loo`, s.50).
  - Posteriors are cached and signature-checked (`HARNESS_CACHE_DIR`; `build_harness_cache.py` fills a cache).
- `src/validate_horizon.py` does the same weeks out: `HORIZONS`, default `56,21`, with `HORIZONS=7` for D-7.
- `validate_threshold.py`, `calibration_arms.py` (s.48) and `width_nested_loo.py` grade threshold pass probabilities and interval widths on the cached posteriors.
- `harness_compare.py` prints a candidate's deltas against the shipped row.

**Shipping rule** (s.46, made explicit in s.51.1 and s.53, amended in s.55). A candidate is graded against the shipped baseline on the same seeds, on the shipped list mask (`--fixed`). It ships if all of these hold:

- pooled over three eve seeds (offsets 0/100/200), it wins or ties (|d| < 0.1 seat) the median MAE in every leave-one-cycle-out fold;
- mean MAE, threshold Brier and interval score are not worse beyond their noise floors (0.010 seat, 0.0010 and 0.05);
- coverage is no further from 0.90;
- D-7 and D-21 do not contradict, also scored on three seeds since s.55.

The rule is written before the result and applied as written. A post-hoc change is disclosed as such (s.55). The dossier records every candidate, its grade and the verdict.

### 11. Evidence registry (`src/build_sources.py`)

Every claim and method on the site rests on a registry entry. The research
desks live in `data/processed/forecast_research/`: `<desk>.json` holds the
findings and sources, `verify_<desk>.json` the verifier's verdicts. The brief
is in `RESEARCH_BRIEF.md` and `CONTENT_BRIEF.md`.

- `build_sources.py` keeps only findings whose verdict is `verified` or `corrected`. A corrected finding carries its corrected numbers and URL.
- Sources are deduplicated by DOI or title, and each gets an id (its first finding's id) with aliases.
- The model's own measurements are added as decision-log entries (`own_measurements.json`, ids `DL-n` → `decision-log.html#sN`).
- Output: `data/forecast_sources.json` and `data/forecast_findings.json`.
- Site citations are `<a class="cite" data-s="ID">`. `site_checks.py` checks that each one resolves and that every cited finding is verified.

### 12. Site build (`src/build_site.py`, `site/template.html`)

- `build_site.py` assembles one JSON payload and injects it into `site/template.html` at `__SITE_DATA__`. The payload holds the forecast, mixture, blocs, formation outputs, house effects, validation tables recomputed from the harness CSVs, kalpi sectors, a 2,500-draw sample, the poll ledger and firm ratings (`site_ledger.py`), the registry, and the live model constants quoted in the prose (`build_params`).
- The output is `output/site/index.html`, plus `site_data.json` so data changes diff in git.
- `build_history.py` reads every committed `output/site/site_data.json` back from git into `data/processed/forecast_history.csv`. Each build is classed polls / model / both / site, with its dossier sections. `build_site` turns the CSV into the "How the forecast has moved" section (`history_payload`), so `build_history` runs first.
- English chapters are HTML. Hebrew chapters come from the template's `HE_CH` table. Hebrew seats are always מנדטים. The site says "small parties", never the pollsters' "Others".
- `build_decision_log.py` renders `docs/priors_dossier.md` as `output/site/decision-log.html`, with an anchor `#sN` on every section, using marked 4.3.0 from cdnjs.
- `src/site_checks.py` runs the publish checks: the script parses (`node --check`; set `NODE` if node is not on the PATH), the EN and HE chapter counts match, citations resolve, the Hebrew and "Others" rules hold, and the registry status is clean.

### 13. Simple pipeline and research modules

The simple pipeline is the benchmark and holdout referee, not the published
forecast:

- `polling_average.py`: a weighted average with recency, sample size, accuracy and correlation-group weights and a trend adjustment.
- `house_effects.py`: consensus deviations with empirical-Bayes shrinkage. Also used for the site's bloc leans.
- `simulate.py`: a correlated-error Monte Carlo.
- `validate_model.py`: its retro-validation.
- `backtest.py`: the final-poll scorecard behind `lam`.
- `bias_audit.py`: seven bias tests.

Research modules:

- `hierarchical_model.py`: a joint nine-cycle model. Research; production calibration stays in `error_decomposition.py`.
- `workflow_bayes.py` and `docs/bayesian_workflow.md`: prior predictive, recovery and model ladder.
- `compare_models.py`, `arab_scenarios.py`, `turnout_layer.py`, `knesset_forecast.py`, `make_trend_chart.py`.

## Repository map

```
src/
  pipeline.py              the one-command build (this README, "How to run")
  scrape_polls.py          Wikipedia poll archive -> polls.csv, results.csv
  scrape_cec.py            CEC filings: download, parse, --discover
  normalize.py             pollster / party label canonicalisation
  bayes_model.py           state-space fit, CEC merge, projection shock stack
  error_decomposition.py   eight-cycle error record -> every projection shock
  registration_scenarios.py  registration mixture (the published distribution)
  simulate.py              seat law (threshold, pairs, d'Hondt); simple simulator
  official_forecast.py     central seat count from the mixture's median shares
  government_formation.py  formation tree -> government / PM probabilities
  kalpi_model.py           locality panel, sector swing, poststratification
  sector_stream.py         sector polls -> national observations
  build_sources.py         evidence registry from the research desks
  build_site.py            site payload -> output/site/index.html
  build_history.py         every committed build (git) -> forecast_history.csv
  build_decision_log.py    docs/priors_dossier.md -> decision-log.html
  site_ledger.py           poll ledger + pollster ratings for the site
  site_checks.py           publish checks (also run by tests/test_site.py)
  validate_*.py            harnesses: bayes (eve), horizon, threshold, seat_law,
                           formation, model (simple pipeline)
  calibration_arms.py, width_nested_loo.py, harness_compare.py,
  build_harness_cache.py   harness tooling
  polling_average.py, house_effects.py, backtest.py, bias_audit.py,
  compare_models.py, hierarchical_model.py, workflow_bayes.py, arab_scenarios.py,
  turnout_layer.py, knesset_forecast.py, make_trend_chart.py   benchmark / research
site/template.html         the bilingual page (payload placeholder __SITE_DATA__)
data/
  party_registry.csv, pollster_meta.csv, cec_filings_index.psv,
  cec_final_counts.csv, manual_polls.csv, sector_polls.csv,
  undecided_leans.csv, ran_vote_shares.csv            curated inputs
  forecast_sources.json, forecast_findings.json      evidence registry (built)
  processed/               tidy outputs (committed), forecast_research/ desks;
                           m3_idata.nc and harness_cache*/ are not committed
  raw/                     scrape caches, CEC PDFs, kalpi files (not committed)
output/site/               index.html, decision-log.html, site_data.json
output/figures/            charts
docs/                      priors_dossier.md (decision log), bayesian_workflow.md,
                           pollsters.md
tests/                     the fast suite; fixtures/cec/ holds four filing PDFs
logs/                      pipeline run logs (not committed)
```

A separate field-targeting project shares the working tree. Its files are
`src/targeting_*.py`, `src/build_targeting_site.py`, `site/targeting_*`,
`data/processed/targeting/` and `output/targeting/`. They are not part of
this pipeline.

## Data sources and terms

The code records where each source comes from and how it is fetched. It
records no licence for any of them. Check each publisher's terms before
redistributing raw data.

| source | used for | as stated in the code |
|---|---|---|
| Wikipedia polling pages (`scrape_polls.PAGES`) | the poll archive, past results | Fetched with the identifying User-Agent `IsraelElectionModel/0.1 (contact: ...)` and cached, so each page is fetched once. Wikipedia text is published under CC BY-SA; the repository does not record this |
| Press articles (`manual_polls.csv`, `undecided_leans.csv`) | polls the archive lacks, undecided leans | a source URL per row |
| CEC poll filings, gov.il (`scrape_cec.py`) | raw shares, methodology | Filed under the Elections (Modes of Propaganda) Law s.16E. The index is harvested from the gov.il DynamicCollector, which sits behind Cloudflare bot protection, by a real browser. The PDF blobs "are openly downloadable" |
| CEC results: votes20-25.bechirot.gov.il expc files, knesset.gov.il / bechirot.gov.il result pages via en.wikipedia, data.gov.il CEC dataset | `cec_final_counts.csv`, the kalpi panel, ledger links | a source per row in `cec_final_counts.csv`. `site_ledger.py` notes which official pages still answer |
| ParlGov (development version) and IDI election pages | the 1977-2006 formation record | `validate_formation.SOURCES` |
| Research literature and reporting | the evidence registry | a URL or DOI per source in `data/forecast_sources.json` |
| Afkar Arab-sector poll | sector stream | "owner-supplied" (`sector_polls.csv`) |

## Conventions

- Dates are ISO 8601. Processed data is UTF-8 CSV or parquet.
- Seat rows per poll must sum to 120 (`sums_ok`).
- Party ids are registry ids. A joint list is a `+`-joined composite.
- Every random stream is seeded (`SEED = 20261027`), so a rebuild from the same posterior reproduces the published outputs bit for bit.
- Model changes go through the harness and the shipping rule, and are written up in the dossier before they ship. Candidate code stays in place behind a flag at its shipped value.
