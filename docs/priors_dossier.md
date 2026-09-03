# Priors Dossier — 2026 Election Model

**Compiled 2026-08-31 (D-57).** This document re-derives every judgment
parameter in the model from a structured expertise base: six research desks
(coalition-formation base rates 1992–2022; polling-error history 1996–2022;
party institutions & leader biographies; electoral sociology & vote flows;
race fundamentals & prediction markets; final-stretch campaign dynamics)
plus measurements run directly on the project's own nine-cycle poll
database. Statistical parameters remain owned by `error_decomposition.py`
(measured, leave-one-cycle-out); this dossier records where independent
evidence *validates* them and where judgment parameters moved.

---

## 1. Validation results — parameters the expertise CONFIRMED

These were checked against independent evidence and left unchanged.

| Parameter | Model value | Independent evidence |
|---|---|---|
| Likud anchor (polled−actual) | −2.30 | Bibi-premium table (9 cycles): mean +1.95, sd 4.0, median +0.4 — bimodal (2015 +8.5, 2019a +7.6, else ≈0±2). A within-bloc vacuum effect, not a bloc premium. |
| Haredi family shock | −1.35 ± 1.77 | Shas beat final polls +1.2 (sd 1.2) over six cycles; UTJ +0.4. Haredi turnout ~80%, poll-relative surprise skews positive. |
| Arab family shock | −0.32 ± 1.45 | No stable sign historically; the error is a turnout error (Arab turnout range 44.6–64.8%, sd ≈ 7.5pp; ±5pp ≈ ±1.5 seats — matches family sd). |
| Bloc swing sd 3.36 (+EVENT_RISK 1.2) | | Final-fortnight-plus-blackout bloc innovation sd ≈ 2.5–3 historically; war-rally analysis (June 2025: Likud +4, bloc ≈0, half-life ~25 days) says variance inflation is the right vehicle, no mean shift. |
| `uncertainty_scale = √(1+days/25)` (simple pipeline) | ratio 1.60 at D-57 | Measured D-60 vs final-week MAE ratio 1.49 (per-cycle band 1.54–1.76). In band. |
| Threshold pass rates (simulated) | e.g. RZP-alone 0.30–0.47; Amcha 0.59 | Historical ledger 2015–2022: 4-seat final polls → P(pass) 0.55 (0.35 new/unmerged, 0.70 established); 5 seats → 0.82; 6 → 0.95. Model's emergent numbers sit on this curve. |
| MERGE_RETENTION 0.90 | | Merger premiums are ~zero-to-negative and decay (Likud-Beytenu 42-45→31; B&W bounce decayed in 6 weeks; Dem Union 7→5). |
| Surplus pairs in Bader-Ofer | mechanical | Measured value +0.5–0.9 expected seats per signed pair; ~6–9 of 120 seats decided at the surplus stage. |
| P(repeat) conditional structure | tree gives ~0.47 given neither bloc ≥61 | Historical base rate: repeat election in 2/4 deadlocked formations (0.50). |
| Headline probabilities vs markets | P(NB≥61) 25%; P(Netanyahu PM) 26%; P(repeat) 22% | Polymarket: Netanyahu PM 30% (aligned); implied NB majority ~26–30% (aligned); hung parliament 26% (aligned). The one large gap — market Eisenkot PM 50% vs model 36.5% — is judged a market error: internally inconsistent with its own hung-parliament and confidence-vote-by-Dec-31 (45%) markets. |
| House-effect design (Filber/Direct/Ch14 as correlated biased cluster) | | Ch14 caught illegally withholding poll filings (Aug 2026); Filber runs its polls; peer-reviewed finding that outlet alignment predicts bloc error. Treat house effects as bimodal — exactly the correlation-group design. |
| Anchors ON for Bayes only | | Harness-validated earlier; fundamentals desk endorses anchor over an added premium (avoids double-count with pre-loaded Ch14 herding). |

## 2. Changes made this round — statistical layer (measured on own DB)

**NEW_LIST_MULT = 1.35** (`bayes_model.py`). First-cycle de-novo lists'
final-30d poll error: sd 2.83 vs 2.14 established (D-60: 3.98 vs 2.93).
Mean fade NOT significant (+0.1 final-window; tails two-sided: New Right
+7.4 over-polled, Yesh Atid 2013 −7.9 under-polled) → variance only, no
drift. Applied to: yashar, amcha_yisrael, zionist_home, unity.

