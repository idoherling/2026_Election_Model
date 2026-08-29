# The Bayesian Workflow

The forecast model, developed in workflow order (Gelman et al. 2020): every
stage below was run before the next was allowed to matter, and each produces
a machine-checkable artifact in `data/processed/workflow_*`. Reproduce with
`python src/workflow_bayes.py all`.

## 0. Estimand and generative story

**Estimand:** the seat count of every registered list in the 26th Knesset
election (by 2026-10-27), and the derived quantities that decide power:
P(list passes 3.25%), P(largest list), P(bloc ≥ 61).

**Generative story.** True national support for the L competing lists is a
smooth latent trajectory: composition-constrained shares that drift week to
week as events land. A pollster observes a noisy snapshot of it: it samples
imperfectly from a panel (sampling + design error), leans systematically
(house effect, correlated across firms that share owners, methods, or
panels), and publishes seats — a discretized, rounded transform of its share
estimate. What no poll observes: how the entire industry is collectively
wrong (shared mode effects, sector under-coverage), and what happens between
the last poll and election day. Both must come from history, not from the
2026 polls.

That story dictates the model structure:

| Story element | Model element |
|---|---|
| smooth latent drift | random walk on additive-log-ratio shares, weekly grid |
| composition constraint | softmax link, reference list fixed at zero |
| house effects, correlated by firm relationships | firm intercepts nested in correlation groups (`data/pollster_meta.csv`) |
| sampling + design + rounding noise | Student-t(4) observation error, per-list scale, estimated |
| industry-wide error | election-day shock priors calibrated on 8 graded cycles (2009–2022), leave-one-cycle-out |
| between-now-and-election drift | the random walk itself, run forward to election day |

**Data:** every published poll of the cycle within a 240-day window, one
observation per poll × list-block (joint lists and their components unified
across mergers: Together = Bennett 2026 + Yesh Atid; the Joint List =
Hadash-Ta'al + Balad, with Ra'am kept separate). Micro-lists no pollster
carries (Zehut, Noam, NEP) join at projection from historical priors.

## 1. Priors, stated and justified

