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

## 17. Afkar Arab-sector poll (Sept 2026): Makom Lekulanu enters the board

Afkar Research (Arab-sector specialist), N=815, mandates computed by the
firm on a 60% sector-turnout assumption (their methodological note says
they prefer publishing answer shares over mandates). Owner-supplied.

Scenario 1 (all lists separate, % of sector): Joint List (Jabareen) 38%
(~9 mandates on their basis) | Ra'am+Segalovitz (Abbas) 19% (~5) |
Makom Lekulanu (Daoud/Green, the Standing Together list) 7% (~1.6) |
Democrats 5% | Likud 3% | Together 2%.

Merger scenarios: JL+Makom polls 53% — an +8pp SYNERGY over the sum of
parts (38+7) — while Ra'am+Makom polls 26%, purely additive (19+7).
If a JL-Makom slate files by Sept 9, this is the transfer evidence.

Integration: makom_lekulanu added to the registry (opposition_bloc) and
to MICRO_POLLED at (1.0%, 0.6%) — 7% of the sector is 0.7-1.3% of the
national vote depending on the turnout basis, its Jewish support is
unmeasured, and three national CEC filings (Midgam Project) register it
at 0.0%, so the sd is wide. MICRO_REALIZE 0.7 (organized movement, no
parliamentary base). CEC keyword added. The sector totals (64% of the
sector to Arab-led lists, 10% crossover to Zionist lists) sit inside
the KALPI_ARAB_CAP arithmetic; the JL 38% reading is consistent with
the Sept 2 national wave's JL 7-9 seats. No non-micro parameter moved.

## 18. Certainty layer (2026-09-03): soft support and the undecided pool

Replaces the flat undecided break (one ~1.6-seat anti-ward shift) and
Together's ad-hoc noise multiplier with a list-specific layer applied at
projection (bayes_model._certainty_layer).