**GEVALT_SD = 2.0** (`bayes_model.py`). Zero-sum Likud↔NB-satellite
coupling (otzma, rzp, amcha, zehut, noam), proportional to satellite size.
Evidence: Likud final-poll beats of +8.4 (2015) and +6.7 (2019a) were paid
by satellites near 1:1 (Jewish Home −4, Yachad dead; New Right/Zehut
dead); ~0–3 in other cycles. The Likud anchor carries the mean; this term
adds the missing negative correlation so satellite threshold deaths
co-occur with Likud surges — the model's Amcha/RZP–Zehut death scenarios
now correlate correctly with Likud upside. Not harness-validated
(era-specific satellite maps would be needed); structurally motivated.

## 3. Changes made this round — formation layer (institutions + base rates)

| Parameter | Old → New | Derivation |
|---|---|---|
| `utj_defects` | 0.35 → 0.26 | Full-UTJ signature needs BOTH councils incl. Gur (deep distrust); Degel-only partial is the likelier form (2004–06 Agudah-alone precedent). Blend: 0.15 full + 0.22 partial × ½. Landau's "no bloc exists" + May 26 Degel–Eisenkot draft-law meeting keep it well above pre-news levels. |
| `shas_defects` | 0.08 → 0.10 | Crossing needs one psak from Yitzhak Yosef — newly empowered (Aug 2026 Maya letter), privately called Eisenkot "a warm Jew who can be trusted"; 1992 Ovadia precedent proves the mechanism. Capped low because the centre's shared anti-exemption identity leaves no deal space. |
| `liberman_haredi_ok` | (new) 0.20 | His haredi veto is electoral identity since 2019, held through every fork; centre-haredi branch must now clear 61 *without* YB in 80% of draws. |
| `likud_sans_bibi` | 0.15 → 0.18 | Unity resolved ~half of historical deadlocks (1984/1988/2020); institutions desk: P(Netanyahu accepts exit \| dead-end) 0.35, tempered because the 2026 cleavage is personalized on Netanyahu (the condition under which unity failed in Sept 2019). Kalon precedent: he trades everything except political existence. |
| `rzp_merge_otzma` | 0.02 → 0.08 | Netanyahu personally forced this merger in 2021 AND 2022 — never fully trust a "final and absolute" refusal; discounted because this cycle Ben Gvir is above threshold and bleeding to Winter (no mutual threshold fear). |
| `amcha_right` 0.87, conditional `amcha_center` | (prior round) | Confirmed by institutions desk (P(recommends Netanyahu) 0.90) and by the two-stage kingmaker analysis: pledge binds the President's-Residence stage only. |
| `raam_joins` 0.35 / `raam_supports` 0.55 | (prior round) | Confirmed: Shura veto abolished Dec 2025 (Abbas signs alone); 2021 precedent delivered and Ra'am *survived* 2022; institutions desk P(signature available) 0.60. Joins < supports because every Jewish party still pledges no Arab party inside at the outset — entry modeled as post-formation expansion. |
| Base-rate warnings encoded | | Investiture needs plurality only (60–59 precedent) — minority branch is legally cheap, behaviorally unprecedented (0 ever sworn from day one → `liberman_minority_ok` 0.25 keeps it a thin tail). Pledge-break probability is endogenous to the offer and election count — 2026 is election #1 of a new sequence (the 25th Knesset served full term), arguing for the *low* end, hence `centre_defects` stays 0.12. |

## 4. Sociology facts the mixture/turnout layers now rest on

