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
   [Corrected 14 Oct, see s.43: 2022 was a SPLIT year (Balad ran alone);
   the raw family errors are 2019s -0.71 and 2021 0.00, not -1.9 and +1.5;
   on the raw record unified years average -0.70 and split years -0.68 -
   there is no unified-regime premium.]
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
[14 Oct, s.43: this mechanism was never graded - the harness kept the
additive e1 mean. Graded now; the -1.35 it replaced rested on the s.24
misreading, and full pass-through of the turnout ratio is not what the
record shows (slope ~0.25).]

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

## 34. Kolot Nodedim's K26 update (2026-09-07): a judgment cross-check, not new data

The project (harelc/elections-vote-transfer, kolot-nodedim.netlify.app)
pushed two commits on 7 September: a simulated 26th Knesset ("K26") retuned
to that day's Madad 120 map, and D'Hondt seat-block displays. The MEASURED
transition files we hold (2021->2022 and 2022->2023-25 with abstention,
alpha estimates) are byte-identical to the repository's current copies; the
2025->2026 files are outputs of the simulation, not measurements. K26 pushes
every 2022 ballot through a hand-written TRANSFER_MATRIX (12 source lists x
14 destination lists), per-source ROW_TURNOUT factors, a 7.5% roll-growth
multiplier and Dirichlet noise (alpha 80), and is calibrated by hand to the
poll map - so its outputs cannot be used as evidence about 2026. Its inputs
are, however, an independent expert's judgment about vote flows, and that is
worth comparing with our LINEAGE_2026 (which is calibrated on the measured
K24->K25 kalpi matrix, R^2 0.889). Their matrix converted to destination
composition on the official 2022 shares, no turnout factors:

| 2026 list | Kolot Nodedim implied composition | ours (LINEAGE_2026) | verdict |
|---|---|---|---|
| Yashar | Yesh Atid 52 / Nat'l Unity 39 / Labor 4 / Meretz 3 | Nat'l Unity 45 / Yesh Atid 25 / Likud 15 / Labor 10 / Shas 5 | they give Eisenkot NO ex-Likud vote; our 15% is the N12-sourced soft-right crossover the certainty desk measured - kept |
| Together | Yesh Atid 78 / Nat'l Unity 12 / Labor+Meretz 8 | Yesh Atid 60 / Likud 13 / Nat'l Unity 13 / RZP 9 / Jewish Home 5 | they give Bennett none of ex-Yamina's 2022 electorates (RZP/JH/Likud localities); the K24->K25 matrix says that is where Yamina's voters went - kept |
| Likud | Likud 91 / RZP 6 | Likud 82 / Nat'l Unity 11 / RZP 7 | they have Likud retaining 73% with no inflow; we let Gantz-2022 localities feed Likud (Likud's 2022 vote was itself partly ex-B&W) |
| Otzma | RZP 67 / Likud 30 | RZP 55 / Likud 30 / Shas 15 | close; our Shas 15 is the masorti-periphery term |
| Amcha | Likud 52 / RZP 48 | Likud 47 / RZP 37 / YB 10 / JH 4 | close (the Ynet dati poll: Amcha's vote is ~20% national-religious, consistent with both) |
| RZP-Zehut | RZP 76 / Likud 24 | RZP 90 / JH 10 | they route 10% of Likud 2022 into Smotrich; the dati poll's 70% national-religious share favours ours |
| Democrats | Labor 38 / Meretz 33 / Yesh Atid 19 / Hadash 6 | Labor 50 / Meretz 50 | their 19% ex-Yesh Atid is plausible (Golan's polling exceeds Labor+Meretz 2022 by ~3 seats); a note for the next lineage revision |
| Reservists-Economic | Nat'l Unity 52 / Yesh Atid 38 | (absent) | GAP in ours - added below |
| Blue and White | Yesh Atid 41 / B&W 35 / YB 10 | (absent) | GAP in ours - added below |
| Joint List | Hadash-Ta'al 51 / Balad 42 / Ra'am 5 | Hadash-Ta'al 65 / Balad 35 | both judgment; ours follows 2022 vote weights |

Their ROW_TURNOUT is the striking part: Shas 0.62, Likud 0.80, RZP 0.84
against Yisrael Beytenu 1.40, National Unity 1.18, Yesh Atid 1.08 - a
40-50% differential-turnout swing against the right, which is the device that
makes the hand matrix land on the poll map. The measured record runs the
other way: haredi lists beat their final polls by +1.35 seats on average
and 2022's haredi turnout surge is the reason; our haredi shock and
HAREDI_FLOOR keep that sign. We do not adopt any of their turnout factors.

**What changes here.** Two lists with real pass probability (Reservists-
Economic 0.28, Blue and White 0.03) had no lineage in LINEAGE_2026, so the
kalpi poststrat and capacity truncation ignored them. Added: Reservists-
Economic = Nat'l Unity 0.50 / Yesh Atid 0.30 / Likud 0.10 / YB 0.05 / Labor
0.05 (Hendel's New Hope voters went NU 58 / Likud 42 in 2022; Zelekha's NEP
and Wilf are centre-left Tel Aviv electorates); Blue and White = its own
2022 pattern, NU 0.70 / Yesh Atid 0.30. Unity (withdrew) needs none.
Nothing else in the projection changes.

## 35. Owner taxonomy: unaligned lists close coalitions explicitly (2026-09-09)

Two formation outcomes are redefined so the kingmakers are visible rather
than folded into bloc sums:

* **Change coalition with unaligned / Amcha** (was "with Amcha"): the change
  lists alone are short of 61 and Blue and White, the Reservists–Economic list
  (on their centre-side draws) or Amcha close the gap. "Change coalition
  (without Ra'am)" now means the change lists ALONE reach 61.
* **Netanyahu + unaligned / defector coalition** (was "+ centrist defector"):
  Netanyahu's bloc (with Amcha on its right-side draws) is short and unaligned
  seats on their right-side draws, or a pledge-breaking centrist, close it.
  "Netanyahu rightist coalition" now means the bloc alone reaches 61.

Precedence: bloc-alone outcomes override everything; the unaligned-closed
outcomes override the haredi / Ra'am / minority / unity branches. PM
allocation for the unaligned/Amcha row: Eisenkot 0.73 / Bennett 0.21 /
Liberman 0.03 / other 0.03 (the Together>Yashar flip still makes Bennett the
PM in Amcha-closed draws). Same posterior. Outcomes: Netanyahu rightist 0.147,
+ unaligned/defector 0.079, change alone 0.137, change + unaligned/Amcha
0.027, + haredi 0.050, JL-backed minority 0.019, unity 0.089, repeat 0.367,
change + Ra'am 0.084. PM: repeat 36.7 / Eisenkot 26.8 / Netanyahu 22.7 /
Bennett 6.9.

## 36. Accuracy round four (2026-09-10): what the record said about the four proposals

Owner asked for items 1, 2, 4 and 5 of the post-filing list. Each was
MEASURED before anything was built; two of the four were reshaped by the
measurement.

**#1 Threshold straddlers: no late-desertion term.** For every graded cycle,
lists whose D-60..D-30 poll average sat within [threshold - 0.75, threshold
+ 1.5] points (27 list-cycles) were compared with their result:

| cycle | straddlers | mean drift (result - D-45 avg, pp) |
|---|---|---|
| 2009 | 5 | +0.66 |
| 2013 | 5 | +0.01 |
| 2015 | 2 | -1.75 (Otzma-Yachad 3.29 -> 2.97) |
| 2019a | 6 | -0.06 (Zehut 2.86 -> 2.74; Shas 4.3 -> 6.7) |
| 2021 | 4 | +1.94 (RZP, Blue and White, Meretz, Labor all rose) |
| 2022 | 5 | +0.03 |

Pooled: mean drift +0.27, median +0.37, realised pass rate 0.85; the spread
(sd ~1.5 pp) is what the residual shock already gives a 4-seat list. Lists
that failed had polled BELOW the line at D-45 (Zehut, Am Shalem, Otzma-
Yachad) and lists that polled below and passed are just as common (National
Union 2009, Yisrael Beytenu 2019a, RZP and Blue and White 2021). A
desertion term would have biased 2021 badly and helped nowhere. NOT built.
Instead the threshold question is graded directly: src/validate_threshold.py
projects every cycle from the cached D-56 and D-21 posteriors and scores
pass probabilities for straddlers (Brier, reliability bins, realised drift);
results below once the cache is complete.

**#4 The conditional gevalt is real but the condition is not "rising".**
Likud's final-fortnight trend against its final-week miss:

| cycle | D28-15 -> D14-1 (seats) | final week | result | miss |
|---|---|---|---|---|
| 2009 | 30.0 -> 27.6 | 26.6 | 27 | +0.4 |
| 2015 | 23.2 -> 22.0 | 21.2 | 30 | +8.8 |
| 2019a | 28.9 -> 28.1 | 28.2 | 35 | +6.8 |
| 2019s | 31.4 -> 32.1 | 32.5 | 32 | -0.5 |
| 2020 | 32.9 -> 33.7 | 34.1 | 36 | +1.9 |
| 2021 | 28.3 -> 29.6 | 30.6 | 30 | -0.6 |
| 2022 | 32.4 -> 31.5 | 31.2 | 32 | +0.8 |

The two big beats came with Likud FALLING in the polls, not rising: the
gevalt is a reaction to perceived danger. The predictor that separates the
record is whether Likud trailed or tied the largest non-bloc list in the
final week (2015 behind Zionist Union, April 2019 behind Blue and White,
September 2019 tied): misses +8.8 / +6.8 / -0.5, mean +5.0, sd 4.9, n=3;
in the years it led clearly (2013, 2021, 2022) the miss was -3 / -0.6 /
+0.8. Built as a harness layer (`gevalt_cond`, TRAIL_MARGIN 0.5 seats):
when Likud's projected standing trails the leader, add the leave-one-
cycle-out mean of trailing years with its sd, zero-sum against the field.
n=3 is thin, so it is tested on top of the shipped no-anchor configuration
at full and half strength and ships only if the eight-cycle harness says so.
Likud (23) trails Yashar (25) today, so the condition is ON for 2026.

**#2 Width: joint stack x forward-variance grid.** Runs on the horizon
cache (D-56 and D-21 posteriors for every cycle), STACK_GRID 0.7/0.85/1.0 x
RW_GRID 1.0/1.25/1.5, scored by interval score and coverage at both
horizons and by the straddler Brier. Verdict below.

**#5 Post-filing remeasurement: what exists and what does not.** Searched
every post-filing publication (N12/Midgam 7 Sept, Kan/Kantar 9 Sept,
Maariv/Lazar 8 Sept, Walla/Lazar 9 Sept, Ch13, i24, Ch14). No pollster has
published an undecided-lean crosstab or a list-certainty wave since the
lists closed; the N12 lean (n~60, 27 Aug) remains the only measurement and
keeps its pooled weight. What was published: N12 7 Sept - 11.5% undecided,
turnout intention 69% overall, coalition voters 75% vs opposition voters
81%; 21% say the near-threshold lists strengthen their vote, 27% weaken
(recorded as evidence, not used - self-reported turnout intention has no
graded track record here). Built instead: (a) `REFORMED_NOISE` - every
observation of the Reservists series before 6 Sept (Tropper out, Zelekha
in) carries x1.5 noise and of RZP before 2 Sept (Zehut in) x1.3, so the fit
and its drift term are not pinned to a list that no longer exists (279
observations widened); (b) MICRO_POLLED refreshed from the post-filing CEC
itemizations (Noam 0.6%, the Haredi Public 0.6%, Israel First 0.3%); (c) the
DRI "institute" filing (self-commissioned, no publisher, scrambled names,
Likud 25 / Blue and White 4) is parsed for the record and excluded from the
likelihood by editor.

**#2 verdict (horizon grid, 8 cycles x D-56/D-21, cached posteriors).**
Interval score (lower is better), coverage of the 90% band, straddler-
relevant threshold Brier and seat MAE:

| horizon | config | MAE | coverage | Brier | width | interval score |
|---|---|---|---|---|---|---|
| D-21 | calendar (shipped: stack 1.0, RW 1.0) | 1.935 | 0.964 | 0.074 | 7.77 | 9.75 |
| D-21 | stack 0.85, RW 1.0 | 1.968 | 0.956 | 0.076 | 7.18 | 9.43 |
| D-21 | stack 0.7, RW 1.0 | 2.013 | 0.944 | 0.079 | 6.67 | 9.99 |
| D-21 | stack 1.0, RW 1.25 | 1.935 | 0.964 | 0.074 | 7.88 | 9.65 |
| D-56 | calendar (shipped) | 2.768 | 0.912 | 0.103 | 9.72 | 15.62 |
| D-56 | stack 1.0, RW 1.5 | 2.765 | 0.926 | 0.103 | 10.23 | 15.45 |
| D-56 | stack 0.85, RW 1.0 | 2.791 | 0.906 | 0.106 | 9.30 | 15.78 |
| D-56 | stack 0.7, RW 1.0 | 2.833 | 0.897 | 0.110 | 8.87 | 16.41 |

No configuration dominates. A 0.85 stack buys a 3% better interval score at
D-21 but costs 0.03 seats of MAE and 0.002 of threshold Brier, and at D-56
it loses on every score; a 1.5x forward variance helps the interval score
at D-56 and hurts it at D-21. Per-cycle winners are split (D-21: the 0.7
stack wins 5 of 8 cycles on interval score yet loses the pooled mean, i.e.
its misses are large when they come). The standing rule since RESID_SCALE
(ship only what wins every leave-one-cycle-out fold) is not met, and the
objective is the seat count, where the shipped width is best or tied. The
knobs STACK_SCALE and RW_FORWARD_SCALE are wired into the projection at
1.0 / 1.0; the over-coverage (96% at D-21) is real but shrinking it costs
point accuracy through the threshold nonlinearity, exactly as the width
grid of s.27 found for the residual alone.

**#4 verdict (eight-cycle harness, projection on the cached election-eve
posteriors, LOO parameters).** Median-seat MAE per list, the published
point estimate, and threshold Brier:

| configuration | MAE (mean) | MAE (median) | coverage | Brier |
|---|---|---|---|---|
| no anchors (shipped) | 1.565 | 1.524 | 0.962 | 0.053 |
| + trailing-Likud, full | 1.616 | 1.506 | 0.974 | 0.054 |
| + trailing-Likud, half | 1.578 | 1.467 | 0.983 | 0.053 |

Per cycle (median MAE, shipped -> half): 2015 2.09 -> 1.36, April 2019
2.54 -> 2.31, September 2019 0.57 -> 1.07, the other five untouched (the
condition never fires). Two wins, one loss, best median accuracy of any
ablation ever run on this harness; the mean MAE is 0.01 worse because the
sd it carries (4.9 seats) widens Likud. Shipped at half strength
(`TRAIL_ON`, scale 0.5) with the caveat stated in the code: three trailing
cycles are thin evidence, and the layer is the first thing to revisit if
Likud's final-fortnight polling changes the condition.

**#1 verdict (straddler calibration from the horizon cache).** 24 lists at
D-56 and 27 at D-21 were projected within the band. Established lists are
calibrated (D-21: realised pass 0.70 vs predicted 0.60, drift -0.4 pp;
D-56: 0.58 vs 0.65, drift -1.2). FIRST-CYCLE lists are not: of 11
new-list straddlers across both horizons, 2 passed (Hatnuah 2013, Yamina
September 2019) and 9 failed (Gil, the Greens, Am Shalem, Otzma 2013, New
Right April 2019, Gesher, the IDP, the Israelis), realised pass 0.18 vs
predicted 0.50, mean drift -1.6 pp (sd 2.6; LOO means -1.1 to -2.2). That is
the strategic-desertion effect the poll-based measure could not see
(below-threshold polls are censored at zero seats). Built as a layer,
`new_straddler`: a first-cycle list whose projected share sits within
[-0.75, +1.5] pp of the threshold receives the LOO mean drift with its sd,
zero-sum against the field. Validated projection-only on the horizon cache
(D-56 and D-21) and by the straddler Brier with and without the layer;
verdict below. In 2026 the condition covers Amcha Yisrael and the
Reservists-Economic list.

**Data notes (11 Sept).** Two polls (Lazar/Maariv 10 Sept, Tatika/Zman
Yisrael 10 Sept; 750 in the cycle) and one filing (Direct Polls 4138, a
duplicate of 4136). Duplicate filings are now detected in the merge
(identical party vectors from one firm within three days: 4120/4121 and
4136/4138 count once). The "S.M.L.T." row the archive carries for Channel
14 is the DRI filing (n 2,185, Likud 25, Blue and White 4) under another
label; it is excluded from the likelihood as an unknown firm with no
series. A stray "Haredi Public" row (Lazar 10 Sept, 0 seats) would have
created a 16th latent list; micro-list ids are now kept out of the latent
blocks (they live in the small-party layer).

**#1 verdict (horizon cache, projection-only, LOO parameters).**

| horizon | config | MAE | coverage | Brier | interval score |
|---|---|---|---|---|---|
| D-21 | calendar (shipped) | 1.935 | 0.964 | 0.074 | 9.75 |
| D-21 | + new-straddler | 1.928 | 0.964 | 0.071 | 9.50 |
| D-56 | calendar (shipped) | 2.768 | 0.912 | 0.103 | 15.62 |
| D-56 | + new-straddler | 2.750 | 0.912 | 0.097 | 15.62 |

Straddler Brier alone: D-56 0.256 -> 0.226 (new lists 0.299 -> 0.111,
established 0.247 -> 0.249), D-21 0.245 -> 0.234 (new 0.311 -> 0.269,
established unchanged). Per cycle the layer is neutral where no new list
straddles, better in 2009, 2013, April 2019 and September 2019 at D-56, and
worse only in September 2019 at D-21 (Yamina's late rescue, the one case in
eleven where a new straddler surged). Better on every pooled score at both
horizons: SHIPPED (`NEW_STRADDLER_ON`, mean -1.6 pp, sd 2.6, band -0.75/+1.5
around the threshold, first-cycle lists only). In 2026 it applies to Amcha
Yisrael and the Reservists-Economic list; the annex carries the bullet.

**Refit and headline (11 Sept, 750 polls, 43 filings merged).** 0
divergences, r-hat 1.01, ESS 489, holdout 0.74 seats. Both new layers fire
today (Likud 23 trails Yashar; Amcha and the Reservists sit in the band).
Headline: P(NB>=61) 21.0 / change bloc alone 8.3 / with Ra'am 25.9 /
deadlock 53.1; PM repeat 38.4 / Netanyahu 28.2 / Eisenkot 21.2 / Bennett
5.6. Central: Likud 27, Yashar 23, Together 11, Democrats 10, UTJ 8, Shas
8, YB 8, Joint List 8, Otzma 7, RZP-Zehut 5 (.77), Ra'am 5 (.77); Amcha 0
(.20), Reservists 0 (.19), B&W 0 (.02). The move since the previous build
(NB 14.5 -> 21.0, Likud 23 -> 27) is the trailing-Likud layer (+2.5 seats
mean, zero-sum) plus the two new-straddler desertions redistributed to the
field; the polls themselves moved little.

## 37. Update of 16 September: petitions, the archive's relabelling, filings

**Events.** The disqualification-petition deadline passed on 15 Sept (Israel
Hayom, Kipa, JDN, Ynet): three petitions against Ra'am (Likud, Otzma, the
"Voters' Forum"), Likud against the Joint List and MK Kasif, Otzma against
Balad's Abu Shahada, Orot HaShachar against Balad, the Democrats and Zulat
against Otzma Yehudit, Zulat against RZP-Zehut, Otzma against the
Democrats; the Betsalmo petition against Kasif was struck for lacking the
12 committee signatures. The CEC hears the rest the week of 21 Sept; the AG
files a position; a list disqualification is appealable to the Supreme
Court and a candidate disqualification needs its approval. Record: the
court reinstated every Arab list the committee barred (2003, 2009, 2019),
struck no Jewish list since Kach (1988), and did bar one candidate
(Ben-Ari, 2019). Modeled as open mixture events with residual priors -
Ra'am 0.02, Joint List 0.015, Otzma 0.01, RZP-Zehut and Democrats 0.005 -
each zeroing the list and redistributing its voters within the family
(`DISQUALIFY_TRANSFER`); candidate-level petitions are not modeled (a
seat does not leave the list). Collapse on the rulings.

**Archive relabelling.** The polling archive renamed the 2026 firms to
consortium abbreviations (LRI+P4A = Lazar/Panel4All, MM+SN = Maagar Mochot/
StatNet, MP+TM+SN+A = the Channel 13 consortium, SF+ND = Filber/Next Data);
aliases added so the series stay whole. "S.M.L.T." remains excluded.

**Filings.** Nine new (4139-4149; 72 indexed, 51 merged after duplicates).
Two Sept 13-15 filings (Kantar, Filber) carry a "unity government"
question whose line matched the withdrawn Unity list's keyword (27% and
24%): lines for a withdrawn list after its withdrawal date are now dropped
before the sum filter (`ABSORBED_FROM["unity"]`).