| Parameter | Prior | Why |
|---|---|---|
| z₀ (initial ALR position) | N(empirical early-window ALR, 0.5); N(0, 1.5) for pure prior checks | weakly informative around the observed starting field; the pure version spans landscapes from dominant-party (Kadima '09) to fully fragmented |
| τ (weekly innovation, per list) | HalfNormal(0.06) | 0.06 in ALR ≈ ±0.4 seats/week for a mid-sized list; the prior's tail allows the ~2-seat weekly swings seen after major events |
| house effects σ_g, σ_f | HalfNormal(0.015), HalfNormal(0.008) | 0.015 share ≈ 1.8 seats — brackets the measured range of leans (±1–12 seats) after group pooling |
| observation scale s | HalfNormal(0.012) + 0.002 floor, t(ν=4) | ≈1.5 seats of noise; the floor blocks herding from implying impossible precision; t-tails absorb outlier polls |
| industry shocks | bloc swing t(5)·3.5 seats; Arab (−0.7, 1.2), haredi (−1.0, 1.6) | moment-matched on the eight-cycle backtest, leave-one-cycle-out in validation |

## 2. Prior predictive check (before data)

The joint prior must generate *plausible Israeli polling worlds* — not
certainty, not absurdity. Checked quantities (500 prior draws):
largest-list final share, mean weekly share movement, and the range of
simulated poll values. Results in `workflow_prior_predictive.csv`:

| Check | Result |
|---|---|
| largest list's final share, 5–95% | 0.19 – 0.72 |
| mean weekly share movement, 5–95% | 0.10 – 0.37 pp/week |
| simulated poll values in [0, 0.5] | 93.4% |

**Reading:** weekly movement and general shape are plausible; the upper
tail (a 72%-share list) is far looser than any real Israeli outcome. The
priors are deliberately weakly informative — the fitted model's
empirically-centered start does the tightening — but this is a known
looseness, recorded rather than hidden.

## 3. Fake-data recovery (known truth)

Data were simulated from known parameters (6 lists, 20 weeks, 6 firms,
t-noise, house effects) and the full model fitted to them. If the model
cannot recover truth it is known to contain, its real-data posteriors mean
nothing. Results in `workflow_recovery.csv`:

| Check | Result | Target |
|---|---|---|
| true share trajectories inside the 90% CI | **90.0%** | ~90% |
| innovation (τ) recovery correlation | 0.88 | high |
| house-effect recovery correlation | 0.94 | high |
| divergences | 0 | 0 |

**Reading:** the model recovers what it claims to estimate, with honest
interval calibration on known truth. The estimation machinery is sound.

## 4. The model ladder (real data, simplest first)

Each expansion had to earn its place against its predecessor by PSIS-LOO
(out-of-sample predictive fit) and residual criticism:

* **M0** static shares + normal noise — a fancy average; its residuals are
  serially correlated by construction (opinion moved).
* **M1** + random-walk trend.
* **M2** + per-firm house effects.
* **M3** + correlation-group nesting, Student-t noise, per-list scales — the
  production model.

Results in `workflow_ladder.csv` / `workflow_loo_compare.csv`:

| Model | ELPD (PSIS-LOO) | ΔELPD vs next | median \|resid\| (seats) | div |
|---|---|---|---|---|
| M0 static | 5269 | — | 0.85 | 0 |
| M1 + trend | 6349 | +1079 | 0.72 | 0 |
| M2 + house | 7722 | +1373 | 0.43 | 0 |
| **M3 full** | **8087** | **+365 (≈9 SE)** | **0.37** | 0 |

**Reading:** every expansion earns its place decisively. The two largest
gains are exactly what the generative story predicted: opinion moves
(M0→M1), and pollsters differ systematically (M1→M2) — the house-effect
step is the single biggest improvement, confirming that in the 2026 cycle
*who polled* carries almost as much information as *what they found*. The
robustness layer (M2→M3) still adds ~9 standard errors of out-of-sample
fit.

## 5. Out-of-sample checks

* 14-day holdout (both models frozen, graded on unseen polls): **Bayesian
  0.71 vs simple pipeline 1.09 seats median error.**
* Posterior predictive: ~98% of poll observations inside the 95% predictive
  band (slightly conservative).
* **The eight-cycle retro-validation** (`validate_bayes.py`): the Bayesian
  model refit as-of each past election eve, projected through that era's
  threshold and surplus pairs, graded identically to the simple pipeline.
  Round one FAILED (75.7% coverage vs the 90% target) and forced three
  fixes: a per-list election-day shock the projection had omitted,
  era-correct alliance identities for the historical windows, and
  withdrawal of lists unpolled in their final weeks. Round two, honest
  verdict:

  | Metric (8 cycles pooled) | Bayesian | Simple pipeline |
  |---|---|---|
  | 90% interval coverage | 93.6% | 95.9% |
  | bloc-majority Brier | 0.029 | 0.029 |
  | threshold Brier | 0.071 | **0.050** |
  | seat MAE | 1.95 | **1.55** |

  The Bayesian model matches on calibration and wins the live 14-day
  holdout, but the simple final-window average produces sharper
  election-eve point estimates in 7 of 8 historical cycles — most likely
  because its 5-day-half-life final window tracks last-week movement that
  a weekly-smoothed latent partially averages away. Recorded conclusion:
  the Bayesian model owns structure and uncertainty; the simple pipeline's
  election-eve central estimates remain the point-accuracy benchmark; the
  identified improvement is finer time resolution (or an ensemble center)
  in the final stretch.

### Round three: the party-anchored error decomposition

  All projection shocks were re-derived from one sequential decomposition
  of the eight-cycle error record (`error_decomposition.py`): bloc swing
  (sd 3.36) → family totals (haredi −1.35 ± 1.77, Arab −0.32 ± 1.45) →
  party anchors (Likud **−2.30**, seat-leader **−1.74** — polls understate
  both, stably across every leave-one-out fold) → residual
  (1.83 + 0.044·seats). This exposed and fixed a sign bug: shock means are
  in error space (polled − actual), so simulated truth must subtract them;
  the old code added them.

  Verdict, leave-one-cycle-out on the harness: the anchors **improved the
  Bayesian model on every point metric** (MAE 1.95 → 1.67, threshold
  Brier 0.071 → 0.063, coverage 97.3%) but **hurt the simple pipeline**
  (MAE 1.42 → 1.52) — its final-window average already chases the
  late-leader movement, so anchoring it double-corrects. Final validated
  configuration: anchors ON in the Bayesian projection, OFF in the simple
  pipeline; both calibrated from the same decomposition. Standing scores:
  simple MAE 1.42 / coverage 95.0% / bloc Brier 0.031; Bayesian MAE 1.67 /
  coverage 97.3% / bloc Brier 0.036.

## 6. Sensitivity of the headline number

The industry-shock priors are the one part of the projection the 2026 data
cannot identify. How much do they move P(Netanyahu bloc ≥ 61)?
Results in `workflow_sensitivity.csv`:

| bloc swing sd (seats) | family shocks | P(NB ≥ 61) | NB mean |
|---|---|---|---|
| 2.5 | on | 3.7% | 50.1 |
| 2.5 | off | 2.4% | 50.2 |
| **3.5 (base)** | **on** | **6.2%** | **50.1** |
| 3.5 | off | 4.9% | 50.2 |
| 4.5 | on | 9.3% | 50.0 |
| 4.5 | off | 8.4% | 50.2 |

**Reading:** the central estimate barely moves (the polls decide the mean);
the tail probability roughly doubles per extra seat of assumed industry
error. The honest headline is therefore a range — "P(Netanyahu-bloc
majority) is in the mid-single digits, 2–9% under any defensible reading of
historical polling error" — and that range, not the point 6.2%, is what a
publication should say.

## 7. Known limitations, stated up front

1. The random walk cannot anticipate the **list-registration discontinuity**
   (~47 days before the election) — that day is a scheduled refit, and
   uncertainty around it is understated beforehand.
2. Micro-list entries are prior-driven, not data-driven; their P(pass) is an
   assumption made visible, not a measurement.
3. The seats→shares inversion treats published seat tables as linear in
   shares; pollsters' own rounding and allocation conventions are absorbed
   into observation noise.
4. Surplus-agreement pairs are pre-filing assumptions.
5. ν=4 and the weekly grid are conventions, not estimates; both were chosen
   before seeing results and not tuned to them.