- Two frozen blocs, churn inside: genuinely bloc-crossing voters ~1.3–5%;
  net flows ≤1.5pp. The operative channels: Likud→Yashar masorti raid
  (cap ~2–3 seats — the one live persuasion channel), sub-threshold waste
  (~8% of vote — the race's core), differential abstention.
- Elastic pairs for correlated errors (tier 1): Likud↔Amcha, Likud↔Otzma,
  Otzma↔RZP, Shas↔Otzma, Shas↔Yashar, Yashar↔Together, centre micro pool
  (B&W/ZH/Unity share one electorate — polling shows each at 4 when Erdan
  absent, ~0 when he runs).
- Demographic drift vs 2022: haredi pool +1.5–2 seats (mechanical, partly
  offset by draft-crisis leakage already in polls); first-timer cohort
  (~8.7% of electorate) right-religious-skewed ≈ +1.5–2 NB potential,
  discounted by record "voting changes nothing" cynicism; emigration
  −1–1.5 centre-left seats; Arab eligible share +0.5pp.
- Double envelopes: record 600–700k expected (~12–13% of votes), counted
  late; historical lean: RZ/right lists overperform, haredi and Arab lists
  ~⅓–½ under their regular-station share; night→final drift ≈ +0.5–1 seat
  right, threshold-straddlers at 3.1–3.5% most at risk (Meretz/Balad 2022
  died in the envelopes). → election-night engine must publish
  "election-night seats" vs "final seats" separately.
- Turnout priors: national 70.5% ± 2.5; Arab central 56–62% (unity signed,
  Ra'am-JL coordination; disillusion tail 48–55% p≈0.25); haredi 78–82%
  near-invariant with a small protest-under-vote tail; the CEC's real-time
  voter-ID ban degrades machine-party GOTV (Likud/Shas most) — shrink the
  historical haredi/Likud election-day surge slightly.

## 5. Final-stretch calendar (structural events, dated)

| Date | Event | Model action |
|---|---|---|
| Sept 8 | Trial resumes; HCJ inquiry hearing | — |
| **Sept 9–10** | **Lists filed with CEC** | Collapse RESOLVED dict; registry + SURPLUS_PAIRS refresh; scheduled refit |
| Sept 11 – Oct 3 | Holiday freeze (RH/YK/Sukkot) | Polls sparse/stale — expect herding on re-entry; don't over-read gaps |
| Oct 4 | Trial goes 5 days/week; campaign restarts | — |
| Oct 7 | 3rd anniversary (Yarkon Park memorial) | Eisenkot's peak-salience week |
| **Oct 16** | **Surplus agreements filed** | Update SURPLUS_PAIRS from real filings |
| Oct 20 | Diplomatic-mission voting | — |
| **Oct 23 (Fri)** | **Poll blackout begins**; Rabin memorial weekend | Final refit on Oct 22–23 polls; blackout window carries the full gevalt/late-swing shock (2015/2019a lived here) |
| **Oct 27** | Election day, polls close 22:00 | Exit polls lean ~1–2 seats left/anti-haredi pending envelopes |
| Nov 4 | Results certified | Accuracy report baseline |

## 6. Standing disagreements & open questions

- **Market gap on Eisenkot-PM** (50% vs model 36.5%): holding the model's
  number; the market's own conditional legs are inconsistent. Revisit if
  the gap persists after Sept 9 resolves list structure.
- **Fundamentals mean shifts** (incumbent Oct-7 drag −1.5, fundamentals
  desk): NOT applied — editorial, unvalidated, and P(NB≥61)=25% off a
  48–52 polling bloc already embeds fat uncertainty in both directions.
  Documented here so the choice is visible.
- **Gevalt conditionality**: the premium historically fires when Likud
  *trails* with soft satellites — 2026 matches. GEVALT_SD 2.0 is symmetric;
  an asymmetric version is a candidate post-Sept-9 refinement.
- **Degel-only partial UTJ defection** is blended into `utj_defects`; an
  explicit split-UTJ branch is a possible refinement if the Degel–Agudah
  slate fight reopens.
- Weather: late-Oct rain is low-probability; Arab-sector turnout is the
  weather-sensitive margin. No parameter; watch the forecast in the final
  week.

## 7. Addendum (2026-09-01): the loyal-electorate audit

Owner audit request: Shas/UTJ/YB sub-threshold probabilities (6–10%) priced
events that have never happened. Measured on our own DB (D-60 window,
2013 excluded for YB's joint list): Shas err sd 0.92 (worst downside ever
−0.4 — it BEAT its D-60 polls in all 7 cycles), UTJ 0.74 (worst +1.3),
YB 1.71 (worst +1.2) — vs model totals ~3.3 from the pooled residual +
haredi family shock + t-tails, a triple-count for captive electorates.
Fix: `LOYAL_SD = {shas 1.5, utj 1.3, yisrael_beytenu 2.2}` — post-shock
shrink of each standalone list's draws to its measured total sd × ~1.5
novelty buffer (draft-arrest crisis, Eisenkot masorti raid, Haredi Public
burn are genuinely new channels; and the record is 7 cycles, not a law).
Joint lists keep pooled width (exact-set match). Mirrored into the
validation harness. Result: Shas pass 0.91→0.99, UTJ 0.92→1.00, YB
0.94→0.95; both blocs' majority odds tightened and P(neither) rose to
0.53 (fewer haredi-collapse fantasies in either tail). Caveat noted:
LOYAL_SD derives from the same record the harness scores — floors, not
fitted parameters.

## 8. Addendum (2026-09-01b): full-board volatility + the certainty layer

Extension of the loyal-electorate audit to every list, two new evidence
sources: (a) lineage/analog D-60 measurement per list; (b) the
vote-certainty polling record (JPPI Jul/Aug waves; Midgam certainty +
waverer split; the N12 Likudnikim panel; Winter sourcing).

Lineage targets added: likud 4.8 (measured 3.53 - the mixture was
double-counting structural variance already present in historical D-60
windows), balad+hadash_taal 3.1 (measured 2.30), yashar 4.2 (owner's
analog-class suggestion: Blue & White in its prime, sd 2.76, mean -2.3
under-polled - the upside mean is already the leader anchor). Left at
pooled with reasons: Democrats (lineage sd includes two-list threshold
deaths the merger removed), Together width (but see below), Otzma/RZP
(match), Ra'am (n=2).

Certainty layer (measured): SOFT_LIST_MULT together x1.25 (47% locked,
ten straight weeks bleeding to Yashar); CENTRE_CHURN zero-sum
yashar<->together 1.5 / yashar<->democrats 0.8 (change-bloc internal
wavering measures 3x the NB bloc's: 4.0% vs 1.3% of the electorate;
parts move, bloc holds); AMCHA_FADE -1.5 seats returned to measured
sources (likud .5/otzma .25/rzp .25) - the right-flank leader-vehicle
class over-polled at D-60 by +4.2 (5 of 6 cycles), and Winter's list is
the softest on the board (38% locked, 40% of base unattached a month
ago). Result: Amcha central 2.4, pass 0.36 - exactly the historical
pass rate for 4-seat new lists. official_forecast now uses MIXTURE
intervals/pass for the published table (was baseline - inconsistent).

Headline after this round: P(NB>=61) 19.9 / P(anti>=61) 24.7 /
P(neither) 55.4; PM: Eisenkot 31.4 / repeat 30.0 / Netanyahu 24.0.
Deadlock and Eisenkot are now statistically tied for modal outcome.

## 9. Addendum (2026-09-01c): the kalpi layer

Owner directive: MRP/kalpi-level modeling. Built src/kalpi_model.py on
official per-locality CEC results (expc.csv, media21-25.bechirot.gov.il;
per-kalpi expb.csv downloaded for the election-night engine), 1,221
localities x 5 cycles, letters->lineages hand-mapped and ASSERTED
against national totals at load. Products:
- Sector clustering from vote profiles: sizes (eligible) centre_left
  2.47M / mixed 1.83M / secular_right 1.21M / arab 839k / haredi 304k /
  RZ 128k; measured 2022 turnout haredi .758, arab .538, RZ .756 -
  independently confirms the sociology desk's numbers.
- Family-sum swing decomposition (lineage-stable across list-structure
  changes) + LOTO validation. NEGATIVE RESULT recorded: sector swings
  do not transfer across transitions (uniform 1.20pp vs sector 1.31pp
  locality MAE) - uniform-swing-given-national is the locality baseline;
  the sector layer earns its keep via correlations and capacity, not
  point swings.
- Cross-sector tide correlation: haredi<->arab +0.92 (n=4 transitions,
  both turnout-machine sectors) -> KALPI_FAMILY_RHO=0.5 (shrunk) now
  correlates the projection's haredi/arab family shocks (previously
  independent). Headline effect small: P(neither) 55.4->54.6.
- Poststratification of the 2026 forecast to sectors
  (kalpi_poststrat_2026.csv) with lineage weights from the measured
  vote-flow research; passes capacity checks (Arab-sector implied seats
  ~8.6 vs ~11 turnout capacity).
- Election-night foundation: kalpi-level files + locality panel +
  sector map stored for the October engine.
True respondent-level MRP remains blocked on microdata (pollsters do
not publish crosstab microdata); the kalpi substrate is the honest
ecological equivalent.

## 10. Addendum (2026-09-01d): Kolot Nodedim cross-validation

Owner pointed to kolot-nodedim.netlify.app (harelc/elections-vote-
transfer): kalpi-level voter-transition matrices via constrained convex
optimization (row-stochastic M, R^2 0.75-0.96 per pair, K16-K25) with a
Dirichlet(alpha*p) per-kalpi noise layer, alpha estimated by moments.
Three integrations:
1. LINEAGE_2026 recalibrated against their measured K24->K25 matrix
   (Yamina->RZP 45/JH 24/Likud 14/NU 11; B&W->NU 71+YA 30; Likud
   retention 90%; YB 79%) - also fixed a silent bug where "yamina" keys
   had no 2022 counterpart and zeroed out.
2. Their per-party alpha (effective kalpi sample size ~30-120 vs ~340
   voters, overdispersion 3-14x) INDEPENDENTLY corroborates the
   loyal-electorate calibration: haredi lists tightest (Shas alpha to
   226), big Jewish lists middle, with their honest note that Arab
   lists' low alpha is geographic bimodality, not voter fickleness.
   Their finding that alpha collapses in upheaval cycles (K20->K21)
   mirrors our sector-swing non-transfer result.
3. alpha_estimates.json + transfer matrices stored in
   data/raw/transfer/ - the per-kalpi overdispersion is the noise model
   the October election-night engine needs (without it, early returns
   would be over-trusted ~10x).

## 11. Addendum (2026-09-01e): the measured undecided-allocation layer

Improvement #3 implemented. Published seat polls already allocate
undecideds by each house's opaque method (~proportional or past-vote);
the 2026-MEASURED break is neither: N12/Midgam Jul 30 - pool 12% of the
electorate, 55% "a candidate who is not Netanyahu" / 16% Netanyahu /
29% tossup. With the GIQ 0.65 turnout haircut and the excess-vs-
proportional arithmetic: ~2.7 seats anti-ward raw. Applied at HALF
weight (UNDECIDED_BREAK_SEATS ~1.6, sd equal to mean), because the
decomposition anchors already embed the HISTORICAL late-break (which
favored Likud - the 2026 sign reversal is precisely why this is
cycle-specific information the anchors cannot carry). NB<->opposition
blocs only; Arab lists excluded (different instrument).

FRAGILITY DISCLOSED: the 55/16 lean rests on ~60 undecided respondents
(MoE ~+-13pp); direction is triple-sourced (JPPI certainty asymmetry,
Likud-panel defection destinations) but magnitude is soft - hence sd =
mean and the half discount. N12's own sizing was "~8 potential extra
seats for the change bloc"; we apply 1.6. Inputs are constants to be
REMEASURED after Sept 9 (JPPI shows the pool shrinking ~2pp/month; by
final polls the layer should approach zero as houses' own allocations
absorb the resolved pool). Harness-inactive by construction.

Effect: P(NB>=61) 20.1->14.6, P(anti) 25.4->35.0, PM Eisenkot
31.3->38.6 - landing inside the fundamentals desk's independently
computed "fair value 38-42%" band that both we (31) and Polymarket (50)
had missed from opposite sides.

## 12. Addendum (2026-09-01f): the campaign volatility calendar

Improvement #4. Measured from the own DB (RMS weekly movement of party
poll averages, 7 cycles): list-formation window D-36..77 moves 1.3-1.5
seats/week; final five weeks 0.6-0.75 (measurement includes the
holiday-freeze cycles); early campaign ~1.2. campaign_vol_weight()
(0.64 / 1.25 / 1.13, normalized to the all-window mean) now shapes the
projection's forward random-walk variance per remaining week instead
of uniform sqrt(weeks). Shape-neutral at today's D-56 horizon by
construction; after Sept 9 the remaining path is all calm-zone and
forward intervals tighten ~12% immediately, ~25% by D-35 - the model
now breathes with the campaign's actual calendar.
HERDING measured and DECLINED: final-window cross-pollster dispersion
0.88x mid-campaign (0.6-0.9x pure sampling noise per bias_herding),
but the decomposition's election-day shocks are fitted on final-poll
errors that already contain historical herding - an eve-of-election
inflation would double-count. Harness untouched (its projections run
from election eve, where the forward profile is inactive).