Inputs and their status:
- CERTAINTY (locked share of each list's supporters). MEASURED: Together
  0.47 (JPPI/Midgam certainty series, Aug 2026), Amcha 0.38 (Midgam/N12
  Winter panel). DECLARED tiers for the rest: Shas 0.88 / UTJ 0.90 (never
  missed a final poll downward by more than half a seat), YB 0.80, Likud
  0.78, Arab lists 0.70-0.75 (turnout, not switching), Otzma 0.72,
  RZP-Zehut 0.68, Democrats 0.70, Yashar 0.65, ZH/B&W/Unity 0.40. To be
  replaced list by list as post-Sept-9 certainty waves publish.
- Defection rate of soft supporters d ~ Beta(mean 0.25, sd 0.12) per
  simulation, times a LogNormal(0, 0.35) per-list factor. JUDGMENT,
  anchored on INES panel switching (a quarter to a third of voters change
  intention across a campaign, concentrated among the uncertain).
- Destination split 0.75 within bloc / 0.10 cross / 0.15 abstain.
  DECLARED, anchored on the historical record that bloc error is smaller
  than the sum of its parts. The MEASURED asymmetry (change-bloc within-
  bloc wavering 3x the NB bloc's, Midgam Jul 27) enters through CERTAINTY,
  not through this split. Inflow lands by certainty-weighted support.
- Undecided pool 12% (comparable CEC filings cluster at 10-16%; Kantar's
  24-41% is a different question), GIQ 0.65 turnout haircut, N12 55/16
  lean now carried as Beta(46.5, 13.5) on the anti share of the leaned
  pool (n~60) x LogNormal(0, 0.5) magnitude; half weight retained.
- Amcha: the layer's expected loss counts toward the reference-class fade
  (AMCHA_FADE_TOTAL 1.5), so the mean shift is not doubled.

Effect vs the prior projection (same posterior): Together 12.1 -> 11.2,
Amcha 2.3 -> 1.8, ZH 1.5 -> 1.2; YB 7.7 -> 8.5, Democrats 9.4 -> 9.8,
UTJ/Shas +0.3. Baseline NB mean 53.1 -> 54.0 (the anti bloc's soft base
is larger, so symmetric cross/abstain rates move net mass); P(NB>=61)
20.4 -> 18.8, P(anti>=61) 31.2 -> 29.8. Harness-inactive by construction.

## 19. Configuration-conditional formation gates (2026-09-03)

The BEHAVIOR probabilities are now marginal means: each simulated
parliament's gate probability moves with its seat configuration through
a logistic, p = sigmoid(logit(p0) + beta*x), with x centred over the
draws so the marginal is preserved (government_formation.COND).

| gate | covariate | beta | anchor |
|---|---|---|---|
| shas_defects, utj_defects | NB gap to 61 (per 5 seats) | +0.35 | Shas 1992, Shas+UTJ 1999: haredim joined non-Likud governments only when the right had no path |
| same | that party alone closes the centre's gap | +0.50 | the decisive partner sets the price |
| centre_defects | NB gap to 61 (per 5 seats) | -0.35 | Gantz 2020 at gap 3; no defector at gaps 5-6 in 2019 |
| likud_sans_bibi | deadlock depth min(gap_NB, gap_centre) | +0.35 | unity resolved the deep deadlocks (1984/1988) |

Validation (validate_formation.py, eight real outcomes 2009-2022):
mean log score -0.93 vs -0.92 for the unconditional tree; P(PM side)
0.64 vs 0.63; P(realized) 0.52 vs 0.53. Indistinguishable — eight
outcomes cannot resolve betas of this size — so the mechanism is retained
on institutional grounds, with marginals unchanged by construction. Its
bite is in 2026's configuration distribution, where it moves probability
toward pivotal draws (a haredi party that alone closes the centre's gap
defects more often; a 2-seat NB gap attracts a defector more than an
8-seat one).

## 20. Sector polls as a second observation stream (2026-09-03)

src/sector_stream.py converts sector-specialist polls (data/sector_polls.csv,
currently Afkar Sept 2026, N=815) to national-share observations:
v = share_of_sector x W_sector / conc_list, with W_sector = (locality
eligible / locality concentration 0.78) x measured turnout 0.538 / total
voters = 0.121, and conc from the kalpi poststrat (JL 0.775, Ra'am 0.879;
lists below MIN_CONC 0.5 do not convert). Afkar's 38% / 19% become
5.9% / 2.6% nationally (7.1 / 3.1 seats) — at Afkar's own 60% turnout
assumption they would be 6.6% / 2.9%. The observations enter the fit as
polls by "Afkar (sector)" with a 1.6x noise multiplier for the
conversion's uncertainty (turnout and concentration are estimates).
Turnout is a dial (SECTOR_TURNOUT) for scenario runs. The participation-
attitude series in the repo measures coalition attitudes, not turnout
intention, so it does not drive the dial.

## 21. Time-varying house effects (2026-09-03)

Each firm's per-list lean now carries a linear drift over the 240-day
window, slope_c centred across firms per list so a common drift stays in
the latent trend: delta(t) = delta + slope_c x (t - tbar)/T, prior
HalfNormal(0.01) on the slope scale. Posterior sigma_slope 0.0085 (90%
[0.0069, 0.0103]) — the data want drift at roughly the prior scale.
Largest learned drifts (end-to-end seats, |z|>2): Tatika/Likud -2.95,
Filber/UTJ -1.88, Filber/YB -1.80, Filber/JL -1.70, Maagar/Democrats
+1.65, Lazar/YB +1.31, Tatika/Democrats -1.18, Kantar/UTJ +1.14.
Fit: 0 divergences, r-hat 1.01, ESS 355, predictive coverage 99.2%,
14-day holdout 0.78 (0.74 without drift — within noise; the term is
retained for identification of moving leans, not for holdout gain).
The precision weights already grade each firm's FINAL poll against the
result (backtest.py scorecard -> quality_map), so "final-poll weighting"
needed no change.

## 22. Blue and White and Unity are kingmakers, not change-bloc lists (2026-09-03)

Owner ruling. Gantz sat in Netanyahu's 2020 government; Unity is Erdan
and Edelstein, Likud alumni. Both registry rows carried a "VERIFY bloc
assignment" flag from the first pass. Treatment: bloc "unaligned" —
their seats count toward NEITHER 61 in the headline bloc arithmetic
(they are kingmakers when they pass), and the formation tree sends each
list's seats right / centre / neither per draw by declared side priors:
Blue and White 0.40 / 0.45 / 0.15 (the 2020 precedent against the
2022-24 opposition record), Unity 0.60 / 0.25 / 0.15 (Likud lineage),
each with Beta uncertainty (n_eff 10-12). The registration mixture's
fold events are unchanged: a fold is a merger, and it moves the VOTERS
into the absorbing list, which is measured behaviour, not a bloc label.
Site: a fourth bloc colour and group, "Unaligned"; the change-coalition
preset no longer includes them.

## 23. Pollster weighting audit (2026-09-03, owner: "feels off")

Diagnosis, three defects:

1. **Exit polls graded as final polls.** The backtest's final-poll window
   admitted fieldwork ON election day, so the broadcasters' exit polls
   (Kantar/Kan 11, Midgam/Channel 12, Fuchs/Channel 13) were scored as
   those firms' "final polls": Kantar's four graded cycles all had a
   0-day gap and a 0.65 seats/list error, which put it at the maximum
   trust clip. Midgam's four recent "finals" (0.33-1.08) were exit polls
   while its true pre-election finals (2009-2019a) ran 1.5-2.6.
   Fix: final poll = last fieldwork strictly before election day, in the
   backtest scorecard and in the site ratings.
2. **No small-sample shrinkage.** A firm graded on 1-4 cycles could earn
   the full clip. Fix: q shrunk toward the industry median by
   n_cycles/(n_cycles+3).
3. **Internal consistency read as precision.** Within-firm scatter of the
   NB-bloc total around each firm's own 21-day trend: Filber 0.43 seats,
   Direct Polls 0.50, Lazar 0.54, Kantar 0.66, Midgam 0.67 - against a
   binomial sampling error of 2-3 seats for n~550. Panel stickiness makes
   a series smooth; the likelihood estimated lam from that smoothness and
   pulled Filber (no graded record, +11.5 lean, SMS methodology) to more
   weight than Maagar Mochot's eight cycles, and every weekly panel firm
   far below its historical prior (Lazar 0.98 -> 0.68). Fix: a hard
   sampling floor on observation noise, sqrt(p(1-p)/n x DEFF), with n
   from the poll or the firm's CEC-filing median and a declared design
   effect by fieldwork mode (phone/own infrastructure 1.0, mixed 1.1,
   opt-in online panels 1.3, SMS/undisclosed 1.4; AAPOR/Pew opt-in
   panel literature, and the two SMS firms own the worst graded
   records). The lam prior tightened from sigma 0.25 to 0.20 so the
   graded record holds more weight against within-cycle consistency.

Checked and not a problem: Lazar and Panels Politics (same operation)
do not double-publish the same weekly poll (0 of 20 Panels Politics
polls fall within 2 days of a Lazar poll); correlation groups already
share the bias term.

### 23a. Harness ablation of the sampling floor

| cycle | MAE committed | MAE floor off | MAE floor on | cov off | cov on | Brier off | Brier on |
|---|---|---|---|---|---|---|---|
| 2009 | 1.79 | 1.78 | 1.76 | 1.00 | 1.00 | 0.021 | 0.023 |
| 2013 | 1.98 | 1.99 | 2.19 | 0.92 | 0.92 | 0.052 | 0.054 |
| 2015 | 2.10 | 2.12 | 2.14 | 0.91 | 1.00 | 0.041 | 0.040 |
| 2019a | 2.25 | 2.26 | 2.22 | 1.00 | 1.00 | 0.169 | 0.173 |
| 2019s | 1.12 | 1.11 | 1.10 | 1.00 | 1.00 | 0.031 | 0.026 |
| 2020 | 1.04 | 1.02 | 1.25 | 1.00 | 1.00 | 0.031 | 0.057 |
| 2021 | 1.80 | 1.79 | 1.79 | 0.95 | 0.95 | 0.082 | 0.080 |
| 2022 | 1.23 | 1.24 | 1.25 | 1.00 | 1.00 | 0.066 | 0.068 |
| pooled | 1.66 | 1.66 | 1.71 | 97.2% | 98.4% | 0.062 | 0.065 |

"Floor off" carries every other change of the day (house-effect drift,
exit-poll exclusion, cycle shrinkage, lam sigma 0.20) and reproduces the
committed record exactly - those ship. The floor alone costs 0.05 seats,
widens already-over-wide intervals, and worsens threshold calibration
(2013, 2020). Rejected by the pre-registered arbiter; the diagnosis of
panel stickiness stands and the machinery is kept behind BAYES_FLOOR=1
for research. Bloc Brier 0.029 (off) vs 0.034 (on).

## 24. The Arab lists: why the model sat below the polls (2026-09-03)

Owner observation: since the Joint List re-formed (Aug 24) every poll
puts the Arab lists at 11-14 seats (mean 12.0: JL 7.2, Ra'am 4.8); the
model showed 9.5 (JL 6.5, Ra'am 3.0). Three causes found:

1. **CEC raw shares were not renormalised.** Filings whose parsed parties
   sum to 90-105% were taken as raw percentages of respondents; a filing
   summing to 92% therefore understated every list by 8% relative. For
   Ra'am (raw 3.8-4.0%) that is the difference between 3.9% and 4.2% of
   the decided vote - i.e. between the 3.25% cliff and clearing it. Fixed:
   shares are now divided by the filing's parsed party sum. Refit.
2. **The Arab family error is regime-dependent.** Own backtest, error =
   polled - actual: unified Joint List years 2015 -0.4, 2019s -1.9, 2020
   -1.1, 2022 -2.0 (mean -1.35, polls under-count); split years 2019a
   +1.2, 2021 +1.5 (over-count). Turnout is the mechanism (Arab turnout
   56.5 -> 63.5% in 2015; 49 -> 59 -> 65% across 2019a/2019s/2020; 44.6% in
   split 2021). The pooled -0.32 mixed both regimes. With Balad's stay
   resolved, the unified-regime mean now applies (ARAB_UNIFIED_ERROR_MEAN
   -1.35, pooled sd 1.45 kept).
3. **Threshold-death tails.** Ra'am's mean of 3.0 was a 4-seat median
   with a 49% death rate; the two fixes above move the latent and the
   family mean and are expected to reduce it. Ra'am's per-list residual
   width (pooled, "n=2, turnout risk real") is left as audited.

The owner's reading of pollsters "anticipating a turnout boost" is,
per the record, the reverse: pollsters have UNDER-stated the unified
list every time, so the model should sit above them, not below.

## 25. Stage-by-stage deep dive (2026-09-03)

Method as in s.23: a measured probe per stage, fixes only for
demonstrated defects, harness validation for anything touching the
likelihood or the projection.

**Data (scraper, registry).** No unmapped labels; every result row sums
to 120; no byte-identical duplicates across ids. Found: the archive's
same-day "a/b" variants of one survey (with/without a list, joint vs
split Arab lists) both entered the fit as independent polls - 14 extra
polls in the window, one pair identical (Kantar Aug 9). Fix: one poll
per firm and fieldwork date, keeping the most complete configuration
(most list rows); 4 polls dropped after the existing composite-Ra'am
exclusion. Refit; harness run for the historical cycles.

**State-space fit.** Latent end-state matches the last-14-day poll
averages after wasted-vote renormalisation; posterior weekly innovation
sd 0.45 seats (Likud) to 1.08 (Yashar), in line with the measured
formation-window movement; the calendar trims effective forward weeks at
D-55 from 7.9 to 6.7. No defect.

**Shock stack (ablation, current posterior).** Residual per-list shock
is the dominant width source (Likud sd 4.85 -> 3.89 without). Bloc swing
carries the NB tail (P(NB61) 0.163 -> 0.105 without). Loyal-sd trims
Yashar 6.0 -> 5.0. Gevalt, kalpi rho, kalpi cap, new-list multiplier:
negligible headline effect. The certainty layer is the largest single
lever, and it splits cleanly: the soft-support churn alone moves the
headline little (P(NB61) 0.156 vs 0.163 baseline), while the UNDECIDED
LEAN alone is worth ~8 points of P(NB61) and ~9 of P(anti61) (churn-only
run: 0.246 / 0.157). That lean rests on the N12 55/16 measurement of ~60
respondents. Two consequences: (a) a mean-inflation bug fixed - the
LogNormal magnitude term had mean exp(s^2/2) = 1.13, so the lean was 13%
larger than declared; now mean-one; (b) it is flagged here as the
model's most consequential judgment input, to be REMEASURED at the
first post-Sept-9 certainty/undecided wave and shrunk toward zero by the
final polls as pre-registered (s.11).

**Threshold + Bader-Ofer.** The implementation reproduces the official
2022 allocation exactly from CEC vote counts, including the three
surplus-vote pairs (Likud-RZP, Yesh Atid-National Unity, Shas-UTJ);
without pairs Likud would be 31 and Labor 5, which is the measured worth
of a pair. Every simulated parliament sums to 120 in every file.

**Registration mixture.** Fold transfers retain 60-80% of a folding
list's votes (ZH -> Yashar 0.75; B&W -> Yashar 0.45 + Together 0.15;
Unity -> four absorbers 0.80); shares renormalise to 1; draws sum to
120. No defect.

**Validation harness.** Its projection mirrored the production stack
only partially: bloc swing, family shocks, anchors, residual and
loyal-sd, but NOT gevalt coupling or the kalpi haredi-arab correlation,
so those two production layers had never been graded. Both are now
mirrored into validate_bayes.project_cycle (the era's right-flank NB
lists as satellites). 2026-only layers (certainty, calendar, event risk,
micro-lists, capacity) remain harness-inactive by construction.

## 26. The central seat count (2026-09-03)

Found: the published centres were meant to come from the simple
final-window pipeline (harness point MAE 1.42 vs 1.66), but a name
mismatch (display names vs party ids) meant the match never fired; the
fallback rounded the BASELINE Bayesian means, zeroed non-passing lists,
applied a 4-seat floor, and handed the ~5 missing seats to the highest
pass-probability lists - UTJ showed 9 with a mean of 7.9 and a median of
8. The simple snapshot was also stale (not in the refresh chain), and
centres came from the baseline while intervals came from the mixture.

Now: one distribution. project() exposes the final projected share
distribution's mean vector; registration_scenarios writes it
(mixture_shares.csv); official_forecast passes it once through the real
seat law - 3.25% threshold, surplus pairs, Bader-Ofer - so the table sums
to 120 by construction with no rounding, floors or remainders. UTJ 8,
Yashar 26, Likud 25, Together 12, Democrats 10, Shas 8, YB 8, JL 7,
Otzma 7, RZP-Zehut 5, Ra'am 4. The simple pipeline remains the
point-accuracy benchmark in the validation table, not a component of
the published forecast; the annex says so in both languages.

## 27. Round-two improvements (2026-09-03): what the data allowed

**#1 Undecided pool, pooled.** The CEC filings carry no leaning or
forced-choice tables (scanned all 37: only "still undecided" rows), so
the lean cannot yet be pooled from filings. Implemented instead: (a) pool
SIZE measured every build as the 45-day median of the firms reporting a
genuine undecided share (Lazar, Midgam Project & StatNet, Maagar Mochot;
Kantar includes non-voters, Midgam is post-allocation) - 12.3% today;
(b) a pooling machinery over data/undecided_leans.csv: each measurement
enters by its leaned n, against a proportional-split prior of n = 43 -
the pre-registered half weight made explicit (posterior today Beta(55.4,
30.2), mean excess 0.50, identical to the old point estimate but now a
posterior that every new wave updates by its own n).

**#3 Arab turnout mechanism.** Replaces the additive unified-regime mean
(-1.35 seats). Panels weight the Arab sector to 0.538 (2022); realised
turnout under a unified list 0.635 / 0.592 / 0.648 (2015, 2019s, 2020),
split years 0.492 / 0.446. Each draw: T ~ 0.625 + 0.05 x (the arab
family's correlated t draw), clipped at the kalpi ceiling 0.72; the Arab
lists' joint share scales by T/0.538 and the mass comes from every other
list. JL and Ra'am now move together. Ra'am's idiosyncratic width joins
LOYAL_SD at 1.8 (measured 2021-22 final error 0.6-1.0 x 2 buffer).
Effect vs the additive version: Ra'am pass 0.589 -> 0.620, JL 7.3 -> 7.5.

**#4 Measured transfers.** Kolot Nodedim 2021->2022 with abstention
(7,035 stations): of voters who left their list, change bloc 72.5%
within / 10.3% cross / 17.2% abstain; Netanyahu bloc 85.5 / 6.6 / 7.9 -
the declared 0.75 / 0.10 / 0.15 was within a point; now CHURN_SPLIT by
bloc, measured. Same-list loyalty change 59% vs right 82% corroborates
the CERTAINTY tiers. Fold transfers restructured on absorbed lists'
measured fate (Yamina 45/24/14/11/6 to RZP/JH/Likud/NU/Shas; New Hope
58/42 NU/Likud; B&W 70/30 NU/Yesh Atid): ZH -> Yashar .55 / Together
.15 / Likud .20; B&W -> Yashar .60 / Together .25; Unity -> Likud .45 /
Yashar .25 / YB .10 / Together .10 (analog mapping declared, structure
measured).

**#2 Interval width.** RESID_SCALE on the per-list residual shock;
validate_bayes re-projects each fitted cycle under a grid 0.6-1.1 and
scores coverage, MAE, Brier and the Gneiting-Raftery interval score;
choice by leave-one-cycle-out interval score. Result recorded in s.27a
when the run completes.

### 27a. Interval-width calibration result

| width | coverage | MAE | Brier | interval score |
|---|---|---|---|---|
| 0.6 | 0.950 | 1.897 | 0.067 | 9.764 |
| 0.7 | 0.963 | 1.873 | 0.067 | 9.815 |
| 0.8 | 0.968 | 1.736 | 0.063 | 8.946 |
| **0.9** | 0.983 | **1.655** | 0.060 | **8.364** |
| 1.0 | 0.983 | 1.659 | 0.060 | 8.617 |
| 1.1 | 0.983 | 1.661 | 0.061 | 9.070 |

Leave-one-cycle-out choice by interval score: 0.9 in all eight folds.
RESID_SCALE = 0.9 ships. Two honest notes: (1) narrowing the residual
below 0.8 WORSENS point accuracy - the per-list shock is load-bearing
for the means through the threshold nonlinearity (fewer death draws
shifts the means of straddling lists); (2) coverage barely moves across
the grid (0.95-0.98), so the over-width the harness has always shown is
NOT in the residual shock but in the other layers (bloc swing, sector
shocks, loyal-sd caps). The next calibration target is a joint scale on
those, gated the same way.

## 28. Accuracy round three: layer ablation and the horizon harness (2026-09-03)

**Layer ablation** (validate_bayes, eight cycles, pooled; MAE of the mean
/ of the median; coverage; Brier): full 1.665 / 1.574 / 0.983 / 0.060;
no residual 1.859 / 1.845 / 0.823 / 0.068; no bloc swing 1.664 / 1.591;
no family shocks 1.722 / 1.616; NO ANCHORS 1.589 / 1.541 / 0.972 /
0.058; no gevalt 1.662 / 1.586 / 0.972; no loyal-sd 1.664 / 1.575;
latent only 1.734 / 1.590 / 0.561 / 0.071.
Reading: the residual and the family shocks earn their place; swing,
gevalt and loyal-sd are neutral on points as they should be; the ANCHORS
HURT - 0.08 seats per list, and worse Brier and coverage. Structurally
expected: the Likud beat is +8.4 and +6.7 in two cycles and ~0 in six, so
a mean applied to every cycle is wrong six times in eight. The median is
a better point estimate than the mean by ~0.09 in every configuration.
Finer run (Likud-only, leader-only, half strength) in progress; decision
in s.28a.

**Horizon harness** (validate_horizon, each cycle refit as of D-56 and
D-21, projected with plain vs calendar-effective forward weeks):
D-21 calendar MAE 1.90 / coverage 96.5% / width 7.7 / interval score
9.78 (plain 10.11); D-56 calendar 2.79 / 90.1% / 9.5 / 17.94 (plain
92.0% / 9.7 / 17.63). Per cycle at D-56: 2013 and 2021 under-cover
(0.67-0.78, 0.81-0.86), the rest at or above 0.90.
Reading: (1) the published intervals at the current horizon are
calibrated - coverage 90% at D-56; the 98% over-coverage is an
election-eve artefact where the forward variance has gone to zero and
the shock stack alone over-covers. So the stack is somewhat too wide AND
the forward variance somewhat too small, netting out at D-56. The right
fix is a joint (stack scale, forward-variance scale) calibrated on both
horizons; the harness now caches posteriors so that grid costs no
refits. (2) The volatility calendar helps at D-21 (interval score 9.78
vs 10.11) and is neutral at D-56; retained. (3) Point error roughly
doubles from election eve to D-56 (1.66 -> 2.79), which is the honest
scale of what eight weeks of campaign can do.

### 28a. Anchor decision

Finer ablation (pooled MAE mean / median; Brier): full 1.665 / 1.574 /
0.060; no Likud anchor 1.656 / 1.597 / 0.059; no leader anchor 1.649 /
1.554 / 0.059; half strength 1.614 / 1.553 / 0.059; NO ANCHORS 1.589 /
1.541 / 0.058. Removing both beats every partial option. Per cycle, no
anchors loses in 2019a (2.24 -> 2.47, the gevalt election the anchor was
built for) and slightly in 2020, and wins in 2013, 2019s, 2021 and 2022.
Decision: ANCHORS_ON = False in production; values retained for the
record. Successor to test: a CONDITIONAL gevalt - the Likud beat applied
only when Likud is rising over the final fortnight of polling, which is
what 2015 and April 2019 had in common.

Also shipped from the ablation: the central seat count now uses the
mixture's MEDIAN share vector (renormalised) rather than the mean - the
harness grades the median as the better point estimate by ~0.09 seats
per list in every configuration (threshold deaths skew the means of
straddling lists downward).

## 29. Poll update of 4 September and the religious-Zionist sector poll (2026-09-04)

**What came in.** Three new polls from the public archive (Filber/Ch14,
Kantar/Israel Hayom, Tatika/Zman Yisrael, all fieldwork 3 Sept; 734 polls
in the 2026 cycle), and thirteen new CEC filings (index refreshed from 37 to
50 via the gov.il collector API). A Lazar/Maariv poll published the morning
of 4 Sept (fieldwork 2-3 Sept, n=600, ±4%) is reported only in bloc terms
(Netanyahu bloc 51, Zionist opposition 57, Arab lists 12; RZ-Zehut 5, Amcha
4, Yashar down 2; sub-threshold: Zionist Home 2.1, Economic Party 1.7,
Unity 1.1, Makom Lekulanu 0.7, Blue & White 0.6, Haredi Public 0.4) and
carries no complete seat table yet; it enters at the next scrape once the
archive or its CEC filing has the per-list figures. Nothing is entered by
inference from bloc totals.

**Parser defect found and fixed (scrape_cec).** Two filing formats glue a
count onto the percentage: Tatika files "<list><respondents><pct>%<seats>"
("224.40%6" = 22 respondents, 4.40%, 6 seats) and the Midgam Project
consortium files "<list><seats><pct>%..." with four raw, UNWEIGHTED
sub-sample columns (Jewish adults / young / haredi / Arab) that are not a
national distribution at all. The old regex took the last two digits before
the decimal point, so every Tatika filing summed to 160-270% (rejected by
the 90-105% filter: harmless but wasted) and two Midgam Project filings
(4094, 4106) PASSED the filter with sub-sample garbage - Together at 37-40%,
the Democrats at 17-18%, the Joint List at 0% - and sat in the likelihood as
Midgam Project observations. Fix: the digit run is split by corroboration
(respondents / n, or seats / 1.2), Midgam Project filings and any
sector-only sample (Dialog's reservists poll for Yedioth, ref 4096) are
flagged `national_table = False` and contribute methodology fields only.
The merge filter now also admits a filing whose parties plus its separately
reported undecided line sum to 95-105% (Maagar Mochot files 86-89% beside a
9-13% undecided row; renormalisation puts it on the same footing). Eligible
filings: 35 of 50, all five Tatika filings now readable (sums 98-104).

**Ynet / Dialog poll of religious-Zionist voters** (Dialog, Emet group, for
Ynet and Yedioth; two waves - 31 Aug-2 Sept n=508 before the Smotrich-
Feiglin merger, 3-4 Sept n=484 after it; ±4.4%; self-identified sample: 50%
"national-religious stream", 33% "religious Zionism", 17% hardal). Second
wave: RZ-Zehut 30, Likud 17, undecided 13, Otzma 12, Amcha 6, Yashar 4,
Shas 4, Together 3, Zionist Home 3, other 2, Unity 2, YB 1, Noam 1, none 1,
B&W 1, UTJ 0, Democrats 0. First wave: RZP 21 + Zehut 5 = 26; the merger
added 4 points, taken from Winter (9 -> 6) and Ben-Gvir (14 -> 12).

*Conversion.* The kalpi layer's "religious-Zionist localities" sector is the
settlement/RZ-town cluster (2.0% of the national vote; RZP draws 11.5% of
its vote there), not the population, so the sector stream cannot convert
this poll and it is NOT entered as an observation. Population arithmetic
instead: IDI's 2022 post-election panel (n=12,322 Jews; 10,694 voters) puts
the national-religious at 11% of Jewish voters, i.e. about 10% of all
voters; among deciders (86% of the sample) the second wave is RZ-Zehut
34.9, Likud 19.8, Otzma 14.0, Amcha 7.0, Yashar 4.7, Shas 4.7, Together 3.5,
Zionist Home 3.5, Unity 2.3, YB/Noam/B&W 1.2. National contribution from
this population = share x 0.10:

| list | from dati voters | current polling level | dati share of its vote |
|---|---|---|---|
| RZ-Zehut | 3.5% | ~4.8% (5-6 seats) | ~0.7 |
| Likud | 2.0% | ~17% | ~0.12 (2022: 22.5% x 0.10 / 23.4% = 0.10) |
| Otzma | 1.4% | ~5.5% | ~0.25 |
| Amcha | 0.7% | ~3.5% | ~0.2 |
| Together | 0.35% | ~10% | ~0.035 |
| Zionist Home | 0.35% | ~2% | ~0.17 |
| Unity | 0.23% | ~0.8% | ~0.3 |
| Noam | 0.12% | MICRO 0.4% | ~0.3 |

*What it says.* (1) The poll corroborates RZ-Zehut at 5-6 seats and shows
its vote is ~70% national-religious; that core alone (3.5% national) sits
above the 3.25% threshold, which argues its pass probability is bounded
below by dati loyalty rather than by the national panel noise - a point in
favour of the list's current ~0.7 pass rate and against treating it as a
coin flip. (2) The merger's +4 points of the sector (+0.4% national, about
half a seat) came from Winter and Ben-Gvir, i.e. zero-sum inside the right,
consistent with the GEVALT_SD coupling and with no bloc-level effect; the
STRUCTURAL_BREAK backcast (+1.44% for the Zehut carry) is larger than the
dati contribution of Zehut alone (5% x 0.10 = 0.5%), which is as expected
- Feiglin's remaining vote is secular-libertarian. (3) Bennett at 3% of the
sector (vs the ~20%+ Yamina held in 2021) confirms that Together's vote is
not religious-Zionist at all now; the certainty layer's 0.47 for Together
is a centre-electorate property. (4) Amcha's 6% of the sector is a fifth of
its vote - Winter's base is the traditional and secular right, so the
AMCHA_FADE residualisation toward Likud/Otzma stands. (5) 23% "politically
homeless", 15% naming the haredi draft as the top issue: the sector's
undecided share (13%) is no larger than the national pool (12.3%).

Nothing in the projection changes on this poll; it is recorded as a
composition check and the table above is the reference for a future
population-sector conversion if the sector stream is extended beyond
locality-defined sectors (it would need measured concentrations per list,
which only the 2022 IDI panel provides, and only for the joint RZ-Otzma
list: 45% of dati voters x 0.10 / 10.84% = 0.42 of that list's vote).

Sources: Ynet, "במי תומכים הדתיים הלאומיים" (4 Sept 2026),
https://www.ynet.co.il/news/elections2026/article/sydameiozg ; IDI Viterbi
Center, "Voting Patterns of Jews in the 2022 Elections by Religious
Identity", https://en.idi.org.il/articles/64807 ; Maariv, "סקר מנדטים של
מעריב: כך סמוטריץ' ופייגלין השפיעו על מפת הגושים" (4 Sept 2026, 06:01),
https://www.maariv.co.il/news/politics/article-1362890 ; CEC filings index,
https://www.gov.il/he/Departments/DynamicCollectors/knesset_election_polls_26

## 30. Unity withdraws; Maariv poll lands (2026-09-05)

**Event.** On 4 September Gilad Erdan announced that Unity (Erdan,
Edelstein, Bloch, Samadja) will not run: support "does not guarantee
crossing the threshold with high probability", the merger talks with Blue
and White collapsed the same day, and "a large majority of the public asks
first of all for a clear decision on the identity of the prime minister".
No endorsement was given. Sources: Ynet
https://www.ynet.co.il/news/article/b184d800ofg ; Israel Hayom
https://www.israelhayom.co.il/news/politics/article/21355002 ; N12
https://www.mako.co.il/news-politics/2026_q3/Article-1640e0df3dc60a1027.htm

**Model.** `RESOLVED` now carries `unity_folds: True` and
`centre_union_files: False` (the Erdan-Gantz union can no longer file). The
fold vector already in place applies in every draw - Likud 0.45 / Yashar
0.25 / Yisrael Beytenu 0.10 / rest scattered - built from the measured
fates of absorbed Likud-alumni lists (New Hope -> National Unity 58 /
Likud 42). Unity's polled 0.3-1.1% therefore moves about 0.4% to Likud and
0.2% to Yashar; at the seat level that is noise, and the site drops the
list from the seat rows, chips and small-parties section automatically
(no draw carries a Unity seat). The formation tree's UNALIGNED side priors
for Unity are now unreachable and stay on record. Blue and White's fold
probability is unchanged at 0.65 (the annex previously showed 0.58 = 0.65
x (1 - 0.12) net of the union branch; with the union off it reads 0.65).

**Polls.** The Lazar/Maariv poll of 2-3 September (n=600) is now in the
archive with its full table (Yashar 23, Likud 20, Together 15, Democrats
10, YB 9, Otzma 8, Shas 7, UTJ 7, JL 7, Ra'am 5, RZ-Zehut 5, Amcha 4):
736 polls in the cycle. No new CEC filings (index still 50). The
structural-break backcast for the Zehut carry now skips any observation
whose published column was already the merged "RZP - Zehut" line (one
pre-2 Sept observation was being double-shifted).

**Archive change caught the same day.** Between two scrapes on 5 Sept the
polling archive added a standalone "Zehut" column and re-keyed the
post-merger polls as a cell spanning "RZP" and "Zehut". The scraper's
colspan logic turned that into a composite id `rzp+zehut`, which (a) the
registry did not know, so the list fell into the default bloc, and (b) the
mixture's merge_zehut rule read as two columns and zeroed - RZ-Zehut
vanished from the seat table and P(NB>=61) fell to 6.8% in one build.
Fixes: `COMPOSITE_ALIASES` in scrape_polls maps `rzp+zehut` to `rzp`
(the archive's spanning cell is the absorbing list, not a new one), and
`ABSORBED_IDS` in prepare_data drops the standalone pre-merger Zehut rows
(their support already rides inside RZP through the structural break;
a Zehut column of its own would count those voters twice). The list
count is back to 15 and the fit was rerun on the corrected data. Lesson:
a build whose bloc odds move by eight points on one poll is a data
defect until proven otherwise - check the component list first.

## 31. Filing day (2026-09-08/09): the mixture collapses to one configuration

**What filed.** 38 lists were submitted to the CEC on 7-8 September (chair Justice
Sohlberg; names and letters are examined and approved by 27 September). The
modeled lists and what changed:

| list | filed as | what changed on filing |
|---|---|---|
| Yashar | ישר! (requested דרך) | Tropper joined at #6 after Zionist Home–Reservists dissolved (6 Sept); Stern, Folkman also on the list |
| Together | ביחד (ב / רק) | Bennett–Eisenkot union finally off (7 Sept); asked for ב, contested by Otzma (Ben-Gvir's municipal precedence) |
| Likud | מחל | reserved slots filled (Medan, Gueili, Peter); Avivi withdrew to be an outside minister |
| RZP–Zehut | הציונות הדתית–זהות (ט) | Feiglin #2; Amcha merger refused; Yossi Bachar added |
| Otzma | עוצמה יהודית (ב requested) | Gotliv #2 (from Likud) |
| Amcha Yisrael | עמך ישראל (ך) | Winter refused every merger; Haddad #2 |
| Reservists – Economic Party | המילואימניקים והכלכלית (די) | Hendel + Zelekha (co-#1) + Wilf #3; continues the zionist_home series (Tropper's part to Yashar, NEP's in) |
| Blue and White | כחול לבן (כן) | Gantz FILED (Tamano-Shata #2); Biton left; Hendel asked him to quit |
| Ra'am | רע"ם (עם) | Segalovitz #2 as agreed |
| Joint List | הרשימה המשותפת (ודם) | Jabareen, Tibi, Abu Shahada; Balad inside |
| Noam | נעם לישראל (ני) | filed alone |
| Haredi Public | הציבור החרדי (זך) | filed (Leitner); refused Winter's offer |
| Israel First | ישראל תחילה (יר) | filed (Haskel; Aleh Yarok joined 3 Sept) |
| Unity | — | withdrew 4 Sept |
| Makom Lekulanu, Fourth Quarter, El HaDegel | — | did not file |

**Model consequences.** `RESOLVED` now closes the last two events
(`zionist_home_folds` False, `blue_white_folds` False): the mixture is a single
configuration. The registry's zionist_home row is renamed Reservists – Economic
Party with the archive's new column label ("Reserv. - NEP") as an alias; the
series is kept continuous (Tropper out, Zelekha in roughly offset: 2-3% before,
4 seats in Kantar 6 Sept and Lazar 8 Sept, below threshold elsewhere). `nep`
joins `ABSORBED_IDS` (its pre-merger lines in filings are dropped from 6 Sept
by `ABSORBED_FROM`, as Zehut's are from 2 Sept, so a scenario table left in
a report cannot double count). MICRO_POLLED keeps only lists that filed
(noam, haredi_public, israel_first). Formation: the Reservists–Economic list
stays in the centre set — Hendel is on record refusing a Netanyahu government
and wanting a Zionist coalition without haredi or Arab parties (Ynet, Kikar),
which the existing haredi-inclusion defection gate already prices. Ballot
letters on the site are the REQUESTED ones (Together shown with its
alternative רק while ב is contested), flagged until the 27 Sept ruling.

**CEC parser, third pass.** The new filings exposed two more formats: Kantar
wraps a long list name onto the next line (the percentage sits on the line
after the keyword), and several reports keep merger SCENARIO tables ("if RZP,
Amcha and Zehut united ... 8.9%") whose lines contain party names. The old
keyword "זהות" therefore attributed a scenario line to a phantom Zehut column
(Kantar 8.9%, Filber 27% — the latter pushed a good filing over the sum
filter). Fixes: wrapped names read the next line; scenario tokens skip the
line; Zehut is no longer a keyword (it has been inside RZP since 2 Sept);
keywords added for the Reservists–Economic list, the Haredi Public and Israel
First. 40 of 57 filings are now merge-eligible (Afkar's Arab-sector filing,
ref 4126, is the sector-stream poll already in the model - it is not a
national table and is excluded by design).

**Polls.** Six national polls since the last update (Lazar/Maariv 4 and 8
Sept, Kantar/Kan 6 Sept, Filber/Ch14 7 Sept, Midgam/N12 7 Sept, Lazar/Walla
9 Sept; 741 in the cycle) and seven CEC filings (57 indexed).

**Refit (9 Sept).** 183 polls / 2,332 observations / 40 filings merged; 0
divergences, r-hat 1.01, ESS 553, holdout 0.70 seats. Headline: P(NB>=61)
15.0 / change bloc 22.8 / with Ra'am 41.4 / deadlock 43.7; PM repeat election
32.5 / Eisenkot 31.7 / Netanyahu 20.4 / Bennett 8.2. Central: Yashar 25,
Likud 23, Together 11, Democrats 10, Shas 9, UTJ 8, YB 8, Joint List 8, Otzma
7, RZP-Zehut 6 (pass .78), Ra'am 5 (.70); Amcha 0 (.28), Reservists-Economic
0 (.28), Blue and White 0 (.03). Filing day moved almost nothing: the events
that resolved were already priced near their outcomes (B&W and the Reservists
each filed at roughly their fold-vs-file odds), and the news of the week is
the Reservists-Economic list joining Amcha at the threshold line.

## 32. Owner ruling: the Reservists–Economic list is unaligned (2026-09-09)

The owner's ruling: count the Reservists–Economic list (Hendel, Zelekha, Wilf)
the same way as Blue and White - a kingmaker, not a change-bloc member. The
registry bloc is now `unaligned`; the formation tree routes its seats by side
priors like Gantz's: right 0.30 / centre 0.45 / sits out 0.25 (Beta n=10
each). The priors are lower on the right than Blue and White's 0.40 because
Hendel is on record refusing a Netanyahu government (and was a minister in
the Bennett–Lapid government), and the sit-out residual is larger because his
stated conditions - no haredi and no Arab partners - rule out most feasible
coalitions on either side. The site's change preset excludes the list; it
sits in the Unaligned group with Blue and White.

Effect (same posterior, no refit): change-bloc majority without Arab seats
22.8 -> 16.0, with Ra'am 41.4 -> 33.1, deadlock 43.7 -> 51.4, NB 15.0 ->
15.5; PM repeat election 32.5 -> 34.8, Eisenkot 31.7 -> 28.2, Netanyahu 20.4
-> 22.4. The whole move is the ~28% of draws in which the list passes: those
seats were counted toward the change bloc's 61 and now count toward
neither. Formation outcomes: change without Ra'am 0.187, with a haredi party
0.053, with Ra'am 0.070; Netanyahu rightist 0.162, plus defector 0.062;
unity 0.095; repeat 0.348.

## 33. Owner ruling: Segalovitz's seat counts only with Ra'am (2026-09-09)

Reverses the 2 September rule (s.14/22) that added Segalovitz's Ra'am seat
to the change bloc's "without Arab seats" 61 whenever Ra'am won at least two
seats. From now on the first hero line is the opposition lists alone; the
second ("with Ra'am") adds Ra'am as a whole; the formation tree's change
coalition without Ra'am no longer carries the seat, and the with-Ra'am branch
adds all of Ra'am. Same posterior, no refit. Effect: change-bloc majority
without Arab seats 16.0 -> 13.7 (with Ra'am unchanged at 33.1; NB 15.5;
deadlock 51.4); PM repeat election 34.8 -> 36.2, Eisenkot 28.2 -> 26.9,
Netanyahu 22.4 -> 22.6. Formation: change without Ra'am 0.187 -> 0.162, with
Ra'am 0.070 -> 0.080.