**Refit and headline (16 Sept, 753 polls, 51 filings).** 0 divergences,
r-hat 1.02, ESS 358, holdout 0.75. Headline: P(NB>=61) 15.9 / change bloc
alone 10.1 / with Ra'am 28.1 / deadlock 56.0; PM repeat 40.0 / Netanyahu
23.8 / Eisenkot 23.3 / Bennett 6.0. Central: Likud 26, Yashar 24, Together
11, Democrats 10, UTJ 8, Shas 8, YB 8, Joint List 8, Otzma 7, Ra'am 5
(.77), RZP-Zehut 5 (.75); Reservists 0 (.21), Amcha 0 (.18), B&W 0 (.02).
The week's polls trimmed Likud's trailing-year beat (Likud 27 -> 26, NB
21.0 -> 15.9): Yashar's lead is now 1-4 seats in every poll, so the
condition holds but the latent gap widened, and the petitions cost Ra'am
and the Joint List about a point of pass probability each.

**17 Sept.** Two polls (Channel 13 consortium 15 Sept, relabelled again in
the archive and aliased; Channel 16 / Maagar Mochot 16 Sept - Yashar 21,
Likud 18, Together 16, Otzma 9, Shas 9, Democrats 9, UTJ 7, YB 7, Joint
List 6, Ra'am 5, RZP-Zehut 5, Amcha 4, Reservists 4 - not yet in the
archive, entered through the new data/manual_polls.csv channel with
Maariv's five-channel compilation as its source link; the archive's
signature dedupe and the CEC displacement keep it single once the
official copies arrive). 755 polls; refit 0 divergences, r-hat 1.01, ESS
584, holdout 0.82. Headline: NB 16.6 / change alone 9.3 / with Ra'am 28.1
/ deadlock 55.3; PM repeat 40.0 / Netanyahu 24.3 / Eisenkot 22.9. Likud
26, Yashar 24; Ra'am .79, RZP-Zehut .76, Reservists .21, Amcha .20.

## 38. Catch-up of 8 October: rulings, letters, surplus pacts, 22 polls

**Petitions resolved.** The CEC barred Ra'am (18-5-1), the Joint List, MK
Kasif and Balad's Abu Shahada (31-4; 23 Sept) and rejected the petitions
against Otzma, RZP-Zehut and the Democrats. The Supreme Court unanimously
reinstated Ra'am, the Joint List and Kasif (early Oct; Ynet, N12); Abu
Shahada withdrew his candidacy after the President of the Court suggested
it (Israel Hayom, Ynet) - no seat leaves Balad. The five DISQUALIFY events
are RESOLVED False. The record stands at 0 final list disqualifications in
8 attempts.

**Lists and letters.** All 38 lists approved 27 Sept (Ynet, Walla, Emess).
Final letters as requested except Together = בד (Otzma's prior claim to ב)
and Israel First = י. Site chips updated; contested marks removed.

**Surplus-vote agreements (deadline 16 Oct).** Signed: Likud - RZP-Zehut
(6 Oct; Otzma was left out and is to sign with Amcha or run alone), Together
- Yisrael Beytenu, Yashar - Democrats. Expected: Shas - UTJ, Otzma - Amcha,
Joint List - Ra'am; Reservists - Blue and White negotiating (no effect
unless both pass). SURPLUS_PAIRS replaced with the signed + expected set;
the previous assumed pairs (Together-Yashar, Democrats-YB) were wrong on
both centre pairs.

**Blue and White.** 0.7-1.3% in every post-approval filing; Ch13 and Israel
Hayom report an offer of a "withdrawal with honour", Gantz meeting Eisenkot
on continuing the run. blue_white_folds reopened as a withdrawal event at
0.40 (2022 transfer pattern: Yashar .60 / Together .25).

**Data.** 22 archive polls (777; the archive now carries the Channel 16 poll
the manual channel supplied - the poll_id dedupe dropped the manual copy),
25 filings (97 indexed). Excluded by editor: aChord (one self-commissioned
survey of non-haredi Jews 22-34). Dialog's "liberals" sample (4166) is
non-national and flagged by the marker. Filber 4176 parsed 7 parties (a
partial report) and fails the sum filter by design.

**Refit and headline (8 Oct; 777 polls, 68 filings, D-19).** 0 divergences,
r-hat 1.01, ESS 369, holdout 0.71. Headline: P(NB>=61) 19.1 / change bloc
alone 5.6 / with Ra'am 21.2 / deadlock 59.7; PM repeat 42.8 / Netanyahu 27.3
/ Eisenkot 18.4 / Likud successor 5.8. Central: Likud 26, Yashar 23,
Together 11, YB 9, Democrats 9, Joint List 9, UTJ 8, Shas 8, Otzma 7, Ra'am
5 (.81), RZP-Zehut 5 (.78); Reservists 0 (.21), Amcha 0 (.12), B&W 0
(.01). Three weeks of polls narrowed Together (16 -> 11-13) and lifted the
Joint List (6 -> 8); Amcha slipped to 2-4 and its pass odds to 12%. With
the calendar in the calm zone the forward variance is now small; the
remaining width is the election-day shock stack.