## 13. Addendum (2026-09-01g): parameter uncertainty in the formation tree

Improvement #5. Every BEHAVIOR parameter now carries an evidence-quality
Beta prior (BEHAVIOR_NEFF 12-35: public pledges and institutional
mechanisms concentrated, triangulated judgments diffuse); PM_ALLOC rows
get Dirichlet(alpha*60). The formation run is hierarchical: 200
parameter vectors x 8,000 Knessets. Headline PM (means barely move -
the priors are centered on the dossier values):
Eisenkot 38.7 [34.2-43.0] / repeat 26.1 [20.5-32.2] / Netanyahu 18.1
[15.0-22.5] / Bennett 11.1 [8.4-14.5] / Liberman 2.0 [0.8-3.9].
Diagnostic value of the outcome CIs: Netanyahu-coalition is
arithmetic-dominated (13.7 [13.0-14.3] - parameters barely matter),
while pledge-break [1.3-8.8], unity [2.3-11.6] and Centre+Ra'am
[5.1-13.5] are parameter-dominated - the honest map of which published
claims rest on assumptions vs seat math. pm_probabilities.csv now
feeds the site directly (hardcoded values removed).

## 14. Addendum (2026-09-02): owner formation taxonomy

Formation outcomes restructured to the owner's eight-plus-one list:
NB rightist / NB+centrist defector / change (without Ra'am, Segalovitz
seat counted) / change+Amcha / change+haredi (Shas or UTJ) / JL-backed
minority / unity sans Netanyahu / repeat split into Netanyahu-stays vs
Netanyahu-replaced (new bibi_out_by_repeat 0.25, NEFF 12). The
Ra'am-inside branch is REMOVED per owner judgment - Ra'am enters the
model through the with-Ra'am majority arithmetic, the Segalovitz seat,
and abstention assistance to the JL-backed minority. Scenario-specific
PM rows: JL minority is Eisenkot's own doctrine (0.85); change+Amcha
exists mostly in Bennett-led draws (flip rule makes Bennett modal
there). Result: outcome table above; PM Eisenkot 33.5 [29.8-37.2] /
none 31.1 (23.5 with Bibi + 7.5 replaced) / Netanyahu 19.9 / Bennett
9.4.

## 15. Small-party realization calibration (2026-09-01)

The polling page's footnote itemizations give each sub-threshold list's
*polled* support; the forecast converts it to *expected actual vote* using
the measured record of how such lists' final polls translated into ballots:

| list | final polls | actual | ratio |
|---|---|---|---|
| New Economic Party 2021 | ~1.2% | 0.79% | 0.66 |
| Jewish Home (Shaked) 2022 | 1.9% | 1.17% | 0.62 |
| Yachad (Yishai) 2015 | ~3.3% | 2.97% | 0.90 |
| Zehut Apr 2019 | ~3.0% | 2.74% | 0.91 |
| Otzma Yehudit Sept 2019 | ~1.7% | 1.88% | 1.11 |

Reading: lists without a committed base shed ~30% of polled support to
strategic desertion; sectarian/ideological-core lists hold or beat their
polls. Implemented as MICRO_REALIZE in src/bayes_model.py — x0.7 for
NEP / Israel First / The Fourth Quarter / El HaDegel, x1.0 for The Haredi
Public, Noam, and Zehut (whose voters land on the viable merged RZP-Zehut
list, so wasted-vote flight does not apply). The ratio dispersion
(~0.6-1.1) is folded into each micro-list's sd (+30% of the mean in
quadrature). Sources: CEC official results; Wikipedia results pages;
JPost/ToI final-poll coverage. Revisit at the Sept 9 refit alongside the
Zehut carve retirement.

## 16. Sept 2 poll wave: tripwires fired (2026-09-03)

Four polls with Sept 2 fieldwork (Lazar, Direct Polls, Maagar Mochot,
Midgam Project) are the first to price the resolved registration events
directly, so two pre-registered retirements fired:

1. **Segalovitz boost zeroed.** The polls carry the joint Ra'am slate
   (4-5 seats incl. Segalovitz); the +0.4-seat scenario boost on top
   would count his voters twice.
2. **Zehut carve + MERGE_RETENTION transfer retired.** The pollsters now
   publish a single "RZP - Zehut" column (5-6 seats); zehut was removed
   from MICRO_POLLED and the merge branch no-ops. Registry alias added
   so the merged column maps to rzp.

Also in the wave: Amcha at 4-5 seats in three of four polls (Lazar 0) —
left to the model; no parameter touched.