## 39. CEC parser, fourth pass (2026-10-08)

Two new filings (Filber 4192, Ch13 consortium 4193) exposed three more
format traps, and the fixes corrected two filings that had been IN the
likelihood with a wrong Yashar share since August:

* The keyword "ישר" is a substring of "ישראל": the methodology line
  "ישראל הרשאים לבחור" (followed by the response-rate line) parsed as
  Yashar 7.3% in 4192 - and, it turned out, as 4.4% in Filber 4070 (10 Aug)
  and 9.0% in 4085 (18 Aug), both of which passed the sum filter and sat in
  the fit at a fifth of Yashar's true level. Yashar is now matched as a
  token ("ישר ", "ישר!") or by the leader's name in both spellings.
* Leader names also appear in the PM-suitability tables ("גדי איזנקוט 32%"):
  a leader-only keyword now counts as a party line only when the line
  names a list (בראשות / בהובלת / בהנהגת); the wrapped-name rule treats a
  leader name on the continuation line as part of the name (Maagar's
  "הרשימה המשותפת בראשות פרופ' יוסף" / "ג׳בארין 6% ...").
* Filber 4176 glues the seat count in front of the percentage
  ("2116.4%" = 21 seats, 16.4%; "86.1%" = 8 seats, 6.1%): the digit-run
  splitter now also corroborates a candidate by seats ~ 1.28 x percent
  (120 seats over the ~93% of the vote that passes), within 1.5 seats; a
  two-digit run above 40% is split the same way. The methodology line
  "שיעור האנשים שסרבו ... 77%" contains "שס" inside "שסרבו" and had been
  matching Shas; refusal lines are skipped.

Net: 4070 Yashar 4.4 -> 16.8, 4085 9.0 -> 18.5, 4192 7.3 -> 17.4, 4176 fully
parsed (14 lists, now eligible), Kantar Shas rows unchanged; 70 of 99
filings merge. The fit will move Yashar's August level up slightly at the
next refit (two filings among ~30 August observations of the list).

## 40. Update of 10 October (D-17)

Six archive polls since the 8 Oct build (Direct Polls, Filber, Ch13
consortium 7 Oct; Kantar/Israel Hayom, Lazar/Maariv, Tatika 8 Oct): 783
in the cycle; no new CEC filings beyond 4193. Window fit: 211 polls, 2,752
observations, 71 filings merged (4192 now inside asof).
Events checked, no model change: Eisenkot (Ynet, ~8 Oct) - "even without
61 I will bring my government to the Knesset", will not ask the haredi or
Arab parties to vote for it: consistent with the abstention-based
JL-backed minority branch as coded; he is "convinced" Gantz will withdraw
at 1.5% - the Blue and White camp says otherwise (Walla 1 Oct), so the
0.40 withdrawal event stands. Likud-RZP held a joint "saving the right"
conference without Ben-Gvir (N12, 8 Oct); Otzma has no signed pact, Hendel
publicly asked Winter to sign with him - Otzma-Amcha stays carried as an
expected pair until the 16 Oct deadline.

Refit: 0 divergences, r-hat 1.01, ESS 433, holdout 0.68. Headline: P(NB>=61)
21.7 / change bloc alone 5.2 / with Ra'am 18.8 / deadlock 59.5; PM repeat
41.9 / Netanyahu 29.6 / Eisenkot 17.3. Central: Likud 27, Yashar 23,
Together 11, Democrats 9, Joint List 9, UTJ 8, Shas 8, YB 8, Otzma 7,
Ra'am 5 (.78), RZP-Zehut 5 (.78); Reservists (.20), Amcha (.15), B&W (.01).

## 41. Accuracy search, round five (8-13 Oct): what shipped and why

A multi-agent search audited the model through eight lenses (likelihood and
latent, shock stack, threshold and seat law, 2026 judgment layers, data
quality, mixture and formation, validation methodology, outside knowledge),
merged 54 proposals into 14 candidates, put each through three adversarial
skeptics (statistics and double counting, evidence quality, buildability),
and implemented and tested the survivors in isolated worktrees on the
cached harnesses. One candidate was killed by the skeptics (asof from the
newest filing: a no-op once the archive catches up). Six were built and
graded; seven harder ones (harness scoring integrity, shock-stack width,
centred-log-ratio latent, endpoint re-centring, ballot fidelity, the Arab
turnout regime, the parser fixes) were interrupted by usage limits and are
carried to the next round. The harness now mirrors production and grades
configurations on the SHIPPED configuration's list mask (`*_fixed`
columns; `harness_compare.py --fixed`) so a layer that moves a list across
the 0.5% scoring cutoff is not graded on a different denominator.

**Shipped (harness-validated, the set tested together).**

| candidate | change | evidence |
|---|---|---|
| surplus-pair resolver | `simulate.PAIR_RESOLVER_FIX`: first-occurrence component binding, alias map (together -> bennett_2026+yesh_atid, joint_list -> balad+hadash_taal), membership guard, loud warning on unresolved pairs | Two SIGNED pacts never pooled: Joint List-Ra'am was bound to the zero-share "Balad (alone)" column the mixture appends, and Together-Yisrael Beytenu never resolved after the composite rename. Bit-identical on every harness fold; 2026: JL+Ra'am gain a seat in 30% of draws, Together+YB in 35% |
| trailing-Likud geometry | `TRAIL_SAT_SOURCE`: same draw, gate and half strength, but the beat is taken from Likud's non-haredi satellites (Otzma, RZP-Zehut; capped at 75% of their share; Amcha excluded) | In the trailing years the opposition side's final-poll error was +0.12 (2015) and +0.33 (2019a): the surge was paid by the right flank. 3 seeds: median MAE 1.498 -> 1.480, mean 1.578 -> 1.514, Brier 0.049 -> 0.044, bloc Brier 0.047 -> 0.029, coverage unchanged; one sub-noise fold loss (2015 +0.09) |
| withdrawn-list rule | `WITHDRAWN_DAYS_LATE = 14` inside the final 28 days + `GONE_STAY_ZERO` (a dropped list is not resurrected by the residual shock) | Every list dropped inside four weeks was an off-ballot phantom with 0 seats; the shipped rule resurrected them at 0.5-0.6% each (2026: Unity's fold transfer counted twice) |

Combined set vs shipped, fixed mask (eight cycles; eve = 3 seeds):

| horizon | median MAE | mean MAE | threshold Brier | interval score | coverage |
|---|---|---|---|---|---|
| eve | 1.492 -> 1.411 | 1.576 -> 1.500 | 0.049 -> 0.042 | — | 0.973 -> 0.973 |
| D-7 | 1.522 -> 1.386 | 1.581 -> 1.484 | 0.050 -> 0.041 | 8.65 -> 8.42 | 0.983 -> 0.990 |
| D-21 | 1.816 -> 1.560 | 1.817 -> 1.649 | 0.070 -> 0.051 | 9.38 -> 8.88 | 0.973 -> 0.979 |
| D-56 | 2.419 -> 2.457 | 2.560 -> 2.535 | 0.099 -> 0.095 | 13.83 -> 13.80 | 0.940 -> 0.939 |

Eve folds: 4 wins, 3 ties, 1 sub-noise loss. The D-56 median loss is the
trailing layer in 2020, a horizon now behind us. Note: the horizon harness
never passed the trailing-Likud parameters before this round, so every
earlier D-56/D-21 number on record was for a configuration without it; the
calendar baselines above are the corrected ones.

**Shipped (evidence-class, 2026-only layers - not harness-testable).**

* `U_LEAN_PER_SIDE`: s.11's 0.35 is the change in the bloc GAP, but the
  certainty layer applied it to EACH side, doubling the undecided transfer
  (5.64 seats of gap at full lean vs the measured 2.91). Per-side constant
  0.71 x (0.775 - 0.52) = 0.181. The pre-registered half weight now holds.
  The lean measurement's date is also corrected: N12/Midgam fieldwork 30
  July (n 505), not 27 August. Calendar decay and a 21-day pool window were
  tested and NOT shipped (the decay rate had no support; the window moves
  the pool the wrong way).
* `AMCHA_FADE_RETIRED`: three subtractions were stacked on Amcha (churn
  ~0.4 pp, the 1.5-seat fade 1.17 pp, the new-straddler layer 1.6 pp) on a
  3.29% base, leaving a median share of 0.02% against polls of 2.7-3.3%.
  The fade was a D-60 term; Amcha's latent fell from 4.24% (D-58) to 3.26%,
  so most of it has already happened in the polls. Retired. The churn
  exemption for new straddlers stays OFF pending the re-grade below.
* Formation (government_formation.py, cited October statements):
  Reservists-Economic seats count only in coalitions without haredi or Arab
  partners (`ZIONIST_ONLY`; Hendel, JPost, "we will not complete a 61-seat
  majority" for Netanyahu with the haredim), res_right 0.30 -> 0.12,
  res_centre 0.45 -> 0.70; amcha_right 0.87 -> 0.60 (Winter, INN 2 Sept:
  recommends Netanyahu, JOINS only if a national-service law passes before
  the swearing-in); utj_defects 0.26 -> 0.15 (JPost 17 Sept: the haredi
  parties lean to recommend no one); a UTJ confidence-abstention channel is
  coded but OFF (unsourced Channel 12 report, rebuffed by Asher).
* Blue and White withdrawal 0.40 -> 0.25: Gantz publicly ruled it out
  ("whoever says I am burning votes is lying", Kan live blog); Israel Hayom
  reports a possible exit only in the final days.

**Open findings carried to the next round.**

* The new-straddler mean (-1.6 pp) was measured on seat-implied shares (a
  failed list scored at 0, two non-runners counted as total desertion). On
  the vote shares the failed lists actually won, the nine lists that ran
  drifted -0.33 pp (sd 2.0; D-21 alone +0.17, n=7) with 2 of 7 passing at
  D-21. The layer still improved straddler Brier because pushing a list
  under the line predicts failure; the size is over-stated. Re-grade on CEC
  vote shares (part of harness_ballot_fidelity) before the final build.
* The trailing condition is a 0.5-seat cliff on the Monte-Carlo mean; today
  Likud and Yashar sit on it, so whether it fires is seed-sensitive. With
  satellite sourcing the bloc headline no longer depends on it (P(NB>=61)
  13.2 sourced vs 13.9 off on the 10 Oct posterior), but Likud's central
  count still does (about 27 vs 24). A ramp in the margin scored best of
  all variants (median 1.471, Brier 0.042) but was not pre-registered;
  graded as sensitivity only.

**Refit and headline (13 Oct, D-14; 784 polls, 74 filings merged).** 0
divergences, r-hat 1.01, ESS 448, holdout 0.68. One archive poll (Filber 12
Oct) and filings 4197-4200 since the 10 Oct build. Headline with the ship
set: P(NB>=61) 12.4 / change bloc alone 6.4 / with Ra'am 26.3 / deadlock
61.3; PM repeat 48.1 / Eisenkot 20.3 / Netanyahu 19.1. Central: Likud 25,
Yashar 22, Together 11, Democrats 10, UTJ 9, Shas 9, Joint List 9, YB 9,
Ra'am 6 (.83), Otzma 6 (.78), RZP-Zehut 4 (.56); Amcha 0 (.29),
Reservists 0 (.22), B&W 0 (.01). Decomposition on this posterior (plain
projection, same seed): the old configuration gives P(NB>=61) 20.9; the
trailing-Likud source alone moves it to 13.5 (14.4 with the layer off
entirely) - Likud keeps its beat (25.0 vs 22.2 without it) while Otzma
(-1.6) and RZP-Zehut (-1.2) pay for it, as the right flank did in the
trailing years. The pair fix lifts Ra'am to 6; the retired fade lifts Amcha
to .29. The trailing margin in the published run is 0.0 seats (a tie).

**Baseline restated (13 Oct).** The shipped configuration now holds dropped
lists at zero, so they fall below the 0.5% scoring cutoff and leave the
graded set; the harness numbers are therefore restated on the NEW shipped
list mask and are not comparable with the pre-13-Oct record (the old
configuration's numbers were deflated by phantom lists resurrected at
0.5-0.6% and graded as easy near-zeros). New baseline, own mask (eve: mean
of 3 seeds): eve median 1.630 / mean 1.735 / coverage 0.970 / Brier 0.051;
D-7 1.628 / 1.719 / 0.990 / 0.049 (interval score 9.53); D-21 1.831 /
1.914 / 0.979 / 0.063 (10.14); D-56 2.511 / 2.590 / 0.939 / 0.098 (14.07).
The same configuration graded on the old mask: eve median 1.411, the
figure in the table above. Future candidates are graded on this mask.

## 42. Every polled list modelled the same way (13 Oct)

**Owner request (13 Oct).** Lists the pollsters measure, The Haredi Public,
Noam and the other small lists, are to be treated like every other list
rather than carried as fixed micro-list priors. The same message flagged
Together's ballot letters: the CEC gave Together רק (its filing-day
alternative), and בד belongs to another list (Beyachad Natzliach). The
site said בד since s.38; corrected.

**What changed (commit 6b79a1d).**
- `scrape_polls.footnote_items` turns the archive's "Others" footnotes into
  poll rows (80). Ale Yarok's readings after its 3 September union with
  Israel First are added to Israel First (`FOOTNOTE_MERGES`); "<1%" entries
  and unknown names are skipped; lists already in the table are not counted
  twice.
- `MICRO_POLLED` retired (kept as `MICRO_POLLED_RETIRED`). The Haredi
  Public, Noam and Israel First are latent components with their own trend,
  house effects and election-day shock, as are Ahi, Tzomet Beit Yisrael and
  Code Black (new CEC parser keywords). 21 lists, 230 polls, 2,836
  observations.
- `prepare_data`, 2026 only: lists that did not file are dropped
  (`NOT_ON_BALLOT_2026`); a list needs three polls or legal filings in the
  window (`MIN_LIST_POLLS`, filings counted).
- `_merge_cec`: a filing that displaces a table poll keeps the table's rows
  for lists the filing does not itemize (37 rows).
- `ON_BALLOT_2026`: the withdrawn rule never drops a list on the
  CEC-approved ballot. It now keeps Israel First (itemized 0.0-0.5% until
  22 Sept, then folded into "others"); Unity, which withdrew, is still
  removed.
- Harness parity: the eight-cycle harness has always modelled the record's
  small lists that had their own poll column (Yachad 2015, Otzma Sept 2019,
  Jewish Home 2022) as latent components; Zehut April 2019 and NEP 2021 had
  no column and were never in it. Everything above sits inside
  `modern_remaps`, so the historical harness numbers are unchanged by
  construction and the s.41 baseline stands.

**Fit.** 0 divergences, max r_hat 1.010, min bulk ESS 330; 14-day holdout
median error 0.71 seats (0.73 before). Latent last-week means: The Haredi
Public 0.45%, Tzomet Beit Yisrael 0.60%, Code Black 0.42%, Ahi 0.38%, Israel
First 0.31%, Noam 0.30%.

**Candidate resid_relcap - tested, NOT shipped.** The residual shock is
additive (1.83 + 0.044 x seats, in seats, x0.9, x1.35 for first-cycle lists),
so a list at 0.3% draws a ~1.4-1.9 pp sd shock that the clip at zero turns
into a 0.6-0.8% mean. Across the six small lists that is +1.7 pp of phantom
mean vote (4.15% vs a 2.46% latent). Capping each list's sd at c x its own
projected share (layer `resid_relcap`, production `RESID_REL_CAP`):

| config | eve median | eve mean | eve cov | eve Brier | D-7 cov | D-7 iscore | D-21 median | D-21 cov | D-21 iscore |
|---|---|---|---|---|---|---|---|---|---|
| shipped | 1.630 | 1.735 | 0.970 | 0.0508 | 0.990 | 9.53 | 1.831 | 0.979 | 10.14 |
| c = 0.75 | 1.617 | 1.734 | 0.970 | 0.0515 | - | 9.67 | 1.841 | - | 10.48 |
| c = 1.0 | 1.617 | 1.737 | 0.970 | 0.0516 | 0.979 | 9.68 | 1.841 | 0.969 | 10.32 |
| c = 1.5 | 1.630 | 1.739 | 0.970 | 0.0514 | - | 9.73 | 1.841 | - | 10.33 |

(eve: 3 seeds, shipped mask; horizons: one seed.) At the eve c = 1.0 ties
seven folds and wins 2022 (-0.10), so it passes the fold rule, but the
horizon harness contradicts it: at D-7 and D-21 it loses one list of
coverage, 2021's Religious Zionism, whose latent stood near 1% a week out
against a 6-seat result; the additive shock's tail is what covered it.
The 2026 seat effect is negligible (P(NB>=61) 13.3 vs 13.2; no list moves
more than 0.06 seats), so the flag stays OFF. The phantom mean matters
only for display, so the site's small-parties panel now shows each list's
MEDIAN share (the vector the central seat count is built on) instead of
the mean.

**2026 effect (13 Oct build, registration mixture).** P(NB>=61) 13.1
(12.4 before), change bloc alone 6.9 (6.4), with Ra'am 26.4 (26.3), neither
60.5. Central: Likud 26, Yashar 23, Together 11, Shas 9, Democrats 9, Joint
List 9, YB 9, UTJ 8, Ra'am 6, Otzma 6, RZP-Zehut 4. PM: repeat election
47.4, Eisenkot 20.6, Netanyahu 19.4. The trailing margin is 0.11 seats, so
TRAIL fires. Every new small list passes with probability under 1.5%.

## 43. The Arab turnout term graded and shipped (13-15 Oct)

**Why.** Production's Arab family term (s.27 #3) scaled the Joint List and
Ra'am jointly by T/0.538 with T ~ 0.625: full pass-through of the expected
turnout ratio, about +2.2 seats over the polls. It was never graded - the
harness kept the additive e1 family mean - and its regime mean rested on the
s.24 reading, which does not survive a re-run of the record (raw family
error: unified years -0.70, split years -0.68 seats; no unified premium).
The field atlas's harmonised Arab-locality turnout series reached the same
conclusion independently: final polls absorb most of a turnout swing.

**Candidate (arab_turnout_regime, arm arab_regB).** Family error = a + k x
(error implied by the turnout ratio), regime-B turnout table, a and k
leave-one-cycle-out. Production: ARAB_TURNOUT["mean_unified"] 0.580 (the
table-B mean, inside s.4's pre-registered 56-62% band), ARAB_TURNOUT_K 0.247,
ARAB_TURNOUT_INTERCEPT -0.634 (full-sample fit); the draw's own spread
passes through in full.

**Adversarial verification (15 Oct; three skeptics + judge, no refits).**
Every harness number reproduced. One leak was found and fixed:
`arab_turnout_params` let the graded cycle's realised turnout enter the
regression as the denominator of the NEXT cycle's ratio; rows with c ==
cycle or prev[c] == cycle are now dropped. Strict-LOO result (3-seed
pooled, shipped mask, previous harness -> regB; coverage equal):

| horizon | median MAE | mean MAE | Brier | interval | folds W/T/L |
|---|---|---|---|---|---|
| eve | 1.630 -> 1.558 | 1.735 -> 1.723 | .0508 -> .0496 | 9.663 -> 9.614 | 4/2/2 (2015 +0.121) |
| D-7 | 1.638 -> 1.569 | 1.724 -> 1.702 | .0493 -> .0480 | 9.618 -> 9.534 | 4/2/2 (2015 +0.061) |
| D-21 | 1.827 -> 1.803 | 1.926 -> 1.891 | .0631 -> .0618 | 10.263 -> 10.140 | 3/3/2 (2019a +0.077) |

It ships on the POOLED route only (2015's eve fold loses by more than
noise; D-21 seed 100 loses median MAE by 0.003). Production's previous form
(turnA) fails the rule outright (worse Brier at eve and D-7, lower coverage
at D-21), so the change is also corrective.

**Disclosures.** (a) 2022 threshold flips (Hadash-Ta'al and Ra'am near 50%
pass) supply 84 / 71 / 96% of the median-MAE gain and ~90% of the Brier
gain; with 2022 dropped all four pooled metrics still win at every horizon,
and the interval-score gain is spread across cycles. (b) k is weak: 0.247,
se 0.21 (a -0.634, se 0.41, n = 8); strict-LOO k ranges 0.10-0.32 and rests
on 2019a. In 2026 the k term is worth ~0.3 seats; the change is mostly the
intercept plus the turnout spread, and it should not be described as a
validated pass-through. (c) The arm was chosen among nine graded arms. The
simpler add_e0 fails (loses interval score at every horizon). (d)
Production uses the full-sample a and k; the harness grades strict LOO.
(e) 2022's 0.538 is the kalpi Arab-locality measure; IDI's 53.2% changes
the 2026 ratio from 1.019 to 1.022 (~+0.04 seats). (f) The intercept is
fitted on seat errors and contains non-Arab threshold windfall; the
windfall-netted fit (a -0.318, k 0.271) was graded and is worse on mean MAE
and Brier at every horizon, so it is not adopted (its 2026 effect is
further from the old form). (g) 2026's only structural precedent is 2021
(0.446); across all turnout tables the 2026 result is 12.5-13.7 Arab seats,
every one below the old 14.7. (h) The production-only Arab churn in the
certainty layer adds ~0.10 seats. (i) Re-grade once the harness's merged
2021 JL+Ra'am block is split (round three, harness_ballot_fidelity).

**Harness.** ALL_LAYERS now mirror production (arab_mode "turnout",
arab_regime "B", arab_k "loo", arab_intercept True); the previous harness
default is kept as ablation `arab_e1_prev`. RESTATED BASELINE for future
candidates (3-seed pooled, shipped mask): eve 1.558 / 1.723 / .970 / .0496
(interval 9.614); D-7 1.569 / 1.702 / .986 / .0480 (9.534); D-21 1.803 /
1.891 / .972 / .0618 (10.140).

**2026 effect (14 Oct posterior, production seed).** Arab joint mean 14.72
-> 13.38; Ra'am pass .825 -> .752; central JL 10 -> 9, Ra'am 6 -> 5, Likud
25 -> 26, UTJ 8 -> 9; P(NB>=61) 12.4 -> 14.5 (seeds +1/+2: 11.4/11.7 ->
13.5/13.8); change bloc alone 6.8 -> 8.3; with Ra'am 27.1 -> 27.3; neither
60.5 -> 58.2; PM repeat / Eisenkot / Netanyahu 47.7/20.7/19.0 ->
45.3/21.6/20.4. Shipped in the 15 Oct build (s.45's "not in this build"
note is superseded).

## 44. Site audit fixes (14 Oct)

A 61-entry audit of the published site (EN and HE) was applied. No model
code, fit, harness or forecast output changed; everything below is site
text, the site build (src/build_site.py, src/site_ledger.py), the party
registry's Hebrew label for Together, and a comment in src/simulate.py.

**Facts brought up to date (both languages, every edited claim linked).**
- Surplus pacts: five signed - Together-YB and Yashar-Democrats (10 Sept,
  JPost 908296), Joint List-Ra'am (11 Sept, JPost 908431 / INN 693446),
  Likud-RZP-Zehut (6 Oct, Times of Israel liveblog of 6 Oct 13:24 for the
  date; Ynet asxop5pjn, undated, for the parties), Shas-UTJ (11 Oct, JPost
  911320, Ynet e073g8o82). Otzma-Amcha is unsigned (Ben-Gvir undecided per
  Ynet asxop5pjn, the undated report of the Likud signing) and stays carried as a pair until the 16 Oct deadline, valid only
  if Amcha passes. This corrects s.38 (JL-Ra'am and Shas-UTJ "expected").
  The Hebrew text had still listed JL-Ra'am as expected.
- Disqualification petitions rewritten in the past tense with the full
  record: 23 Sept CEC barred Ra'am, the Joint List, Kasif and Abu Shahada
  (JPost 909454); 24 Sept petitions against the Democrats (14-2), Otzma
  (19-10) and RZP-Zehut (21-3) rejected (ToI); 2 Oct Supreme Court
  reinstated Ra'am and the Joint List unanimously and Kasif 7-2, Abu Shahada
  withdrew (JPost 910422); 4 Oct appeals against Otzma, Ben-Gvir and Gotliv
  rejected (JPost 910555).
- Lists closed 8 Sept (D-49), not 9 Sept; the volatility calendar is
  measured on 7 cycles (s.12), early campaign ~1.2 seats/week (RMS).
- Eisenkot-as-PM: the prose now quotes the model's own D.pm value (20.6%
  today, was "~36%") against Polymarket's late-August 50-60% (linked).
- Jewish Home 2022 result 1.19% (results.csv), not 1.17% (also s.15's
  table row, left as written there).
- Haredi floor printed as 6.6% (KALPI_HAREDI_FLOOR = 0.066); state-space
  noise written sigma_p = s_obs * lambda_f * exp(beta_u u_p), as coded.
- Backtest wording: eight graded cycles 2009-2022 (2009 is a graded fold,
  not a prior seed); the methodology lede said nine.

**Numbers now filled from data instead of typed.** Pipeline diagram counts
(polls, cycles, CEC filings parsed); share of the forecast vote below
3.25% (payload `below`: the renormalised median vector, 4.7% today; the
old "about 8%" was a raw-poll/mean-vector figure); the pollster spread in
the industry lede (max - min of D.house: Lazar -5.7 to Filber +11.5, 17
seats; was "up to ten"); the certainty-layer undecided pool and transfer
(fit.u_pool_pct / u_side_seats / u_gap_seats from bayes_model's own
constants: pool 9.65%, 0.68 seats per side, 1.35 of gap; was "~12%" and
"~1.7 seats"); the ground-game locality count (1,216 with 2022 profiles,
was 1,221); the knife-edges heading (any count, digits past 20; today
twelve lists).

**Validation.** `val` is no longer carried forward: build_site recomputes it
each build from model_validation.csv (simple), model_validation_ablation.csv
shipped rows (Bayesian, eve, one seed: mean-seat MAE 1.74, median-seat MAE
1.63, coverage 97.0%, Brier 0.051) and model_validation_horizon.csv calendar
mode (D-56 / D-21 / D-7: 2.59 / 1.91 / 1.72, coverage 93.9 / 97.9 / 99.0).
The table was showing an old pooled run (1.66 / 97.2 / 0.063). The horizon
prose restates the s.41 baseline and drops the "90% coverage at the
published horizon" and "98% over-coverage is an eve artefact" claims, which
the restated harness contradicts.

**Ledger (src/site_ledger.py).** CEC filings are matched one-to-one: same
firm, same publisher, fieldwork within 3 days, nearest date then nearest
sample size, a filing used by one survey only (a/b variants of one survey
share it); 29 ledger rows changed filing, 3 of them to none (no filing
from that publisher exists).
Publication links skip the citation's author wikilinks (42 rows pointed at
presenters' Wikipedia pages), dead Channel 16 vod.html links are dropped,
and a URL cited for two different surveys is kept only on the survey it was
published for; rows without a usable citation link the archive section that
lists them. Rows are tagged with why the current fit does not use them
(outside the 240-day window, same-day variant, composite Arab scenario, sums
fail), mirroring prepare_data's filters read-only; the count of polls in the
fit is shown separately. Official results link: the dead
bechirot.gov.il/AllElectionResults page is replaced by the CEC's data.gov.il
results dataset, with votes21-25.bechirot.gov.il per cycle where those load.

**Hebrew and RTL.** Together's registry name_he is ביחד (was יחד, Eli
Yishai's 2015 list); the ledger's RZP column reads הציונות הדתית–זהות; the
seats note quotes the letters „רק” so they cannot read as "only"; HE +6.8
(not +6.7) for the April 2019 trailing beat; the ground and pollsters ledes
retranslated from the current English; cover strip, seat legend, builder
captions, title and aria labels, firm names (HE_FIRM), the PM "rotation"
row and the tooltip's P(largest) are now Hebrew; signed table cells and the
builder range are LTR-isolated; the 2021<-2022 arrow fixed.

**UI.** The Netanyahu-bloc preset takes every Netanyahu-bloc list in the
draws (Noam and the Haredi Public were missing); report deep links (#formation
etc.) land on their section; the skip link follows the view; the ratings'
"2026 polls in the ledger" link shows only for firms with 2026 polls.

## 45. Update of 14 October (D-13)

**Polls.** The archive refresh added Kantar/Kan (11 Oct, n=553). Two
archive rows were unfinished: Channel 12 (12 Oct) lacked Ra'am,
Reservists and Amcha, and carried the channel in the firm column; Channel
13 (14 Oct) lacked the firm, UTJ and the Joint List. Both entered through
`data/manual_polls.csv` from the press: Midgam/Channel 12, n=509 (Haaretz,
13 Oct: Yashar 23, Likud 20, Together 13, Democrats 9, YB 9, Otzma 8, Shas
8, JL 8, UTJ 7, RZP-Zehut 6, Ra'am 5, Reservists 4, Amcha 0) and Midgam
Project/Channel 13 (Walla, 14 Oct: Yashar 20, Likud 18, Together 12,
Democrats 9, YB 9, JL 9, UTJ 8, Otzma 8, Shas 7, RZP-Zehut 6, Ra'am 6,
Reservists 4, Amcha 4). `scrape_polls`: when the firm cell is unknown but
the publisher cell names a known firm, the two are swapped back; a manual
entry replaces an archive row with the same poll_id whose seats do not sum
to 120. No new CEC filings after 4200.

**Fit.** 232 polls, 2,861 observations, 21 lists; 0 divergences, max r_hat
1.020, min bulk ESS 261; 14-day holdout median error 0.64 seats.

**Forecast (registration mixture).** P(NB>=61) 12.4 (13.1 on 13 Oct);
change bloc alone 6.8; with Ra'am 27.1; neither 60.5. Central: Likud 25,
Yashar 23, Together 11, Joint List 10, Shas 9, Democrats 9, YB 9, UTJ 8,
Ra'am 6, Otzma 6, RZP-Zehut 4. PM: repeat election 47.7, Eisenkot 20.7,
Netanyahu 19.0. Likud's projected margin over Yashar is -0.03 seats, so
the trailing-Likud layer fires. The Arab turnout candidate (s.43 in its
own patch) is under adversarial verification and is NOT in this build.

## 46. Round three ship set (15 Oct, D-12)

**Decision.** Three candidates came to the combine; the judge shipped all
three, conditionally, and rejected a fourth (46.4). After the combine
plan's two gates:
- **Harness ballot fidelity** (46.1): ships. Harness only;
  `HARNESS_FIDELITY` now defaults ON.
- **CLR latent** (46.2): ships. `bayes_model.CLR_LATENT` now defaults ON
  (`BAYES_CLR` '1'; '0' fits the old ALR latent for research). It is a
  likelihood change, so the next production build must refit, and that
  build must pass the refit gates below.
- **Trailing-Likud ramp** (46.3): merged but held OFF
  (`TRAIL_RAMP_ON = False`). It passed as an increment on CLR on the s.43
  harness (G1). On the fidelity harness (G2) the set lost the eve pooled
  threshold Brier, CLR alone did not, and the plan drops the ramp when
  fidelity reverses only the ramp.

Base: main 804ff2d. Every table below uses 3 seeds pooled, the shipped
list mask, and lists median / mean MAE / 90% coverage / threshold Brier /
interval score.

**Merge.** The fidelity patch went in without its ABLATIONS Arab-arms
hunk, which 804ff2d already carries. CLR was reconciled with fidelity as
follows:
- Caches: one convention for `HARNESS_CACHE_DIR`, a name under
  data/processed or a path (`resolve_cache`).
- Signature: every posterior `load_or_fit` writes carries its components,
  observation count and latent. Legacy caches are checked on latent width
  (ALR "z" has B-1 columns, CLR "zc" has B), and a cache of the other latent
  raises.
- Write guard: a fit whose latent differs from the shared cache's
  (`SHARED_CACHE_LATENT = "clr"`) cannot write into
  data/processed/harness_cache.
- Outputs: they go to `HARNESS_OUT_DIR`. CLR's filename suffixes are
  dropped.
- Refit arms: layer `posterior` loads them through the same signature
  check. A stale or missing arm cache skips the arm and does not stop the
  run.
- `build_harness_cache.py` builds through `harness_frame` /
  `harness_prepare` / `load_or_fit`, so it can build fidelity windows.

The ramp went in by hand at the tail of `trailing_likud_params`. Other
changes:
- New arms: `alr_latent` (the ALR fidelity cache), `clr_latent` (the s.43
  windows), `tramp_m` and its sensitivity variants, `trail_cliff` and
  `clr_tramp_m`. Since 15 Oct the older trail arms spell out the cliff
  they were graded with (`_CLIFF`). Eve ablation rows record `trail_frac`.
- `validate_threshold`: in non-fidelity mode, rewriting the committed
  model_validation_threshold.csv now needs THRESHOLD_WRITE=1, so the
  arab_tab fix cannot silently move the new-straddler LOO inputs. The file
  itself was not regenerated.
- `bayes_model.diagnostics()` now includes the endpoint shares.
- `main()` refits with the gates. It fits the ALR holdout beside CLR's,
  allows one reseed, falls back to ALR, and writes `latent` and
  `refit_gates` to fit_summary.json.
- `registration_scenarios` writes `trail_weight` to fit_summary.json
  (None under the cliff).

**Reproduction checks.** Each of these passed exactly:
- With the flags off, the s.43 baseline at eve, D-7 and D-21.
- The clr_latent arm on harness_cache_clr reproduces round three: eve
  1.468/1.613/.980/.0425/9.418, D-7 1.516/1.634/.990/.0426/9.493, D-21
  1.773/1.827/.977/.0568/10.301.
- tramp_m reproduces eve 1.5323/1.6588/.9696/.0478/9.5967.
- The flipped code, run with the pre-round-three settings spelled out,
  reproduces G1.
- At the production seed, 2026 `project()` with BAYES_CLR=0 is
  bit-identical to 804ff2d.

**G1: the s.43 harness.** ALR shared cache; CLR via the posterior arm.

| horizon | shipped | clr_latent | tramp_m | clr_tramp_m |
|---|---|---|---|---|
| eve | 1.558/1.723/.970/.0496/9.614 | 1.468/1.613/.980/.0425/9.418 | 1.532/1.659/.970/.0478/9.597 | 1.399/1.565/.980/.0423/9.428 |
| D-7 | 1.569/1.702/.986/.0480/9.534 | 1.516/1.634/.990/.0426/9.493 | 1.555/1.681/.986/.0479/9.512 | 1.510/1.611/.990/.0425/9.469 |
| D-21 | 1.803/1.891/.972/.0618/10.140 | 1.773/1.827/.977/.0568/10.301 | 1.780/1.865/.972/.0600/10.094 | 1.726/1.789/.977/.0552/10.259 |

- **clr_tramp_m vs shipped.** At eve it wins all four metrics, coverage
  goes up .010, and the folds are 4W/4T/0L (|d|<0.1 counts as a tie). Seed
  deltas: -.157/-.144/-.176. D-7 wins all four. D-21 wins median, mean,
  Brier and coverage but loses the interval score (+.119); one lost metric
  is not a contradiction.
- **The ramp as an increment on CLR (clr_tramp_m vs clr_latent).** At eve:
  median -.069, mean -.048, Brier -.0002, interval +.010, coverage equal;
  folds 2W/6T/0L (2019s -.367, 2020 -.185), so it passes the fold route.
  D-7 wins all four (folds 1/7/0); D-21 wins all four (2/6/0).
- **Eve trail weight by fold.** Under clr_tramp_m: 2015 1.00, 2019a .90,
  2019s .66, 2020 .39, the rest 0. Under the cliff: 1/1/1/0.

**G2: fidelity windows.** Shipped and tramp_m use the ALR fidelity cache;
the CLR arms use the new CLR-fidelity cache.

| horizon | shipped | clr_latent | tramp_m | clr_tramp_m |
|---|---|---|---|---|
| eve | 1.591/1.683/.981/.0475/9.323 | 1.509/1.628/.981/.0474/9.280 | 1.512/1.615/.981/.0480/9.313 | 1.432/1.577/.981/.0480/9.257 |
| D-7 | 1.542/1.674/.990/.0498/9.462 | 1.520/1.649/.990/.0492/9.430 | 1.520/1.655/.990/.0496/9.442 | 1.503/1.630/.990/.0491/9.407 |
| D-21 | 1.676/1.830/.973/.0576/9.977 | 1.619/1.776/.990/.0542/9.622 | 1.643/1.792/.973/.0566/9.919 | 1.578/1.732/.990/.0530/9.545 |

- **The gate.** The set must not lose the eve pooled median or Brier and
  must not lose coverage.
  - clr_tramp_m: median -.160 and coverage equal, but Brier .0475 -> .0480,
    worse in all 3 seeds (+.0004/+.0010/+.0003).
  - clr_latent alone: Brier -.00003 (seeds -.0002/+.0005/-.0003); median
    -.082, folds 3W/5T/0L; wins all four pooled metrics at eve; coverage
    equal.
  - The Brier cost is the ramp's: +.0005 in every seed, both as tramp_m vs
    shipped and as clr_tramp_m vs clr_latent. It comes from 2019s (+.0038)
    and 2020. On the s.43 windows the ramp's Brier gain came from 2020
    (-.0157), the window fidelity rebuilt.
  - Decision: per the plan, the ramp is dropped and CLR ships.
- **What the ramp still does on fidelity.** Apart from Brier it wins
  everywhere: eve median -.078 (2W/6T/0L), mean -.052, interval -.023;
  D-7 and D-21 win all four metrics. The continuity argument (no 0.5-seat
  cliff) is untouched. Re-opening it is an owner override or a ramp
  recalibrated on the fidelity record.
- **CLR on fidelity at the horizons.** D-7 wins all four metrics (folds
  1W/5T/2L; 2019a +.119, 2020 +.111). D-21 wins all four, coverage rises
  .973 -> .990, and the interval score falls 9.977 -> 9.622. The D-21
  interval caveat from the s.43 harness (2019s Yamina) does not survive
  fidelity.

**Restated baseline: the new yardstick.** These are the code defaults
(CLR, cliff, fidelity windows) on harness_cache_clr_fidelity, which stands
in for the shared cache until the owner moves it. 3 seeds, own mask:

| horizon | median | mean | coverage | Brier | interval |
|---|---|---|---|---|---|
| eve | 1.509 | 1.628 | .981 | .0474 | 9.280 |
| D-7 | 1.520 | 1.649 | .990 | .0492 | 9.430 |
| D-21 | 1.619 | 1.776 | .990 | .0542 | 9.622 |

nstrad_regrade and sector_stream_single_division must be rebased on these
numbers.
- **Layer checks on this baseline.**
  - no_trail loses every metric (median +.074, coverage -.011, Brier
    +.0053), so the trail layer stays.
  - no_nstrad: median -.035, but Brier +.0047 and interval +.009, so the
    new-straddler layer stays.
- **Width grid** (seed-independent):

  | width | coverage | MAE | Brier | interval |
  |---|---|---|---|---|
  | 0.6 | .960 | 1.609 | .043 | 8.773 |
  | 0.7 | .972 | 1.616 | .044 | 8.832 |
  | 0.8 | .981 | 1.622 | .046 | 9.037 |
  | 0.9 (shipped) | .981 | 1.626 | .047 | 9.302 |
  | 1.0 | .981 | 1.630 | .049 | 9.450 |
  | 1.1 | .990 | 1.635 | .050 | 9.896 |

  Every LOO fold picks 0.6 or 0.7. Under CLR on fidelity the intervals are
  wider than they need to be. RESID_SCALE is not changed here; that is a
  separate calibration candidate.

**CLR-fidelity caches** (data/processed/harness_cache_clr_fidelity in the
combine worktree).
- **What was fitted.** 16 windows differ from the shipped data and were
  refitted: 2015 D-21, and eve, D-7 and D-21 of 2019a, 2019s, 2020, 2021
  and 2022. Settings: BAYES_CLR=1, HARNESS_FIDELITY=1, eve 600/600,
  horizons 400/400, 185-1111 s each on 4 queues.
- **What was reused.** The other 8 windows (2009 and 2013 at all three
  horizons, 2015 eve and D-7) have identical y, blocks, weeks and
  components, so they are links to harness_cache_clr. The judge counted
  19 differing windows; the data check finds 16. The 10 Oct CLR caches
  that were reused without a refit are therefore replaced wherever the
  data differ, and remain only in those 8 identical windows.
- **Diagnostics.** 0 divergences, except 2020 D-7, which has 1, as the ALR
  fidelity fit does. Endpoint-share r-hat is at most 1.01 in all 24. The
  2021 D-21 bimodality (The Israelis) is gone, because fidelity drops that
  list as a phantom.
- **sigma_g.** At harness draw counts, sigma_g mixes poorly under both
  latents: r-hat 1.07-1.79 in the CLR caches and 1.10-1.65 in the ALR
  caches checked. The judge's 2022 D-21 sigma_g r-hat of 1.29 is one case.
  This predates CLR. The projection reads endpoint shares and tau, and
  those mix.

**2026 refits** (scratch only; 804ff2d data: 232 polls, 2,867
observations, 21 lists). m3_idata.nc, fitted 14 Oct, predates the rows
804ff2d added (2,861 observations), so both latents were refitted on the
same data. Fits are 800/800:

| fit | divergences | max r-hat | min ESS | holdout median error |
|---|---|---|---|---|
| ALR | 0 | 1.02 (endpoint shares 1.023 unrounded) | 305 | 0.619 |
| CLR, NUTS seed 20261027 | 0 | 1.04 (s_obs) | 98 | 0.613 |
| CLR, reseed 20261028 | 0 | 1.01 | 395 | 0.613 |

The first CLR fit fails the r-hat and ESS gates. The reseed passes all
four gates, which is the reseed path main() now takes. The 14 Oct
production fit had min ESS 261, so the ALR fallback sits close to the ESS
gate itself.

**2026 effect** (production chain: registration mixture ->
official_forecast -> government_formation, at seed offsets +0/+1/+2).
Shipped means the ALR refit with the cliff; combined means the CLR reseed
with the cliff, which is what ships.

| | shipped | combined | CLR + ramp (held) |
|---|---|---|---|
| P(NB>=61) | 14.4 / 13.1 / 13.5 | 13.3 / 13.3 / 13.7 | 13.4 / 13.6 / 13.8 |
| change bloc alone | 8.3 / 8.5 / 8.5 | 8.6 / 8.3 / 8.6 | 8.4 / 8.2 / 8.5 |
| with Ra'am | 27.6 / 28.9 / 28.1 | 28.1 / 28.4 / 28.0 | 27.4 / 27.9 / 27.0 |
| neither | 57.9 / 58.0 / 58.4 | 58.6 / 58.3 / 58.3 | 59.2 / 58.5 / 59.2 |
| Likud central | 26 / 25 / 26 | 26 / 26 / 26 | 25 / 25 / 24 |
| Otzma pass | .771 / .762 / .766 | .768 / .764 / .768 | .834 / .835 / .840 |
| RZP-Zehut pass | .544 / .536 / .537 | .529 / .534 / .540 | .595 / .600 / .605 |
| Ra'am pass | .751 / .762 / .760 | .764 / .778 / .768 | same as combined |
| Likud margin over Yashar | +0.02 / +0.04 / -0.10 | +0.01 / -0.05 / +0.05 | w .66 / .68 / .65 |

- **Central seats.** Combined gives the same seats at all three seeds:
  Likud 26, Yashar 23, Together 11, UTJ 9, Shas 9, Democrats 9, JL 9, YB 9,
  Otzma 6, Ra'am 5, RZP-Zehut 4. Shipped differs at one seed (Likud 25 and
  Together 12 at +1).
- **Latents.** Tzomet Beit Yisrael (the frozen ALR reference) moves from
  0.595% to 0.339%, toward its 0.30% polls. Every other latent stays
  within 0.04 pp.
- **Summary.** P(NB>=61) moves within seed noise (mean 13.7 -> 13.4).
- **PM.** Repeat election .450/.455/.452 -> .455/.454/.454; Eisenkot
  .218/.221/.221 -> .220/.221/.220.
- **Data versus latent.** The 15 Oct headline of 14.5 was the old
  posterior on older data. The ALR refit on 804ff2d data gives 14.4 at the
  production seed, so the data change accounts for -0.1 at that seed and
  the latent for the rest.

**Production refit needed.**
1. Run `python src/bayes_model.py` once (BAYES_CLR unset). It refits CLR at
   800/800 with the 14-day holdouts for both latents, checks the refit
   gates, takes one reseed (SEED + 1) if they fail, and falls back to ALR
   if the reseed fails too. It overwrites m3_idata.nc and fit_summary.json,
   which records `latent` and `refit_gates`.
2. Then run registration_scenarios, official_forecast,
   government_formation and build_site, as for any build.
3. At today's data the default seed fails and the reseed passes, as above.

**Owner steps.**
1. The other session must commit or stash its own uncommitted project()
   hook (project.last_shares / last_pairs) before this lands. This session
   never touched it, launch.json or targeting_* files.
2. Move the caches:
   - data/processed/harness_cache (ALR, s.43 windows) ->
     harness_cache_alr. The legacy run is HARNESS_FIDELITY=0 BAYES_CLR=0
     HARNESS_CACHE_DIR=harness_cache_alr.
   - .claude/worktrees/wf_afb7b088-248-1/.../harness_cache_fidelity ->
     data/processed/harness_cache_alr_fidelity, the `alr_latent` arm.
   - This worktree's harness_cache_clr_fidelity (resolve its 8 links into
     files) -> data/processed/harness_cache.
   - Keep harness_cache_clr from wf_386865e9-189-1.
3. Until step 2 is done, a default harness run stops on the latent check.
   It does not grade CLR code against ALR posteriors.
4. Any published accuracy figure must name its harness: s.43, or fidelity
   (restated).

**Not done here.**
- D-56 under CLR. CLR D-56 fidelity caches do not exist yet; nstrad_regrade
  needs them.
- Entry-anchored start states for late entrants, a separate refit
  candidate.
- A RESID_SCALE recalibration (see the width grid).
- The 8-seed stability and gate-shift reruns, which only matter if the ramp
  is switched on.

### 46.1 Harness ballot fidelity and the Arab term on the split 2021 ballot (15 Oct)

**Why.** The eight-cycle harness built each past window from every poll id
it found, so it graded lists that were not on the ballot and fused lists
that were. The one that matters for s.43: five composite polls of 1-3
February 2021 measured the Joint List and Ra'am as one list, `merge_blocks`
fused the two into a single latent block, and the 2021 Arab family was
graded as one 10-seat list - the Arab turnout term's only ungraded fold
(s.43 (i)). Ra'am, the 2021 threshold case, was never scored.

**What was built (behind `HARNESS_FIDELITY`, merged OFF and flipped ON
at the round-three restatement; production is untouched -
`prepare_data(drop_absorbed=True)` is the default - and the OFF harness
reproduces the s.43 baseline to the last digit).**
- `drop_unfiled` (validate_bayes): from the filing deadline (D-47) + 3
  days, the ballot is read from the lists polled after deadline + 2, using
  only polls with fieldwork_end <= as-of (no look-ahead). An id spanning two
  ballot lists is dropped together with the rest of that poll's
  observation of the blocks it fed (no partial sums); an id with no
  component on the ballot is dropped. Dropped per window: 2015 Likud+YB
  (D-21); 2019a Joint List, Zionist Union, Hatnuah; 2019s New Right, Jewish
  Home+National Union, Hadash-Ta'al, Balad+Ra'am, Kulanu; 2020 the three
  Jewish Home+Otzma composites (+22 same-poll rows), Greens; 2021 Joint
  List+Ra'am, Labor+Meretz, Gesher+Labor+Meretz, Israelis, Tnufa, Gesher,
  Jewish Home, Derekh Eretz; 2022 Joint List, Yamina, Zionist Spirit, New
  Hope, Otzma. 2009 and 2013 are unchanged (Gil and the Greens 2009 kept).
- `DECOMP_FIDELITY`: 2020 Yamina = JH+NU+New Right, URWP = JH+NU; 2021
  Yesh Atid-Telem = Telem+Yesh Atid.
- ABSORBED_IDS (Zehut, NEP) are 2026 identities: kept in 2019a and 2021;
  Zehut 2019s leaves the ballot on its 29 Aug 2019 withdrawal (`WITHDRAWALS`).
- Cache safety (`load_or_fit`): each fidelity posterior carries its
  component list and observation count; a mismatch raises. A fidelity run
  that scores fewer than eight cycles exits.
- (The Arab ablation arms spelling out k and the intercept were found
  here too; main already carries that fix as 804ff2d, so this hunk was
  dropped at the merge.)
- validate_threshold: had raised KeyError('arab_tab') on main since the
  s.43 ship; fixed. Under fidelity it grades on CEC vote shares
  (data/ran_vote_shares.csv, every straddler that ran and failed included,
  each row cited), passed = seats > 0, a `ran` flag, D-56/D-21 only
  (THRESHOLD_HORIZONS), layer-off base run explicit; output goes to
  HARNESS_OUT_DIR so the shipped new-straddler parameters are not touched.
- harness_compare reads HARNESS_OUT_DIR.

**Caches.** data/processed/harness_cache_fidelity: 22 posteriors refitted
(eve 600/600, D-21/D-7 400/400, same seeds; 2015 D-21; 2019a, 2019s, 2020,
2021 and 2022 at eve/D-7/D-21; 2019s, 2020, 2021 at D-56) by the
interrupted first attempt (03:20-04:54 15 Oct, parallel); the other ten are
links to the shared cache after checking that the fidelity data equal the
shipped data. All 32 checked against this code before use (components and
observation count); 0 divergences except 2020 D-7 (1). No fit was needed
in this session. The shared harness_cache is untouched.

**Restated baseline under fidelity** (3 seeds, shipped configuration, its
own mask; the list set differs, so these replace rather than compare with
the s.43 numbers):

| horizon | median MAE | mean MAE | coverage | Brier | interval |
|---|---|---|---|---|---|
| eve | 1.558 -> 1.591 | 1.723 -> 1.683 | .970 -> .981 | .0496 -> .0475 | 9.614 -> 9.323 |
| D-7 | 1.569 -> 1.542 | 1.702 -> 1.674 | .986 -> .990 | .0480 -> .0498 | 9.534 -> 9.462 |
| D-21 | 1.803 -> 1.676 | 1.891 -> 1.830 | .972 -> .973 | .0618 -> .0576 | 10.140 -> 9.977 |

Eve median by fold, old -> fidelity: 2019a 1.95 -> 2.43 (Zehut back:
3.5 projected, 0 won), 2019s 1.30 -> 1.40, 2020 0.78 -> 0.89, 2021 2.47 ->
2.05, other four unchanged. D-21: 2015 1.53 -> 1.24, 2019a 2.05 -> 2.26,
2019s 1.60 -> 1.27, 2020 0.81 -> 0.70, 2021 2.97 -> 2.52, 2022 1.13 ->
1.08. As the evidence skeptic predicted, the eve median rises (Zehut), the
horizons fall less than the proposal's "~1.6".

**The Arab term on the split 2021 ballot.** 2021 Arab family error (mean
projected - actual seats, eve, shipped regB): merged block +3.05, split
-0.15 (Joint List 8.5 vs 6, Ra'am 1.4 vs 4). Pooled re-grade, 3 seeds,
delta = arm - shipped regB (median / mean / Brier / interval; coverage
equal unless noted):

| horizon | arab_e1_prev (old harness) | arab_e1_prev (fidelity) | arab_turnA (old) | arab_turnA (fidelity) |
|---|---|---|---|---|
| eve | +.072 / +.012 / +.0012 / +.049 | +.093 / +.013 / +.0011 / +.039 | +.003 / -.014 / +.0022 / +.004 | -.018 / -.005 / +.0032 / +.061 |
| D-7 | +.070 / +.022 / +.0013 / +.084 | +.114 / +.021 / +.0012 / +.084 | -.015 / -.026 / +.0017 / +.017 | -.039 / -.021 / +.0032 / +.063 |
| D-21 | +.024 / +.035 / +.0013 / +.123 | +.065 / +.024 / +.0014 / +.151 | -.068 / -.009 / +.0012 / +.161 (cov -.007) | -.071 / -.022 / +.0026 / +.193 (cov -.003) |

- regB still wins every pooled metric against the previous harness default
  at every horizon, by more than before; the s.43 ship stands. The 2021
  fold is a tie (eve +0.048 for e1_prev, D-7 and D-21 0.000). 2015 is still
  regB's one fold loss beyond noise (-0.121 for e1_prev), so it remains a
  pooled-route ship.
- Production's previous form (turnA, k = 1) now wins point accuracy at every
  horizon (2021 folds -0.02 / -0.33 / -0.17) but loses Brier and interval
  score at all three and coverage at D-21; it does not pass the rule
  against regB and regB does not dominate it. No production change.

**Other layers on the fidelity baseline (3 seeds).** Trailing-Likud (half,
satellite-sourced): switching it off loses median / mean / Brier at eve
(+.017 / +.042 / +.0051, coverage -.011), D-7 (+.078 / +.107 / +.0044)
and D-21 (+.096 / +.090; Brier -.0003, interval -.108); full strength is
worse than half at D-7 and D-21. Kept. New-straddler layer: off is
better on median at the eve (-.019) and worse at D-7 (+.019) and D-21
(+.089); on wins Brier at all three (.0051 / .0048 / .0023). Kept.

**Straddler record on CEC vote shares (D-56/D-21, layer off, diagnostic).**
First-cycle straddlers that ran: n 11, mean drift -0.42 pp (sd 1.72; D-21
-0.04, n 7; D-56 -1.09, n 4); pass rate 0.27 vs mean p_pass 0.47. The
shipped record (seat-implied shares, failed lists at 0%, non-runners
included) gives -1.68 (sd 2.56, n 11). The -1.6 pp production constant is
mostly the zero-share censoring the s.41 note flagged. It is NOT changed
here: re-measuring it is a separate candidate, which must re-grade the
layer LOO with an explicit layer-off base. Straddler Brier, layer off ->
on: D-21 .198 -> .190, D-56 .253 -> .222. Ra'am 2021 now enters the record
as a D-21 straddler (projected 3.16%, won 3.79%, p_pass .25).

**Not established.** The registered surplus agreements (item 4) and the
common list set for the simple-vs-Bayes benchmark (item 6) were not built.
D-56 was not re-graded (its fidelity caches exist for 2019s, 2020 and
2021). At 2021 D-56 Ra'am has no separate poll and its 4 seats are not
scored. Surplus pairs are applied at D-21/D-7 although signed ~D-11 (mild
look-ahead, as before). The 2026 forecast is unchanged by construction.

**Recommendation (adopted at the round-three restatement, 46).** The
fidelity windows are the grading harness: `HARNESS_FIDELITY` now defaults
ON, and the shared cache becomes the CLR-on-fidelity set, as the owner
step in 46 describes. Future candidates grade against the restated
baseline in 46. No production change.

### 46.2 The centred-log-ratio latent (clr_latent; shipped)

**The defect.** `fit()` modelled B-1 random walks against the LAST latent
block, an additive log-ratio (ALR) latent. That block had no z0, tau or
steps of its own, so it could move only when every other list drifted in
unison. `prepare_data` orders blocks by first appearance, so the frozen
list is always the newest one. Examples:
- 2021's RZP-Otzma-Noam: eve latent 0.85 seats against 4.8 polled in the
  final two weeks; it won 6.
- 2020's Otzma composite: 3.84 against 1.99.
- 2013 Hatnuah at D-21: 1.96 against 10.9.

The misfit lands in that list's s_obs, and renormalisation pushes every
other list the wrong way. In 2026 the frozen list is Tzomet Beit Yisrael.

**The change.** Under `CLR_LATENT`, every list gets z0 ~ N(log early -
mean, 0.5), its own tau ~ HalfNormal(0.06) and its own steps. The walk is
row-centred ("zc", weeks x B) and soft-maxed over all B lists. House
effects, drift, s_obs, lam, beta_u and the Student-t likelihood are
unchanged. `project()` and `validate_bayes.project_cycle()` dispatch on the
posterior ("zc" present) and project natively over B columns.
NEW_STRADDLER, TRAIL and the widths keep their ALR-record values, exactly
as graded.

**Ship case.** It ships on both routes at eve (s.43 harness): every pooled
metric wins in every seed (median deltas -.092/-.080/-.098), coverage
rises, and the folds are 2W/6T/0L.
- Without 2021, which carries -.60, eve still wins all four pooled metrics,
  and so does D-7.
- On the fidelity windows it wins all four metrics at eve, D-7 and D-21
  (46 above).
- D-21 caveat (s.43 harness only): the interval score went 10.140 ->
  10.301 because of 2019s Yamina. Yamina was a late entrant (29 July) with
  four weeks of polls at D-21, started at the 1% fill value under tau ~
  .06. Under ALR it was the reference and took the residual.
  - This mechanism is closed in 2026: filing closed at D-47 and every 2026
    list has 15+ weeks of polls.
  - On fidelity the D-21 interval improves.
- The D-21 gains on the s.43 harness are concentrated in the
  frozen-reference cycles. CLR is a correctness fix more than a broad D-21
  improvement.
- Follow-up: entry-anchored start states for late entrants, as its own
  refit candidate.

**Refit gates for every production build** (`REFIT_GATES`; checked in
`bayes_model.main`):
- 0 divergences.
- Max r-hat <= 1.02 over tau, sigma_g, sigma_f, s_obs AND the endpoint
  shares. diagnostics() did not check the shares before, and CLR's extra
  common-mode direction showed bimodal endpoints in two harness windows.
- Min bulk ESS >= 300.
- 14-day holdout median error no worse than the ALR fit on the same data.

One reseed is allowed. If the reseed also fails, that build ships ALR and
fit_summary.json records why.

### 46.3 Trailing-Likud ramp (trail_ramp, tramp_m; merged, held OFF)

**What it does.** It replaces the 0.5-seat cliff on the Monte-Carlo mean
margin with a weight w = 1 at margin <= -1.0 seats, 0 at >= +2.0, linear
in between. The beat's mean and sd are re-estimated on the record with the
same weight: production mu 5.58, sd 4.15 (the w-weighted full record,
n_eff 3.4); in the harness they are strict LOO per fold. Satellite
sourcing, the 0.5 scale, the 0.75 cap and the Amcha exclusion are
unchanged. Code: `bm.TRAIL_RAMP_ON` / `TRAIL_RAMP` / `trail_weight`;
harness `trail_mode 'ramp'`, `trail_lo`, `trail_wcal`, `trail_ramp_params`.
The variants tramp_d, tramp05_m, tramp05_d and tramp_m_cliffcal remain as
sensitivity arms.

**How it graded.**
- s.43 harness on ALR: wins every pooled metric at eve, D-7 and D-21 with
  coverage equal.
- As an increment on CLR: passes (G1).
- On the fidelity windows: loses the eve threshold Brier by .0005 in every
  seed, whether added on ALR or on CLR. The combine plan's G2 gate drops
  it.

**What remains true.** The cliff is discontinuous. With it, a poll move of
about half a seat across +0.5 swings Likud's central count 26 -> 23,
RZP-Zehut pass .545 -> .753 and P(NB>=61) by +1.1 pt. Today's margins
(+0.01 to -0.10 across seeds) sit inside that band. With the ramp at
today's margin (w ~ .66), the effect would be: Likud central 26 -> 25/25/24,
Otzma pass .77 -> .84, RZP-Zehut pass .53 -> .60, and P(NB>=61) +0.1 to
+0.3 pt.

**To turn it on.** Set `TRAIL_RAMP_ON = True` and mirror it in
`ALL_LAYERS` (trail_mode 'ramp', trail_lo -1.0, trail_wcal True). Change
the site copy from "the layer fires" to its weight; `trail_weight` is
already written. Then rerun the 8-seed stability and gate-shift checks.
That takes an owner override of the G2 gate, or a ramp recalibrated on the
fidelity record that does not lose Brier.

### 46.4 churn_abstain_record_gap: rejected (note for the post-election review)

`CHURN_SPLIT` sits in the certainty layer. That is a 2026-only judgment
layer no harness runs, and the candidate's own eve run with the flag on is
bit-identical. Such layers change only on cited post-filing evidence. This
candidate rested on a Goodman regression over 2013-2022 CEC locality
results, which is historical evidence. Its one 2026 item, N12 of 7 Sept,
is pre-filing, direction-only and was not used. The weaknesses:
- The voter-space inter-election gap was carried over to the mover-space
  campaign gap by an unvalidated typicality ratio (0.20-0.27).
- The Goodman fit is misspecified: abstention levels fall outside [0,1],
  NB loyalty is above 1, and the cross-bloc coefficients are negative.
- Its source panel belongs to the other session's untracked atlas.
- The effect (P(NB>=61) -0.4 pt, no central seat moves) is under half the
  seed-to-seed spread.

The flag code is not merged. For the review: the abstention-record gap
input is sensitive, re-measured 0.093 -> 0.020 on the atlas record, and
2021 -> 2022 is the extreme of six transitions. Re-open only if
post-filing polls give a sized bloc-differential turnout intention, with n
and fieldwork dates.

## 51. Sector family terms (15 Oct, D-12)

Two accuracy candidates for the sector family shocks, graded on the
restated round-three yardstick (s.46: CLR latent, ballot-fidelity windows,
shared CLR-fidelity cache, shipped list mask). Both flags default OFF.

### 51.1 Pre-registration (written before any harness run of these arms)

**Candidate A, `hared_e0` (the only haredi arm).** The haredi family mean
becomes the leave-one-cycle-out RAW (e0) family total,
`decompose(exclude_cycle)["family_e0"]["haredi"]`, in place of the e1 mean
(measured after the bloc swing is removed). The sd stays the LOO e1 sd.
Rationale as s.43 for the Arab term: the projection's bloc swing has mean
zero, so the NB over-poll that e1 strips out (+1.66 seats raw, on average)
is applied nowhere, and e1's extra -0.37 haredi seats have no counterpart.
Production: `HAREDI_FAMILY_FORM = "e0"` gives mean -0.980 (shipped e1
-1.352), sd 1.768. LOO e0 by fold: 2009 -1.06, 2013 -0.89, 2015 -1.25,
2019a -0.50, 2019s -1.08, 2020 -1.14, 2021 -1.02, 2022 -0.92 (e1: -1.41,
-1.05, -1.68, -0.92, -1.37, -1.56, -1.36, -1.47).

**No recency variant is registered.** Under leave-one-cycle-out, a "last
four cycles" window re-admits April 2019 (e0 -4.33) in exactly the four
recent folds (2019s-2022 would get -1.30 to -1.69, more negative than e0),
so the harness would grade a different object from production's -0.58,
which excludes April 2019 by construction. It is not graded and not
proposed.

**Candidate B, `arab_raam_split`.** The regB intercept keeps its family
total; only its allocation across the Arab lists changes.
- Lineages: a list containing a Ra'am id (raam, raam_taal, raam_balad) vs
  the other Arab lists of the same cycle.
- Shares: for each fold, over the split cycles of the decomposition record
  (two or more Arab rows, one of them Ra'am) without the graded cycle,
  m_R and m_O = each lineage's mean raw error; u = max(0, -m);
  s_R = u_R / (u_R + u_O), falling back to base share when both are 0.
- Allocation: Ra'am columns take s_R of the intercept, the other Arab
  columns 1 - s_R, each split by base share; the mass still comes from the
  non-Arab lists by base share. The turnout term is unchanged
  (base-proportional). Windows with one Arab column (2009, 2013 and 2015 as
  merged in the harness, 2019s, 2020) are unchanged by construction.
- Record (computed before grading): Ra'am lineage 2013 -0.45, 2019a 0.00,
  2021 -2.29, 2022 -0.57; the other lists +0.18, +1.22, +2.29, -1.00.
  m_O > 0 in every fold and in the full sample, so s_R = 1.0 everywhere:
  the arm places the whole intercept on Ra'am wherever Ra'am runs
  separately (harness: 2019a Ra'am-Balad, 2021, 2022; production: Ra'am).
- Turnout-ratio allocation: support test registered and run on the record
  first. Per-lineage regression of raw error on the ratio-implied error
  over the four split cycles; "supported" iff |k_O - k_R| > 2 se and every
  strict-LOO fold keeps at least three cycles per lineage. Result: k_R
  -0.18 (se 0.87), k_O +0.83 (se 0.16), z = 1.14, and the 2021 fold keeps
  two cycles. Not supported, so not implemented and not graded.

**Grading.** `--fixed` mask throughout. Eve: 3 seeds (offsets 0/100/200)
pooled. D-7 and D-21: seed offset 0.

**Decision rule** (s.36 / s.46 shipping rule, made explicit):
1. Eve passes by the FOLD route if no fold's median-MAE delta (3-seed
   mean) is +0.1 or worse and the pooled median MAE falls; or by the
   POOLED route if median MAE, mean MAE, threshold Brier and interval
   score all fall and coverage does not move away from 0.90 (the baseline
   is above 0.90, so coverage may not rise).
2. D-7 and D-21 must not contradict: an arm contradicts at a horizon if it
   loses two or more of the four pooled metrics there, or moves coverage
   away from 0.90.
3. B only (three split windows, two Ra'am cycles of record): additionally
   no pooled eve metric may get worse beyond rounding (0.0005 MAE and
   interval, 0.00005 Brier). If it ships, it ships as disclosed judgement.
4. A and B are graded separately against the shipped baseline. If both
   pass, the pair is run together once on the same seeds and ships only if
   the pair passes too.
5. The 2026 effect is reported for each arm whatever the verdict.

### 51.2 Results (3 seeds pooled at eve; seed offset 0 at D-7 / D-21; fixed mask)

The flags-off run reproduces the restated baseline exactly. With the flags
off, production `project()` is bit-identical to the pre-change code at the
production seed (same seat-draw hash).

| horizon | arm | median MAE | mean MAE | coverage | Brier | interval |
|---|---|---|---|---|---|---|
| eve | shipped | 1.509 | 1.628 | .981 | .0474 | 9.280 |
| eve | hared_e0 | 1.504 (-.006) | 1.626 (-.002) | .981 | .0472 (-.0002) | 9.277 (-.003) |
| eve | arab_raam_split | 1.523 (+.014) | 1.605 (-.024) | .981 | .0453 (-.0021) | 9.286 (+.006) |
| D-7 | shipped | 1.495 | 1.650 | .990 | .0492 | 9.454 |
| D-7 | hared_e0 | -.013 | -.001 | = | -.0003 | -.020 |
| D-7 | arab_raam_split | +.018 | -.024 | = | -.0021 | +.001 |
| D-21 | shipped | 1.620 | 1.773 | .990 | .0538 | 9.655 |
| D-21 | hared_e0 | -.010 | +.001 | = | -.0002 | -.051 |
| D-21 | arab_raam_split | .000 | -.024 | = | -.0019 | +.045 |

**hared_e0: PASSES the pre-registered rule.**
- Eve passes both routes. Pooled, it wins all four metrics with coverage
  equal. Fold deltas (3-seed mean median MAE): 2015 -.030, 2019a -.071,
  2019s +.083, 2021 +.024, 2022 -.051, three folds 0. That is 0W/8T/0L,
  with no fold loss and a lower pooled median.
- D-7 wins all four metrics. D-21 loses only mean MAE (+.0009), which is
  not a contradiction.
- **Size: at the noise floor.**
  - Per seed, median MAE is +.009 / +.012 / -.038 and the interval score
    +.001 / -.013 / +.003. The pooled wins on those two metrics each come
    from one seed.
  - Brier (-.0001 / -.0002 / -.0002) and mean MAE (-.001 / -.003 / -.002)
    win in every seed.
- **List level** (eve, 3 seeds; error = projected mean - actual):
  - The haredi family's mean error moves from +0.05 to -0.16. On this
    harness the e1 mean was already about unbiased at the family level.
  - UTJ improves: error +0.55 -> +0.36, MAE 0.95 -> 0.85.
  - Shas gets worse: error -0.46 -> -0.68, MAE 0.98 -> 1.06.
  - The harness rewards a smaller haredi push only because base-share
    allocation over-feeds UTJ. That is the desk's third arm (allocation
    by each list's own record, Shas about 90%), which was not registered
    here.
- Post-hoc robustness (three more eve seeds, not part of the rule): see
  51.4. Over six seeds the median-MAE gain vanishes (+.0009).

**arab_raam_split: FAILS the pre-registered rule.**
- Eve fold route: 2022 loses +0.205, beyond noise.
- Eve pooled route: loses median MAE (+.014) and the interval score
  (+.006).
- B's extra no-loss condition fails.
- D-7 contradicts: it loses median MAE and the interval score.
- **What it does well.**
  - Brier -.0021 and mean MAE -.024 at eve, the same in all three seeds
    (Brier -.0021 / -.0021 / -.0022). It is about ten times A's Brier gain.
  - The Ra'am lineage carries it. Over 2019a / 2021 / 2022 at eve, Ra'am's
    threshold Brier falls .329 -> .239 and its mean MAE 2.01 -> 1.39
    (2021 Ra'am 1.44 -> 1.67 seats against 4; 2019a Ra'am-Balad
    2.56 -> 3.69 against 4).
- **Why it fails.** Moving the whole intercept off the other Arab lists
  pushes the 2022 Hadash-Ta'al straddler toward the threshold:
  - pass .54 -> .50, median 4 -> 1.3 seat-equivalents across seeds,
    against 5 won;
  - the other Arab lists' Brier rises .067 -> .075.
- **Verdict.** With two Ra'am cycles of record, this is a real but
  unbalanced gain. It does not ship.

**The pair (sector_both)** was run alongside for information. Rule 4 does
not apply because B fails. Eve: median +.004, mean -.026, Brier -.0023,
interval +.003. That fails the pooled route.

**Turnout-ratio allocation:** not supported by the record (51.1), so it
was not graded.

**error_decomposition step 4.** The family means and sds (e1 and e0) are
fixed in the per-cycle loop, step 2, before the anchors (step 3) and the
residual leader correction (step 4). The non-unique-index bug being fixed
separately in step 4 moves only `resid_base` / `resid_slope`. So neither
arm's family mean depends on it, but the harness baseline will move when
that fix lands, and these deltas should be re-checked then.

### 51.3 2026 effect (registration mixture -> official forecast -> formation; outputs in scratch)

Two frozen posteriors, at seed offsets +0 / +1 / +2:
- **CLR reseed** (the s.46 fit that passes the refit gates, which the next
  build ships).
- **14 Oct ALR** (the posterior behind the published build).

Main's m3_idata.nc was rewritten in place by another session at 18:08 and
was briefly 0 bytes. It was restored at 18:09 with the same hash as the
frozen ALR copy.

**CLR reseed:**

| | shipped | hared_e0 | arab_raam_split |
|---|---|---|---|
| Shas mean (central) | 8.93 / 8.87 / 8.87 (9) | 8.73 / 8.68 / 8.66 (9) | 8.92 / 8.86 / 8.86 (9) |
| UTJ mean (central) | 8.75 / 8.72 / 8.74 (9) | 8.56 / 8.53 / 8.56 (8) | 8.74 / 8.71 / 8.73 (9) |
| JL mean (central), pass | 8.75 / 8.78 / 8.75 (9), .978 / .978 / .975 | 8.79 / 8.81 / 8.78 (9), .978 / .979 / .976 | 8.28 / 8.32 / 8.27 (8), .967 / .966 / .961 |
| Ra'am mean (central), pass | 4.73 / 4.82 / 4.76 (5), .764 / .778 / .768 | 4.76 / 4.84 / 4.78 (5), .767 / .780 / .770 | 5.34 / 5.40 / 5.35 (6), .829 / .838 / .829 |
| P(NB>=61) | 13.0 / 13.1 / 13.5 | 12.3 / 12.4 / 12.7 | 12.8 / 12.9 / 13.4 |
| change bloc alone | 8.6 / 8.4 / 8.6 | 9.0 / 8.7 / 9.2 | 8.3 / 8.3 / 8.4 |
| with Ra'am | 28.3 / 28.5 / 28.1 | 29.1 / 29.8 / 29.5 | 31.1 / 31.4 / 31.3 |
| neither | 58.8 / 58.4 / 58.4 | 58.5 / 57.9 / 57.9 | 56.2 / 55.7 / 55.3 |
| PM repeat / Eisenkot / Netanyahu | 45.5 / 22.1 / 19.5 (+0) | 45.4 / 22.6 / 19.0 (+0) | 45.2 / 22.6 / 19.2 (+0) |

**Central seats.**
- hared_e0: UTJ 9 -> 8 and Together 11 -> 12, at all three seeds. Every
  other list holds.
- arab_raam_split: the Joint List 9 -> 8 and Ra'am 5 -> 6, at all three
  seeds.

**14 Oct ALR, same seeds.**
- hared_e0: P(NB>=61) 14.2 / 13.2 / 13.4 -> 13.4 / 12.6 / 12.6. Shas+UTJ
  17.56 -> 17.17 at +0. UTJ central 9 -> 8.
- arab_raam_split: Ra'am pass .752 / .765 / .765 -> .820 / .827 / .828.
  With Ra'am 27.5 / 28.6 / 28.6 -> 30.6 / 31.7 / 31.2. JL 9 -> 8 and
  Ra'am 5 -> 6.

The shipped CLR row reproduces s.46's central seats and Ra'am pass
(.764 / .778 / .768) exactly. Its bloc probabilities differ from the s.46
table by 0.1-0.3 pt; these runs patch the seed of the registration and
formation modules only.

### 51.4 Post-hoc robustness (three more eve seeds; NOT part of the rule)

These were run after the verdicts above, because hared_e0's median-MAE
delta changed sign across the registered seeds. Offsets are 300, 400 and
500; the shipped pooled score on these seeds is 1.489 / 1.625 / .981 /
.0470 / 9.295.

**hared_e0.**
- On the three new seeds: median +.007, mean -.002, Brier -.0002,
  interval -.021.
- Over all six seeds: median +.0009, mean -.0023, Brier -.0002 (6/6
  seeds), interval -.012 (4/6 seeds); coverage equal.
- On six seeds it would fail by +.0009 of median MAE. Its eve pass rests on
  seed noise in the median. The consistent part is small: Brier and mean
  MAE win in every seed.
- Read it as harness-neutral, not as a measured accuracy gain.

**arab_raam_split.**
- Over six seeds: median +.0009, mean -.0237 (6/6), Brier -.0021 (6/6),
  interval +.003 (losses in 5/6). The 2022 fold is +0.103.
- The 2022 median loss is partly a coin flip: Hadash-Ta'al passes in about
  half the draws, and the new seeds show 0.000 there. The interval loss
  persists. The verdict does not change.

### 51.5 Recommendation

**hared_e0: ship, disclosed as a consistency correction that is neutral on
the harness.**
- It passes the pre-registered rule. Its case is the s.43 argument: with a
  zero-mean projected bloc swing, the e1 mean applies a bloc correction the
  projection never makes.
- The harness can neither confirm nor refute it beyond Brier and mean MAE
  gains of about .0002 and .002. The six-seed median is a tie.
- To ship: set `HAREDI_FAMILY_FORM = "e0"` and the mirror
  `ALL_LAYERS["haredi_mean"] = "e0"`, then rerun the production chain. The
  2026 effect is Shas+UTJ -0.4 seats, UTJ central 9 -> 8, Together
  11 -> 12, and P(NB>=61) -0.7 pt.
- The site's "haredi lists underpolled by 1.35 +/- 1.77" becomes
  0.98 +/- 1.77.
- The list-level result points to the better next candidate, the desk's
  third arm. Base-share allocation over-feeds UTJ (harness error +0.55)
  and under-feeds Shas (-0.46). An arm that allocates the family mean by
  each list's own LOO record, shrunk, should be pre-registered next.

**arab_raam_split: do not ship.**
- It fails the rule: the eve median and interval score, and a
  contradiction at D-7.
- It is the larger Brier gain of the two arms (-.0021 in every seed) and
  repairs Ra'am's threshold record (.329 -> .239). But putting the whole
  intercept on Ra'am starves the other Arab lists at the threshold (2022
  Hadash-Ta'al), and the interval score worsens.
- A softer allocation could be registered as its own candidate: a partial
  share such as the desk's two-thirds, or Ra'am's own LOO mean with the
  Joint List taking the remainder. The flag code stays, OFF.

Both flags remain OFF in this patch.
