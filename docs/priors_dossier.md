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

## 47. Seat-law fidelity (15 Oct, D-12)

**Why.** Desk SYS (data/processed/forecast_research/electoral_system.json)
and its verifier raised two seat-law challenges: (A) the harness's
historical surplus pairs are not the agreements registered with the CEC;
(B) s.81(a) sets the threshold at 3.25% of ALL valid votes, but every
simulated share vector sums to one over the modelled lists only. The
verifier added a larger instance of (B): official_forecast.allocate_central
renormalises the MEDIAN share vector, which sums to ~0.957 because medians
are not additive.

**Decision (15 Oct).** Part A is adopted as the harness instrument:
`HARNESS_REG_PAIRS` now defaults ON ('0' restores PAST_PAIRS), and arm
`past_pairs` grades the old instrument. Part B's code is kept, but
`simulate.THRESHOLD_ALL_VALID` stays OFF. With HARNESS_REG_PAIRS=0, every
harness number below reproduces the s.46 restated baseline exactly
(eve 1.509/1.628/.981/.0474/9.280; D-7 1.520/1.649/.990/.0492/9.430;
D-21 1.619/1.776/.990/.0542/9.622). Production is bit-identical.

### 47.1 Part A: the registered surplus agreements (instrument; adopted)

**The record.** `validate_model.REGISTERED_PAIRS`, sources in
`REGISTERED_PAIR_SOURCES`:

| cycle | registered agreements | source |
|---|---|---|
| 2009 | Labor-Meretz, Likud-YB, Hadash-Ra'am-Ta'al, UTJ-Shas, JH-NU, Kadima-Greens, Gil-Tzabar, Green Movement-Meimad-Yisrael Hazaka | CEC notice, Yalkut HaPirsumim 5912 (1 Feb 2009), via he.wikipedia 'הסכם עודפים' fn 34-35 and hamichlol fn 57 (same 8 pairs); Gil-Tzabar also JPost 28 Jan 2009 |
| 2013 | Labor-Yesh Atid, Likud Beytenu-JH, Hadash-Balad, UTJ-Shas, Kadima-Am Shalem, Dor-Social Justice, Hatnua-Meretz | CEC notice (he.wikipedia fn 36); the same seven in en.wikipedia |
| 2015 | ZU-Meretz, Likud-JH, UTJ-Shas, YB-Kulanu | CEC notice (he.wikipedia fn 37) |
| 2019a | Labor-Meretz, New Right-YB, Ra'am-Balad-Hadash-Ta'al, Likud-URWP, Shas-UTJ, Kulanu Haverim-Pirates | CEC notice (fn 38); JPost 585334: B&W signed none |
| 2019s | B&W-YB, Likud-Yamina, Labor-Gesher-Democratic Union, UTJ-Shas, Noam-Otzma | CEC notice (fn 39); JNS (B&W-YB) |
| 2020 | B&W-Labor-Gesher-Meretz, Likud-Yamina, UTJ-Shas | he.wikipedia (uncited) = Dayan Center, Bayan Oct 2020 |
| 2021 | Likud-RZ, B&W-New Economic, Yamina-New Hope, YA-YB, Labor-Meretz, UTJ-Shas | he.wikipedia (uncited); Times of Israel (Yamina-New Hope, YA-YB); Ynetnews B17bk9plu (B&W-NEP) |
| 2022 | YA-National Unity, Labor-Meretz, UTJ-Shas, Likud-RZ, Yesh Kivun-Pirates | he.wikipedia (uncited) = Kenig, IDI 63750 |

**Cross-check by reproduction** (`src/validate_seat_law.py`, new). The
statute (ss.81-82: threshold on all valid votes, integer quota, floor
seats, highest averages, pairs pooled only if both pass, inner split) in
exact arithmetic on the CEC final counts gives the official seats in
8/8 cycles with the registered pairs, 0 ties. The harness's own allocator
(`allocate_vector`) gives the same 8/8. The counts are in
data/cec_final_counts.csv (new; one row per list). 2015-2022 come from the
CEC station files with the outer envelopes (expc_20..25). 2009 and 2013
come from the CEC final results as tabulated by Wikipedia, since the
repo's 2013 file lacks the envelopes. The desk had checked 2015-2022 only.
The four pairs of two micro-lists (Gil-Tzabar, GM-Meimad-Yisrael Hazaka,
Kulanu Haverim-Pirates, Yesh Kivun-Pirates) are inert: both partners
fail. Noam-Otzma 2019s is inert too: Noam is not on the CEC count.

**What the old harness used.** PAST_PAIRS differs from the registered
list in 7 of 8 cycles (all but 2020). As run, the harness also dropped
every PAST_PAIRS id that DECOMP had renamed, because `pair_alias` was off.
Pairs actually pooled, before -> after (eve, D-7 and D-21 alike):

| | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 | total |
|---|---|---|---|---|---|---|---|---|---|
| PAST_PAIRS as run | 2 | 2 | 2 | 1 | 2 | 1 | 3 | 3 | 16 |
| registered, DECOMP-resolved | 4 | 5 | 4 | 5 | 4 | 3 | 6 | 4 | 35 |

Not applicable after the fix: pairs inside one merged harness block (2009
JH-NU and Hadash-Ra'am-Ta'al, 2013 Hadash-Balad), plus the inert micro
pairs above. On the official counts, the old pairs misallocate 10
list-seats: 2009 Kadima +1 / Labor -1 (new; Labor-Meretz missing), 2015
Likud +1 / Kulanu -1, 2019s UTJ +1 / B&W -1, and 2021 Likud +1, YA +1,
Meretz -1, New Hope -1. The registered pairs misallocate none.

**Seat-law error at perfect shares.** Feed the official votes,
aggregated to each eve window's columns, through the harness's seat law
and score them against the actual seats. MAE per graded list:

| pairs | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 | mean |
|---|---|---|---|---|---|---|---|---|---|
| PAST as run | .200 | .167 | .182 | 0 | .200 | 0 | .286 | 0 | .129 |
| registered | 0 | .167 | 0 | 0 | 0 | 0 | 0 | 0 | .021 |

The remaining 2013 error comes from the harness grading the three Arab
lists as one merged block, not from the pairs.

**Graded, 3 seeds pooled, shipped mask** (median / mean / coverage /
Brier / interval; central = MAE of the published central-count estimator,
`seat_mae_central`, new in the eve rows):

| horizon | PAST_PAIRS (s.46 baseline) | registered: THE RESTATED BASELINE | central |
|---|---|---|---|
| eve | 1.509/1.628/.981/.0474/9.280 | 1.496/1.626/.981/.0474/9.242 | 1.569 -> 1.519 |
| D-7 | 1.520/1.649/.990/.0492/9.430 | 1.518/1.648/.986/.0492/9.515 | 1.549 -> 1.583 |
| D-21 | 1.619/1.776/.990/.0542/9.622 | 1.592/1.789/.987/.0542/9.730 | 1.606 -> 1.614 |

- Eve median folds (|d|<0.1 tie): 1W/7T/0L. 2015 -.136; 2009 +.091 and
  2022 +.026 are ties. Seed deltas: -.012/+.012/-.040.
- D-7: 0W/8T/0L. D-21: 2W/5T/1L (2013 -.111, 2019s -.152; 2019a +.119).
- Brier cannot move: pairs act only among lists that passed.
- At D-7 and D-21 the interval score rises (+.085 and +.108) and coverage
  falls slightly (.990 -> .986/.987).
- The rebased code (default ON) reproduces the registered column at eve
  seed 0 (1.471/1.627), and past_pairs reproduces the old one
  (1.484/1.629).

**How much of the graded error was seat-law error.** At perfect shares
the old pairs cost 0.13 seat per list, about 8.5% of the eve median MAE.
As graded, swapping in the registered pairs moves the median MAE by -.013
at the eve (0.9%), -.003 at D-7 and -.026 at D-21. The pair effects are
±1-seat events, and under forecast error they offset as often as they
compound. The 2015, 2013 and 2019s folds gain; 2009 loses (Labor-Meretz
and Kadima-Greens, both true pairs).

**Why adopt it.** This is a correction of the measuring instrument, not a
model candidate, and the law decides it. The registered pairs are the only
set that reproduces the official allocations. Future candidates grade
against the restated column above. There is no 2026 effect: production
carries the 2026 agreements in SURPLUS_PAIRS.

**Not established.** Signing dates. All pairs are applied at D-21 too,
though most were signed in the last two to three weeks (s.67(b) deadline:
day 11), so the D-21 look-ahead noted in s.46.1 remains.

### 47.2 Part B: the threshold denominator (candidate; not shipped)

**Change** (`simulate.THRESHOLD_ALL_VALID`, `UNMODELLED_SHARE = 0.01`):
- Draws pass on sh x (1 - u) >= 3.25% in `bayes_model.project`,
  `simulate.simulate_core` and `validate_bayes.project_cycle`.
- The central count (`allocate_central`; harness `central_raw`) tests the
  UN-renormalised median x (1 - u). It no longer renormalises the median
  vector.
- The seat division among the passing lists (integer quota, d'Hondt on
  factions) is scale-invariant, so the Bader-Ofer quota needs no change.
  It is taken over the passing lists only, s.81(b).

**Choice of u = 0.01** (pre-registered before grading):
- (i) The observation layer reserves exactly 0.01 for unitemized lists
  in every seat-derived row (`implied_share_obs`). Every complete harness
  poll's observed shares sum to 0.990. Measured on the big lists, the
  2015-2022 latents sit 1.00-1.11% above the observed scale.
- (ii) CEC record of the vote outside each cycle's modelled set (eve
  window): 2015 1.53%, 2019a 0.81%, 2019s 0.97%, 2020 0.38%, 2021 0.68%,
  2022 1.50% (3.25%-era mean 0.98%). The 2%-era values are 2009 2.19% and
  2013 4.12% (`UNMODELLED_REC`).
- (iii) The desk's micro-list band: lists under 0.3% took 0.28-0.85%.
- Sensitivity arms: u = .005, the LOO record mean, and the realised value
  (oracle, diagnostic).

**Graded on the registered pairs** (reg_thr vs reg_pairs, 3 seeds):

| horizon | median | mean | Brier | interval | central | coverage | folds W/T/L |
|---|---|---|---|---|---|---|---|
| eve | +.001 | +.003 | +.0007 (.0474 -> .0482) | -.0001 | +.012 | = | 0/7/1 (2021 +.119) |
| D-7 | +.009 | +.003 | +.0008 | +.021 | +.006 | = | 0/8/0 |
| D-21 | +.038 | +.001 | +.0006 | +.020 | +.048 | = | 0/7/1 (2019a +.286) |

- It fails both routes at every horizon. The Brier loss sits in 6-7 of 8
  cycles, led by 2019a and 2021 (+.002 each).
- Every sensitivity arm loses Brier at every horizon: u = .005 (+.0004),
  LOO (+.0012/.0013/.0011), and even the realised u (oracle; +.0008).
- On the old pairs (thr_valid vs past pairs) the result is the same: eve
  Brier +.0007, D-21 median +.036.
- The draws' test carries all of the Brier and point-MAE change.
- The central fix alone (reg_central_raw) changes nothing at D-7 or D-21.
  At the eve it costs +.012 in one seed of 2019a: Ra'am-Balad's median
  falls under the line in the central count, and it passed with 3.33%.

**Why the law-correct test scores worse.** On the straddler record
(validate_threshold, fidelity windows, registered pairs; 24 lists within
-0.75/+1.5 pp of the line at D-21 and at D-7), 71% passed against a mean
p_pass of 52%. In the 0.5-0.75 bin, predicted .60-.62 passed .88-.90.
Mean drift was +0.25 to +0.30 pp. The stack already under-predicts
straddler survival. The extra 0.03 pp of strictness lowers each
straddler's p_pass by 0.2-1.3 pp, and straddler Brier rises .181 -> .184
(D-21) and .173 -> .176 (D-7). In 2026 the latent sits BELOW the observed
scale on the 13 big lists (by 2.6%), because the six micro columns hold
2.3% (medians) to 4.2% (means) of projected share. This agrees with the
verifier: the net sign of the denominator bias is not what the formal
argument says.

**2026 effect** (production chain on the linked 14 Oct posterior,
seed offsets +0/+1/+2; u = .01; outputs in scratch):
- P(NB>=61): 14.2/13.2/13.4 -> 14.2/13.3/13.4.
- Change bloc alone: 8.3/8.3/8.4 -> 8.6/8.4/8.6.
- With Ra'am: 27.5/28.6/28.6 -> 27.7/28.8/28.8.
- Neither: 58.3/58.2/58.0 -> 58.1/57.9/57.8.
- Pass probabilities: Ra'am .752/.765/.765 -> .745/.758/.759; RZP-Zehut
  .545/.541/.539 -> .536/.531/.532; Otzma .771 -> .766; Amcha .258 ->
  .254; Reservists .212 -> .209.
- PM (seed means): repeat election .455 -> .452, Eisenkot .219 -> .221,
  Netanyahu unchanged. At u = .0056 every effect is about half as large.
- Central seats are unchanged at all three seeds: Likud 26, Yashar 23,
  Together 11, Shas/UTJ/Democrats/YB/JL 9, Otzma 6, Ra'am 5, RZP-Zehut 4.
- The median vector sums to .9565/.9578/.9580. Renormalising lifts
  RZP-Zehut from 3.437% to 3.593%; the fix tests 3.403%. RZP-Zehut stays
  the closest list to a central flip, 0.15 pp above the line.

**Decision: not shipped, flag OFF.** The statute is clear, but the graded
stack is calibrated on the renormalised scale. That holds for the
new-straddler constant, which was measured on that pipeline, and for the
micro columns. Making the threshold law-exact on its own moves pass
probabilities in the direction the record already punishes. Re-open the
denominator together with two pieces of work: the straddler re-measurement
on CEC vote shares (s.46.1), and a candidate for the under-predicted
survival of established straddlers that this record shows (realised 71%
vs 52%). Only the joint change can be graded fairly. The central-count
renormalisation stays as shipped. It flips nothing today, and the harness
does not favour removing it. The site's sub-threshold-vote figure
(build_site) follows the same flag.

**Code** (production bit-identical; harness default = registered pairs):
- validate_model: REGISTERED_PAIRS and REGISTERED_PAIR_SOURCES.
- validate_bayes: REG_PAIRS (`HARNESS_REG_PAIRS`, default '1') and layers
  `pairs`, `thr_u` and `central_raw`. Also UNMODELLED_REC,
  allocate_vector(raw, u), the arms reg_pairs, past_pairs, thr_valid,
  reg_thr, reg_thr_draws, reg_central_raw, reg_thr_u005, reg_thr_loo and
  reg_thr_oracle, and the eve `seat_mae_central(_fixed)` and `n_pairs`
  columns.
- validate_horizon and validate_threshold pass the registered pairs.
  validate_horizon also gains `seat_mae_central_fixed` and `n_pairs`.
- simulate: THRESHOLD_ALL_VALID (OFF), UNMODELLED_SHARE and valid_scale.
- bayes_model.project (draw test only; the targeting hook is untouched)
  and official_forecast.allocate_central(all_valid, u).
- New files: src/validate_seat_law.py and data/cec_final_counts.csv.

## 48. Uncertainty calibration (15 Oct, D-12)

### 48.1 Pre-registration (written before any grade was run)

**Why.** On the s.46 yardstick (CLR latent, ballot-fidelity windows) the
90% intervals cover .981 / .990 / .990 of list results at eve / D-7 /
D-21, against a 0.90 target. Desk ERR (forecast_research/poll_error.json)
names four sizes or shapes in the election-day shock stack that look
wrong; desk EVAL (forecast_evaluation.json) asks for the residual width to
be chosen by nested leave-one-cycle-out and for coverage to be scored as
distance from 0.90, not as "more is safer". This section grades one
family of candidates on exactly those points.

**Arms.** Every arm is the shipped configuration (s.46 code defaults: CLR,
fidelity windows, trailing cliff, regB Arab term) with one change set.
- `base`: shipped, RESID_SCALE 0.9.
- `A` (t-scale fix): every Student-t shock is scaled to unit variance
  (x sqrt((df-2)/df) = sqrt(3/5) at T_DF 5), so the bloc swing, the
  haredi family shock and the Arab turnout draw (which shares the family
  t draw) have the sd they were measured or declared at, instead of 1.29x
  it. Production and harness alike (production keeps EVENT_RISK on top).
- `B` (vote-share residual): the per-list residual (base + slope x size)
  is re-estimated leave-one-cycle-out from VOTE-SHARE errors of the lists
  that RAN, instead of seat errors in which threshold deaths enter as 0
  seats. Units: u = 120 x vote share, the units the projection applies the
  residual in. Polled side: the final-window (21 days, latest poll per
  firm) average of each list's implied share under the model's own map
  (seats/120 x (1 - wasted - 0.01); a 0-seat row at its printed percentage;
  a 0-seat row with no percentage at HALF the cycle threshold, the
  midpoint of what the poll reports). Actual side: lists that won seats
  through the same seat->share map (seats x (1 - W - 0.01), W = the
  failed lists' CEC share), lists that ran and failed at their CEC vote
  share (data/ran_vote_shares.csv). A list enters if it ran, its polled
  share is measured (seats > 0 or a printed percentage) in at least half
  of its final-window polls, and it won seats or polled >= 0.5 u. Then
  the same sequence as error_decomposition.decompose: bloc swing and
  family totals removed proportionally (vote-share totals), anchors
  removed, and the same two-group (<= 8 / > 8 seats) sd line.
- `AB`: A and B together.
- `D` (fat-tailed residual): the residual drawn from a Student t with
  sd matched (draw x sqrt((df-2)/df)); df estimated leave-one-cycle-out by
  the method of moments from the excess kurtosis G2 of the training
  record's residuals standardised by their fitted sd line, df = 4 + 6/G2,
  clipped to [4.5, 30] (G2 <= 0.2 -> 30). Graded on the shipped stack
  (seat-space record).
- Width arms (c), nested: `C0` = base, `CA` = A, `CAB` = A+B, `CABD` =
  A+B+D (D's df from the vote-share record), each with its residual width
  chosen by nested leave-one-cycle-out. Grid 0.4 to 1.6 in steps of 0.1,
  multiplying the arm's own residual sd. Rule: for each held-out cycle,
  the width with the lowest mean interval score over the other seven
  cycles, averaged with equal weight over eve (3-seed mean), D-7 and
  D-21; the held-out cycle is then graded at that width at every horizon.
  D-56 never enters the choice. The production width is the same rule's
  choice on all eight cycles.
- A, B, AB and D are graded at the shipped width 0.9 with no selection.

**Grading.** Eve on 3 seeds (offsets 0/1/2, pooled = seed mean); D-7,
D-21 and D-56 on 1 seed (offset 0), calendar forward weeks as in
validate_horizon. Shipped list mask (`*_fixed`: base at 0.9, same seed).
D-56 is graded on the cycles whose CLR-fidelity caches exist and is
reported, not gating. Reproduction gate: `base` must reproduce the s.46
restated eve 1.509/1.628/.981/.0474/9.280 before any arm is read.

**Decision rule.** Primary: the pooled interval score IS (Gneiting &
Raftery 2007, alpha 0.10, mean over the 8 cycles of the per-list score)
and the calibration error CE = |pooled 90% coverage - 0.90|; lower is
better for both, so a coverage drop toward 0.90 is a gain. Secondary:
median-seat MAE, mean-seat MAE, threshold Brier; reported: the bloc Brier
for P(NB >= 61) and the per-fold IS wins / ties / losses (|d| < 0.05 a
tie). An arm PASSES if, at eve (3 seeds pooled), IS is lower than base,
CE is not higher than base by more than 0.005, and no secondary metric
is worse by more than its noise floor (twice the seed-to-seed sd of the
paired difference over the 3 eve seeds, at least 0.010 seats for MAE and
0.0010 for Brier); and at D-7 and D-21 IS is not worse than base by more
than 0.05 and CE not higher by more than 0.010. The recommended arm is
the passing arm with the lowest eve IS; within 0.02 of each other, the
lower CE, then the lower mean IS over D-7/D-21. A nested arm is judged
only on its held-out numbers.

**Amendment (17:50, before any grade; the text above was hashed at 17:37,
sha256 2fdebcf2...).** Building arm B exposed a defect in the shipped
residual: `decompose()` pools the per-cycle frames with their block-number
index, so step 4's `resid.loc[<leader label>]` subtracts the seat-leader
anchor (-1.74 seats) from every cycle's row carrying that label. With
unique labels the full-sample line is 1.48 + 0.041 x seats instead of
1.83 + 0.044 (LOO intercepts 1.07-1.67 instead of 1.20-2.19); bloc_sd,
family terms and anchors are unchanged. B's vote-share record is built
with unique labels, so B bundles two changes. One arm is added to
separate them, graded like A/B/AB/D (width 0.9, no selection, same rule):
- `Bfix`: the seat-error residual with unique labels
  (`decompose(index_fix=True)`), nothing else changed.
Arm D's tail df is estimated on the unique-label record in both spaces.

**Amendment 2 (18:05, before any arm was graded).** The s.46 restated
baseline is the mean of harness seed offsets 0 / 100 / 200 (the main
restatement run), not 0 / 1 / 2: offsets 0/100/200 reproduce it exactly
(1.5093 / 1.6284 / .9807 / .0474 / 9.2798; offset 0 bit-identical to the
committed 17:21 ablation file). The eve grade uses offsets 0/100/200; the
horizons offset 0. This was checked on the base arm only.

**Amendment 3 (18:20, before any arm was graded; on the coordinator's
relay of the ERR verifier, verify_poll_error.json).**
- The verifier found the same decompose() index collision independently
  (32 of 91 rows hit, label-0 rows three times). `Bfix` above is that
  "resid_fix" arm. Because RESID_SCALE 0.9 was tuned on the collided
  width, the width must be re-chosen after the fix: a fifth nested width
  arm `CBfix` (Bfix + nested width, same grid and rule) is added and
  graded under the same decision rule.
- Arm A is kept unchanged and graded by the same rule. The verifier's
  caveat is recorded in advance: bloc_sd (3.36) is a ddof-1 sd around a
  +1.66 sample mean; the RMS around zero is 3.55 and the posterior-
  predictive sd for a new cycle about 4.1-4.2, so the t(5)-on-sd scaling
  (4.33 in the harness) acts roughly as a parameter-uncertainty allowance
  and A may make the swing too narrow. The bloc Brier for P(NB >= 61) is
  the score that speaks to the swing and is reported for every arm; the
  per-list coverage mostly reflects the residual. The production-only
  EVENT_RISK 1.2 is not graded here (no harness analogue).
- Arm D is sized by the record as already specified (df from the
  standardised residual's G2, not from the raw-error kurtosis of 4-4.6 the
  desk quoted). Before grading, the full-sample estimator gives G2 2.59 ->
  df 6.3 on the unique-label seat record and G2 1.25 -> df 8.8 on the
  vote-share record (the verifier: excess kurtosis about 2 on e3).
- Arm B's vote-share line before grading: full sample 0.73 + 0.073 x u
  (n 95; LOO intercepts 0.63-0.89), against the verifier's like-for-like
  won-seat e3 refit 0.79 + 0.075 and the desk's non-comparable 0.67 +
  0.097.

### 48.2 Results

**Runs.** `src/calibration_arms.py` (new) projects every arm x width x
seed with the harness's own `project_cycle` on the cached CLR-fidelity
posteriors (read only) and scores on the shipped list mask (base at 0.9,
same seed). Eve: offsets 0/100/200; D-7, D-21, D-56: offset 0, calendar
forward weeks. All eight D-56 CLR-fidelity caches existed by the run (the
main session fitted 2020-2022 D-56 at 17:49-18:43). Graded on the code
of 804ff2d plus the round-three files; re-projected on main 806c6f4 plus
this patch, base / A@0.4 / AB / Bfix are bit-identical at eve (8 cycles)
and D-21 (2013, 2021), so the grade carries over.

**Reproduction gate: passed.** base at eve, offsets 0/100/200:
1.5093 / 1.6284 / .9807 / .0474 / 9.2798 (s.46: 1.509 / 1.628 / .981 /
.0474 / 9.280).

**Inputs as fitted (leave-one-cycle-out ranges).** Bfix line 1.07-1.67 +
0.023-0.055 x seats (full 1.48 + 0.041). Vote-share line 0.63-0.89 +
0.050-0.081 x u (full 0.73 + 0.073; n 81-86 per fold, 95 in all). Tail
df: seat record 6.1-7.0 (full 6.3), vote record 6.2-11.0 (full 8.8).

**Nested width picks** (held-out cycle -> width; ALL = the production
choice):

| arm | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 | ALL |
|---|---|---|---|---|---|---|---|---|---|
| C0 (base) | .4 | .4 | .5 | .5 | .6 | .5 | .4 | .6 | .5 |
| CA (A) | .4 | .4 | .4 | .4 | .6 | .4 | .4 | .4 | .4 |
| CAB (AB) | .5 | .7 | .9 | .7 | 1.2 | .9 | .6 | .9 | .8 |
| CABD (ABD) | .5 | .6 | 1.1 | .6 | 1.1 | 1.1 | .6 | 1.1 | .6 |
| CBfix (Bfix) | .6 | .5 | .6 | .6 | .7 | .6 | .4 | .6 | .6 |

Grid-floor check (diagnostic, not part of the rule): adding widths 0.2
and 0.3 for base and A leaves every CA pick unchanged (0.4 is interior);
C0's 2021 fold moves to 0.3.

**Pooled metrics** (median MAE / mean MAE / coverage / threshold Brier /
interval score IS; CE = |coverage - .90|; bloc = bloc Brier for
P(NB >= 61); IS folds = wins / ties / losses vs base, |d| < .05 a tie).

Eve (3 seeds):

| arm | median | mean | cov | Brier | IS | CE | bloc | width | IS folds |
|---|---|---|---|---|---|---|---|---|---|
| base | 1.509 | 1.628 | .981 | .0474 | 9.280 | .081 | .0439 | 8.06 | - |
| A | 1.506 | 1.628 | .981 | .0473 | 9.157 | .081 | .0369 | 7.94 | 6/2/0 |
| B | 1.525 | 1.599 | .972 | .0408 | 8.482 | .072 | .0374 | 6.90 | 7/0/1 |
| Bfix | 1.518 | 1.623 | .972 | .0446 | 9.015 | .072 | .0401 | 7.62 | 5/2/1 |
| AB | 1.523 | 1.598 | .968 | .0406 | 8.288 | .068 | .0290 | 6.64 | 7/0/1 |
| D | 1.504 | 1.619 | .981 | .0461 | 9.212 | .081 | .0441 | 7.99 | 4/4/0 |
| ABD | 1.500 | 1.596 | .961 | .0403 | 8.388 | .061 | .0293 | 6.54 | 7/0/1 |
| C0 | 1.517 | 1.607 | .960 | .0418 | 8.728 | .060 | .0344 | 6.54 | 4/0/4 |
| **CA** | **1.509** | **1.599** | **.960** | **.0411** | **8.061** | **.060** | **.0232** | **5.79** | **5/1/2** |
| CAB | 1.504 | 1.598 | .915 | .0407 | 9.517 | .015 | .0285 | 6.41 | 4/0/4 |
| CABD | 1.507 | 1.603 | .911 | .0414 | 9.679 | .011 | .0311 | 6.50 | 5/0/3 |
| CBfix | 1.524 | 1.603 | .937 | .0409 | 9.072 | .037 | .0341 | 6.47 | 4/0/4 |

D-7 / D-21 / D-56 (offset 0; median / mean / cov / Brier / IS / bloc):

| arm | D-7 | D-21 | D-56 |
|---|---|---|---|
| base | 1.495/1.650/.990/.0492/9.454/.0426 | 1.620/1.773/.990/.0538/9.655/.0616 | 2.367/2.432/.922/.0882/14.591/.1119 |
| A | 1.465/1.650/.978/.0490/9.511/.0359 | 1.630/1.774/.990/.0537/9.460/.0547 | 2.377/2.432/.922/.0884/15.000/.1075 |
| B | 1.492/1.626/.951/.0441/8.988/.0374 | 1.613/1.736/.944/.0501/9.754/.0588 | 2.391/2.387/.909/.0900/15.212/.1104 |
| Bfix | 1.508/1.644/.969/.0468/9.285/.0394 | 1.634/1.759/.972/.0518/9.498/.0594 | 2.404/2.415/.916/.0888/15.486/.1112 |
| AB | 1.505/1.625/.951/.0437/8.762/.0297 | 1.625/1.736/.935/.0499/9.675/.0513 | 2.375/2.387/.909/.0902/14.909/.1056 |
| D | 1.513/1.638/.990/.0481/9.385/.0434 | 1.577/1.714/.981/.0513/9.654/.0594 | 2.384/2.437/.922/.0882/14.735/.1150 |
| ABD | 1.477/1.621/.951/.0435/8.810/.0294 | 1.569/1.677/.935/.0476/9.644/.0491 | 2.340/2.393/.909/.0903/14.963/.1105 |
| C0 | 1.476/1.634/.934/.0451/9.600/.0350 | 1.623/1.750/.924/.0516/9.815/.0567 | 2.378/2.398/.909/.0894/14.837/.1068 |
| **CA** | **1.481/1.625/.934/.0444/9.126/.0246** | **1.606/1.744/.924/.0516/9.252/.0480** | **2.366/2.395/.899/.0905/16.040/.1033** |
| CAB | 1.494/1.628/.913/.0443/10.030/.0292 | 1.614/1.740/.901/.0511/10.436/.0516 | 2.382/2.393/.896/.0892/15.164/.1046 |
| CABD | 1.466/1.631/.913/.0449/10.182/.0317 | 1.560/1.686/.901/.0493/10.456/.0524 | 2.333/2.400/.896/.0883/15.539/.1098 |
| CBfix | 1.492/1.632/.925/.0444/9.624/.0346 | 1.611/1.745/.935/.0506/9.776/.0565 | 2.378/2.394/.909/.0894/14.914/.1083 |

**Decision rule (as pre-registered).**
- PASS: Bfix, AB, D, ABD, CA.
- FAIL: A (D-7 IS +.056 > .05), B (D-21 IS +.099), C0 (D-7 +.146,
  D-21 +.160), CAB and CABD (eve IS above base; D-7 +.58/+.73, D-21
  +.78/+.80), CBfix (D-7 +.169, D-21 +.121).
- Recommended: **CA** (lowest eve IS among the passing arms, 8.061; next
  AB 8.288, ABD 8.388). Seed sd of CA's paired eve IS difference .11
  against a gain of 1.22. No secondary metric is worse at eve (median
  1.5085 vs 1.5093, mean -.030, Brier -.0063).

**Reading.**
- Over-coverage is not one layer's fault. With the swing and family
  shocks at their measured sd (A) the interval score still wants the
  residual at 0.4 of the shipped line (about 0.49 of the corrected line),
  and eve coverage stays .960 even there. The misses are a few large
  tail events (2013 Yesh Atid, 2019a, 2021) that no moderate width covers;
  in the other five cycles every narrowing pays.
- The t-scale fix (A) improves the bloc Brier at every horizon (.0439 ->
  .0369 eve, .0426 -> .0359 D-7, .0616 -> .0547 D-21, .1119 -> .1075 D-56)
  and the eve IS, and fails alone only by .006 at D-7. The verifier's
  concern (the t(5)-on-sd width acts as a parameter-uncertainty allowance)
  is not borne out on these eight outcomes, which cannot certify it
  either way. In production A gives the swing sd 3.36 x 1.2 = 4.03 seats,
  just under the verifier's 4.1-4.2 predictive figure; in the harness 3.36.
- The vote-share residual (B) gives the lowest threshold Brier of the
  stack arms (B .0408 / .0441 at eve / D-7; with A and D .0403 / .0435)
  but loses the D-21 interval score alone, and
  its width curve is jagged (a straddler's interval flips between [0, 0]
  and [0, 5]), so the nested choice on AB is unstable (0.5-1.2) and CAB /
  CABD lose held-out.
- The index fix alone (Bfix, width 0.9) passes: IS -.27 / -.17 / -.16 at
  eve / D-7 / D-21. Re-choosing the width after the fix (CBfix, picks
  0.4-0.7, ALL 0.6) gains at eve but loses held-out at D-7 and D-21, so
  under this rule the fix ships, if at all, at 0.9, not with a re-chosen
  width.
- Fat tails (D, df about 6) are a small, consistent gain (eve IS -.07,
  D-21 MAE -.04, D-56 bloc Brier slightly worse) and pass; they do not
  rescue CABD.
- CA's costs: IS fold losses at eve (2009 +.6, 2013 +.4), D-7 (2009 +1.5,
  2013 +.2, 2021 +5.6) and D-21 (2013 +3.6, 2021 +6.2: coverage .64 there); D-56 IS
  14.59 -> 16.04 (2013 +5.0, 2022 +4.2, 2015 +2.0), which is reported and
  not gating, but says a narrow stack is wrong eight weeks out.

### 48.3 2026 effect (frozen production posterior; outputs in scratch)

Main 806c6f4 code with this patch, the CLR production posterior of 15 Oct
19:41 frozen in scratch (sha256 4f502286...), the production chain
(registration mixture -> official_forecast -> government_formation) with
every output redirected to a scratch copy of data/processed, projection
seeds +0 / +1 / +2. Flags off reproduces main's committed mixture draws,
official forecast and PM table bit for bit.

| | shipped (+0/+1/+2) | CA (+0/+1/+2) | A only (+0) | width 0.4 only (+0) | AB (+0) | Bfix (+0) |
|---|---|---|---|---|---|---|
| P(NB >= 61) | 13.0 / 13.1 / 13.5 | 6.6 / 6.2 / 6.4 | 10.7 | 9.5 | 7.8 | 11.8 |
| change bloc alone | 8.6 / 8.4 / 8.6 | 3.1 / 3.2 / 3.4 | 6.8 | 5.1 | 4.4 | 7.5 |
| with Ra'am | 28.3 / 28.5 / 28.1 | 24.6 / 25.4 / 24.8 | 26.4 | 27.5 | 25.9 | 28.0 |
| neither | 58.8 / 58.4 / 58.4 | 68.8 / 68.4 / 68.8 | 62.8 | 63.0 | 66.2 | 60.3 |
| NB seats, mean [90%] | 52.9 [41-65] | 52.6 [44-61] | 52.9 [43-63] | 52.6 [42-63] | 52.6 [43-62] | 52.8 [42-64] |
| PM: repeat election | .455 / .454 / .454 | .541 / .538 / .542 | .485 | .501 | .521 | .469 |
| PM: Netanyahu | .195 / .194 / .196 | .151 / .148 / .149 | .179 | .172 | .159 | .187 |
| PM: Eisenkot | .221 / .221 / .220 | .186 / .190 / .187 | .209 | .202 | .196 | .216 |
| mean 90% width, lists >= 3 seats | 9.5 / 9.6 / 9.5 | 7.1 / 7.1 / 7.1 | 9.2 | 7.5 | 8.2 | 8.7 |
| Otzma pass | .768 / .764 / .768 | .847 / .847 / .847 | .774 | .838 | .833 | .793 |
| Ra'am pass | .764 / .778 / .768 | .923 / .926 / .928 | .766 | .907 | .896 | .795 |
| RZP-Zehut pass | .529 / .534 / .540 | .586 / .589 / .594 | .530 | .582 | .579 | .544 |
| Amcha pass | .247 / .250 / .256 | .226 / .227 / .230 | .247 | .226 | .229 | .239 |
| Reservists pass | .214 / .222 / .221 | .188 / .194 / .195 | .214 | .188 | .190 | .205 |

Central seats are unchanged under every arm (Likud 26, Yashar 23,
Together 11, Democrats / Shas / JL / YB / UTJ 9, Otzma 6, Ra'am 5,
RZP-Zehut 4); the intervals narrow (Likud 17-34 -> 18-32, Yashar 15-30 ->
17-28, Ra'am 0-9 -> 0-7). CA halves P(NB >= 61) because the bloc's
central count (52.6) sits eight seats below 61 and both pieces cut the
tail: at seed +0, A alone -2.3 pts, the width alone -3.5, together -6.4
(13.0 -> 6.6).

### 48.4 Recommendation and constants

- By the pre-registered rule: ship **CA**:
  `bayes_model.T_UNIT_VAR = True` and `bayes_model.RESID_SCALE = 0.4`
  (was 0.9); `RESID_SPACE` stays "seat" and `RESID_T_DF` None; mirror in
  the harness with `ALL_LAYERS["t_unit"] = True` (the width is
  `resid_scale`, which defaults to `bm.RESID_SCALE`).
- What the rule cannot see, for the owner: the effect on the headline is
  large (P(NB >= 61) about 13 -> 6, deadlock 58 -> 69) and rests on eight
  bloc outcomes; D-56 says a stack this narrow is wrong at long horizons;
  two cycles (2013, 2021) lose 4-6 interval-score points at D-7/D-21.
- The decompose() index collision is a bug whatever is shipped. Fixing it
  at 0.9 (Bfix) passes on its own, but CA's 0.4 was chosen on the collided
  line: fixing the index under CA needs the width re-chosen (about 0.49 is
  the mechanical equivalent; not graded). `decompose(index_fix=...)` is in
  the patch, default False.

### 48.5 Not established

- WIS over several levels and a discrete PIT (desk EVAL) were not run;
  the rule uses the 90% interval score only.
- A width grid on A + Bfix (the fixed line under the t-scale fix) and on
  D alone was not run; CA's width on the corrected line is unknown.
- EVENT_RISK (production only) and the anchors-retired e2-vs-e3 residual
  question (verifier) were not graded.
- 1 seed at D-7 / D-21 / D-56; the horizon tolerance (.05 IS) is below
  the eve seed sd of some paired differences (.08-.14), so A's and
  CBfix's D-7 failures are near noise.

### 48.6 Re-grade on the leak-free harness, and the decision (16 Oct)

The CA recommendation above was graded on the shared cache whose firm
precision priors included each graded cycle's own final polls (the s.50
leak), and on the 15 Oct configuration (old surplus pairs, haredi e1). A
leak can make past averages look sharper than they were, which pushes a
width chosen on the record towards narrow, so before shipping CA it was
re-graded under the same pre-registered rule on the s.50 leave-one-out
scorecard caches and the shipped 16 Oct configuration (registered pairs,
hared_e0). Arms base / A / Bfix and their nested-width versions; eve on
offsets 0/100/200, D-7 and D-21 on offset 0; runs in scratch (w48loo,
w48loo_bfix).

| arm | eve IS | eve CE | D-7 IS | D-21 IS | nested width (all 8) |
|---|---|---|---|---|---|
| base (0.9) | 9.217 | .081 | 9.254 | 9.704 | - |
| A (0.9) | 9.142 | .081 | 9.446 (+.192) | 9.656 | - |
| CA | 8.858 | .051 | 9.428 (+.174) | 9.940 (+.236) | 0.6 (was 0.4) |
| Bfix (0.9) | 9.011 | .072 | 9.397 (+.143) | 9.555 | - |
| CBfix | 8.766 | .051 | 9.271 (+.017) | 9.790 (+.086) | 0.5 |
| C0 | 8.851 | .051 | 9.338 (+.084) | 9.779 (+.075) | 0.4 |

- **No arm passes.** CA's nested width moves from 0.4 to 0.6, its eve gain
  shrinks from 1.22 to 0.36, and it loses at D-7 and D-21 beyond the .05
  tolerance. Bfix fails at D-7; CBfix fails at D-21 by .036 beyond the
  tolerance, on one seed.
- **Decision: nothing ships from s.48.** The shipped stack stays
  (RESID_SCALE 0.9, T_UNIT_VAR off, the seat-space residual line as
  decompose() fits it). Every s.48 flag stays in the code, OFF. The
  headline is unchanged.
- What stands: the 90% intervals cover about 98% of list results at eve
  and 99% at D-7/D-21 on the leak-free harness, so they are wider than
  their label; decompose()'s index collision is a real defect, and the
  shipped width 0.9 was tuned on the collided line, so the shipped total
  residual is an empirical calibration of that line, not of a correct
  one. Both are stated on the site as limitations.
- Next candidate (not registered yet): CBfix with the horizon gate scored
  on three seeds, since the .05 tolerance at one seed is below the paired
  seed noise (.08-.14) the s.48 grade measured.

## 49. Formation calibration (15-16 Oct, D-12)

This section does four things:

- rebuilds the formation harness on the shipped parameters and on 17
  Knessets;
- adds a post-deadlock stage calibrated to the Israeli record;
- sets the unity gate (`likud_sans_bibi`) from the record instead of by
  hand;
- corrects the COND anchor text.

It uses only desk COA findings that the verifier marked verified or
corrected (`forecast_research/verify_coalition_formation.json`), plus the
atlas findings D10-F16 to F28 (`targeting/research/verify_coalition.json`).
The 2026 runs use a frozen copy of `mixture_draws.parquet`. Its sha256
begins 2e2eec97 and matches production byte for byte. The formation layer
reads nothing else from the model.

### 49.1 The harness now grades the shipped tree

The old `validate_formation.py` graded its own, older parameters, while its
header said they matched the shipped tree (COA-F08, verified). It used
haredi 0.30, Ra'am joins 0.55, unity 0.15 and a hard-coded pledge-break of
0.33. The site's "−0.93 vs −0.92" and "−0.92 ... five of eight" came from
it, and the verifier found that the second sentence mixes two trees. All
three numbers are retired.

The rebuilt harness imports `BEHAVIOR`, `BEHAVIOR_NEFF`, `PM_ALLOC`, `COND`
and `simulate_formation`. It uses 200 parameter vectors drawn as in
`main()`, and 2,000 draws per Knesset. It adds only the historical seat maps
and the 2026 role each list plays:

- **Likud and the right:** the right's main list plays Likud; the other
  right lists play RZP.
- **Haredi parties:** Shas, and Agudah/Degel/UTJ.
- **Change lists:** the largest plays Yashar; the rest play the Democrats.
- **Yisrael Beytenu:** plays YB only from 2020, so Liberman's vetoes bite
  only from then.
- **Kingmakers:** lists that declared for neither PM candidate, or made
  joining conditional. Each gets the tree's generic split (0.40 right /
  0.45 centre) with its own draw.
- **Arab lists:** the Ra'am lineage (ADP 1988-92, UAL from 1996) plays
  Ra'am; every other Arab list plays the Joint List.

Roles were fixed before scoring. Gate covariates are centred on the 2026
draws, as shipped.

Sources: ParlGov development version (view_election, view_cabinet),
cross-checked with the IDI election pages, for 1977-2006 (atlas D10-F23,
F24; COA-F11 recomputed); CEC `results.csv` for 2009-2022. Outcomes come
from the IDI pages and atlas D10-F17, F22, F25, F26 and F28.

1949-1973 is left out. In the dominant-party era the religious parties were
Mapai's partners and the bloc roles do not exist; all eight elections
formed a government.

Seven cycles are **certain**: 1977, 1981, 1988, 2003, 2009, 2013 and 2022.
The bloc alone held 61, so every tree scores P = 1, and they carry weight 0.
1996 and 1999 elected the PM directly; they carry weight 0.5, in a secondary
score only. The **primary score** is the mean log P(realized class) over
eight cycles: 1984, 1992, 2006, 2015, 2019a, 2019s, 2020 and 2021. 1984 is
class 6 (unity, both leaders kept); a sensitivity row scores it as {1, 6}.

Four trees are scored on common random numbers:

- **production:** the pre-s49 tree, with unity 0.18 (NEFF 20) and no stage;
- **unity_record:** the record unity prior alone;
- **stage_only:** the stage with unity at 0.18;
- **candidate:** the stage plus the record unity prior.

Both record-fitted pieces are scored leave-one-out:

- **the stage:** the Beta for each deadlock cycle is refitted without that
  cycle's outcome;
- **the unity prior:** for 1984 and 2020, which are themselves unity
  governments, it is refitted on 0 of 2, Beta(0.5, 2.5).

### 49.2 The post-deadlock stage

**The event.** A deadlock is a Knesset in which no side reaches 61 with its
own lists plus the unaligned lists (and Amcha) that sided with it. In code:
`deadlock = (nb < 61) & (ce_pure + res_c + amcha_ce < 61)`. The ways out
are haredi crossings, Ra'am's seats, pledge-breaks, unity and minority
investiture.

**What the stage does.**

- **Outside a deadlock** the outcome is arithmetic (classes 0-3) and
  nothing changes.
- **Whether a government forms:** inside a deadlock, the record decides.
  A government forms with probability 1 − r, where r is drawn from the Beta
  posterior once per parameter vector.
- **Which government forms:** the shipped gates decide. Where the gates
  had sent a draw to a repeat but the stage says a government forms, the
  gates are re-drawn, with kingmaker and Amcha sides held fixed, until one
  fires.

Each stage step has its own generator. With `--stage off` and the pre-s49
unity value, `government_formation.csv`, `pm_probabilities.csv` and
`government_sensitivity.csv` reproduce production bit for bit (checked). In
2026, 1,315 of about 1.2 million deadlock draws (0.1%) had no feasible gate
and stayed repeats.

**The record, on the same event, with the kingmakers' realized sides.**

| deadlock | position in run | outcome | source |
|---|---|---|---|
| 1984 | 1 | unity with rotation, inside Peres's first extended mandate | IDI 1984; atlas D10-F24; COA challenge check (CSM 14 Sep 1984) |
| 1992 | 1 | Labor-Meretz 56 + Shas 6; Hadash and ADP outside | IDI 1992; atlas D10-F23 |
| 2006 | 1 | Kadima-Labor-Meretz 53 + Gil 7 + Shas 12 | ParlGov Olmert I; atlas D10-F28 (corrected) |
| 2019a | 1 | **repeat**: the Knesset dissolved first | IDI 2019; atlas D10-F25 |
| 2019s | 2 | **repeat**: the 21-day window lapsed | IDI; atlas D10-F22 |
| 2020 | 3 | Gantz's faction joins Netanyahu | IDI 2020; atlas D10-F25 |
| 2021 | 4 | change + Yamina + Ra'am, second mandate | IDI 2021; atlas D10-F26 |

That is **2 repeats in 7**. With a Jeffreys prior the posterior is
Beta(2.5, 5.5): mean **0.312**, 90% interval [0.088, 0.593]. The
pre-s49 tree gave 0.596 on the same 2026 event, which sits at the 95th
percentile (P = 0.048).

**Why not the verifier's 2 of 5.** The conventional list of five deadlocks
(1984, 2019a, 2019s, 2020, 2021) is not the tree's event. On the tree's
arithmetic, 1992 and 2006 are also deadlocks, closed by haredi entry. The
site's earlier "~0.61" was measured on the desk's own event, and on that
event the parliamentary record is 2 of 8. The conventional counts are kept
as sensitivity rows.

| reference class | count | posterior mean [90%] | 2026 P(repeat), central draw |
|---|---|---|---|
| **stage record (post-election, parliamentary)** | **2/7** | **0.312 [0.088, 0.593]** | **0.235** |
| + 1999 (direct election) | 2/8 | 0.278 [0.076, 0.538] | 0.209 |
| + Oct 2008 (Livni, mid-term) | 3/8 | 0.389 [0.150, 0.657] | 0.292 |
| + Nov 1995 and Oct 2008 (mid-term) | 3/9 | 0.350 [0.132, 0.604] | 0.264 |
| bloc era 2019-21 only | 2/4 | 0.500 [0.165, 0.835] | 0.373 |
| conventional five (event mismatch) | 2/5 | 0.417 [0.128, 0.739] | 0.309 |
| conventional five + Oct 2008 | 3/6 | 0.500 [0.209, 0.791] | 0.373 |

Mid-term cases are sensitivity rows only, because the stage is about
post-election formation. Counting the 2008 failure without the 1995
formation would be one-sided. Sources: The National, 26 Oct 2008 (COA-F18,
corrected); Wikipedia, 26th government of Israel, 58 seats (COA-F15,
corrected).

**Position in an election run.** A grid-posterior logistic, with priors
a ~ N(0, 1.5) and b ~ N(0, 1), gives P(repeat) of 0.376, 0.291, 0.243 and
0.223 at positions 1 to 4. The slope's mean is −0.45, with P(b < 0) = 0.74.
Counted directly, 1 of 4 first-election deadlocks repeated, 1 of 3 later
ones, and 0 of 2 at positions 3-4. Four of the seven cases come from one
2019-21 run, so the slope is not distinguishable from zero. The stage is
**not** position-dependent. For 2026, the first-election estimates (0.30
and 0.38) bracket the pooled 0.31.

**Deadlock depth** is not a covariate either. Repeats came at gaps to 61 of
1 (2019a) and 6 (2019s). Governments formed at gaps of 1-3 (1984, 1992,
2006, 2020) and 3-9 (2021). There is no pattern.

### 49.3 The unity gate from the record

`likud_sans_bibi` was a hand value of 0.18 (NEFF 20). Its stated base,
"unity resolved ~half of deadlocks (1984/1988/2020)", fails on the verified
record:

- 1988 was not a deadlock: the right-religious bloc held 65 (atlas D10-F24).
- All three unity governments kept both leaders: 1984 Peres/Shamir with
  rotation, 1988 Shamir with Peres, 2020 Netanyahu/Gantz (COA-F24,
  verified; COA-F16).
- No Israeli party has dropped its sitting leader after an election to
  form a government (COA-F24). The one comparative case, Spain's PSOE in
  Oct 2016, came after two failed elections.

It is now **Jeffreys on 0 of 3 unity governments: Beta(0.5, 3.5), mean
0.125, NEFF 4**. The median is 0.067, the 90% interval [0.0006, 0.444], and
P(> 0.18) = 0.26.

Two other reference classes were considered:

- **0 of 5 deadlocks where a unity was on the table** (1984, 2019a, 2019s,
  2020, 2021): Beta(0.5, 5.5), mean 0.083.
- **0 of 7 stage deadlocks:** Beta(0.5, 7.5), mean 0.0625. In 1992 and 2006
  haredi entry closed the gap before unity was tested, so those two cases
  are censored.

The 0-of-3 class is the one COA-F24 verifies directly, and it is the most
conservative: it moves least from the old value. The narrower classes are
sensitivity rows. The 0.08 used as a sensitivity row in the first draft of
this section was the midpoint of the desk's proposed first-election range,
0.05-0.10 (COA challenge 4). It was not taken from the record. It happens to
equal the 0-of-5 Jeffreys mean, which replaces it. Herzog's plea-deal and
unity push stays a tripwire, not a prior.

**COND anchor text corrected (betas unchanged).**

- **Haredi defection:** Shas joined non-Likud premiers in 1992, 1999
  (directly elected PM) and 2006, and joined the 1984 Peres-led unity
  government. It declined viable ones in 1990 (Peres), Oct 2008 (Livni,
  which forced the 2009 election) and Feb 2009 (it recommended Netanyahu
  although Kadima was largest), and it has joined none since 2006. UTJ
  joined only Barak in 1999, briefly (COA-F18, corrected).
- **Unity and deadlock depth:** the anchor "1984/1988" is replaced. 1984
  is the one deadlock resolved by unity, and it kept both leaders; 1988 was
  not a deadlock. The +0.35 depth beta therefore has no direct anchor in
  the record and is kept as judgment.

The haredi priors themselves are unchanged, as the verifier advised. Dossier
s.3 and s.19 are left as they stood when written; this section supersedes
their anchor text.

### 49.4 The four trees on the record (leave-one-out)

| score (8 informative cycles unless noted) | production | unity_record | stage_only | candidate |
|---|---|---|---|---|
| mean log P(realized class) | −1.572 | −1.580 | −1.589 | **−1.533** |
| difference from production (bootstrap SE) | | −0.008 (0.038) | −0.016 (0.238) | +0.039 (0.250) |
| + 1996, 1999 at weight 0.5 | −1.556 | | | −1.484 (+0.072, SE 0.221) |
| 1984 scored as {1, 6} | −1.472 | | | −1.390 (+0.082, SE 0.260) |
| YB 2015/2019a in Amcha's role | −1.617 | | | −1.563 (+0.055, SE 0.248) |
| repeat vs government, 10 non-certain cycles: log / Brier | −0.800 / 0.302 | −0.859 / 0.328 | −0.758 / 0.253 | −0.758 / 0.253 |
| repeat vs government, all 17: log / Brier | −0.450 / 0.170 | −0.483 / 0.185 | −0.426 / 0.142 | −0.426 / 0.142 |
| realized class is the top class | 1 of 8 | 1 of 8 | 1 of 8 | 2 of 8 |

A uniform guess over the nine classes scores −2.197.

The record cannot tell the trees apart on nine classes: every difference is
within one standard error. The candidate is the best of the four on every
row, and it beats production on the repeat event by both log and Brier.

**What production gets wrong.** On the seven record deadlocks, production
averages P(repeat | deadlock) **0.602**. That implies 4.2 expected repeats
against 2 observed; P(≤ 2 repeats) = 0.09 under its own probabilities. Its
top class was "repeat" in five deadlocks that went on to form a government
(1984, 1992, 2006, 2020, 2021).

In the calibration table, production's [0.50, 0.70) bin holds 5 forecasts
with a mean of 0.60, and none was realized. The candidate averages
P(repeat | deadlock) 0.327, with 2.3 expected repeats (P(≤ 2) = 0.58). Its
[0.50, 0.70) bin holds 2 forecasts, 1 realized.

**Per cycle, candidate minus production (log):**

| cycle | gain |
|---|---|
| 1984 | +0.32 |
| 1992 | +0.76 |
| 2006 | +0.25 |
| 2015 | +0.22 |
| 2020 | +0.92 |
| 2021 | +0.02 |
| 2019a | −1.13 |
| 2019s | −1.05 |

**The candidate's misses.** In 2019a and 2019s the candidate puts 0.74 and
0.62 on "Netanyahu + unaligned / defector". Part of that comes from the
kingmaker (YB) going right. Part comes from the stage handing the formed
deadlock mass to the pledge-break gate. The pledge-break gate is now the
largest single recipient of that mass, so it is the next gate to check
against the record.

Files: `formation_validation.csv`, `formation_validation_classes.csv`,
`formation_calibration.csv` and `formation_deadlock_record.csv`.

### 49.5 The 2026 effect (frozen mixture draws, 8,000 Knessets × 200 vectors)

| outcome | production | unity_record only | stage_only | **candidate [90%]** |
|---|---|---|---|---|
| Netanyahu rightist coalition | 0.120 | 0.120 | 0.120 | 0.120 |
| Netanyahu + unaligned / defector | 0.084 | 0.084 | 0.165 | **0.213** [0.050, 0.367] |
| Change coalition (without Ra'am) | 0.083 | 0.083 | 0.083 | 0.083 |
| Change + unaligned / Amcha | 0.033 | 0.033 | 0.033 | 0.033 |
| Change + a haredi party | 0.033 | 0.033 | 0.051 | 0.061 |
| JL-backed minority | 0.017 | 0.020 | 0.023 | 0.031 |
| Unity (Likud without Netanyahu) | 0.105 | 0.079 | 0.203 | **0.136** [0.002, 0.348] |
| Repeat election | 0.453 | 0.478 | 0.246 | **0.248** [0.070, 0.486] |
| Change + Ra'am | 0.073 | 0.070 | 0.075 | 0.075 |

| P(PM) | production | unity_record only | stage_only | **candidate [90%]** |
|---|---|---|---|---|
| Netanyahu | 0.204 | 0.204 | 0.285 | **0.333** [0.175, 0.492] |
| Eisenkot | 0.216 | 0.206 | 0.269 | **0.258** [0.173, 0.347] |
| none (repeat) | 0.453 | 0.478 | 0.246 | **0.248** [0.070, 0.486] |
| rotation / Likud successor | 0.061 | 0.048 | 0.110 | **0.079** [0.012, 0.183] |
| Bennett | 0.055 | 0.053 | 0.071 | 0.069 |
| Liberman | 0.012 | 0.010 | 0.018 | 0.013 |

**Deadlock numbers, candidate:**

- P(deadlock) is 0.759 on the stage's event and 0.641 on the desk's.
- P(repeat | deadlock) is 0.326 on the stage's event; the gates alone give
  0.629.
- On the desk's event it is 0.298, down from 0.610.
- P(Reservists' seats counted | the list passes) is 0.299, against 0.251
  in production.

**Central-draw sensitivity, stage on.** Read P(successor PM) / P(Netanyahu
PM) / P(Eisenkot PM) at each unity value:

| unity value | successor | Netanyahu | Eisenkot |
|---|---|---|---|
| 0.125, shipped | 0.107 | 0.306 | 0.264 |
| 0.083 | 0.084 | 0.337 | 0.258 |
| 0.0625 | 0.072 | 0.357 | 0.254 |
| 0.18 | 0.126 | 0.277 | 0.269 |

Lowering the unity gate moves the freed deadlock mass to the pledge-break,
not to repeats. Markets are not a target. Kalshi lists no "No one" strike:
the residual is about 0.01 at mids, range 0-0.15, on thin volume.
Polymarket resolves differently. Likud-alternative prices are about 0.04
(Kalshi mids) and 0.006 (Polymarket), and the model's "successor" row is not
like-for-like with them (COA-F09, corrected).

### 49.6 Site wording drafts (EN / HE)

These are written against the current template text and are not applied.
The site session has already handled the largest-list "7 of 10" and the
1993-96 minority line. Citation keys are unchanged.

1. **Formation tree, the COND sentence and the grading sentence.** Replace
   from "(Shas joined non-Likud prime ministers in 1992, 1999 and 2006, and
   refused in 2021 ...)" through "... preserved by construction.".
   - EN: "(Shas joined non-Likud prime ministers in 1992, 1999 and 2006,
     but declined viable ones in 1990, October 2008 and February 2009, and
     has joined none since 2006 [COA-F18]), a centrist defection falls as
     the gap grows (Gantz 2020 at a gap of three), and unity rises with
     deadlock depth — a judgment: Israel's one deadlock settled by unity,
     1984, kept both leaders, and 1988 was not a deadlock [COA-F24]. The
     tree is graded with its shipped parameters on the 17 Knessets since
     1977. Seven were settled by arithmetic and score 1 under any tree. On
     the other eight its mean log score is −1.53, against −1.57 before the
     deadlock stage and −2.20 for a uniform guess over its nine outcomes
     [COA-F08]. Eight outcomes cannot resolve the conditional effects, so
     they are retained on institutional grounds, with the marginals
     preserved by construction."
   - HE: "(ש״ס הצטרפה לראשי ממשלה שאינם מהליכוד ב־1992, ב־1999 וב־2006,
     אבל דחתה מועמדים ברי־סיכוי ב־1990, באוקטובר 2008 ובפברואר 2009, ולא
     הצטרפה לאף אחד מאז 2006 [COA-F18]), עריקה של מפלגת מרכז יורדת ככל
     שהפער גדל (גנץ 2020 בפער של שלושה), ואחדות עולה עם עומק המבוי הסתום —
     הערכה שיפוטית: המבוי הסתום היחיד בישראל שהוכרע באחדות, 1984, שמר על
     שני המנהיגים, ו־1988 לא היה מבוי סתום [COA-F24]. העץ נבחן בפרמטרים
     שבשימוש על 17 הכנסות מאז 1977. שבע מהן הוכרעו בחשבון המנדטים ומקבלות
     1 תחת כל עץ. בשמונה האחרות ציון הלוג הממוצע שלו ‎−1.53, לעומת ‎−1.57
     לפני שלב המבוי הסתום ו־‎−2.20 לניחוש אחיד על תשע התוצאות [COA-F08].
     שמונה תוצאות אינן יכולות להכריע את האפקטים המותנים, ולכן הם נשמרים
     על בסיס מוסדי, כשהשוליים נשמרים מעצם הבנייה."
2. **PM allocation.** Replace "This layer has no current grade ... under
   way."
   - EN: "The rebuilt harness grades which government forms, not who leads
     it, so the allocation within each coalition type has no record grade
     of its own [COA-F08]."
   - HE: "המתקן המחודש מדרג איזו ממשלה קמה, לא מי עומד בראשה, ולכן לחלוקה
     בתוך כל סוג קואליציה אין ציון היסטורי משלה [COA-F08]."
3. **Outcome 07, precision.**
   - EN: "... no Israeli government formed after an election has started
     as a minority; Peres's mid-term government of November 1995 began
     with 58–59 seats, and Rabin and Peres governed on outside support
     from Hadash and the Arab Democratic Party in 1993–96 [COA-F15]".
   - HE: "... ושום ממשלה ישראלית שהוקמה אחרי בחירות לא התחילה כממשלת
     מיעוט; ממשלת פרס שהוקמה באמצע הקדנציה בנובמבר 1995 התחילה עם 58–59
     מנדטים, ורבין ופרס משלו בתמיכת חד״ש ומד״ע מבחוץ ב־1993–96 [COA-F15]".
4. **Outcome 08.**
   - EN: "Likud drops him (0.125, set from the record: none of the three
     unity governments, 1984, 1988 and 2020, dropped a leader) — no Israeli
     party has ever dropped its sitting leader to form a government, and
     the one comparative case came after two failed elections [COA-F24]".
   - HE: "הליכוד מוותר עליו (0.125, נקבע מהרשומה: אף אחת משלוש ממשלות
     האחדות — 1984, 1988, 2020 — לא החליפה מנהיג) — שום מפלגה ישראלית לא
     הדיחה את מנהיגה המכהן כדי להרכיב ממשלה, והמקרה ההשוואתי היחיד הגיע
     אחרי שתי מערכות בחירות כושלות [COA-F24]".
   - Note: `build_site` prints the `data-par` value with two decimals, so
     0.125 would show as "0.12". It should use three decimals for
     `likud_sans_bibi`.
5. **Outcome 09, if the stage ships.**
   - EN: "in a deadlock the record decides whether a government forms: 2
     of the 7 parliaments since 1977 in which no side reached 61 with its
     own lists and the kingmakers that sided with it went to a repeat
     election, both in 2019 (2 of 5 on the conventional count) [COA-F11];
     which government forms comes from the gates above. A new election
     would follow about three months after the last mandate lapses
     [COA-F13]".
   - HE: "במבוי סתום הרשומה ההיסטורית קובעת אם תקום ממשלה: 2 מתוך 7 הכנסות
     מאז 1977 שבהן אף צד לא הגיע ל־61 עם רשימותיו ועם רשימות לשון המאזניים
     שתמכו בו הלכו לבחירות חוזרות, שתיהן ב־2019 (2 מתוך 5 בספירה המקובלת)
     [COA-F11]; איזו ממשלה תקום נקבע בשערים שלמעלה. בחירות חדשות היו
     נערכות כשלושה חודשים אחרי שפג המנדט האחרון [COA-F13]".

### 49.7 Not established

- **Ra'am-Balad, April 2019.** The 2/2 split of its four seats is
  approximate. No score depends on it.
- **Era roles are judgment.** The roles and the generic kingmaker rule were
  fixed before scoring. The Amcha-role variant moves both trees in the same
  direction.
- **ParlGov counts only portfolio-holding parties** (COA-F15). Coalition
  sizes here come from seats and the IDI pages, not from ParlGov sums.
- **The record is small and clustered.** It has 7 deadlocks, four of them
  from one 2019-21 run. On nine classes, no test separates the trees. The
  case for the candidate rests on three things:
  - the record counted on the tree's own event;
  - production's systematic repeat over-forecast on that record
    (P(≤ 2 | production) = 0.09);
  - the better repeat-event score.
- **Two gates remain unchecked against the record:** the pledge-break gate
  (`centre_defects`) and the unity depth beta.

## 50. Leave-one-out pollster scorecards in the harness (15-16 Oct, D-11)

**The defect.** `fit()` gives each firm a precision prior
lam ~ LogNormal(log 1/q^2, 0.20). q comes from `polling_average.quality_map()`,
which reads backtest_pollsters.csv: each firm's mean total absolute seat
error of its final polls over ALL eight graded cycles, 2009-2022
(backtest.py). Every harness refit of cycle c (validate_bayes at the eve,
validate_horizon at D-h, build_harness_cache) therefore had c's own
final-poll errors in its prior, a look into the outcome being graded. The
purest cases are firms graded in one cycle only: Miskar and TNS entered the
2019a fits, and Sarid the 2013 fits, with priors built entirely from their
own final poll against that cycle's result. Production 2026 is not
affected, because all eight cycles are in its past.

**The fix.** It touches the harness only; production is bit-identical.
- backtest.py also writes data/processed/backtest_pollster_cycles.csv.
  It has one row per (cycle, pollster, final poll) with the total absolute
  seat error, which is the scorecard's input. `backtest.scorecard(by_poll,
  exclude_cycle)` builds the scorecard. backtest_pollsters.csv,
  backtest_blocks.csv and backtest_summary.csv are unchanged.
- `polling_average.quality_map(exclude_cycle=c)` rebuilds the scorecard
  without c. It then applies the same transform (`quality_from_scorecard`:
  median ratio, sqrt, n/(n+3) shrinkage, clip 0.7-1.3). A firm graded only
  in c leaves the scorecard and gets the neutral 1.0.
  `quality_map()` with no argument is the old function. Rebuilt from the
  per-cycle file with no exclusion, it reproduces all 17 firms' q exactly.
- `bayes_model.lam_prior_q(firms, exclude_cycle)` and
  `fit(..., scorecard_exclude=None)`. Production passes nothing.
- validate_bayes:
  - `harness_prepare` records the window's cycle, and `load_or_fit` fits
    with that cycle left out of the scorecard.
  - `HARNESS_SCORECARD` takes `loo` (the default) or `full` (the pre-s.50
    prior, for grading legacy caches).
  - Every posterior written carries the attrs `scorecard` ("loo:<cycle>"
    or "full"), `lam_prior_q` (JSON, per firm) and `nuts_seed`.
  - `check_signature` refuses a cache fitted under the other scorecard. A
    cache without the attr predates s.50 and counts as "full". The check
    also covers the refit arms (alt_posterior) and validate_threshold.
- build_harness_cache logs each job's scorecard, fit time, divergences,
  max r-hat and min ESS.

**How far the prior moved.** In the full scorecard q spans 0.91-1.12.
Taking the cycle out moves it as follows:

| | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 |
|---|---|---|---|---|---|---|---|---|
| max abs(q_loo - q_full) | .028 | .041 | .010 | .112 | .033 | .045 | .034 | .025 |
| firms leaving | - | Sarid | - | Miskar, TNS | - | - | - | - |

2019a moves most: Direct Polls 1.025 -> 1.112, Midgam Project 1.000 ->
1.112, Kantar 1.123 -> 1.077, and Miskar .914 and TNS .930 -> 1.0. The
prior median of lam is 1/q^2, so it moves by at most about 2 dq (under 9%
outside 2019a), against a prior sd of 20% on the log scale. The fitted
posteriors moved even less. Posterior lam medians moved by at most 16%
(2019a) and at most 8% elsewhere. Endpoint mean shares moved by at most 0.1
seat in every window except 2019a D-56 (below).

**The cache.** The new cache is data/processed/harness_cache_loo in the
worktree that built it. It holds 32 windows: eve at 600/600; D-7, D-21 and
D-56 at 400/400. Settings: BAYES_CLR=1, HARNESS_FIDELITY=1,
HARNESS_SCORECARD=loo, NUTS seed 20261027.
- **Build.** It ran 15 Oct 17:42-19:14 on 4 queues: 5,499 s wall for
  21,758 s of fits (92-3,140 s each). Other sessions held the machine at
  load 40-70.
- **Still valid on the current main.** Main then moved twice: first to
  806c6f4 plus the seat-law patch, then to the s.48 calibration flags and
  hared_e0. Every window's fit inputs are still identical: y, blocks,
  weeks, firms, n_resp, noise multipliers, components, and the LOO q.
  fit() is unchanged, so no refit was needed. The past-cycle rows of
  polls.csv are identical in 804ff2d, 806c6f4 and the working copy.
- **Diagnostics.**
  - The 32 cached fits have 0 divergences, and endpoint-share r-hat is at
    most 1.01 in 31 of them.
  - 2021 D-56 had 9 divergences at the default seed. Its one reseed
    (FIT_SEED 20261028) has 0 divergences and endpoint r-hat 1.01, and is
    the cached fit.
  - 2019a D-56's endpoint shares do not mix: r-hat 1.42, and 1.53 for the
    reseed, which was rejected. D-56 is reported with and without that
    fold.
  - The shipped cache, for comparison, has 1 divergence (2020 D-7) and
    endpoint r-hat at most 1.02 everywhere.
  - sigma_g and sigma_f r-hat is above 1.05 in nearly every window of
    both caches: sigma_g in 32 of 32 in both, sigma_f in 23 (LOO) and 22
    (shipped). This is the known harness-draw mixing of the house-effect
    scales (s.46), which the projection does not read.

**Reproduction.** No baseline has been published yet for the current code
(registered pairs, plus hared_e0 since 16 Oct). The leaky column below is
therefore that code run on the shipped caches with HARNESS_SCORECARD=full.
Two earlier code states were checked against their published baselines:
- At the first rebase (registered pairs, haredi e1), the same full-scorecard
  runs reproduced s.47 exactly at eve, D-7 and D-21. The one rounding
  difference: the D-7 median is 1.5175, which s.47 prints as 1.518.
- The 804ff2d-based code with PAST_PAIRS reproduced s.46 and its width
  grid exactly.

**Restated baseline on the LOO scorecard.** Current code: registered pairs
and hared_e0, 3 seeds (0/100/200), each run's own mask. Each cell is
median / mean / coverage / Brier / interval.

| horizon | leaky (shipped caches) | LOO scorecard | LOO - leaky |
|---|---|---|---|
| eve | 1.457/1.625/.981/.0472/9.205 | 1.493/1.629/.981/.0475/9.217 | +.036/+.004/0/+.0003/+.012 |
| D-7 | 1.500/1.649/.990/.0489/9.458 | 1.487/1.648/.990/.0490/9.360 | -.014/-.001/0/+.0001/-.098 |
| D-21 | 1.608/1.789/.987/.0540/9.739 | 1.621/1.794/.990/.0541/9.690 | +.013/+.005/+.003/+.0001/-.049 |
| D-56 | 2.368/2.442/.922/.0882/14.684 | 2.381/2.454/.922/.0910/14.697 | +.012/+.012/0/+.0028/+.013 |
| D-56 without 2019a | 2.152/2.197/.932/.0634/11.805 | 2.156/2.193/.932/.0635/11.816 | +.004/-.004/0/+.0001/+.011 |

Median-MAE delta by fold (LOO - leaky, 3 seeds):

| | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 |
|---|---|---|---|---|---|---|---|---|
| eve | +.061 | +.028 | +.106 | +.095 | 0 | 0 | 0 | 0 |
| D-7 | 0 | 0 | 0 | 0 | -.067 | -.019 | 0 | -.026 |
| D-21 | +.030 | +.056 | -.030 | 0 | +.061 | -.037 | 0 | +.026 |
| D-56 | +.033 | 0 | 0 | +.071 | -.024 | 0 | +.019 | 0 |

- **Seed deltas of the median:**
  - Eve: +.011/+.051/+.046.
  - D-7: -.019/-.024/+.002.
  - D-21: +.033/+.031/-.025.
  - D-56: +.012/+.003/+.023.
- **Folds.** Under |d| < 0.1 every fold ties at every horizon except eve
  2015 (+.106).
- **Other moves:**
  - Eve: Brier 2019a +.0012.
  - D-7: interval 2013 -.53 and 2009 -.12.
  - D-21: interval 2021 -.43 and 2020 +.11.
  - D-56: 2019a Brier +.021 and mean +.12, both from the non-mixing fit.
- **Bloc-majority Brier** (seed-independent main rows): .0432 -> .0441.
- **The same caches under the first rebase's projection** (registered
  pairs, haredi e1):
  - Eve: -.005/+.003/0/+.0002/+.089.
  - D-7: -.014/-.001/0/+.0001/-.037.
  - D-21: +.025/+.005/+.003/+.0001/-.045.
  - D-56: +.019/+.013/0/+.0028/-.065.
  - Eve folds there: 2009 -.015, 2015 -.015, 2019a -.024.

**Refit-noise check.** The leaky 2009 and 2015 eve fits were refitted with
NUTS seed 20261028, keeping the full scorecard, and graded the same way.
- Against the shipped fits: median 0 / 0, mean +.009 / +.002, interval
  0 / +.064.
- List means in the seed-independent main rows move by at most .05 / .06
  seat under the reseed, and by at most .08 / .05 under the LOO scorecard.
  No list's median moves under either.
- The LOO fits therefore move the projection by about as much as a
  different NUTS seed does. In 2015 the q values moved by at most .01, so
  that window has no leak to remove.

**How much of the harness's accuracy came from the leak: none that the
harness can resolve.**
- **Metrics that agree across projection configurations and seeds** give
  an upper bound for what the leak bought. They are:
  - mean MAE: +.004 at the eve, -.001 at D-7, +.005 at D-21;
  - Brier: +.0001 to +.0003 at the eve to D-21;
  - coverage: equal, or up .003.
- **The median MAE changes sign.** It is integer-valued per list, so it
  moves by whole-list flips: +.036 at the eve here against -.005 under the
  e1 projection, on the same two caches. Its eve rise comes from 2015,
  2019a and 2009. 2015 is a fold whose prior did not move (q within .01).
  Neither rise is a leak effect.
- **2019a, the fold with the purest leak**, has two firms graded on it
  alone and the largest q shifts. Its list means move by at most .07 seat,
  the same size as the 2015 reseed.
- **D-56.** The +.0028 Brier comes entirely from 2019a, whose LOO fit
  does not mix. Without that fold: +.004/-.004/0/+.0001/+.011.
- **The reason is the prior's shape.** The sqrt, the shrinkage and the clip
  keep q within 0.91-1.16, against a lam prior sd of 0.20. The window's
  own 11-139 polls then decide lam.

**Width grid** (LOO, current code; it does not depend on the seed):

| width | coverage | MAE | Brier | interval |
|---|---|---|---|---|
| 0.6 | .960 | 1.610 | .042 | 8.724 |
| 0.7 | .972 | 1.615 | .044 | 8.813 |
| 0.8 | .981 | 1.621 | .045 | 8.964 |
| 0.9 (shipped) | .981 | 1.623 | .047 | 9.077 |
| 1.0 | .981 | 1.627 | .049 | 9.437 |
| 1.1 | .990 | 1.632 | .050 | 9.827 |

- **Leaky grid**, same code: interval 8.785 at 0.6 and 9.100 at 0.9.
- **width_nested_loo** (the held-out effect of the nested pick against
  0.9):
  - LOO cache: interval -.200, coverage -.020, MAE -.012, Brier -.0047;
    folds 5W/3L. Every fold picks 0.6 except 2020, which picks 0.7.
  - Leaky cache: -.315 / -.020 / -.014 / -.0047; 5W/3L; every fold picks
    0.6.
- **The finding stands.** Intervals are wider than they need to be, as
  s.46 and s.48 found. This grid does not reach s.48's 0.4, and
  RESID_SCALE is not changed here.

**Owner steps.**
1. Move harness_cache_loo into data/processed/harness_cache, or point
   HARNESS_CACHE_DIR at it. Until then, a default harness run
   (HARNESS_SCORECARD=loo) stops on the scorecard check against the shared
   pre-s.50 cache. Use HARNESS_SCORECARD=full to grade the legacy caches.
2. Commit data/processed/backtest_pollster_cycles.csv. quality_map(c) needs
   it, and `python src/backtest.py` regenerates it.
3. Re-run validate_bayes (seed 0, into data/processed), so the committed
   model_validation_*.csv and the site's track record come from the LOO
   harness. The LOO column above is the new yardstick.
4. The refit-arm caches (alr_latent, clr_latent) predate s.50. They are
   skipped as stale by default; grade them with HARNESS_SCORECARD=full or
   refit them LOO.

**Not done.**
- **The simple pipeline is still leaky.** validate_model.py builds its
  averages through `polling_average.poll_weights`, which uses the full
  scorecard. The simple-vs-Bayes head-to-head therefore still has a leaky
  comparator. poll_weights needs the same `exclude_cycle`.
- **LAM_PRIOR_SIGMA.** It was tightened from 0.25 to 0.20 (s.23) on a
  harness whose prior contained each graded cycle, and was not re-graded
  here. At the effect sizes above a re-grade is unlikely to move it.
- **The straddler record.** model_validation_threshold.csv (behind
  new_straddler_params) was built from pre-s.50 posteriors and was not
  re-measured.
- **2019a D-56.** Its LOO posterior is not converged at harness draws.

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

### 51.6 Decision (16 Oct)

- **hared_e0 shipped** as recommended: `HAREDI_FAMILY_FORM = "e0"` in
  production and `ALL_LAYERS["haredi_mean"] = "e0"` in the harness, so the
  harness baseline grades the shipped form from now on. The site states the
  case for it (a consistency correction), not a measured accuracy gain. The
  six-seed median is a tie; only Brier and mean MAE move, by about .0002
  and .002.
- The haredi under-count the projection draws becomes the raw record mean,
  0.98 seats, with the e1 sd of 1.77 kept. The site reads both from the
  parameters payload.
- arab_raam_split stays OFF. The two follow-up candidates (each list's own
  shrunk LOO record for the haredi family; a partial Ra'am allocation) are
  not registered yet.

## 52. Formation outputs: who leads, who sits, what each seat is worth (16 Oct, D-11)

Owner request (16 Oct): improve the formation outcome and next-PM outputs
by adding options where that makes them more accurate or more informative.
Nothing here changes a probability the tree already produced; every new
number is a different cut of the same simulations (8,000 Knessets x 200
parameter vectors).

- **Outcome split.** The owner's "Netanyahu + unaligned / defector
  coalition" is now reported as two outcomes: closed by kingmakers / Amcha
  (code 1) and closed by a change-bloc list breaking its pledge (code 9,
  the 2020 Gantz path). The gate order is unchanged; the defector gate now
  writes 9 and the unaligned gate still overrides it. The site keeps the
  owner's label as the parent row. 16 Oct numbers: 0.5% and 21.3% (sum
  21.8%, as before). So nearly all of the "Netanyahu + others" path is a
  pledge-break, not the kingmakers: in most deadlocks the unaligned lists
  are below the threshold.
- **Formation harness.** validate_formation.py now codes 2020 as 9 (1996
  and 2015 stay 1, closed by kingmakers). The finer partition can only
  lower the realized-class probability: 2015 0.458 -> 0.399 and 1996
  0.669 -> 0.613 under the production tree; 2020 unchanged (0.164). Mean
  log score over the informative cycles moves accordingly; the s.49
  verdicts do not change.
- **Who leads** (government_groups.csv): Netanyahu-led (0, 1, 9),
  change-led (2, 3, 4, 5, 8), unity (6), repeat (7), with 90% intervals
  over the parameter vectors; and "Netanyahu still prime minister when
  the formation round ends" = Netanyahu-led + repeat, since the outgoing
  government continues until a new one is constituted (Basic Law: The
  Government s.30, finding COA-F26, verified by the coordinating session
  against the WIPO Lex English text). 16 Oct: 33.5 / 27.4 / 14.0 / 25.1;
  in office 58.6.
- **What each seat is worth** (government_by_nb.csv): the outcome group
  by the Netanyahu bloc's seats as the headline counts them (NB_CORE +
  Amcha + The Haredi Public), clipped to 44 / 68. Netanyahu-led rises
  from 21% at 51 seats to 46% at 60 and 91% at 61; at 61+ it is not 100%
  because the headline bloc counts Amcha, whose joining is a drawn gate.
- **Who sits** (government_membership.csv): membership implied by the
  gate that formed the government, with no new behavioural assumption:
  the bloc's own lists (+ Amcha if right-aligned, + kingmakers that sided
  right) in 0/1/9; the change lists (+ centre-sided kingmakers; the
  Reservists only with no haredi or Arab partner; Amcha in 2/3/4/6) in
  2-8; Yisrael Beytenu out of 4 unless Liberman's haredi veto is waived and
  out of 5 unless his minority veto is; Shas / UTJ in 4 only where their
  gate fired; Likud in 6; Ra'am in 8; the Joint List and Ra'am as outside
  support in 5. The outcome-9 pledge-breaker is NOT named: the record
  says one happens (COA-F02), not which list. A first version that named
  the smallest list closing the gap (size principle) put The Democrats in
  most pledge-break governments and, once restricted to lists whose
  leaders sat with Netanyahu, still handed one party most of a 21% event;
  both were dropped. The path is reported as its own row.
- **PM names.** The allocation's last column is reported as "a Likud
  successor (unity government)" in outcome 6 and "another leader"
  elsewhere, instead of one "rotation / Likud successor" bucket.
- **Timetable.** The site states the statutory calendar (COA-F13) and the
  record's formation times (COA-F11); no timing model is fitted.

## 53. House effects centred on operations, not firms (16 Oct, D-11)

### 53.1 Pre-registration (written before any harness run of this arm)

**Why.** The fit identifies house effects by centring them on the
unweighted mean over the firms in the window (`delta_c = delta -
delta.mean(axis=0)`, the slope likewise). Firms that are one operation
therefore count several times in the centre: in 2026 Filber and Direct
Polls (the two halves of the 2019 Direct Polls, correlation group
sms_likud; leans on Likud +7.8 and +5.3 seats) are 2 of 9 firms, and the
Arab-sector firm Afkar, whose rows are converted to national shares, is a
ninth. The site says related firms count as one voice; in the centring
they do not. Centring on operations instead moves the 2026 latent by the
operation-weighted mean of the firm effects (Likud about -0.5 seat).

**Arm `house_group`.** Each firm weighs 1 / (number of firms of its
operation in the window); operation = pollster_meta.csv correlation_group,
except the methodology class phone_mixed, whose firms are separate
operations; firms whose name marks them as sector-only ("(sector)") weigh
0. The shift is applied to the endpoint draws as an exact
re-parameterisation of the fitted posterior: shares + sum_f w_f (delta_c_f
+ slope_c_f x t_end) / sum_f w_f, clipped at zero and renormalised (the
likelihood mean shares + delta_c + slope_c x t is unchanged). No refit.

**Grading.** The leave-one-out scorecard caches (s.50), shipped 16 Oct
configuration; eve on seed offsets 0/100/200 (ablation stream), D-7 and
D-21 on offset 0 (validate_horizon).

**Rule (the standing shipping rule).** Ships if, pooled over the three eve
seeds, it wins or ties (|d| < 0.1 seat) median MAE in every leave-one-
cycle-out fold, with mean MAE, threshold Brier and interval score not worse
beyond their noise floors (0.010 seat, 0.0010, 0.05) and coverage not
further from 0.90; and D-7 / D-21 do not contradict (no metric worse beyond
the same floors). Otherwise not shipped, and the site's "one voice" wording
for the fit is corrected instead.

### 53.2 Result: does not pass

Eve, offsets 0/100/200 pooled, against the shipped arm on the same seeds:
median MAE 1.4899 vs 1.4927 (every fold a tie: 2013 -.014, 2015 +.015,
2021 -.024, the rest 0); mean MAE 1.6351 vs 1.6291 (+.006, inside the
.010 floor); coverage .981 both; threshold Brier .0476 vs .0475; interval
score 9.296 vs 9.217 (+.078, beyond the .05 floor). D-7: median 1.473 vs
1.484, interval score 9.474 vs 9.254 (+.220). D-21: median 1.664 vs 1.612
(+.052), interval 9.697 vs 9.704. Fails on the interval score at eve and
D-7 and on the median at D-21. **Not shipped**; HOUSE_CENTRE stays "firm"
and the site's "one voice" wording for the fit is corrected as
pre-registered (related firms share a group lean; in the centring each
firm counts once, so the two Filber/Direct Polls halves count twice).

## 54. The haredi under-count allocated by each list's own record (16 Oct, D-11)

### 54.1 Pre-registration (written before any harness run of this arm)

**Why.** s.51.5 named this the next haredi candidate: the shipped family
mean (hared_e0, 0.98 seats) is spread over Shas and UTJ by base share,
which on the harness over-feeds UTJ (+0.55) and under-feeds Shas (-0.46).
The record, error = final poll minus result: Shas -1.11, -0.55, +0.38,
-2.67, -1.00, -0.25, -0.43, -1.43 (mean -0.88, under-polled in 7 of 8);
UTJ +0.67, -1.09, +0.50, -1.67, +0.71, +0.38, -0.29, 0.00 (mean -0.10).
The haredi desk (haredi_2026.json, verification pending) reports the same
pattern in 2019-22 pollster-cycles and a phone/online mode gap in Channel
13's haredi samples that is consistent with a Shas-heavy under-count.

**Arm `hared_alloc`.** The family MEAN is allocated by the lineages'
leave-one-cycle-out under-count shares, the Arab rule applied to the
haredi family: s_shas = u_S / (u_S + u_U), u = max(0, -mean error) over the
other seven cycles (Shas lineage = components containing "shas"; the rest
of the family is the UTJ lineage); base shares when neither is
under-counted or the window lacks one of the two. The family's random part
(t draw x sd) stays base-allocated. Production flag HAREDI_ALLOC
"record"; harness layer haredi_alloc. Expected 2026 effect: Shas about
+0.4, UTJ about -0.4 seat against the shipped allocation.

**Rule.** The s.53 rule: ships if, pooled over eve offsets 0/100/200, it
wins or ties median MAE (|d| < 0.1) in every leave-one-cycle-out fold with
mean MAE, threshold Brier and interval score not worse beyond 0.010 /
0.0010 / 0.05 and coverage not further from 0.90; D-7 and D-21 must not
contradict.

### 54.2 Result under the registered rule: does not pass (by .012 at D-21)

Eve, offsets 0/100/200 pooled: median MAE 1.4544 vs 1.4927 (-.038; paired
by seed -.035 / -.045 / -.035), folds 2009 -.091, 2013 +.056 (tie), 2019s
-.200, 2021 -.071, the rest 0; mean MAE 1.6071 vs 1.6291 (-.022, every
seed); coverage .981 both; threshold Brier -.0001; interval score 9.256 vs
9.217 (+.038, inside the .05 floor; by seed +.071 / +.002 / +.042). D-7
(offset 0): median -.050, mean -.028, Brier -.0001, interval +.013. D-21
(offset 0): median -.040, mean -.034, Brier -.0001, interval 9.766 vs
9.704 (+.062, beyond the .05 floor). Under the rule as registered the arm
**fails** on the D-21 interval score, by .012 on one seed.

## 55. Protocol amendment: the horizon gate on three seeds (16 Oct)

Written AFTER the s.54 result above, and disclosed as such. s.48 measured
the paired seed-to-seed noise of horizon interval scores at .08-.14, and
s.48.6 already listed "the horizon gate scored on three seeds" as the next
protocol step; one seed against a .05 floor cannot tell a .06 loss from
noise. From now on the D-7 and D-21 metrics in the shipping rule are pooled
over offsets 0/100/200, as the eve metrics are, with the same floors. The
amendment applies to every later candidate. It is used here to re-grade
s.54 (the only open candidate that failed at the horizon gate alone and
can be re-scored without a refit); CBfix (s.48.6) is the other one and is
queued. Because the amendment was written after a failing result, s.54 is
reported both ways on the site if it ships.

### 55.1 s.54 re-graded under the amendment: still does not pass

D-7 and D-21 on offsets 0/100/200 pooled. D-7: median 1.4427 vs 1.4866
(-.044), mean -.027, Brier -.0001, interval score 9.376 vs 9.360 (+.016,
inside the floor). D-21: median 1.5631 vs 1.6211 (-.058), mean -.034,
Brier -.0001, interval score 9.748 vs 9.690 (+.058; by seed +.062 /
+.066 / +.045). The D-21 interval loss is consistent across seeds, so it
is a real (small) cost, not seed noise, and it exceeds the .05 floor.
**hared_alloc is not shipped** under the rule as registered or as
amended. What the grade establishes: putting the haredi under-count on
Shas improves point accuracy at every horizon (median -.04 to -.06, mean
-.02 to -.03) and costs a little interval score three weeks out. The site
states this. HAREDI_ALLOC stays "base". The amendment stands for later
candidates.

## 56. Which government forms when a deadlock resolves (17 Oct, D-10)

### 56.1 Pre-registration (written 17 Oct before any run)

This subsection was written and hashed before any model code ran for this
test. Its sha256 is recorded in the patch notes. Nothing below 56.1 was
known when it was written.

**Why.** s.49.7 left the pledge-break gate unchecked against the record.
The events-desk verifier reviewed it
(`forecast_research/verify_events_oct2026.json`, `parameter_review`,
`centre_defects`, verdict "partly"). It found that the s.49 stage's gate
re-draw gives outcome 9, "Netanyahu + a change-bloc defector", about 0.41
of the resolved-deadlock mass. In the record a change list joined
Netanyahu in 1 of the 5 parliamentary-era deadlocks that resolved.

Outcome 9 is the largest single government path in the 2026 headline
(0.216). Kalshi prices P(Netanyahu PM | a government forms) near 0.30; the
model gives about 0.44 on the committed outputs. The verifier preferred
allocating the stage's resolutions by the record's shares over cutting
`centre_defects`. This section tests that as one pre-registered arm.

**The arm: `STAGE_RESOLUTION = "record"` (shipped value `"gates"`).**

- **Where it acts.** Only inside the s.49 stage. It applies to draws that
  are deadlocks on the s.49.2 event and in which the stage's Beta draw says
  a government forms.
- **Whether a government forms is unchanged.** The arm uses the same Beta
  posterior, the same generator and the same uniforms, so P(repeat) is on
  common random numbers between the arms.
- **Which government forms comes from the record.** In every such draw the
  government TYPE is drawn from the record and replaces the gate
  precedence. This includes draws where the first-pass gates had already
  formed a government. Outside a deadlock nothing changes: outcomes 0-3 are
  arithmetic.
- **Types and their outcome codes:**
  - unity → 6;
  - change + haredi party → 4;
  - Netanyahu + change-bloc defector → 9;
  - change + Ra'am → 8;
  - JL-backed minority → 5.

  These are exactly the outcomes a deadlock can reach, since 0-3 need a
  side at 61. The mapping inherits s.49's coding of the record: 1984 = 6,
  1992 and 2006 = 4, 2020 = 9, 2021 = 8.
- **Type shares.** One share vector is drawn per parameter vector from
  Dirichlet(α), with α = 0.5 + counts. It uses its own generator
  (`SEED + 5601`), so the behavioural, stage and PM streams are untouched.
- **Feasibility.** In each draw the shares are restricted to the types
  whose own gate condition in the tree can hold. The condition is evaluated
  on that draw's seats and its kingmaker and Amcha sides, with every
  behavioural flag of that gate at its favourable value. Each condition is
  monotone in its flags, so this is exact.
  - **Unity:** `ce_pure + res_c + amcha_ce + Likud >= 61`.
  - **Change + haredi:** `ce_pure + amcha_ce + Shas + UTJ >= 61` and
    Shas + UTJ > 0. This is both haredi lists crossing with Liberman's
    veto waived.
  - **Defector:** the tree's `feasible`: some change list's seats
    ≥ 61 − nb > 0.
  - **Change + Ra'am:** `ce_pure < 61` and `ce_pure + Ra'am >= 61`.
  - **JL-backed minority:** the JL and Ra'am abstain (plus Agudah's share
    only when `UTJ_ABSTAINS > 0`) and Liberman's minority veto is waived.
    The condition is then abstaining > 0 and
    `ce_pure > (120 − abstaining) / 2`.

  The shares are renormalised over the feasible types, and one uniform per
  draw picks the type. A draw with no feasible type stays a repeat and is
  counted as unresolved, as in s.49.
- **Details within a type.** These come from the existing gates,
  conditioned on that type's condition holding. They are computed exactly
  by enumeration rather than by re-drawing.
  - **Change + haredi:** the eight combinations of
    (`shas_on`, `utj_on`, `lib_haredi`) are weighted by the draw's
    p_shas and p_utj (configuration-conditional, COND) and by
    `liberman_haredi_ok`. Combinations are kept where `ch_seats >= 61` and
    a haredi list crosses, and one is drawn.
  - **JL-backed minority:** `jl_supports` is true, because it is part of
    the condition. The combinations of (`raam_supports`, `lib_ok`,
    `utj_abst`) are weighted by `raam_supports`, `liberman_minority_ok` and
    `UTJ_ABSTAINS` × (1 − p_utj). They are kept where the minority
    condition holds.
  - **Unity, change + Ra'am and defector** carry no detail flags. The
    defector stays unnamed, as in s.52. Ra'am is inside in outcome 8 by
    definition.
- **Membership flags (`government_membership.csv`).**
  - In a record-resolved draw of type 4, `shas_on`, `utj_on` and
    `lib_haredi` are set to the drawn combination.
  - In type 5, `jl_supports`, `raam_supports` and `lib_ok` are set the
    same way.
  - Every other flag keeps its first-pass value. The membership code does
    not read it for that outcome: it reads the YB, Shas and UTJ flags only
    in 4, and the Ra'am and JL support flags and YB's minority flag only
    in 5.
  - The rest of membership is the s.52 rule, applied to the outcome and to
    the fixed kingmaker and Amcha sides. The feasibility conditions use
    those same quantities, so each row's members reach the arithmetic that
    formed it.
- **What the arm makes inert.** In deadlock draws, the rates of four gates
  no longer move which government forms: unity (`likud_sans_bibi`),
  pledge-break (`centre_defects`), haredi (`shas_defects`, `utj_defects`)
  and Ra'am-joins. The haredi, Liberman and Ra'am-support rates still set
  the details. This is a property of the arm, disclosed in advance.
- **Mapping caveat, disclosed in advance.** The record's one unity, 1984,
  kept both leaders. The model's outcome 6 is unity with Likud *without*
  Netanyahu, which has no precedent (s.49.3). The arm gives outcome 6 the
  record's unity share regardless; the 2026 report states the size of
  that.

**The record classes and the prior.**

| cycle | regime | resolution | class |
|---|---|---|---|
| 1984 | parliamentary | unity with rotation | unity (6) |
| 1992 | parliamentary | Labor-Meretz + Shas | change + haredi (4) |
| 2006 | parliamentary | Kadima-Labor-Gil + Shas | change + haredi (4) |
| 2020 | parliamentary | Gantz's faction joins Netanyahu | defector (9) |
| 2021 | parliamentary | change + Yamina + Ra'am | change + Ra'am (8) |
| 1999 | direct | PM-elect Barak + Shas, UTJ and others | change + haredi (4), sensitivity only |
| 1995m | mid-term | Peres II at 58-59, Hadash and ADP outside | JL-backed minority (5), sensitivity only |
| 2008m | mid-term | Livni fails | a repeat: adds no type count |

The decisive counts use the parliamentary, post-election cases: unity 1,
change + haredi 2, defector 1, change + Ra'am 1, JL minority 0. The
Jeffreys-style Dirichlet is α = (1.5, 2.5, 1.5, 1.5, 0.5), with means
0.200, 0.333, 0.200, 0.200 and 0.067.

**Leave-one-cycle-out.**

- When `validate_formation.py` scores a cycle that is in the counts, that
  cycle's own resolution is removed:
  - 1984: unity becomes 0.5;
  - 1992 and 2006: haredi becomes 1.5;
  - 2020: defector becomes 0.5;
  - 2021: Ra'am becomes 0.5.
- The whether-stage and the unity prior keep their s.49 leave-one-out. The
  unity prior is inert in this arm.
- The repeats, 2019a and 2019s, are not in the type counts. Their type
  shares are the full-record ones; their leave-one-out is the
  whether-stage's.
- **Expected asymmetry, disclosed in advance.** Under leave-one-out each
  singleton class (unity, defector, Ra'am) falls to 0.5 of about 6.5 when
  its own cycle is scored. The shipped tree's gate rates were set with
  those cycles in view: `centre_defects` was "graded on the 2020
  realization", and `raam_joins` rests on the 2021 precedent. The decisive
  comparison is therefore stricter on the arm than on the shipped tree.
  The rule accepts that asymmetry as registered. The in-sample row below
  is reported to measure it.

**Scores.**

- **The harness:** s.49's, unchanged. It runs 17 Knessets, 2,000 rows per
  cycle and 200 parameter vectors drawn as in `main()`, on common random
  numbers, with COND centred on 2026.
- **The shipped tree:** s.49's "candidate" (the stage plus the record
  unity prior), called "shipped" here.
- **Primary score:** mean log P(realized class) over the eight informative
  cycles: 1984, 1992, 2006, 2015, 2019a, 2019s, 2020 and 2021.
- **Brier:** the multi-class score Σ_k (p_k − y_k)² over the ten outcome
  classes, averaged over the same eight cycles. It is added to the harness
  for this test. s.49's binary repeat Brier is reported too.

**Decision rule.** `stage_record` ships only if all three conditions hold.
They are judged on point estimates; bootstrap SEs are reported but not
used.

1. **Log score:** mean log P(realized) over the 8 informative cycles,
   leave-one-out: `stage_record` ≥ shipped.
2. **Brier:** multi-class Brier on the same cycles, leave-one-out:
   `stage_record` ≤ shipped.
3. **Tolerance (fixed before running):** for each realized 2019-2022
   outcome, P_stage_record(realized) ≥ 0.75 × P_shipped(realized), and
   above the harness's Monte Carlo floor. The outcomes are 2019a repeat,
   2019s repeat, 2020 defector, 2021 change + Ra'am and 2022 Netanyahu
   bloc alone. 0.75 allows a loss of at most 0.29 nats on any one recent
   cycle. That is about the size of the per-cycle gains s.49 treated as
   meaningful (+0.25 to +0.32). These are also the bloc-era cycles most
   like 2026.

If any one condition fails, the arm does not ship and `STAGE_RESOLUTION`
stays `"gates"`.

**Sensitivity variants (reported, not decisive; all leave-one-out unless
noted).**

- **+ 1999 (direct election):** haredi count 3. 1999 itself is left out
  when it is scored, at weight 0.5, in the secondary score.
- **+ mid-term:** minority count 1, from 1995m. 2008m is a repeat and adds
  no type.
- **+ 1999 and mid-term.**
- **In-sample (no leave-one-out), decisive counts:** measures the
  singleton-class penalty.

The whether-stage stays on the s.49 record in every variant, so the
variants move only the type shares. Also reported: the secondary score
with 1996 and 1999 at weight 0.5, and the binary repeat log score and
Brier.

**The 2026 run.** The flag is turned on and the output goes to a scratch
directory. The input is the committed `mixture_draws.parquet` (sha256
3741588ca50b4c31063566275b3601bd1420963e397e12c7c85ae91bd6691764). The
report covers, each against the shipped values:

- the outcome table;
- the groups (Netanyahu-led, change-led, unity, repeat, Netanyahu in
  office);
- the PM probabilities;
- membership;
- the type shares among resolved deadlocks under both arms.

It is reported whatever the verdict. Markets are a comparison, not a
target (s.49.5).

**Bit-identity.** With `STAGE_RESOLUTION = "gates"`, the formation outputs
must reproduce the committed files byte for byte:
`government_formation.csv`, `pm_probabilities.csv`,
`government_membership.csv` and `government_groups.csv`, and also
`government_deadlock.csv`, `government_sensitivity.csv` and
`government_by_nb.csv`. The harness's existing four trees must reproduce
their committed columns.

### 56.2 Results on the record (leave-one-cycle-out)

**Verdict: `stage_record` fails all three registered conditions and does
not ship. `STAGE_RESOLUTION` stays `"gates"`.**

**Run.** `validate_formation.py` ran on the committed v45 draws
(`mixture_draws.parquet`, sha256 3741588c…). It took 75 s. The run uses
the s.49 harness unchanged, with `stage_record` and the four registered
variants added, all on common random numbers.

**Checks.**

- With the flag off, all seven formation CSVs reproduce the committed
  files byte for byte.
- The four s.49 trees reproduce the unmodified harness exactly, on the
  same data: every original column, class row and calibration row.
- The committed `formation_validation*.csv` files date from v41. Two later
  refits moved the gates' 2026 centring. On today's draws the shipped
  tree's primary score is −1.579; the committed file has −1.574, and
  s.49.4 has −1.533. Re-running the harness at merge refreshes these
  files.

**P(realized class) by cycle.** Shipped is the s.49 tree; the arm is
`stage_record`. The four columns to its right are the registered,
non-decisive variants.

| cycle | realized | shipped | arm | + 1999 | + mid-term | both | in-sample |
|---|---|---|---|---|---|---|---|
| 1984 | unity | 0.197 | 0.184 | 0.184 | 0.169 | 0.167 | 0.315 |
| 1992 | change + haredi | 0.173 | 0.203 | 0.267 | 0.214 | 0.293 | 0.267 |
| 2006 | change + haredi | 0.189 | 0.176 | 0.238 | 0.174 | 0.250 | 0.238 |
| 2015 | Netanyahu + unaligned | 0.399 | 0.399 | 0.399 | 0.399 | 0.399 | 0.399 |
| 2019a | repeat | 0.131 | 0.131 | 0.131 | 0.131 | 0.131 | 0.131 |
| 2019s | repeat | 0.131 | 0.131 | 0.131 | 0.131 | 0.131 | 0.131 |
| 2020 | defector | **0.413** | **0.081** | 0.068 | 0.087 | 0.072 | 0.177 |
| 2021 | change + Ra'am | **0.179** | **0.023** | 0.020 | 0.022 | 0.019 | 0.047 |
| 1999 (weight 0.5) | change + haredi | 0.150 | 0.222 | 0.222 | 0.236 | 0.236 | 0.222 |
| 1996 (weight 0.5) | Netanyahu + unaligned | 0.613 | 0.613 | 0.613 | 0.613 | 0.613 | 0.613 |

**Scores and the decision rule.** Bootstrap SEs are over the scored
cycles.

| score (8 informative cycles unless noted) | shipped | arm | arm − shipped |
|---|---|---|---|
| 1. mean log P(realized), leave-one-out | −1.579 | −2.038 | **−0.459** (SE 0.284; P(≤ 0) 0.95): **fail** |
| 2. multi-class Brier, leave-one-out | 0.835 | 0.942 | **+0.107: fail** |
| 3. tolerance: 2019a / 2019s / 2020 / 2021 / 2022, arm ÷ shipped | | | 0.995 / 0.999 / **0.196** / **0.129** / 1.000: **fail** (2020, 2021) |
| + 1999 counts (log / Brier) | −1.579 / 0.835 | −2.007 / 0.922 | −0.428 |
| + mid-term counts | | −2.041 / 0.941 | −0.462 |
| + 1999 and mid-term | | −2.001 / 0.917 | −0.421 |
| in-sample, no leave-one-out | | −1.711 / 0.841 | −0.132 (SE 0.208) |
| + 1996, 1999 at weight 0.5 | −1.536 / 0.802 | −1.922 / 0.890 | −0.386 |
| YB 2015/2019a in Amcha's role | −1.624 / 0.863 | −2.082 / 0.971 | −0.459 |
| repeat vs government, 10 non-certain cycles (log / Brier) | −0.758 / 0.253 | −0.758 / 0.253 | 0 |
| realized class is the top class | 2 of 8 | 1 of 8 | |

Scoring 1984 as {1, 6} changes nothing, because class 1 cannot occur in
the 1984 deadlock. The repeat event is identical by construction: the
whether-draw is shared. In the calibration table the arm's [0, 0.05) bin
holds one realized class, 2021 at 0.023; the shipped tree's holds none.

**Per-cycle log gain of the arm over the shipped tree:**

| cycle | leave-one-out | in-sample |
|---|---|---|
| 1984 | −0.07 | +0.47 |
| 1992 | +0.16 | +0.43 |
| 2006 | −0.08 | +0.23 |
| 2020 | **−1.63** | −0.85 |
| 2021 | **−2.05** | −1.33 |

2015 and the 2019 repeats move by 0.005 or less.

**Why it fails.**

- **The leave-one-out penalty on singleton classes.** This was expected
  and registered. With its own case removed, 2020's defector share falls
  to 0.5 of 4.5 reachable weight, and 2021's Ra'am share to 0.5 of 6.5.
- **It also fails in-sample.** The registered in-sample row loses 0.13
  nats and still fails the tolerance (2020 0.43×, 2021 0.26×), so the
  leave-one-out penalty is not the whole story. The arm restricts the
  types by arithmetic only, then spreads the record's pooled shares over
  every type the arithmetic allows. The shipped gates instead concentrate
  mass on the types the configuration makes likely.
  - **2020.** "Change + haredi" needs both haredi lists to cross plus
    Liberman's waiver. The shipped gates give it 0.005 of formed
    governments; the arm gives it 0.54 under leave-one-out and 0.43
    in-sample.
  - **2021.** Ra'am is reachable only in draws where Yamina sides with the
    change lists. There the arm puts it on a par with four other types:
    0.04 of formed governments, against the shipped tree's 0.28.
  - **Where the arm gains:** 1992 and 1999, where the shipped tree
    under-forecasts the haredi crossing.
- **The verifier's diagnosis holds on the record itself.** Count the five
  resolved deadlocks and take, for each, the probability of each type
  given that a government formed.

  | type | shipped, expected | arm, expected | realized |
  |---|---|---|---|
  | defector | 2.53 | 1.73 | 1 |
  | change + haredi | 0.62 | 1.55 | 2 |
  | unity | 1.21 | 1.51 | 1 |
  | change + Ra'am | 0.50 | 0.13 | 1 |
  | JL-backed minority | 0.14 | 0.08 | 0 |

  The shipped gates over-forecast the defector, which is the verifier's
  point. The arm corrects the defector and the haredi counts but collapses
  Ra'am.
- **Monte Carlo.** With 200 vectors, the Dirichlet draws' sample means
  sit off their analytic values by a few points. For 1984 the drawn mean
  is 0.293 against an analytic 0.250, in the arm's favour. This is far
  below the 1.6-2.1 nat losses in 2020 and 2021.

**Membership consistency (registered design, checked).** Over 20
parameter vectors × 8,000 Knessets, in both modes, no government's listed
members fail to reach the arithmetic that formed it:

- outcomes 4, 6 and 8: members' seats ≥ 61;
- outcome 5: members > half of those present;
- outcome 9: the members plus the largest change list outside them
  ≥ 61.

Every outcome-4 government has a haredi member. In the 2026 run (1.6
million draws), 14 resolved deadlock draws had no reachable type under
the record and stayed repeats, against 1,215 left unresolved by the gate
re-draws.

Files (scratch, not committed): `formation_validation.csv`,
`formation_validation_classes.csv`, `formation_calibration.csv` (with the
rows "s.56 tolerance" and "s.56 decision") and
`formation_deadlock_record.csv` (rows "TYPES").

### 56.3 The 2026 effect if the arm were on (not shipped; reported as registered)

`government_formation.py --resolution record` was run into a scratch
directory on the same draws: 8,000 Knessets × 200 vectors.

| outcome | shipped [90%] | record arm [90%] | change |
|---|---|---|---|
| Netanyahu rightist coalition | 0.108 | 0.108 | 0 |
| Netanyahu + unaligned / Amcha | 0.005 | 0.005 | 0 |
| Change coalition (without Ra'am) | 0.081 | 0.081 | 0 |
| Change + unaligned / Amcha | 0.032 | 0.032 | 0 |
| Change + a haredi party | 0.058 [0.016, 0.127] | **0.194** [0.052, 0.357] | +0.136 |
| JL-backed minority | 0.033 [0.009, 0.071] | 0.020 [0.000, 0.081] | −0.013 |
| Unity (Likud without Netanyahu) | 0.141 [0.002, 0.356] | 0.147 [0.021, 0.357] | +0.006 |
| Repeat election | 0.252 [0.073, 0.493] | 0.251 [0.072, 0.493] | −0.001 |
| Change + Ra'am | 0.074 [0.037, 0.114] | **0.020** [0.002, 0.053] | −0.054 |
| Netanyahu + a change-bloc defector | 0.216 [0.046, 0.384] | **0.142** [0.026, 0.313] | −0.074 |

**Which government the resolved deadlocks get.** Shares of deadlock draws
that formed one, mean over vectors:

| type | shipped | record arm |
|---|---|---|
| unity | 0.271 | 0.274 |
| change + haredi | 0.112 | 0.376 |
| defector | **0.413** | 0.275 |
| change + Ra'am | 0.142 | 0.038 |
| JL-backed minority | 0.062 | 0.037 |

The shipped 0.413 confirms the verifier's "about two-fifths". Under the
arm, the defector's 0.275 exceeds its record mean of 0.200. In 2026, Ra'am
and the minority are rarely reachable, so their weight renormalises onto
the other three types.

**Groups:**

| group | shipped | record arm |
|---|---|---|
| Netanyahu-led | 0.329 [0.164, 0.500] | 0.255 [0.140, 0.427] |
| change-led | 0.278 [0.183, 0.376] | 0.347 [0.195, 0.524] |
| unity | 0.141 | 0.147 |
| repeat | 0.252 | 0.251 |
| Netanyahu in office | 0.581 [0.399, 0.735] | 0.506 [0.289, 0.713] |

**Prime minister:**

| PM | shipped | record arm |
|---|---|---|
| Netanyahu | 0.329 | 0.255 |
| Eisenkot | 0.256 | 0.289 |
| none (repeat) | 0.252 | 0.251 |
| Bennett | 0.068 | 0.105 |
| Likud successor (unity) | 0.071 | 0.073 |
| Liberman | 0.014 | 0.013 |
| another leader | 0.010 | 0.014 |

Conditional on a government forming, P(Netanyahu) falls from 0.440 to
0.340 and P(Eisenkot) rises from 0.342 to 0.386. Kalshi is about 0.30 and
0.48; markets are a comparison, not a target. Bennett's gain comes
through `PM_ALLOC` row 4, the haredi coalition with a right-credentialed
PM.

**Membership: P(in the government), shipped → record arm.**

| list | shipped | record arm |
|---|---|---|
| Likud | 0.470 | 0.402 |
| Yashar | 0.419 | 0.494 |
| Together (Bennett + Yesh Atid) | 0.418 | 0.492 |
| The Democrats | 0.416 | 0.489 |
| Yisrael Beytenu | 0.395 | 0.449 |
| UTJ | 0.372 | 0.417 |
| Shas | 0.362 | 0.403 |
| Otzma Yehudit | 0.295 | 0.226 |
| RZP | 0.232 | 0.177 |
| Amcha | 0.077 | 0.063 |
| Reservists | 0.074 | 0.070 |
| Ra'am, in government | 0.074 | 0.020 |
| Ra'am, outside support | 0.020 | 0.014 |
| Joint List, outside support | 0.033 | 0.020 |
| the unnamed change-bloc defector row | 0.216 | 0.142 |

Shas and UTJ rise although the Netanyahu-led share falls: the arm's
haredi mass is haredi entry into a change government.

**Central-draw sensitivity, P(Netanyahu PM):**

| type counts | P(Netanyahu PM) |
|---|---|
| decisive counts | 0.257 |
| + 1999 | 0.238 |
| + mid-term | 0.247 |
| + 1999 and mid-term | 0.234 |
| gates (shipped), same central draw | 0.298 |

**Inert gates, as registered.** Under the arm, the `utj_defects` grid and
the three `likud_sans_bibi` rows leave every PM probability unchanged:
P(Netanyahu PM) stays at 0.257 across unity 0.0625-0.18 and across
`utj_defects` 0.05-0.30 (Amcha at 0.60).

This is the 2026 face of the 2020 failure. "Change + haredi" triples,
from 0.058 to 0.194, on arithmetic reachability alone. The 2026 haredi
evidence is the 17 Sept reporting that the haredi parties lean to
"recommend nobody" and would sit in opposition for about a year, and UTJ
chair Asher's 29 Sept condition (see `utj_defects`). The shipped gates
price that evidence and the arm cannot see it.

The pre-registered mapping caveat costs little: outcome 6 moves by
+0.006.

### 56.4 Recommendation

**Do not ship.** Under the s.56.1 rule, `stage_record` fails all three
conditions:

- mean log −2.038 against −1.579;
- multi-class Brier 0.942 against 0.835;
- 2020 and 2021 keep only 0.20 and 0.13 of their shipped probability,
  against a floor of 0.75.

`STAGE_RESOLUTION` stays `"gates"`. The code is kept behind the flag:
with the flag off it is bit-identical, and the harness rows keep the test
reproducible.

**What the test establishes.**

- **The verifier's diagnosis is right on the record.** Given that a
  deadlock resolves, the shipped gates expect about 2.5 defector
  governments in the five historical resolutions, against 1 realized. In
  2026 they give the defector 0.41 of resolved deadlocks.
- **A configuration-blind record share is not the fix.** It loses far more
  on 2020 and 2021 than it gains on 1992 and 1999. In those two cycles the
  realized government was the one the configuration made likely: the arm
  overrides that with pooled shares. In 2026 it would also overrule the
  haredi parties' stated stance.
- **The Kalshi gap.** The arm closes most of it (P(Netanyahu | formation)
  0.44 to 0.34), but through a channel the record grades as worse, so the
  rule correctly refuses it.

**Next candidates (not run here; each needs its own pre-registration on
this harness, with the s.56 tolerance):**

1. **A configuration-aware allocation.** In each draw, the probability of a
   type would be proportional to two factors:
   - the record weight, fitted by conditional likelihood over each
     historical cycle's reachable set, not by raw counts;
   - the type's own gate probability in that draw.

   This would keep 2020's double haredi crossing near zero, keep 2021's
   Ra'am path where the configuration puts it, and let the record correct
   the overall defector rate.
2. **The verifier's gate-only fallback.** Cut `centre_defects` from 0.12
   to 0.08; the verifier's rerun puts outcome 9 at about 0.15. Watch the
   verifier's caveat: mass moves to unity without Netanyahu, which has no
   precedent.

**For the site.** The existing "deadlock-resolution weakness" disclosure
(v44) can now cite a graded number: on the record the shipped tree
expects about 2.5 defector governments in five resolved deadlocks, and
one happened.


### 56.5 Note added 17 Oct (engineering test suite)

The test suite (tests/test_formation.py) found a defect in the record path
graded here: type 4's reachability counts Yisrael Beytenu's seats whatever
liberman_haredi_ok is, and the detail draw then forces lib_haredi = True,
so Liberman's veto has no effect on that path (at liberman_haredi_ok = 0
the fallback even picks a zero-probability combination). The shipped
"gates" path is unaffected. The defect made the record arm seat a
change + haredi government more easily; it failed on the 2020 and 2021
cycles regardless. Fix before any re-grade of this path (strict xfail in
the suite marks it).

## 57. Near-threshold calibration (17 Oct, D-10)

### 57.1 The gap and where it comes from (diagnostic, run before 57.2)

**The gap.** The site's track record (build_val, D.val.rel; eve, the
main projection stream of the s.50 LOO harness) puts 20 lists in the
50-90% pass-probability bins: stated .673, realised .900 (18 of 20
passed; the two failures, New Right 2019a at 3.22% and Meretz 2022 at
3.16%, missed by under 0.1 pp). On the graded ablation stream (offsets
0/100/200, shipped configuration, shipped list mask) the same bins hold
21.3 lists per seed at the eve (stated .667, realised .844), 18.3 at D-7
(.680 -> .891) and 19.7 at D-21 (.729 -> .898). The 10-30% bin is
over-stated (eve .196 -> .100): the stack is too WIDE near the line, not
only shifted.

**Decomposition by layer.** Every layer ablation already in ABLATIONS
(validate_bayes), run on the s.50 LOO-scorecard caches (shared cache, read
only) at the eve, D-7 and D-21, offsets 0/100/200 (scratch runner, same
streams as validate_bayes / validate_horizon; its shipped rows reproduce
the s.50 / s.55 baselines exactly: eve 1.4927 / 1.6291 / .9807 / .0475 /
9.217, D-7 1.4866 / ... / 9.360, D-21 1.6211 / ... / 9.690). The cell is
the change in the mean pass probability of the lists in the SHIPPED
50-90% bins (fixed set, pooled over seeds) when the layer is switched off;
the fixed set's realised rate is .844 / .891 / .898 and its stated rate
.667 / .680 / .729.

| layer switched off | eve | D-7 | D-21 |
|---|---|---|---|
| per-list residual (resid) | +.158 | +.164 | +.145 |
| trailing-Likud (gevalt_cond) | +.026 | +.043 | +.015 |
| new-straddler (new_straddler) | +.010 | -.003 | -.004 |
| gevalt coupling (gevalt, GEVALT_SD 2.0) | +.004 | +.006 | +.006 |
| family shocks | +.002 | +.002 | -.002 |
| bloc swing | +.001 | +.004 | +.002 |
| loyal-sd | -.001 | -.001 | -.002 |
| withdrawn-list rule (35-day rule, no zero hold) | .000 | .000 | .000 |
| every layer (latent only) | +.190 | +.189 | +.134 |
| residual on vote shares (cal_B, s.48 arm B) | +.066 | +.070 | +.072 |
| residual index fix only (cal_Bfix) | +.022 | +.024 | +.025 |

- **The residual carries almost all of it** (.158 of the .177 eve gap).
  The other layers that push near-threshold lists down are small: the
  gevalt coupling .004-.006, the new-straddler layer .010 at the eve and
  nothing at the horizons, the withdrawn-list rule nothing (it drops no
  graded list differently). The trailing-Likud layer is second (.015-.043);
  it is harness-validated and not a target here.
- **Why the residual is too wide near the line.** decompose() fits the
  per-list sd on SEAT errors. A list that died at the threshold enters as
  a miss of its whole polled seat count: New Right 2019a 6.1 seats, Zehut
  5.6, Meretz 2022 4.4, Otzma-Yachad 2015 4.0 (vote misses 2.0 / 2.0 / 0.5
  / 0.6 u, u = 120 x share). The projection applies that sd to the vote
  share and then applies the threshold again, so each death is counted
  twice. In the small group (<= 8 seats, n 57, unique labels) the eight
  deaths have RMS 3.77 seats against 1.22 for the 49 lists that won seats;
  the group sd is 1.69 on seat errors and 1.09 on vote-share errors of the
  lists that ran (decompose_vote, n 61). This is the s.48 arm-B mechanism.
- **The straddler record on CEC vote shares, re-measured on the s.50 LOO
  caches** (validate_threshold, HARNESS_FIDELITY=1, layer OFF, D-56/D-21;
  scratch output sha256 cce4c050...). First-cycle lists that RAN: n 10,
  mean drift -0.617 pp, sd 1.314 (D-21 -0.43, n 6; D-56 -0.91, n 4); pass
  rate .20 against a mean p_pass of .43. The shipped constant (-1.6, sd
  2.6) is the seat-implied record (failed lists at 0%, three non-runners -
  Joint List 2019a, IDP 2019s, the Israelis 2021 - counted as total
  desertion). Established lists that ran: n 32, mean drift +0.50 pp, pass
  rate .91 against .63; that mean rests on 2021 (without it +0.18; without
  2021 and the two sector families -0.12), so it is not registered as a
  candidate.

**Disclosure.** The decomposition ran every ABLATIONS arm on exactly the
seeds and streams the rule below uses, so the pooled grade of cal_B was
seen before this registration (median / mean / coverage / Brier /
interval, shipped first): eve 1.4927 -> 1.5196 / 1.6291 -> 1.6013 / .981
-> .972 / .0475 -> .0409 / 9.217 -> 8.671; D-7 1.4866 -> 1.4591 / 1.6478
-> 1.6273 / .990 -> .951 / .0490 -> .0439 / 9.360 -> 9.008; D-21 1.6211
-> 1.6196 / 1.7943 -> 1.7550 / .990 -> .952 / .0541 -> .0502 / 9.690 ->
9.526. Its per-fold medians were not examined before 57.2 was hashed.
Also seen and NOT registered here: no_gevalt (eve 1.4660 / 1.6250 / .981
/ .0468 / 8.938; it barely touches the near-threshold bins) and cal_Bfix
(eve 1.4858 / 1.6253 / .972 / .0447 / 9.011). nstrad_ran had never been
run.

### 57.2 Pre-registration (written before any grade of nstrad_ran and before the fold check of cal_B)

**Candidate 1, `nstrad_ran` (the s.46.1 lead).** The new-straddler layer
unchanged in form (first-cycle lists - no component polled in an earlier
cycle - whose projected share sits in [-0.75, +1.5] pp of the threshold;
a zero-sum draw N(mu, sd) pp against the field), with mu and sd measured
on the CEC VOTE SHARES of the first-cycle straddlers that RAN, instead of
the seat-implied record.
- Record: the rows `new & ran` of validate_threshold under
  HARNESS_FIDELITY=1 with the layer OFF (an explicit layer-off base), on
  the s.50 LOO-scorecard caches, D-56 and D-21: the ten rows of 57.1,
  carried in validate_bayes as NSTRAD_RAN_RECORD with that provenance.
- LOO: the graded cycle's rows are left out (n >= 3 or the layer is off,
  as shipped). Fold values: without 2009 -0.271 / 1.409 (n 7), 2013 -0.707
  / 1.460 (n 8), 2019a -0.478 / 1.427 (n 8), 2021 -1.020 / 0.747 (n 7),
  the other four -0.617 / 1.314 (n 10).
- Production: bayes_model.NEW_STRADDLER_RECORD "ran" uses the full record
  (mu -0.617, sd 1.314, same band); "seat" (default) is shipped. Harness
  layer `nstrad_record` "ran" (default "seat"), arm `nstrad_ran`.

**Candidate 2, `cal_B` (s.48 arm B, unchanged).** The per-list residual
line re-estimated leave-one-cycle-out on vote-share errors of the lists
that ran (error_decomposition.decompose_vote; full sample 0.73 + 0.073 x
u), at the shipped width 0.9. Production bayes_model.RESID_SPACE "vote";
harness layer resid_space "vote". It was graded in s.48 on the leaky
cache with one horizon seed (it failed the D-21 interval score by .099),
was never re-graded on the s.50 caches, and is re-graded here under the
s.55 three-seed horizon protocol. Its pooled outcome is known (57.1).

**Grading.** Shipped vs each arm on the s.50 LOO-scorecard caches (shared
cache, read only; outputs in scratch), shipped list mask (`*_fixed`).
- Eve: `HARNESS_ABLATIONS=shipped,no_nstrad,nstrad_ran,cal_B
  HARNESS_SKIP_WIDTH=1 python src/validate_bayes.py`, offsets 0/100/200.
- D-7 and D-21: `HORIZONS=7,21 HORIZON_SKIP_GRID=1
  HORIZON_LAYERS='no_nstrad:{"new_straddler": false};nstrad_ran:
  {"nstrad_record": "ran"};cal_B:{"resid_space": "vote"}' python
  src/validate_horizon.py`, offsets 0/100/200, against "calendar".
- The pair, if graded: `nstrad_ran_B` = {"nstrad_record": "ran",
  "resid_space": "vote"}, same commands.
- Pooling: per seed the mean over the eight cycles, then the mean over
  the three seeds. A fold is a cycle, its value the three-seed mean.
- no_nstrad (layer off) is reported beside nstrad_ran as the explicit
  layer-off base; it is not part of the rule.

**Rule (s.53 / s.55).** An arm passes if, at EACH of eve, D-7 and D-21:
- it wins or ties median MAE in every leave-one-cycle-out fold (fold
  delta < +0.1 seat);
- pooled mean MAE, threshold Brier and interval score are not worse than
  shipped by more than 0.010 / 0.0010 / 0.05;
- pooled 90% coverage is not further from 0.90 than shipped's.

If both arms pass, the pair is graded as one arm (`nstrad_ran_B`) under
the same rule before both are recommended; if the pair fails, the passing
arm with the lower eve threshold Brier is recommended alone.

**Reported, not gating.** The reliability table (site bins 0-.1-.3-.5-.7-
.9-1, three seeds pooled, eve / D-7 / D-21) for shipped and each arm, the
50-90% row (n, stated, realised), the Brier over the lists shipped puts
in [0.1, 0.9), per-fold medians, and the 2026 effect: the frozen 16 Oct
production posterior (m3_idata.nc copied to scratch), the
BAYES_PROJECT_ONLY projection (bayes_model.project, config "current") at
the production seed and +1/+2, flags off reproducing main's
bayes_forecast_2026.csv; p_pass of RZP-Zehut, Otzma, Ra'am, Amcha, the
Reservists and Blue and White, and the bloc probabilities.

### 57.3 Results: neither arm passes

The 57.2 text (from its heading to the end of the reliability paragraph)
was hashed at 22:11 and committed before any grade (worktree commit
60dcaee; sha256 31dd0872bf436576099140637ea15fe14f4c366b9d4f527fff5cc6efd4605b11).
Runs: the registered commands on the shared s.50 cache (read only),
HARNESS_OUT_DIR in scratch, at most four processes.

**Reproduction.** With the flags at their shipped values the patched
harness is bit-identical to the committed s.50 run: at offset 0 every
shipped and no_nstrad row of model_validation_ablation.csv and the whole
model_validation_bayes_lists.csv match main's files to the last digit, and
the three-seed shipped rows are the s.50 / s.55 baselines (eve 1.4927 /
1.6291 / .9807 / .0475 / 9.217; D-7 1.4866 / 1.6478 / .9896 / .0490 /
9.360; D-21 1.6211 / 1.7943 / .9896 / .0541 / 9.690). The scratch runner
behind the reliability tables reproduces the graded rows of every arm
exactly.

**Pooled, three seeds** (median / mean / coverage / threshold Brier /
interval; median folds W/T/L at |d| < 0.1):

| horizon | shipped | nstrad_ran | cal_B | no_nstrad (layer off, reported) |
|---|---|---|---|---|
| eve | 1.4927/1.6291/.981/.0475/9.217 | 1.4937/1.6391/.981/.0507/9.232 (0/8/0) | 1.5196/1.6013/.972/.0409/8.671 (0/6/2) | 1.4527/1.6303/.981/.0523/9.212 (1/7/0) |
| D-7 | 1.4866/1.6478/.990/.0490/9.360 | 1.5186/1.6557/.990/.0519/9.330 (0/7/1) | 1.4591/1.6273/.951/.0439/9.008 (1/7/0) | 1.4981/1.6538/.990/.0538/9.356 (1/6/1) |
| D-21 | 1.6211/1.7943/.990/.0541/9.690 | 1.6256/1.7994/.990/.0570/9.676 (0/8/0) | 1.6196/1.7550/.952/.0502/9.526 (1/7/0) | 1.6568/1.7930/.990/.0577/9.680 (0/7/1) |

- **nstrad_ran fails.** Threshold Brier is worse beyond the .0010 floor at
  all three horizons (+.0031 / +.0029 / +.0029; +.0027 to +.0032 in every
  seed), and the D-7 2019a fold loses +.286 on the median. Mean MAE at the
  eve is +.00999, just inside its floor. The interval score is a tie.
- **cal_B fails on the eve fold test only.** 2019s +.100 is exactly on the
  tie boundary and is therefore not a tie: Blue and White's median goes
  from 32 to 31 seats in all three seeds. 2022 loses +.128: Likud's median
  goes from 32 to 33, Yesh Atid's from 25 to 26 and UTJ's from 7 to 8 in
  one or two seeds, against Yisrael Beytenu going from 5 to 6. Every other
  test passes at every horizon. Beyond the floors, cal_B improves the mean
  MAE by .028 / .021 / .039, the Brier by .0066 / .0051 / .0039 and the
  interval score by .546 / .352 / .164. Coverage moves toward .90 (.981 to
  .972, .990 to .951, .990 to .952). The eve pooled median is worse by .027
  (seeds +.067 / -.029 / +.042). The s.48 D-21 interval-score loss (+.099
  on one leaky seed) does not reproduce here (-.164 on three LOO seeds).
  Both lost folds are one-seat median flips on large lists, not
  near-threshold misses. With a narrower small-list residual,
  sub-threshold lists die in more draws, and their seats move to the large
  lists.
- The pair was not graded: the rule grades it only if both arms pass.

**Reliability, three seeds pooled** (lists per seed, stated -> realised):

| horizon | arm | 0-.1 | .1-.3 | .3-.5 | .5-.7 | .7-.9 | .9-1 | 50-90% row | gap |
|---|---|---|---|---|---|---|---|---|---|
| eve | shipped | 1.0 .089->0 | 10.0 .196->.100 | 3.0 .443->.778 | 14.0 .600->.762 | 7.3 .796->1 | 58.7 .991->1 | 21.3 .667->.844 | +.177 |
| eve | nstrad_ran | 1.0 .089->0 | 8.7 .213->.115 | 4.3 .410->.538 | 14.0 .607->.762 | 7.3 .795->1 | 58.7 .991->1 | 21.3 .672->.844 | +.172 |
| eve | cal_B | 6.7 .047->0 | 4.3 .194->.231 | 3.3 .424->.700 | 9.7 .603->.690 | 8.7 .824->1 | 61.3 .995->1 | 18.3 .708->.836 | +.129 |
| D-7 | shipped | 2.0 .076->0 | 9.0 .206->.111 | 5.7 .445->.647 | 12.0 .615->.833 | 6.3 .801->1 | 59.0 .990->1 | 18.3 .680->.891 | +.211 |
| D-7 | nstrad_ran | 2.0 .076->0 | 7.7 .229->.087 | 6.0 .418->.667 | 13.0 .612->.769 | 6.7 .805->1 | 58.7 .990->1 | 19.7 .677->.848 | +.170 |
| D-7 | cal_B | 7.0 .049->0 | 4.3 .211->.308 | 5.0 .423->.600 | 8.7 .621->.885 | 6.7 .815->.850 | 62.3 .993->1 | 15.3 .705->.870 | +.164 |
| D-21 | shipped | 1.0 .077->0 | 10.3 .207->.097 | 6.7 .413->.600 | 8.0 .597->.875 | 11.7 .819->.914 | 57.3 .992->1 | 19.7 .729->.898 | +.170 |
| D-21 | nstrad_ran | 1.0 .077->0 | 8.3 .219->.120 | 8.7 .406->.462 | 8.0 .597->.875 | 11.7 .816->.914 | 57.3 .992->1 | 19.7 .727->.898 | +.171 |
| D-21 | cal_B | 7.0 .057->0 | 6.0 .221->.333 | 5.0 .424->.600 | 5.3 .588->1 | 7.3 .827->.864 | 64.3 .990->.984 | 12.7 .726->.921 | +.195 |

- **Two caveats on the table.**
  - The 50-90% row is binned by each arm's own probabilities, so cal_B's
    D-21 row grows. cal_B moves lists out of the band, most of them
    upward.
  - On the lists the SHIPPED arm puts in the 50-90% band, cal_B lifts the
    stated rate from .667 / .680 / .729 to .733 / .750 / .801, against
    .844 / .891 / .898 realised. It closes about 40% of the gap.
- **Near-threshold Brier**, over the lists shipped puts in [.1, .9):
  shipped .143 / .153 / .153, nstrad_ran .153 / .162 / .161, cal_B .126 /
  .140 / .144.
- **By class**, for lists projected in the band (rates are per seed):
  - Established lists, 18-21 per seed, passed .86 / .84 / .89. Shipped
    gives them .60 / .58 / .61 (Brier .156 / .172 / .190); cal_B gives .66
    / .62 / .66 (.135 / .160 / .186). nstrad_ran leaves them unchanged.
  - First-cycle lists, 5-6 per seed, passed .20 / .20 / .17. Shipped gives
    them .28 / .27 / .24 (Brier .186 / .177 / .158), nstrad_ran .37 / .37 /
    .32 (.245 / .229 / .201), and layer off .49 / .50 / .40.
  - The underconfidence is therefore an ESTABLISHED-list problem. The
    shipped -1.6 / 2.6 is the wrong number for the vote drift. It is still
    the better-calibrated pass probability for first-cycle lists under
    this stack: the over-wide residual gives sub-threshold debutants too
    much chance of crossing, and the over-stated desertion offsets that.
- **Post-hoc, not part of the rule.** nstrad_ran on top of cal_B is worse
  than cal_B alone on Brier at every horizon (+.0037 / +.0032 / +.0032).
  First-cycle p_pass under the pair is .34 / .34 / .26, against .27 / .26
  / .20 under cal_B. The joint change s.47.2 asked for does not rescue the
  re-measured constant.

### 57.4 2026 effect (frozen production posterior; outputs in scratch)

The posterior is main's m3_idata.nc of 16 Oct 18:54, copied to scratch
(sha256 654a4414...). It was run through the BAYES_PROJECT_ONLY path of
bayes_model.main with bayes_model.PROCESSED_DIR pointed at a scratch copy,
so the repo's data/processed was never written. Projection seeds were the
production seed, +1 and +2.
- **Reproduction.** With the flags off, the run is byte-identical to the
  committed v45 bayes_forecast_2026.csv and bayes_forecast_blocs.csv.
- **Main's live files differ.** Main's working-copy bayes_forecast files
  were rewritten by another process at 17 Oct 22:00 (P(NB>=61) .128), so
  they are not the reference here. This session wrote nothing outside its
  worktree and scratch.

| (seeds +0 / +1 / +2) | shipped | nstrad_ran | cal_B |
|---|---|---|---|
| RZP-Zehut pass | .560 / .559 / .562 | .549 / .547 / .552 | .618 / .612 / .619 |
| Otzma pass | .796 / .787 / .796 | .786 / .777 / .782 | .852 / .840 / .850 |
| Ra'am pass | .761 / .769 / .764 | .754 / .761 / .755 | .880 / .883 / .878 |
| Amcha pass | .252 / .251 / .245 | .294 / .293 / .289 | .231 / .230 / .225 |
| Reservists pass | .225 / .225 / .220 | .255 / .259 / .252 | .202 / .204 / .204 |
| Blue and White pass | .016 / .015 / .016 | .017 / .015 / .017 | .000 / .000 / .000 |
| P(NB >= 61) | .145 / .131 / .137 | .150 / .137 / .145 | .116 / .106 / .108 |
| P(change bloc >= 61) | .070 / .072 / .074 | .072 / .073 / .076 | .056 / .059 / .056 |
| P(neither) | .785 / .797 / .789 | .778 / .790 / .779 | .828 / .835 / .836 |
| NB seats, mean [90%] | 53.0 [42-65] | 53.1 [41-65] | 52.8 [42-64] |

- **Central seats.** They are unchanged under every arm: Likud 25, Yashar
  23, Together 11, Democrats / Joint List / UTJ 9, Shas and YB 8 (Shas 9 at
  one seed of each candidate), Otzma 6, Ra'am 5, RZP-Zehut 4.
- **nstrad_ran.** Its desertion on Amcha and the Reservists is smaller, so
  less is redistributed to the field. Amcha and the Reservists rise about
  4 and 3 points; every other list falls slightly.
- **cal_B.** It moves the three established satellites toward the
  polls-and-markets reading of EVT-F25: RZP-Zehut .56 to .62, Otzma .79 to
  .85, Ra'am .76 to .88. It still sits well short of the markets (.86-.95
  / .95+ / .91-.98). It lowers the sub-threshold lists and P(NB >= 61):
  13.8 to 11.0 on the seed mean. Both blocs' majority tails thin, and
  deadlock rises from 79.0 to 83.3.

### 57.5 Recommendation

- **Nothing ships from s.57.** Under the pre-registered rule neither arm
  passes. NEW_STRADDLER_RECORD stays "seat" and RESID_SPACE stays "seat",
  and both flags are in the code at the shipped values. The headline is
  unchanged.
- **What the grade establishes.**
  - The near-threshold underconfidence is real at every horizon: the
    50-90% band realises .84-.90 against .67-.73 stated.
  - It belongs to ESTABLISHED lists: those in the band pass .84-.89
    against .58-.61 stated.
  - Its main source is the per-list residual: switching the residual off
    moves the band's stated rate by +.145 to +.164 of a .17-.21 gap, and
    no other layer moves it by more than .043. Part of the residual's
    width is threshold deaths counted twice.
  - The gevalt coupling (+.004 to +.006), the new-straddler layer (+.010
    at the eve, nothing at the horizons) and the withdrawn-list rule (0)
    are not the cause.
  - The vote-share residual (cal_B) is the only arm graded here that
    narrows the gap without losing a pooled metric beyond its floor. It
    fails only the eve fold test, on one-seat median flips of large lists
    (2019s on the boundary, 2022 +.128).
  - The new-straddler constant re-measured on CEC shares is the honest
    drift. It is a worse pass-probability calibration, so the shipped
    -1.6 / 2.6 stays.
- **For the site.** The track record should keep stating the gap. It can
  now add that the gap sits with established lists and comes mostly from
  the width of the per-list residual. The pass probabilities of
  RZP-Zehut, Otzma and Ra'am are therefore more likely understated than
  overstated: on the record, established lists stated at 60% passed about
  85% of the time. No number on the site changes.

### 57.6 Not established

- **cal_B with a re-chosen width, and Bfix on three horizon seeds.**
  Neither was graded. Bfix is the CBfix item queued since s.48.6; in the
  57.1 diagnostic its pooled numbers did not lose a floor. A residual that
  narrows only the small-list group, keeping the large-list widths and
  medians, would address cal_B's actual failure mode. It is not
  registered, so it is a new candidate if wanted.
- **The first-cycle rule is by party id.**
  - RZP 2021 and Ra'am 2021 count as debutants: both had run inside
    alliances, and both passed.
  - Without them the CEC-share first-cycle record is n 8, mean -1.14 pp.
  - A lineage-based definition is a separate candidate, and its LOO
    re-grade would need its own layer-off record.
- **The established-straddler drift** (+0.50 pp, n 32) is not registered.
  It rests on 2021: +0.18 without that cycle, and -0.12 without 2021 and
  the two sector families.
- **no_gevalt.** It looked favourable on the pooled metrics in the
  diagnostic (eve interval -.28, Brier -.0007). It barely touches the
  near-threshold band, and it was not graded under the rule.
- **D-56** was not graded.
- **The 2026 effect is the plain projection.** The registration mixture,
  official forecast and formation chain was not run.
- **Production-only layers are not graded here.** The certainty churn,
  EVENT_RISK 1.2, NEW_LIST_MULT and the kalpi caps also widen 2026's
  near-threshold lists and have no harness analogue.

## 58. Event risk on the remaining calendar (17 Oct, D-10)

A judgment layer, outside the backtest (no harness analogue), so it changes
only on cited, verified evidence. Ported from the 15 Oct draft (judgment
layers, scratch judgment_layers_s52.patch; never merged) onto the current
code.

**What changed.** `EVENT_RISK = 1.2` multiplied the election-day bloc
swing at every horizon, the final build included; it was set at D-58 and
never decayed. With `EVENT_RISK_HORIZON = True` the swing keeps its graded
scale (t(5) on BLOC_SWING_SD 3.36, sd 4.33 seats) and a compound-Poisson
walk of Netanyahu-bloc jumps runs over h = days to election minus the
4-day blackout. Rate: 8 events in 1,096 days (DYN-F24, corrected); sizes:
the within-pollster 0-35 day effects of the five events that reproduced
(+2.15, +1.6, +0.9, +3.1, +0.7 seats) and October 7 (-11.2, one firm;
DYN-F22, corrected); blackout D-4 (DYN-F08, corrected). The walk draws
from a jumped child generator, so the rest of the projection's stream is
unchanged.

**Why.** Events before the blackout are observed by the polls and enter
through the refit; the swing was fitted on final-poll errors and already
covers the blackout. Only the unpolled days between the asof and the
blackout are new risk. The verified hazard arithmetic (DYN-F24) gives an
equivalent multiplier of 1.005-1.036 at D-12; the events verifier
(verify_events_oct2026.json, EVENT_RISK review: "partly") judged 1.05-1.10
now, falling to 1 by the final build, defensible.

**Effect** (production posterior of 16 Oct, Bayesian projection before the
registration mixture, two seeds): equivalent multiplier 1.029 at h = 8;
P(NB>=61) 14.5 / 13.1 -> 12.8 / 11.8; NB mean 53.0 unchanged; 90% NB
interval 42-65 -> 42-64. At twice the record rate (markets price an Israel
or Iran strike before polling day at about 0.12, EVT-F17, roughly twice the
base rate): multiplier 1.057, P(NB>=61) 13.0 / 12.0.

**Not established.** The event record is short (eight events, three years)
and one size (October 7) rests on a single firm at 0-35 days. The sign of
any event is not fixed (DYN-F21, DYN-F22). Shipped as a disclosed judgment;
the post-election review grades it.

## 59. Deadlock resolution, configuration-aware (17 Oct, D-10)

### 59.1 Pre-registration (written 17 Oct before any run)

This subsection was written and hashed before any s.59 code existed or
ran. Its sha256 is committed alone and recorded in the patch notes.
Nothing below 59.1 was known when it was written. The base is main at
cb4d1a6, with s.56 merged and the harness CSVs refreshed. It contains the
s.56 numbers quoted here.

**Why.** s.56 confirmed the verifier's diagnosis on the record. Given that
a deadlock resolves, the shipped gates expect 2.53 defector governments
across the five historical resolutions, against 1 realized. In 2026 they
give the defector 0.413 of resolved deadlocks.

The configuration-blind fix (s.56) failed: it overrode what each
Knesset's configuration made likely. This section tests two other
answers, each against the shipped tree:

- **Arm A, `stage_mix`:** the record and the gates combined.
- **Arm B, `defect_08`:** a gate-only cut.

**Common to both arms.**

- **The harness:** s.49/s.56's, unchanged. It runs 17 Knessets, 2,000 rows
  per cycle and 200 parameter vectors drawn as in `main()`, on common
  random numbers, with COND centred on the 2026 draws. The stage's
  whether-draw and the unity prior keep their s.49 leave-one-out.
- **The shipped tree:** the s.49 tree (`candidate` in the harness), with
  the stage on and `STAGE_RESOLUTION = "gates"`.
- **Scores:**
  - primary: mean log P(realized class) over the eight informative cycles
    (1984, 1992, 2006, 2015, 2019a, 2019s, 2020, 2021);
  - multi-class Brier Σ_k (p_k − y_k)² over the same eight cycles;
  - the s.56 secondary rows: 1996 and 1999 at weight 0.5, YB in Amcha's
    role, and the binary repeat score.

**Decision rule** (s.56's, unchanged). Each arm is judged on its own
against the shipped tree, on point estimates:

1. **Log score:** mean log P(realized), 8 informative cycles,
   leave-one-out: arm ≥ shipped.
2. **Brier:** multi-class Brier, same cycles, leave-one-out:
   arm ≤ shipped.
3. **Tolerance:** for each realized 2019-2022 outcome, P_arm(realized)
   ≥ 0.75 × P_shipped(realized), and above the Monte Carlo floor. The
   outcomes are 2019a repeat, 2019s repeat, 2020 defector, 2021 change +
   Ra'am and 2022 Netanyahu bloc alone.

An arm ships only if all three hold. If both arms pass, the one with the
higher primary mean log ships, and both are reported. If neither passes,
`STAGE_RESOLUTION` stays `"gates"` and `centre_defects` stays 0.12. The
arms are not combined here: an A + B tree would need its own
registration.

**Arm A: `stage_mix` (`STAGE_RESOLUTION = "mix"`).**

- **Where it acts.** As in s.56: every deadlock draw (s.49.2 event) in
  which the stage's Beta draw says a government forms. This includes draws
  the first-pass gates had already resolved. Whether a government forms is
  unchanged: the same generator and the same uniforms as the shipped
  stage.
- **The type draw.** One uniform per draw, from the s.56 generator
  (`SEED + 5601`), picks the type with
  P(type t | draw) ∝ w_t × g_t(draw), over the five types (unity 6,
  change + haredi 4, defector 9, change + Ra'am 8, JL-backed minority 5).
- **g_t(draw)** is the type's own gate probability in that draw, from the
  existing behavioural gates, precedence-free. It uses the draw's seats,
  its kingmaker and Amcha sides and that vector's behavioural values:
  - **unity:** `p_unity` (`likud_sans_bibi`, with the COND deadlock-depth
    shift) if `ce_pure + res_c + amcha_ce + Likud >= 61`, else 0;
  - **defector:** `p_defect` (`centre_defects`, with the COND gap shift)
    if the tree's `feasible` holds, else 0;
  - **change + Ra'am:** `raam_joins` if `ce_pure < 61` and
    `ce_pure + Ra'am >= 61`, else 0;
  - **change + haredi:** the probability that the haredi gate's
    condition holds. That is the sum, over the eight combinations of
    (`shas_on`, `utj_on`, `lib_haredi`) that satisfy `ch_seats >= 61` with
    a haredi list crossing, of Π Bernoulli(p_shas, p_utj,
    `liberman_haredi_ok`), with p_shas and p_utj configuration-conditional
    as shipped;
  - **JL-backed minority:** `jl_supports` × the sum, over the combinations
    of (`raam_supports`, `lib_ok`, `utj_abst`) that satisfy the minority
    condition, of their Bernoulli products. The `utj_abst` probability is
    `UTJ_ABSTAINS` × (1 − p_utj), which is 0 as shipped.

  Every gate value therefore still moves the numbers: `utj_defects`,
  `shas_defects`, `likud_sans_bibi`, `centre_defects`, `raam_joins`,
  `jl_supports` and the Liberman flags. A draw with Σ_t w_t g_t = 0 stays
  a repeat and is counted as unresolved.
- **Details and membership.** Exactly as s.56. Type 4 draws its
  (`shas_on`, `utj_on`, `lib_haredi`) combination in proportion to the
  same terms whose sum is g_4. Type 5 sets `jl_supports` = true and draws
  (`raam_supports`, `lib_ok`, `utj_abst`) in proportion to the terms of
  g_5. The detail uniform comes from the same generator. The membership
  rule is s.52's, so each government's members reach its arithmetic.
- **The estimator for w (exact).** The likelihood is the arm's own
  forecast model. For each resolved historical deadlock c with realized
  type t_c:

  L_c(w) = E[ w_{t_c} g_{t_c} / Σ_s w_s g_s ]

  The expectation runs over the harness's deadlock draws for cycle c:
  its 200 parameter vectors × 2,000 rows, with the kingmaker sides drawn
  as the harness draws them. Rows with Σ_s g_s = 0 are dropped.
  - **Conditioning on the reachable set.** g_s = 0 for any type
    unreachable in that draw, so the denominator runs over each cycle's
    reachable set draw by draw.
  - **Why not a feasibility-only fit.** Fitting w on a feasibility-only
    choice model and then multiplying by g would count each gate's
    propensity twice. That version is registered as a variant below.
  - **The behavioural inputs to g** are the ones the scored cycle's
    forecast uses: draw_behavior per vector, with the unity value drawn
    from that cycle's `unity_prior`. When the scored cycle is 1984 or
    2020, the fit's g therefore also uses the 0-of-2 unity prior.
  - **Prior:** w normalised to sum 1, Dirichlet(0.5, 0.5, 0.5, 0.5, 0.5),
    the multinomial Jeffreys prior. Its mean is uniform, which is "trust
    the gates' relative rates, without precedence".
  - **Posterior:** importance sampling. K = 20,000 prior draws (generator
    `SEED + 5901`), weighted by Π_c L_c(w) over the fit cycles. The M =
    200 per-vector weight vectors are a multinomial resample from these
    (generator `SEED + 5902`). The effective sample size is reported. If
    any fit's ESS is below 200, K is raised to 100,000 for every fit and
    reported.
  - **The record:** the five parliamentary resolutions of s.56.1 (1984
    unity, 1992 and 2006 change + haredi, 2020 defector, 2021 change +
    Ra'am).
  - **Leave-one-cycle-out:** when a record cycle is scored, its own term
    is left out of the fit. Every other scored cycle uses the fit on all
    five. The 2026 run uses the fit on all five with the shipped unity
    prior.
  - **Maximum likelihood was considered and rejected.** Under
    leave-one-out it sets a singleton class's weight to 0 whenever the
    other cycles reached that class and did not choose it. 2020's
    defector would then score the Monte Carlo floor.

**Arm B: `defect_08`.**

- `centre_defects` goes from 0.12 to 0.08, with NEFF unchanged (25):
  Beta(2, 23). Everything else is shipped, including the stage with gate
  resolution.
- **Decisive form:** exactly as it would ship. `draw_behavior` reads
  `BEHAVIOR` with `centre_defects` = 0.08, so the random stream is the
  one an edit of `BEHAVIOR` would produce.
- **2026 run:** `government_formation.py --set centre_defects=0.08` into
  a scratch directory.

**Registered variants (reported, not decisive).**

- **`mix_feas`.** The weights are fitted on the feasibility-only choice
  model, L_c(w) = E[ w_{t_c} 1[t_c reachable] / Σ_s w_s 1[s reachable] ],
  under the same prior, posterior and leave-one-out; the forecast still
  uses w × g. This addresses the estimator ambiguity.
- **`mix_insample`.** Arm A with the weights fitted on all five cycles
  for every scored cycle (no leave-one-out). It measures the
  singleton-class penalty, as in s.56.
- **`defect_08_paired`.** Arm B with each vector's `centre_defects` set
  by quantile coupling to the shipped draw:
  `Beta(2, 23).ppf(Beta(3, 22).cdf(x))`, every other value untouched. It
  shows how much of B's difference from shipped is Monte Carlo pairing
  noise.

**Expectation disclosed in advance.** A back-of-envelope on 2020 puts B's
defector probability at about 0.78 of shipped, close to the 0.75
tolerance. The rule is applied as written: point estimate, no margin, no
re-run with another seed. For A, the leave-one-out penalty on 2020 and
2021 is expected to be smaller than in s.56, because g keeps 2020's double
haredi crossing near zero. Its sign is not known.

**Reported for every tree.**

- Per-cycle P(realized).
- Mean log and Brier, with bootstrap SEs.
- The tolerance table.
- Expected-versus-realized resolution counts over the five historical
  resolutions: Σ_c P(type | a government formed), for the defector,
  change + haredi, unity, change + Ra'am and minority types. Arm A's
  counts are reported under leave-one-out (as scored) and in-sample.
- The posterior mean weights and ESS of each fit.
- **The 2026 effect** of A and of B, in scratch only, on the committed
  `mixture_draws.parquet` (sha256 3741588c…): outcomes, groups, PM and
  membership, against shipped, plus the type shares among resolved
  deadlocks.

**Bit-identity.**

- With `STAGE_RESOLUTION = "gates"` and no `--set`, all seven formation
  CSVs must reproduce the committed files byte for byte.
- `--resolution record` must reproduce the s.56 scratch outputs byte for
  byte.
- The harness's nine existing trees must reproduce their committed
  columns in `formation_validation.csv`.

### 59.2 Results on the record (leave-one-cycle-out)

**Verdict under the s.59.1 rule:**

- **Arm B (`defect_08`) passes all three conditions and ships:**
  `centre_defects` 0.12 → 0.08, NEFF 25.
- **Arm A (`stage_mix`) fails all three.** Two of the failures are narrow.

The patch leaves both flags at their shipped values; the coordinator
flips B (see 59.4).

**Two deviations from 59.1, disclosed.**

- **The input hash.** 59.1 quotes the formation input as sha256
  3741588c…, which is the v45 file. The base cb4d1a6 carries the v46
  refit (s.58), sha256
  28a7423d530a6e8012d5bbf17938af83e8bbf75884dbf12947a1ae9ebfe3d05f. Every
  s.59 run, harness and 2026 alike, used that committed v46 file. The
  quoted hash was a transcription error; nothing was run on v45.
- **The record-mode check.** 59.1 asked `--resolution record` to
  reproduce the s.56 scratch outputs. Those were made on v45 draws, so
  the check was run in its intended form instead: the refactored record
  mode against the unmodified cb4d1a6 code, on the same v46 draws. The
  two agree byte for byte on all seven CSVs.

**Checks.**

- With the flags at their shipped values, all seven formation CSVs
  reproduce the committed files byte for byte.
- The nine existing harness trees reproduce every committed column of
  `formation_validation.csv` and every original class and calibration
  row. The coordinator's refresh used the same v46 draws.
- Membership is consistent under the mix arm. Over 20 vectors × 8,000
  Knessets, no government's members fail to reach the arithmetic that
  formed it, and every outcome-4 government has a haredi member.
- The posterior's effective sample size is 3,216-6,598 for `stage_mix`
  and at least 2,469 for `mix_feas`. That is above the 200 floor, so
  K = 20,000 stands.

**P(realized class):**

| cycle | realized | shipped | A `stage_mix` | B `defect_08` | `mix_feas` | `mix_insample` | B paired |
|---|---|---|---|---|---|---|---|
| 1984 | unity | 0.195 | 0.166 | **0.247** | 0.103 | 0.272 | 0.246 |
| 1992 | change + haredi | 0.174 | **0.340** | 0.208 | 0.209 | 0.401 | 0.208 |
| 2006 | change + haredi | 0.190 | **0.275** | 0.208 | 0.202 | 0.344 | 0.208 |
| 2015 | Netanyahu + unaligned | 0.399 | 0.399 | 0.398 | 0.399 | 0.399 | 0.399 |
| 2019a | repeat | 0.131 | 0.131 | 0.134 | 0.131 | 0.131 | 0.134 |
| 2019s | repeat | 0.131 | 0.131 | 0.132 | 0.131 | 0.131 | 0.132 |
| 2020 | defector | **0.415** | 0.211 | 0.358 | 0.208 | 0.319 | 0.359 |
| 2021 | change + Ra'am | **0.179** | 0.113 | 0.184 | 0.105 | 0.169 | 0.184 |
| 1999 (weight 0.5) | change + haredi | 0.150 | 0.314 | 0.173 | 0.230 | 0.314 | 0.173 |

**Scores and the rule.** Bootstrap SEs are over the scored cycles.

| | shipped | A `stage_mix` | B `defect_08` |
|---|---|---|---|
| 1. mean log, 8 cycles, leave-one-out | −1.579 | −1.611 (−0.032, SE 0.142): **fail** | **−1.527 (+0.053, SE 0.039; P(≤ 0) 0.09): pass** |
| 2. multi-class Brier | 0.835 | 0.837: **fail** | **0.810: pass** |
| 3. tolerance, arm ÷ shipped: 2019a / 2019s / 2020 / 2021 / 2022 | | 0.995 / 0.998 / **0.510** / **0.634** / 1: **fail** | 1.021 / 1.006 / 0.863 / 1.029 / 1: **pass** |
| + 1996, 1999 at weight 0.5 | −1.536 / 0.802 | −1.524 / 0.787 | −1.482 / 0.777 |
| YB 2015/2019a in Amcha's role | −1.624 / 0.864 | −1.656 / 0.866 | −1.572 / 0.840 |
| repeat vs government, non-certain (log / Brier) | −0.758 / 0.253 | −0.758 / 0.253 | −0.757 / 0.254 |
| realized class is the top class | 2 of 8 | 1 of 8 | 1 of 8 |

**The reported variants, against shipped:**

| variant | mean log | diff | Brier |
|---|---|---|---|
| `mix_feas` | −1.782 | −0.203 | 0.913 |
| `mix_insample` | −1.399 | +0.180 | 0.740 |
| `defect_08_paired` | −1.527 | +0.052 | 0.811 |

In-sample, the mix would pass the tolerance as well: 2020 at 0.77× and
2021 at 0.94×.

**Per-cycle log gain over the shipped tree:**

| cycle | A | B | `mix_insample` |
|---|---|---|---|
| 1984 | −0.16 | +0.24 | +0.33 |
| 1992 | +0.67 | +0.18 | +0.84 |
| 2006 | +0.37 | +0.10 | +0.60 |
| 2019a | −0.005 | +0.02 | −0.005 |
| 2019s | −0.002 | +0.006 | −0.002 |
| 2020 | −0.67 | −0.15 | −0.26 |
| 2021 | −0.46 | +0.03 | −0.06 |

2015 is unchanged under every tree.

**Expected versus realized resolutions** over the five resolved
deadlocks: Σ_c P(type | a government formed).

| type | realized | shipped | A (leave-one-out) | A (in-sample) | B |
|---|---|---|---|---|---|
| defector | 1 | **2.54** | 1.71 | 1.63 | 2.15 |
| change + haredi | 2 | 0.62 | 1.25 | 1.38 | 0.71 |
| unity | 1 | 1.20 | 1.52 | 1.43 | 1.49 |
| change + Ra'am | 1 | 0.50 | 0.35 | 0.44 | 0.51 |
| JL-backed minority | 0 | 0.14 | 0.17 | 0.12 | 0.15 |

**Reading.**

- **A is the better-fitting model but cannot show it out of sample.**
  With all five cycles in the fit, the posterior mean weights are:

  | type | weight |
  |---|---|
  | unity | 0.124 |
  | change + haredi | 0.364 |
  | defector | 0.053 |
  | change + Ra'am | 0.316 |
  | JL-backed minority | 0.143 |

  The record pushes the defector down and haredi entry and Ra'am up,
  relative to the gates.
  - **In-sample** it beats shipped by 0.18 nats and cuts the defector's
    excess from 1.5 governments to 0.6.
  - **Under leave-one-out** the singletons cost it, as in s.56 but far
    less: −0.03 here against −0.46 there. Without 2020, the
    defector was reachable and not chosen in 1984, 1992, 2006 and 2021,
    so its weight falls to 0.030 and 2020 keeps 0.51×. Without 2021, the
    Ra'am weight falls from 0.316 to 0.176 and 2021 keeps 0.63×.
  - **Five resolutions cannot validate a five-weight model.** The gate
    factor g makes the loss small, but it cannot be made to vanish.
  - **The feasibility-only fit is worse** (`mix_feas`, −0.20), as 59.1
    expected: it counts each gate's propensity twice.
- **B is a small, consistent gain.**
  - It gains in 1984, 1992, 2006 and 2021 and loses 0.15 nats in 2020.
    The bootstrap puts P(diff ≤ 0) at 0.09.
  - **The quantile-coupled version agrees to 0.001**, so this is not
    Monte Carlo pairing noise.
  - **The back-of-envelope in 59.1 was pessimistic.** 2020 keeps 0.86 of
    its shipped probability, not 0.78.
  - **It narrows the defector over-forecast only partly:** 2.54 → 2.15
    against 1 realized.
- **Caveat on B's largest gain (1984, +0.24).** It rests on s.49's coding
  of 1984 as class 6, "Likud without Netanyahu". 1984 kept both leaders.
  Without 1984, B's mean gain over the other seven cycles is still
  +0.026. This is descriptive, not a registered test.
- **Caveat on the choice of 0.08.** The verifier proposed it with the
  record's 1-in-5 in view. The shipped 0.12 was likewise "graded on the
  2020 realization". So neither value is out-of-sample for its own choice;
  the registered rule treats them alike.

Files (scratch): `formation_validation.csv`,
`formation_validation_classes.csv` and `formation_calibration.csv`. The
calibration file holds the rows "s.59 tolerance", "s.59 decision",
"s.59 verdict" and "s.59 resolution counts".

### 59.3 The 2026 effect (scratch only; v46 draws, 8,000 Knessets × 200 vectors)

Arm A ran as `--resolution mix`, with the weights fitted on all five
resolutions. Arm B ran as `--set centre_defects=0.08`. B's run is the
exact stream the edit of `BEHAVIOR` would ship.

| outcome | shipped | A `stage_mix` | B `defect_08` |
|---|---|---|---|
| Netanyahu rightist coalition | 0.095 | 0.095 | 0.095 |
| Netanyahu + unaligned / Amcha | 0.005 | 0.005 | 0.005 |
| Change coalition (without Ra'am) | 0.071 | 0.071 | 0.071 |
| Change + unaligned / Amcha | 0.032 | 0.032 | 0.031 |
| Change + a haredi party | 0.061 [0.017, 0.132] | 0.148 [0.020, 0.340] | 0.069 [0.018, 0.157] |
| JL-backed minority | 0.034 | 0.032 | 0.036 |
| Unity (Likud without Netanyahu) | 0.145 [0.002, 0.369] | 0.165 [0.002, 0.415] | **0.170** [0.003, 0.414] |
| Repeat election | 0.260 | 0.259 | 0.262 |
| Change + Ra'am | 0.074 | 0.067 | 0.076 |
| Netanyahu + a change-bloc defector | 0.225 [0.048, 0.399] | 0.127 [0.005, 0.314] | **0.185** [0.028, 0.380] |

**Which government the resolved deadlocks get:**

| type | shipped | A | B |
|---|---|---|---|
| unity | 0.271 | 0.308 | 0.318 |
| change + haredi | 0.113 | 0.273 | 0.130 |
| defector | 0.417 | 0.237 | 0.344 |
| change + Ra'am | 0.137 | 0.123 | 0.142 |
| JL-backed minority | 0.062 | 0.059 | 0.067 |

Under B, 5,110 draws find no gate in the 60 re-draws, against 1,255
shipped. They stay repeats, which accounts for repeat +0.002.

**Groups:**

| group | shipped | A | B |
|---|---|---|---|
| Netanyahu-led | 0.325 [0.155, 0.500] | 0.227 [0.105, 0.409] | 0.285 [0.129, 0.479] |
| change-led | 0.270 | 0.349 | 0.283 |
| unity | 0.145 | 0.165 | 0.170 |
| repeat | 0.260 | 0.259 | 0.262 |
| Netanyahu in office | 0.584 | 0.486 | 0.547 |

**Prime minister:**

| PM | shipped | A | B |
|---|---|---|---|
| Netanyahu | 0.325 | 0.227 | 0.285 |
| Eisenkot | 0.251 | 0.306 | 0.269 |
| none (repeat) | 0.260 | 0.259 | 0.262 |
| Likud successor (unity) | 0.073 | 0.082 | 0.085 |
| Bennett | 0.068 | 0.097 | 0.074 |
| Liberman | 0.013 | 0.014 | 0.015 |
| another leader | 0.010 | 0.014 | 0.011 |

**Given a government forms:**

| PM | shipped | A | B | Kalshi |
|---|---|---|---|---|
| Netanyahu | 0.439 | 0.306 | 0.386 | ~0.30 |
| Eisenkot | 0.339 | 0.413 | 0.364 | ~0.48 |

Markets are a comparison, not a target.

**Membership: P(in the government).**

| list | shipped | A | B |
|---|---|---|---|
| Likud | 0.470 | 0.392 | 0.455 |
| Yashar | 0.416 | 0.514 | 0.453 |
| Together (Bennett + Yesh Atid) | 0.415 | 0.513 | 0.452 |
| The Democrats | 0.413 | 0.509 | 0.449 |
| Yisrael Beytenu | 0.391 | 0.468 | 0.425 |
| UTJ | 0.370 | 0.341 | 0.336 |
| Shas | 0.359 | 0.321 | 0.324 |
| Otzma Yehudit | 0.289 | 0.207 | 0.256 |
| RZP | 0.227 | 0.167 | 0.202 |
| Amcha | 0.076 | 0.063 | 0.070 |
| Reservists | 0.072 | 0.075 | 0.076 |
| Ra'am, in government | 0.074 | 0.067 | 0.076 |
| Ra'am, outside support | 0.021 | 0.020 | 0.022 |
| Joint List, outside support | 0.033 | 0.032 | 0.036 |
| the unnamed change-bloc defector row | 0.225 | 0.127 | 0.185 |

Under both arms, Shas and UTJ fall because there are fewer Netanyahu-led
governments. Under A, part of that is offset by haredi entry into a
change government.

**The gates still move the numbers under A, as registered.** P(Netanyahu
PM) at the central draw, with the mix weights at their posterior mean:

| gate value moved | P(Netanyahu PM) |
|---|---|
| mix, all gates shipped | 0.202 |
| `utj_defects` 0.05 / 0.15 / 0.30 | 0.209 / 0.202 / 0.197 |
| `centre_defects` 0.08 / 0.12 / 0.20 | 0.175 / 0.202 / 0.242 |
| `likud_sans_bibi` 0.0625 / 0.125 / 0.18 | 0.241 / 0.202 / 0.182 |
| gates (shipped), same central draw | 0.294 |

**B's cost, as the verifier warned.** Of the 0.040 that B takes from the
pledge-break, 0.025 goes to unity without Netanyahu, a path with no
precedent (s.49.3). Unity rises from 0.145 to 0.170. The rest goes to
haredi entry (+0.008), the minority, Ra'am and repeats.

### 59.4 Recommendation

**Ship B: set `BEHAVIOR["centre_defects"]` = 0.08, with
`BEHAVIOR_NEFF` unchanged at 25.** It passes every condition of the
registered rule:

- mean log +0.053;
- Brier 0.810 against 0.835;
- every realized 2019-2022 outcome keeps at least 0.86 of its shipped
  probability.

The edit is one line. The `centre_defects` comment should then cite s.59:
"0.12 → 0.08 (s.59): the stage's gate re-draw gave the pledge-break 0.42
of resolved 2026 deadlocks, and on the record the shipped tree expected
2.5 defector governments in five resolved deadlocks against one realized;
graded on the formation harness, +0.053 mean log, Brier 0.810 vs 0.835,
2020 keeps 0.86 of its probability."

After the edit:

- The 2026 outputs equal this section's B run exactly: outcome 9 0.185,
  P(Netanyahu PM) 0.285, 0.386 given formation.
- Re-run `validate_formation.py`. The `defect_08` tree becomes identical
  to the shipped tree, and the s.59 rows then compare the new shipped
  tree with itself. These pre-flip numbers are the record of the test.

**Keep A off.** `STAGE_RESOLUTION` stays `"gates"`. A is the better model
in-sample (+0.18), but the registered leave-one-out test fails narrowly
(−0.03 mean log, Brier +0.002), and the tolerance fails on 2020 and
2021. The code stays behind the flag. When the record gains a sixth
resolved deadlock, re-grade it as is; it needs no new registration.

**Disclose on the site with B:**

- The pledge-break rate is now 0.08.
- The shipped tree still expects about 2.2 defector governments in the
  five historical resolutions, against one realized. B narrows the
  over-forecast; it does not remove it.
- B moves 0.025 to unity without Netanyahu, a path with no precedent.
- B's largest record gain rests on 1984 being coded as that class.

## 60. Hybrid residual for small lists (17-18 Oct, D-10)

### 60.1 Pre-registration (written before any run of this arm)

**Why.** s.57 found the near-threshold underconfidence in established
lists. Its main source is the per-list residual. decompose() fits the
residual sd on seat errors, so each threshold death is a whole-list miss,
and the projection then applies the threshold again: deaths are counted
twice. That double count lives only in the small group (<= 8 seats).
The vote-share residual (cal_B, s.48 arm B) removes it, but it changes
every list's width. Under the s.53 rule its only failures were the eve
folds 2019s (+.100) and 2022 (+.128), both one-seat median flips on
large lists (Blue and White 32 -> 31; Likud, Yesh Atid, UTJ).

**Disclosure.** The coordinator proposed this arm after the s.57 results.
The cal_B grade is known; this arm's has never been run. The boundary is
decompose()'s own two-group split (actual seats <= 8). It was fixed in
the proposal, before any run, and is not tuned.

**Arm `resid_hybrid`.** Every list draws the shipped per-list residual,
eps x sd_list with eps ~ N(0, 1) and width RESID_SCALE 0.9 (x
STACK_SCALE in production). Only the line that gives sd_list changes:
- lists whose PRE-SHOCK base share satisfies base0 x 120 <= 8 take the
  vote-share line (decompose_vote: lists that ran, u = 120 x share);
- every other list keeps the shipped seat line (decompose()).

Everything else is shipped. That includes NEW_LIST_MULT, the zero hold
for dropped lists, the 0.5% scoring mask and, in production,
EVENT_RISK_HORIZON. base0 is the mean share of the forward-walked latent
draws after the withdrawn-list drop and before any shock, the quantity
both projections already call base0. The same test applies at every
horizon.
- Production: bayes_model.RESID_SPACE "hybrid", with RESID_HYBRID_SEATS
  = 8.0. Both lines are full sample: seat 1.830 + 0.0438 x seats, vote
  0.732 + 0.0730 x u. RESID_SPACE "seat" (the default) is shipped.
- Harness: layer resid_space "hybrid", resid_hybrid_seats 8.0, arm
  `resid_hybrid`. Both lines are leave-one-cycle-out, the vote line from
  add_calibration_params and the seat line from decompose(exclude_cycle).

**LOO lines** (estimation inputs, computed before registration; seat
line / vote line, each as base + slope):

| left out | seat line | vote line | at 4 seats: seat / vote | at 8 seats: seat / vote |
|---|---|---|---|---|
| none (production) | 1.830 + .0438 | 0.732 + .0730 | 2.00 / 1.02 | 2.18 / 1.32 |
| 2009 | 1.679 + .0474 | 0.678 + .0781 | 1.87 / 0.99 | 2.06 / 1.30 |
| 2013 | 1.597 + .0345 | 0.885 + .0495 | 1.73 / 1.08 | 1.87 / 1.28 |
| 2015 | 2.009 + .0333 | 0.671 + .0703 | 2.14 / 0.95 | 2.27 / 1.23 |
| 2019a | 1.199 + .0558 | 0.634 + .0746 | 1.42 / 0.93 | 1.64 / 1.23 |
| 2019s | 1.934 + .0353 | 0.776 + .0748 | 2.07 / 1.07 | 2.22 / 1.37 |
| 2020 | 1.827 + .0405 | 0.724 + .0810 | 1.99 / 1.05 | 2.15 / 1.37 |
| 2021 | 2.194 + .0406 | 0.753 + .0723 | 2.36 / 1.04 | 2.52 / 1.33 |
| 2022 | 1.865 + .0478 | 0.765 + .0752 | 2.06 / 1.07 | 2.25 / 1.37 |

The sd is discontinuous at the boundary (about 1.3 below, 2.2 above,
before the 0.9 width). The design accepts that and does not smooth it.

**Grading.** Shipped vs `resid_hybrid` on the s.50 LOO-scorecard caches
(the shared cache, read only; outputs in scratch), on the shipped list
mask (`*_fixed`).
- Eve: `HARNESS_ABLATIONS=shipped,resid_hybrid HARNESS_SKIP_WIDTH=1
  python src/validate_bayes.py`, offsets 0/100/200.
- D-7 and D-21: `HORIZONS=7,21 HORIZON_SKIP_GRID=1
  HORIZON_LAYERS='resid_hybrid:{"resid_space": "hybrid"}' python
  src/validate_horizon.py`, offsets 0/100/200, against "calendar".
- Pooling: per seed the mean over the eight cycles, then the mean over
  the three seeds. A fold is a cycle, its value the three-seed mean.
- Reproduction gate: the shipped rows must equal the s.57 baselines (eve
  1.4927 / 1.6291 / .9807 / .0475 / 9.217; D-7 1.4866 / 1.6478 / .9896 /
  .0490 / 9.360; D-21 1.6211 / 1.7943 / .9896 / .0541 / 9.690). The
  harness has no event-risk term, so EVENT_RISK_HORIZON does not enter.

**Rule (s.53 / s.55, unchanged).** The arm passes if, at EACH of eve, D-7
and D-21 (offsets 0/100/200):
- it wins or ties median MAE in every leave-one-cycle-out fold (fold
  delta < +0.1 seat);
- pooled mean MAE, threshold Brier and interval score are not worse than
  shipped by more than .010 / .0010 / .05;
- pooled 90% coverage is not further from .90 than shipped's.

**Reported, not gating.**
- The reliability rows for the 50-90% and 10-30% bands, binned on each
  arm's own probabilities, three seeds pooled, eve / D-7 / D-21, with n,
  stated and realised.
- The fixed-set rate: the lists the SHIPPED arm puts in 50-90%.
- The near-threshold Brier and the by-class straddler Brier
  (established / first-cycle), as in s.57.3.
- Per-fold medians.
- cal_B's s.57 numbers beside the arm, for reference.
- The 2026 effect. The run is the BAYES_PROJECT_ONLY projection on a
  scratch copy of main's m3_idata.nc, with bayes_model.PROCESSED_DIR on a
  scratch copy. The baseline is the shipped configuration, which since
  s.58 carries EVENT_RISK_HORIZON = True; with the flag off the run must
  reproduce the committed v46 bayes_forecast_2026.csv. Seeds are the
  production seed, +1 and +2. Reported: the pass probabilities of
  RZP-Zehut, Otzma, Ra'am, Amcha, the Reservists and Blue and White; the
  bloc probabilities; and which 2026 lists fall under the 8-seat
  boundary.

### 60.2 Result: does not pass

60.1 was committed alone before any run: worktree commit c939a67, 22:57,
text sha256 9a38d2c6816421d4a9385de1bbdff68a4e6f7f233637ec7a9a0921ae67447859.
Runs used the registered commands on the shared s.50 cache (read only),
with HARNESS_OUT_DIR in scratch and at most four processes.
- **Reproduction gate: passed.** The shipped rows equal the s.57
  baselines at all three horizons.
- **Flags off.** With the flags off, the patched harness and production
  are unchanged.

**Pooled, three seeds** (median / mean / coverage / threshold Brier /
interval; median folds W/T/L at |d| < 0.1; cal_B from s.57.3 for
reference):

| horizon | shipped | resid_hybrid | cal_B (s.57) |
|---|---|---|---|
| eve | 1.4927/1.6291/.981/.0475/9.217 | 1.5111/1.6000/.972/.0410/8.815 (1/6/1) | 1.5196/1.6013/.972/.0409/8.671 (0/6/2) |
| D-7 | 1.4866/1.6478/.990/.0490/9.360 | 1.4607/1.6250/.977/.0439/8.970 (1/6/1) | 1.4591/1.6273/.951/.0439/9.008 (1/7/0) |
| D-21 | 1.6211/1.7943/.990/.0541/9.690 | 1.6181/1.7535/.968/.0503/9.442 (1/7/0) | 1.6196/1.7550/.952/.0502/9.526 (1/7/0) |

- **Two fold losses fail it.** 2022 at the eve loses +.128 and 2021 at D-7
  loses +.119. Every pooled test passes at every horizon:
  - mean MAE -.029 / -.023 / -.041;
  - Brier -.0066 / -.0051 / -.0039;
  - interval score -.402 / -.390 / -.248;
  - coverage .981 -> .972, .990 -> .977, .990 -> .968;
  - bloc Brier -.0039 / -.0030 / -.0014.
  The eve pooled median is +.018 (seeds +.048 / -.011 / +.019); D-7 is
  -.026 and D-21 -.003.
- **The failing folds.**
  - 2022 eve repeats cal_B's loss to the digit. Likud goes 32 -> 33
    (actual 32) and Yesh Atid 25 -> 26 (actual 24), both on the SEAT line.
    UTJ (6.6 share-seats, vote line) goes 7 -> 8. Yisrael Beytenu goes 5
    -> 6 the right way.
  - 2021 D-7 is new. The Joint List sits at 8.04 share-seats, just above
    the boundary, on the seat line, and goes 8 -> 9 (actual 6) in all
    three seeds. Likud goes 30 -> 31 (actual 30) in two seeds.
  - 2019s, cal_B's other eve loss, is now a tie (+.067; Blue and White
    loses the seat in two seeds instead of three).
- **What this settles.** cal_B's large-list flips did not come from the
  large lists' own widths. The hybrid keeps those lists on the seat line,
  and their medians still move. The flips come from the small lists: a
  narrower small-list residual kills sub-threshold lists in more draws and
  trims passing small lists' upper tails, and the freed seats land in the
  large lists' medians. Under the whole-seat median fold test this cost is
  intrinsic to narrowing the small-list residual. A residual-only change
  cannot avoid it by shielding the large lists.

**Reliability rows**, three seeds pooled (lists per seed, stated ->
realised; each arm binned on its own probabilities):

| horizon | arm | 10-30% | 50-90% | fixed set (shipped 50-90%) |
|---|---|---|---|---|
| eve | shipped | 10.0 .196 -> .100 | 21.3 .667 -> .844 | .667 -> .844 |
| eve | resid_hybrid | 4.3 .195 -> .231 | 18.0 .703 -> .833 | .733 -> .844 |
| eve | cal_B | 4.3 .194 -> .231 | 18.3 .708 -> .836 | .733 -> .844 |
| D-7 | shipped | 9.0 .206 -> .111 | 18.3 .680 -> .891 | .680 -> .891 |
| D-7 | resid_hybrid | 4.3 .212 -> .308 | 15.3 .705 -> .870 | .749 -> .891 |
| D-7 | cal_B | 4.3 .211 -> .308 | 15.3 .705 -> .870 | .750 -> .891 |
| D-21 | shipped | 10.3 .207 -> .097 | 19.7 .729 -> .898 | .729 -> .898 |
| D-21 | resid_hybrid | 6.0 .222 -> .333 | 12.7 .725 -> .921 | .800 -> .898 |
| D-21 | cal_B | 6.0 .221 -> .333 | 12.7 .726 -> .921 | .801 -> .898 |

- **Near the threshold the hybrid behaves like cal_B.** Every
  near-threshold list is small.
  - The 10-30% band flips from over-stated to slightly under-stated, on 4-6
    lists per seed.
  - On the shipped 50-90% lists the hybrid closes about 40% of the gap.
- **Near-threshold Brier** (shipped's [.1, .9) lists): .126 / .140 / .144,
  against shipped's .143 / .153 / .153.
- **By class:**
  - established lists .135 / .160 / .186, against shipped's .156 / .172 /
    .190;
  - first-cycle lists .187 / .177 / .151, against shipped's .186 / .177 /
    .158.

### 60.3 2026 effect (frozen production posterior; outputs in scratch)

The posterior is main's m3_idata.nc, 16 Oct 18:54, sha256 654a4414....
It is the same posterior as s.57.4, copied to scratch. The run used the
BAYES_PROJECT_ONLY path with bayes_model.PROCESSED_DIR on a scratch copy;
the repo's data/processed was not written.
- **Baseline.** The baseline is shipped with EVENT_RISK_HORIZON = True
  (factor 1.029 at h = 8 days). With the flags off the run is
  byte-identical to the committed v46 bayes_forecast_2026.csv and
  bayes_forecast_blocs.csv.
- **Seeds.** Production seed, +1 and +2.

| (seeds +0 / +1 / +2) | shipped (event-risk horizon) | resid_hybrid | change, seed mean |
|---|---|---|---|
| RZP-Zehut pass | .560 / .559 / .563 | .618 / .613 / .622 | .561 -> .618 |
| Otzma pass | .799 / .792 / .798 | .855 / .842 / .853 | .796 -> .850 |
| Ra'am pass | .760 / .769 / .763 | .882 / .885 / .882 | .764 -> .883 |
| Amcha pass | .252 / .252 / .244 | .230 / .231 / .225 | .249 -> .229 |
| Reservists pass | .224 / .225 / .219 | .200 / .203 / .204 | .223 -> .202 |
| Blue and White pass | .016 / .015 / .016 | .000 / .000 / .000 | .016 -> .000 |
| P(NB >= 61) | .128 / .118 / .126 | .108 / .099 / .101 | .124 -> .103 |
| P(change bloc >= 61) | .063 / .064 / .064 | .056 / .055 / .057 | .064 -> .056 |
| P(neither) | .809 / .819 / .810 | .835 / .846 / .842 | .813 -> .841 |
| NB seats, mean [90%] | 53.0 [42-64] | 52.9 [43-63] | |

- **Which lists fall under the boundary** (base0 x 120, seed +0):
  - On the vote line: Otzma 7.56, Ra'am 4.94, RZP-Zehut 5.58, Shas 7.17,
    UTJ 7.16, YB 7.35, the Joint List (Balad + Hadash-Ta'al) 7.88, Amcha
    3.74, the Reservists 3.58, Blue and White 1.0, and every micro-list.
  - On the seat line: Likud 20.59, Yashar 20.71, Together 11.33 and the
    Democrats 8.47.
  - The Joint List and the Democrats sit within half a seat of the
    boundary.
- **Central seats** are unchanged except Shas at seed +2 (8 -> 9). Under
  both arms Shas is 8 or 9 depending on the seed.
- **Intervals narrow on the small lists.** YB 4-12 -> 6-11, the Joint
  List 5-13 -> 6-12, Otzma 0-11 -> 0-10, Ra'am 0-9 -> 0-8, RZP-Zehut 0-8
  -> 0-7.
- **In 2026 the hybrid and cal_B are nearly the same change.** Only the
  four largest lists keep the seat line, and the satellites move as under
  cal_B (s.57.4).

### 60.4 Recommendation

- **Not shipped.** Under the pre-registered s.53 / s.55 rule
  resid_hybrid fails: eve 2022 +.128 and D-7 2021 +.119.
  `RESID_SPACE` stays "seat". `RESID_HYBRID_SEATS` (8.0) and the harness
  layer stay in the code, unused by default. The headline is unchanged.
- **What the grade establishes.**
  - The vote-share residual's near-threshold gain survives the hybrid
    intact: the 50-90% band, the Brier and the by-class Brier are the same
    as cal_B's.
  - Its interval score is better than cal_B's at D-7 and D-21.
  - Its fold failures are not the large lists' widths but the seats that
    small-list deaths free up. Any small-list narrowing will meet the
    whole-seat median fold test on the large lists.
  - Passing would take a change outside the residual, or an owner
    decision on the fold test. Neither is registered here.
- **For the site.** The s.57 statement stands. The pass probabilities of
  RZP-Zehut, Otzma and Ra'am are more likely understated than overstated.
  The graded arm that would correct part of it (to about .62 / .85 / .88)
  costs a one-seat median flip in two of eight past folds.

### 60.5 Not established

- **The boundary discontinuity is not graded** (about 1.3 vs 2.2 seats of
  sd at 8 share-seats). In 2026 the Joint List and the Democrats sit next
  to it, and the 2021 D-7 loss is a list just above it. A smooth blend
  was not registered.
- **D-56** was not run.
- **The formation chain was not run.** The 2026 effect is the plain
  projection; the registration mixture, official forecast and formation
  chain were not run.

## 62. Bayesian stacking of error-stack variants (18 Oct, D-9)

### 62.1 Pre-registration (written before any run of this section)

**Why.** Four graded variants of the election-day error stack each win
most pooled scores against shipped and fail the strict per-fold rule:
- cal_B, the vote-share residual (s.57.3: eve folds 2019s +.100 and 2022
  +.128; every pooled test passes at every horizon);
- resid_hybrid (s.60.2: eve 2022 +.128 and D-7 2021 +.119; every pooled
  test passes);
- cal_A, the t-scale fix (s.48.6, leak-free caches: eve interval score
  -.075, D-7 +.192 on one horizon seed);
- Bfix, the decompose() index fix at width 0.9 (s.48.6: D-7 interval
  score +.143 on one horizon seed; the s.57.1 eve diagnostic lost no
  floor).

The shipped stack is one point in that space. Bayesian stacking (Yao,
Vehtari, Simpson & Gelman 2018, "Using stacking to average Bayesian
predictive distributions", Bayesian Analysis 13(3)) chooses weights on
the simplex over the candidates' predictive distributions to maximise the
leave-one-out log score. The mixture can beat every component. Its median
sits between the components' medians, so it may avoid the whole-seat
median flips that fail cal_B and resid_hybrid.

**Candidate set (fixed in advance; no arm is added after results).**
Five harness arms, each at the shipped width RESID_SCALE 0.9 with every
other layer shipped:

| arm | harness layers | production flags |
|---|---|---|
| shipped | {} | T_UNIT_VAR False, RESID_SPACE "seat" |
| cal_A | {"t_unit": True} | T_UNIT_VAR True |
| cal_B | {"resid_space": "vote"} | RESID_SPACE "vote" |
| resid_hybrid | {"resid_space": "hybrid"}, 8.0 seats | RESID_SPACE "hybrid" |
| Bfix | {"resid_space": "seat_fix"} | RESID_SPACE "seat_fix" |

- CBfix (Bfix with a nested width) is not in the set. Its width differs
  by fold, so it is not one predictive per cycle.
- The five arms consume the random stream identically. They change the
  residual sd line or the t scaling, never which draws are made. At one
  seed the five projections therefore share their random numbers.

**Disclosure.** The pooled rule metrics of the components are known:
cal_B (s.57.3), resid_hybrid (s.60.2), Bfix (s.57.1, eve only) and cal_A
(s.48.6: eve on three seeds, D-7 / D-21 on one seed). No log score, CRPS
or stacking weight has been computed for any arm. cal_A and Bfix have
never been run at D-7 / D-21 on three seeds.

**Projections.**
- Inputs: the s.50 leave-one-out-scorecard caches (the shared harness
  cache, read only), and the shipped configuration of main 2a8477f.
- Grid: the eight cycles, at eve, D-7 and D-21, on seed offsets 0 / 100 /
  200.
- Streams: eve uses SEED + 11 + offset with the eve forward weeks (the
  validate_bayes ablation stream). D-h uses SEED + h + offset with the
  calendar-effective weeks (validate_horizon's "calendar" config).
- Each arm x cycle x horizon x seed is projected once with project_cycle,
  N_PROJ 4000, and its seat draws are stored (int8 npz, scratch).
- Every harness parameter is leave-one-cycle-out: decompose(exclude_cycle),
  add_calibration_params and the lam-prior scorecard. Each cycle's
  predictive is therefore already a LOO predictive.
- **Reproduction gate.** Before any score is read, the stored shipped
  draws must give the s.57 baselines (eve 1.4927 / 1.6291 / .9807 /
  .0475 / 9.217; D-7 1.4866 / 1.6478 / .9896 / .0490 / 9.360; D-21 1.6211
  / 1.7943 / .9896 / .0541 / 9.690). cal_B's and resid_hybrid's draws
  must give their s.57.3 / s.60.2 rows.

**List set.** The shipped list mask of each cycle, horizon and seed: lists
with shipped base share >= 0.005 or a realised seat (the `*_fixed` mask).
Every arm and the stack are scored on it.

**Score.**
- p_j(y) is the fraction of an arm's 4000 draws (one seed) that give
  list j exactly y seats.
- The per-list log score is log max(p_j(y_j), eps), with y_j the
  realised seats and eps = 1e-4. The floor is below one draw in 4000, so
  it acts only on a seat count that no draw produced, which then scores
  log 1e-4 = -9.21.
- The cycle score S is the sum over the list set. A horizon's score is
  S averaged over the three seeds.
- The floor is applied to each arm's pmf before mixing (p~_k =
  max(p_k, eps)). The mixture's score, sum_j log sum_k w_k p~_kj(y_j), is
  then concave in w.
- CRPS is reported, not used for the weights. It is the discrete form
  sum_{x=0..120} (F_j(x) - 1{x >= y_j})^2, summed over the list set per
  cycle (lower is better), seed mean.

**Stacking.**
- The weights w on the five-arm simplex maximise
  sum_c (1/3) sum_{h in eve, D-7, D-21} mean_seed S_{c,h,s}(w).
- The optimiser is scipy.optimize (BFGS) on a softmax parametrisation
  with the analytic gradient, started from equal weights. The objective
  is concave in w, so the optimum is global. The EM fixed point for
  mixture weights is run as a check.
- **Production weights** are fitted on all eight cycles, the three
  horizons averaged, as s.48's width choice was. They are rounded to
  three decimals and renormalised on the largest weight. An arm that
  rounds to zero drops out.
- **Nested LOO.** For each held-out cycle c, w_(-c) is fitted the same
  way on the other seven cycles and rounded the same way.
- **The held-out stacked forecast** is the harness mirror of the
  production mechanism. One project_cycle pass with layer
  error_stack = w_(-c) draws each simulation's variant from a dedicated
  child generator (the SeedSequence of the projection seed, spawn key 62).
  It applies that variant's residual line and t scaling to that
  simulation. The rest of the stream is the shipped one.
- Its seats are graded like any arm's: the rule metrics, the log score
  and CRPS. Its median seats come from its own draws.
- Beside it, the exact pmf mixture sum_k w_k p_k from the stored draws is
  scored. The mirror differs from it only through Monte Carlo and the
  ensemble-level couplings: the base-share weights of the later layers
  and the loyal-list shrink.

**Rule (s.53 / s.55, unchanged).** The nested-LOO stacked forecast is
graded against shipped at each of eve, D-7 and D-21 on offsets 0 / 100 /
200. Pooling is per seed the mean over the eight cycles, then the mean
over the seeds. A fold is a cycle, and its value is the three-seed mean.
The stack passes if, at each horizon:
- it wins or ties median MAE in every fold (fold delta < +0.1 seat);
- pooled mean MAE, threshold Brier and interval score are not worse than
  shipped by more than .010 / .0010 / .05;
- pooled 90% coverage is not further from .90 than shipped's.

If it passes, ERROR_STACK ships with the production weights. If it fails,
ERROR_STACK stays None. If the production weights put .99 or more on
shipped, the question is moot and nothing changes.

**Reported, not gating.**
- The log score and CRPS per horizon for every arm, for the nested stack
  (mirror and exact mixture), and for the in-sample stack (all-eight
  weights scored on the same eight cycles, which is optimistic).
- Single-arm selection by nested LOO: per fold, the arm with the best
  training score.
- The weights of every fold and their stability (range and sd of each
  weight over the eight folds).
- The fold table: median MAE per cycle, shipped against the stack, at
  each horizon.
- The bloc Brier for P(NB >= 61).

**2026 effect.**
- The run is the BAYES_PROJECT_ONLY projection on a scratch copy of
  main's m3_idata.nc (sha256 recorded), with bayes_model.PROCESSED_DIR on
  a scratch copy. Seeds are the production seed, +1 and +2.
- Arms: shipped (the flags as on main) against ERROR_STACK = the
  production weights.
- Flag-None check: the patched code with the flag at None must reproduce
  main HEAD's unpatched code on the same posterior byte for byte.
- Reported: the pass probabilities of RZP-Zehut, Otzma, Ra'am, Amcha,
  the Reservists and Blue and White; P(NB >= 61), P(change bloc >= 61)
  and P(neither); the NB mean with its 90% interval; and the central
  (p50) seats of every list.

### 62.2 Results: the stack does not pass

62.1 was committed alone before any run: worktree commit 557771a, 23:31
(47af096 after the rebase onto main 651b955, which touched only the
site), text sha256 e800051f83d4f8ad0e4d4257d8cc986c2e472e2fade09d3785d33ee1c3e0ef2f.
The runs used `src/stacking.py` (run / fit / run_stack / grade) on the
shared s.50 cache (read only), with outputs in scratch and at most four
processes. Each projection takes about 0.65 s.

**Reproduction gate: passed.** The stored shipped draws give the s.57
baselines to the last digit at all three horizons:
- eve 1.4927 / 1.6291 / .9807 / .0475 / 9.2173;
- D-7 1.4866 / 1.6478 / .9896 / .0490 / 9.3600;
- D-21 1.6211 / 1.7943 / .9896 / .0541 / 9.6900.

cal_B and resid_hybrid give their s.57.3 / s.60.2 rows exactly. cal_A
and Bfix at seed offset 0 give the s.48.6 one-seed D-7 interval-score
losses (+.192 and +.143).

**Mirror checks.**
- Bit for bit, error_stack = {arm: 1} gives each arm's own draws. This
  holds in the harness (2022 eve, all five arms) and in production
  (tests/test_stacking.py, synthetic posterior).
- The one-pass mirror and the exact mixture differ by at most .2 log
  points and .004 interval score per horizon (table below). The exact
  mixture's log score and CRPS are those of the pmf mixture sum_k w_k
  p_k. Its rule metrics come from the stored draws, each simulation
  taking its assigned arm's draw (the same child generator as the
  mirror).
- At equal weights on 2022 eve, 74% of the mirror's draws equal the exact
  mixture's, and the mean difference is .05 seats per list. The
  ensemble-level couplings (the base-share weights and the loyal-list
  shrink) account for the rest.

**Weights** (raw optimum; BFGS and EM agree to 1e-5; shipped and Bfix are
0.000 in every fit):

| fitted on | cal_A | cal_B | resid_hybrid | cal_B + hybrid |
|---|---|---|---|---|
| all eight (production) | .302 | .448 | .250 | .698 |
| without 2009 | .281 | .508 | .211 | .719 |
| without 2013 | .293 | .494 | .213 | .707 |
| without 2015 | .383 | .000 | .617 | .617 |
| without 2019a | .316 | .622 | .061 | .684 |
| without 2019s | .378 | .112 | .511 | .622 |
| without 2020 | .334 | .396 | .270 | .666 |
| without 2021 | .000 | 1.000 | .000 | 1.000 |
| without 2022 | .456 | .090 | .454 | .544 |

- **Stability.** It is poor:
  - cal_B ranges 0 to 1.00 (sd .33 over the eight folds), the hybrid 0 to
    .62 (sd .22), and cal_A 0 to .46 (sd .14).
  - cal_B and the hybrid are nearly the same predictive for the small
    lists, so the split between them is weakly identified. Their sum is
    steadier, at .54-.72 in seven folds.
  - One cycle moves everything. Without 2021 the other seven put all the
    weight on cal_B.
- **Shipped and Bfix get zero weight.** cal_A is shipped with the swing
  and family shocks at their measured sd. Its log score beats shipped's
  in 19 of the 24 cycle-horizons, so it dominates shipped. Bfix sits
  between shipped and the vote-share arms, and the mixture of those
  covers it.
- **Production weights**, rounded as registered: {cal_A .302, cal_B .448,
  resid_hybrid .250}.

**Pooled, three seeds.** Columns: median MAE / mean MAE / coverage /
threshold Brier / interval score / log score / CRPS / bloc Brier.
- The log score and CRPS are the totals over the eight cycles (the sum
  over lists, seed mean). A higher log score is better; a lower CRPS is
  better.
- "stack" is the graded nested-LOO forecast (the mirror). "exact" is the
  exact pmf mixture with the same fold weights. "in-sample" uses the
  all-eight weights on the same cycles, so it is optimistic. "select" is
  the single arm with the best training score in each fold.

| horizon | arm | median | mean | cov | Brier | IS | log | CRPS | bloc |
|---|---|---|---|---|---|---|---|---|---|
| eve | shipped | 1.4927 | 1.6291 | .981 | .0475 | 9.217 | -177.14 | 105.91 | .0428 |
| eve | cal_A | 1.4852 | 1.6291 | .981 | .0473 | 9.142 | -176.25 | 105.45 | .0357 |
| eve | cal_B | 1.5196 | 1.6013 | .972 | .0409 | 8.671 | -175.16 | 104.10 | .0363 |
| eve | resid_hybrid | 1.5111 | 1.6000 | .972 | .0410 | 8.815 | -175.81 | 104.18 | .0389 |
| eve | Bfix | 1.4858 | 1.6253 | .972 | .0447 | 9.011 | -175.34 | 104.77 | .0388 |
| eve | **stack** | **1.4855** | **1.6130** | **.972** | **.0423** | **9.027** | **-177.60** | **105.19** | **.0367** |
| eve | exact | 1.4857 | 1.6135 | .972 | .0423 | 9.024 | -177.80 | 105.26 | .0368 |
| eve | in-sample | 1.4914 | 1.6080 | .972 | .0422 | 8.802 | -174.05 | 104.04 | .0362 |
| eve | select | 1.4887 | 1.6270 | .972 | .0440 | 9.082 | -178.28 | 105.43 | .0387 |
| D-7 | shipped | 1.4866 | 1.6478 | .990 | .0490 | 9.360 | -179.49 | 108.59 | .0410 |
| D-7 | cal_A | 1.4869 | 1.6479 | .978 | .0488 | 9.459 | -179.06 | 108.21 | .0348 |
| D-7 | cal_B | 1.4591 | 1.6273 | .951 | .0439 | 9.008 | -179.02 | 108.16 | .0355 |
| D-7 | resid_hybrid | 1.4607 | 1.6250 | .977 | .0439 | 8.970 | -177.66 | 107.38 | .0380 |
| D-7 | Bfix | 1.4860 | 1.6424 | .960 | .0465 | 9.389 | -178.00 | 107.75 | .0375 |
| D-7 | **stack** | **1.4748** | **1.6363** | **.955** | **.0450** | **9.424** | **-181.32** | **108.81** | **.0365** |
| D-7 | exact | 1.4733 | 1.6368 | .955 | .0450 | 9.427 | -181.27 | 108.81 | .0363 |
| D-7 | in-sample | 1.4740 | 1.6315 | .973 | .0449 | 8.962 | -177.13 | 107.50 | .0357 |
| D-7 | select | 1.4979 | 1.6453 | .951 | .0461 | 9.621 | -181.55 | 108.67 | .0375 |
| D-21 | shipped | 1.6211 | 1.7943 | .990 | .0541 | 9.690 | -185.20 | 117.87 | .0593 |
| D-21 | cal_A | 1.6272 | 1.7955 | .980 | .0540 | 9.663 | -184.44 | 117.38 | .0529 |
| D-21 | cal_B | 1.6196 | 1.7550 | .952 | .0502 | 9.526 | -184.71 | 117.37 | .0553 |
| D-21 | resid_hybrid | 1.6181 | 1.7535 | .968 | .0503 | 9.442 | -184.55 | 117.15 | .0579 |
| D-21 | Bfix | 1.6249 | 1.7795 | .968 | .0519 | 9.599 | -183.59 | 116.81 | .0558 |
| D-21 | **stack** | **1.6169** | **1.7698** | **.952** | **.0510** | **9.804** | **-186.89** | **117.96** | **.0552** |
| D-21 | exact | 1.6207 | 1.7710 | .952 | .0510 | 9.800 | -186.78 | 117.93 | .0554 |
| D-21 | in-sample | 1.6275 | 1.7670 | .961 | .0508 | 9.470 | -183.34 | 116.85 | .0550 |
| D-21 | select | 1.6189 | 1.7782 | .959 | .0514 | 9.813 | -186.42 | 117.49 | .0558 |

**The rule, applied to the stack: FAIL.** It fails the interval score at
D-7 and D-21. Every other test passes at every horizon.
- **Median folds.** All 24 folds are ties (0 / 8 / 0 at each horizon).
  The largest fold loss is +.095, at D-7 in 2021.
- **Interval score.** Eve -.190 (seeds -.034 / -.257 / -.279). D-7
  +.064, beyond the .05 floor (seeds +.223 / +.097 / -.128). D-21 +.114
  (seeds +.093 / +.139 / +.109).
- **Other pooled tests.** Mean MAE moves -.016 / -.012 / -.025 and the
  Brier -.0052 / -.0040 / -.0031. Coverage moves toward .90 (.981 ->
  .972, .990 -> .955, .990 -> .952). The bloc Brier moves -.0061 /
  -.0045 / -.0041.

**Fold table** (median MAE, three-seed mean; stack minus shipped, with
shipped's own value in the first row):

| horizon | | 2009 | 2013 | 2015 | 2019a | 2019s | 2020 | 2021 | 2022 |
|---|---|---|---|---|---|---|---|---|---|
| eve | shipped | 1.606 | 1.667 | 1.530 | 2.262 | 1.200 | 0.926 | 1.905 | 0.846 |
| eve | stack | -.061 | -.028 | -.076 | .000 | +.033 | .000 | +.048 | +.026 |
| D-7 | shipped | 1.545 | 2.000 | 1.182 | 1.833 | 1.333 | 0.759 | 2.214 | 1.026 |
| D-7 | stack | -.061 | .000 | .000 | -.036 | .000 | -.056 | +.095 | -.038 |
| D-21 | shipped | 1.697 | 2.139 | 1.091 | 2.429 | 1.152 | 0.889 | 2.548 | 1.026 |
| D-21 | stack | -.091 | -.028 | +.030 | .000 | +.030 | +.074 | -.024 | -.026 |

- **The flips are gone.** The mixture's median sits between its
  components', so cal_B's eve 2019s (+.100) and 2022 (+.128) losses and
  resid_hybrid's D-7 2021 loss (+.119) become ties (+.033, +.026, +.095).
  This is the failure mode s.57 and s.60 could not get past.
- **Why the interval score is lost: 2021.**
  - The fold that holds out 2021 is pure cal_B (weight 1.000).
  - cal_B is the worst arm on 2021: Blue and White polled a median of 4
    seats and won 8. Its log probability is -6.23 / -6.01 / -5.78 under
    cal_B against -3.08 / -3.05 / -3.20 under shipped. Yamina, Meretz and
    the Joint List lose too.
  - The stack's 2021 interval score is +.64 / +3.31 / +3.60 against
    shipped.
  - Over the other seven cycles the stack beats shipped by .31 / .40 /
    .38. The D-21 2013 fold also loses +1.08.
- **The log score says the same.**
  - The nested stack's LOO log score is below shipped's at every horizon
    (-.47 / -1.83 / -1.69), so it is below every component. It is above
    the single-arm selection at eve and D-7 and below it at D-21.
  - Without 2021 it is above shipped's (+3.19 / +2.72 / +2.03), but 2021
    alone costs -3.66 / -4.56 / -3.72.
  - The in-sample stack beats every component at every horizon. Its gap
    to the nested stack is 3.5-4.2 log points per horizon, the cost of
    four free weights fitted on seven cycles.
  - The bound is the mixture's, not the optimiser's: BFGS and EM reach
    the same optimum in every fold.
- **Single-arm selection** picks Bfix in seven folds and cal_B in the
  2021 fold, so it fails on the same cycle.

**The components under the same rule** (reported; s.62 registered the rule
for the stack only):
- cal_A fails D-7 alone: interval score +.099 (seeds +.192 / +.069 /
  +.035). Every other test passes, and its log score beats shipped's at
  every horizon (+.89 / +.43 / +.76).
- cal_B and resid_hybrid fail on the s.57.3 / s.60.2 folds.
- **Bfix passes every test at every horizon.** It is the only arm here
  that does.
  - Eve: median -.007, mean -.004, Brier -.0028, interval -.206,
    coverage .972.
  - D-7: median -.001, mean -.005, Brier -.0025, interval +.029 (seeds
    +.143 / -.067 / +.011), coverage .960.
  - D-21: median +.004, mean -.015, Brier -.0022, interval -.091,
    coverage .968.
  - Folds: 0 / 8 / 0 at each horizon. The closest to the boundary is
    D-21 2020 at +.093, then eve 2022 at +.051.
  - Its log score beats shipped's at every horizon (+1.80 / +1.49 /
    +1.61), it is the best single arm at D-21 on log score and CRPS, and
    its 2021 loss is small (-.72 / -1.01 / -.89).

### 62.3 2026 effect (frozen production posterior; outputs in scratch)

**Setup.**
- The posterior is main's m3_idata.nc of 16 Oct 18:54, copied to
  scratch (sha256 654a4414b4d48a762979e3755bd779d3d8b7c171736efe7f55ecb024df9a7382,
  the s.57.4 / s.60.3 posterior).
- The run used the BAYES_PROJECT_ONLY path, with
  bayes_model.PROCESSED_DIR on a scratch copy; the repo's data/processed
  was not written. Seeds are the production seed, +1 and +2.
- **Flag-None check: passed.** With ERROR_STACK None, the patched code is
  byte-identical to main 2a8477f's unpatched code at all three seeds:
  bayes_forecast_2026.csv, bayes_forecast_blocs.csv and the draws. At
  seed +0 both equal the committed bayes_forecast files.
- The stack uses the production weights {cal_A .302, cal_B .448,
  resid_hybrid .250}. The realised variant shares are .296-.299 /
  .449-.459 / .242-.252.
- The Bfix column is outside the registration. It is added because Bfix
  passed in 62.2.

| (seeds +0 / +1 / +2) | shipped | stack (production weights) | Bfix (not registered) |
|---|---|---|---|
| RZP-Zehut pass | .560 / .559 / .563 | .599 / .600 / .603 | .581 / .578 / .584 |
| Otzma pass | .799 / .792 / .798 | .837 / .827 / .840 | .822 / .813 / .821 |
| Ra'am pass | .760 / .769 / .763 | .842 / .851 / .846 | .795 / .797 / .796 |
| Amcha pass | .252 / .252 / .244 | .236 / .236 / .232 | .241 / .242 / .235 |
| Reservists pass | .224 / .225 / .219 | .206 / .211 / .208 | .216 / .218 / .214 |
| Blue and White pass | .016 / .015 / .016 | .005 / .004 / .004 | .006 / .006 / .004 |
| P(NB >= 61) | .128 / .118 / .126 | .100 / .093 / .094 | .113 / .102 / .108 |
| P(change bloc >= 61) | .063 / .064 / .064 | .051 / .050 / .050 | .056 / .055 / .056 |
| P(neither) | .809 / .819 / .810 | .849 / .857 / .856 | .831 / .843 / .836 |
| NB seats, mean [90%] | 53.0 [42-64] | 52.9 [43-63] | 52.9 [43-63] |

- **Seed means.**
  - Shipped: RZP-Zehut .561, Otzma .796, Ra'am .764; P(NB >= 61) .124,
    deadlock .813.
  - Stack: .601 / .835 / .846; .096 and .854.
  - Bfix: .581 / .819 / .796; .108 and .837.
- **Central seats** are unchanged under every arm and seed: Likud 25,
  Yashar 23, Together 11, the Democrats, the Joint List and UTJ 9, Shas
  9 / 8 / 8 by seed (the same under each arm), YB 8, Otzma 6, Ra'am 5,
  RZP-Zehut 4, Amcha and the Reservists 0.
- **The stack's intervals narrow on the small and middle lists.** YB 4-12
  -> 5-11, the Democrats 5-13 -> 6-13, the Joint List 5-13 -> 6-12 / 6-13,
  Otzma 0-11 -> 0-10, Ra'am 0-9 -> 0-8 and Amcha 0-8 -> 0-7. Likud and
  Yashar barely move.
- **Size of the move.** The stack moves the established satellites
  about 70% of the way to resid_hybrid's s.60.3 effect, which has the
  same baseline. Ra'am goes .764 -> .846, against the hybrid's .883. The
  stack cuts P(NB >= 61) by about 2.8 points and raises deadlock by about
  4. Bfix moves the same way, about half as far.

### 62.4 Recommendation under the rule

- **Not shipped.** The nested-LOO stacked forecast fails the
  pre-registered s.53 / s.55 rule: the interval score is +.064 at D-7 and
  +.114 at D-21.
  - ERROR_STACK stays None, and production is bit-identical to main.
  - The fitted weights are recorded as bayes_model.ERROR_STACK_WEIGHTS.
    The mechanism is in the code: ERROR_STACK, error_stack_assign, and
    the harness layer error_stack.
  - The headline is unchanged.
- **What the grade establishes.**
  - Stacking removes the whole-seat median flips that failed cal_B and
    resid_hybrid: all 24 folds tie. It also improves mean MAE, Brier,
    coverage and the bloc Brier at every horizon.
  - With eight cycles the weights are not identified. One cycle (2021,
    Blue and White doubling from 4 to 8) moves cal_B's weight from .45 to
    1.00.
  - The leave-one-out log score of the stack is below shipped's at every
    horizon, although the in-sample stack beats every component. The
    in-sample gain is overfitting of four weights to seven cycles. It is
    not a forecast gain.
  - Under this record a stack of these five arms cannot be shown to beat
    shipped.
- **For the owner: Bfix passes the standing rule.**
  - On these runs Bfix (the decompose() index fix at the shipped width
    0.9, RESID_SPACE "seat_fix") passes every test at eve, D-7 and D-21
    on three seeds. It is the only arm of the five that does.
  - It was a component here, not s.62's registered candidate, so its
    grade is known before any registration of it. The streams and the
    rule are the ones a registration would use, so a re-run would
    reproduce these numbers exactly.
  - Its margins are thin: the D-7 interval score is +.029 against a .05
    floor (seed 0 alone +.143, the s.48.6 failure), and the D-21 2020
    fold is +.093 against .1.
  - It fixes a defect (s.48 amendment 1: the label collision subtracts
    the leader anchor from every cycle's row carrying that label).
  - 2026 effect: P(NB >= 61) .124 -> .108, RZP-Zehut .56 -> .58, Otzma
    .80 -> .82, Ra'am .76 -> .80; central seats unchanged.
  - Shipping it is a one-line change (RESID_SPACE "seat_fix"). It is
    recommended as the next decision, disclosed as graded inside s.62.
- **For the site.** No number changes. The s.57 / s.60 statement stands:
  RZP-Zehut, Otzma and Ra'am are more likely understated than
  overstated. Every graded correction (cal_B, resid_hybrid, the stack,
  Bfix) moves them up.

### 62.5 Not established

- **A regularised stack was not registered.** Candidates are a
  Dirichlet prior on the weights, fewer arms (shipped against one
  vote-share arm), or hierarchical stacking (Yao, Pirš, Vehtari & Gelman
  2022). The fold instability says an unregularised stack on eight
  cycles is too noisy.
- **Not graded:**
  - per-horizon weights;
  - a bloc-level score in the objective (the weights see only per-list
    seats);
  - D-56.
- **The 2026 effect is the plain projection.** The registration
  mixture, official forecast and formation chain were not run.
- **Production-only layers** (EVENT_RISK_HORIZON, NEW_LIST_MULT, the
  certainty churn and the kalpi caps) act identically under every
  variant and have no harness analogue.

### 62.5 Decision (18 Oct): Bfix ships

The stack (the registered candidate) does not ship. Its component Bfix -
the decompose() index-collision fix at the shipped width (RESID_SPACE
"seat_fix"; line 1.48 + 0.041 x seats instead of 1.83 + 0.044) - was
graded here on three seeds at eve, D-7 and D-21, the s.55 protocol, and
passes the standing s.53/s.55 rule at every horizon: interval score -.206 /
+.029 / -.091, Brier and mean MAE better at every horizon, every median
fold a tie. This is the three-seed re-grade s.48.6 queued for this family
(it had failed at D-7 on one seed, +.143). Provenance disclosed: the
three-seed result was produced inside s.62, not under its own
pre-registration, and the margins are thin (D-7 interval +.029 against .05;
D-21 2020 fold +.093 against the .1 tie bound). Shipped because it corrects
a real defect and passes the rule; the harness mirror (ALL_LAYERS
resid_space) now reads bm.RESID_SPACE, so later candidates grade against
it. Effect on 2026 (frozen 16 Oct posterior, three seeds): P(NB>=61) .124 ->
.108; RZP-Zehut pass .561 -> .581, Otzma .796 -> .819, Ra'am .764 -> .796;
central seats unchanged.

## 61. Hierarchical Bayesian error model (18 Oct, D-9)

### 61.1 Pre-registration (written before any harness run of these arms)

**Why.** The election-day error stack is a set of moment estimates from
eight cycles (about 90 list-cycle errors), plugged in as fixed values:
the bloc swing t(5) x BLOC_SWING_SD 3.36, the haredi family t x 1.77 around
the e0 mean -0.98, and the per-list residual (1.83 + 0.044 x seats) x
RESID_SCALE 0.9 (x NEW_LIST_MULT 1.35 in production). Four defects are on
the record:
- decompose() has the pooled-index collision (s.48);
- its seat-error widths count threshold deaths twice (s.57);
- RESID_SCALE 0.9 was tuned on the collided line (s.48.6);
- parameter uncertainty is not propagated: the ERR verifier's
  posterior-predictive bloc sd for a new cycle is about 4.1-4.2 against
  the plugged-in 3.36.

This section replaces the three layers with one joint hierarchical model of
final-poll error, in the spirit of Shirani-Mehr, Rothschild, Goel & Gelman
(2018, JASA) and Heidemanns, Gelman & Morris (2020), and grades it under
the standing rule.

**The record** is decompose_vote's: error_decomposition._vote_frames,
reused unchanged. It holds 95 list-cycles of lists that ran, 9-14 per
cycle. Each error is the final-window polled share minus the actual share,
in u = 120 x share. I checked its construction.
- Labels are unique (reset_index per cycle, ignore_index on concat), so
  the s.48 collision does not exist here.
- A list that died at the threshold enters at its VOTE miss (Meretz 2022
  +0.49 u, not 4.4 seats), so there is no double count.
- For lists that won seats, both sides go through the same seat-to-share
  map: polled is seats/120 x (1 - wasted - 0.01), actual is seats x (1 - W
  - 0.01). Actual_u therefore carries d'Hondt rounding. It is kept,
  because the polled side is built the same way.
- The errors do not sum to zero. Per cycle they sum to +0.24 to +2.36 u
  (mean +1.39): the modelled lists are over-polled together by the share
  of the unpolled lists. The model gives this its own nuisance term
  (kappa, below), so it does not bias the other components.

**The model** (src/error_model.py), for list l in cycle c:

    e_cl = beta_c s_cl + phi^h_c f^h_cl + phi^a_c f^a_cl + kappa_c g_cl + eps_cl
    eps_cl ~ Student-t(nu, 0, sigma_l),
    log sigma_l = a + b log(size_l / 8) + gamma new_l

- **Loadings are exactly the projection's.** Let w be the polled share,
  clipped at 0.1 as in decompose().
  - The bloc loading s is +w/W_NB on the Netanyahu bloc and -w/W_rest
    elsewhere. It is zero-sum, and beta_c is the NB-side total error in u.
  - The family loadings f^h and f^a are +w/W_fam on the family and
    -w/W_others elsewhere. This is the zero-sum allocation that
    project() and project_cycle() use for family shocks.
  - g = w/W_all is the common proportional error.
- **The bloc is the harness's.** It is the registry bloc plus
  VAL_BLOC_OVERRIDES on the DECOMP-expanded components: the bloc the
  projection moves and P(NB >= 61) counts. It differs from decompose()'s
  family bloc (right + haredi) on nine rows: Yisrael Beytenu 2019a-2022,
  Zehut 2019a, Yamina 2019s and 2021, New Hope 2021. On this definition
  the NB-side totals are +2.67 / +5.72 / -1.75 / -4.05 / +2.60 / +1.68 /
  -0.27 / +0.85 (mean +0.93, sd 2.99); on decompose()'s they are mean
  +1.47, sd 2.99.
- **Size and first-cycle covariates.**
  - size = polled u, floored at 0.5. The record's smallest is 1.7 u, and
    the projection floors base0 x 120 at the same 0.5.
  - new = a first-cycle list: none of its components was on an earlier
    ballot (results.csv, ran_vote_shares.csv). Components are expanded
    by DECOMP / DECOMP_FIDELITY plus four lineage facts:
    - Yamina 2019s = New Right + URWP;
    - the Joint List 2019s = Hadash-Ta'al + Balad + Ra'am;
    - RZP 2021 = Tkuma + Otzma + Noam;
    - the Democrats 2026 = Labor + Meretz.
  - 2009 has no earlier cycle in the record: every list it polled had
    run in 2006, so none is flagged.
  - The record has 10 first-cycle rows: Hatnuah, Yesh Atid, Am Shalem and
    Otzma 2013; Kulanu 2015; New Right, Zehut and Gesher 2019a; New Hope
    and NEP 2021.
  - In 2026 the rule flags Yashar, Amcha, the Reservists and the micro
    lists. NEW_LIST_IDS has the same substantive lists, plus Unity, which
    has withdrawn.
- **Cycle effects are hierarchical and non-centred.**
  - beta_c = mu_beta + sigma_beta z_c.
  - phi^h_c = mu_h + sigma_h z^h_c.
  - phi^a_c = mu_a + sigma_a z^a_c.
  - kappa_c = mu_k + sigma_k z^k_c.
  - Each z is N(0, 1).
- **Priors** (weakly informative, in u):
  - mu_beta ~ N(0, 3), sigma_beta ~ HalfNormal(5);
  - mu_h, mu_a, mu_k ~ N(0, 3); sigma_h, sigma_a, sigma_k ~ HalfNormal(3);
  - a ~ N(0, 1), the log scale of an 8-u list;
  - b ~ N(0.5, 0.5), centred on sampling-theory sd proportional to
    sqrt(share);
  - gamma ~ N(0, 0.5);
  - nu = 2 + Gamma(2, 0.1), which keeps the variance finite (mean 22).
- **Anchors are not in the model.** They are retired in production
  (ANCHORS_ON False), so Likud's and the leader's misses stay in the
  residual, which is the stack the projection runs.

**Scale: u = 120 x share, not logit.**
- Every shock the projection applies is additive in u. The bloc swing
  and the family shocks are zero-sum allocations of a u total, and the
  residual is added to the share vector before the threshold.
- On the logit scale a zero-sum total cannot be allocated additively.
  Fitting on logits would also change what the projection does, not only
  how the parameters are estimated.
- The reason to prefer logits is heteroscedasticity, and b models it
  directly. With b ~ 0.5 the residual behaves like a logit-scale error.
- The record is measured in u.

**The Arab family stays with the graded turnout term.** It enters the fit
only as a nuisance: phi^a is estimated so that the Arab lists' correlated
error does not leak into beta (Arab lists load on the non-NB side) or into
the residual scale. It is never drawn at projection.
- The turnout term was graded and shipped (s.43, regB). It carries
  information an exchangeable phi cannot:
  - the regime, unified vs split, through the LOO regime mean of
    turnout;
  - the regression of the family error on the ratio-implied error.
- On the record the regimes have opposite signs: unified under-counts
  (mean -1.35 seats), split over-counts (+1.35). An exchangeable N(mu_a,
  sigma_a) would centre the 2026 draw near zero with an inflated sd, and
  would discard the 2026 regime (unified Joint List).
- The haredi effect keeps the kalpi coupling to the Arab draw. The haredi
  draw uses the normal part z of the same correlated bivariate draw
  (KALPI_FAMILY_RHO 0.5) whose t version drives the Arab turnout draw.

**Projection (H1).** Each simulation does three things.
1. It takes one joint posterior draw j of (mu_beta, sigma_beta, mu_h,
   sigma_h, a, b, gamma, nu).
2. It draws a NEW election from the posterior predictive:
   - beta = mu_beta_j + sigma_beta_j z;
   - phi^h = mu_h_j + sigma_h_j z^h;
   - eps_l = sigma_l(j) x t(nu_j), with size = base0 x 120 (the pre-shock
     projected share, the quantity the shipped residual uses), floored
     at 0.5, and new by the same rule as the fit.
3. The truth moves by -beta, -phi and -eps (error space), at the stack's
   existing positions and with the existing base-share loadings.

What changes and what stays:
- **Replaced:** the bloc swing (t(5) x BLOC_SWING_SD), the haredi family
  shock (t x sd around the e0 mean), and the residual line x RESID_SCALE
  (and NEW_LIST_MULT in production; gamma replaces it).
- **The width multiplier is 1.0,** because the width is now estimated
  (bm.HIER_RESID_SCALE, harness layer hier_width).
- **Unchanged:**
  - the Arab turnout term;
  - the gevalt coupling, trailing-Likud, new-straddler, loyal-sd and
    kalpi caps;
  - the withdrawn-list zero hold;
  - in production, EVENT_RISK_HORIZON's event walk (added to -beta),
    STACK_SCALE (on the random parts) and the certainty layer.
- **Code:**
  - production: bayes_model.ERROR_MODEL, "moments" (shipped) or
    "hierarchical";
  - harness: ALL_LAYERS error_model / hier_width, arm `hier_H1`;
  - calibration_arms: arms H1 / H2.

Flag off, production and harness are bit-identical to main.

**Leave-one-cycle-out.** The harness grades cycle c with the fit that
leaves c's record out: 8 fits, plus the full-sample fit that production
uses. They are cached as netcdf under data/processed/error_model/, keyed by
a hash of the record, the priors, the sampler settings and the spec.

**Sampler and gates.**
- Settings: NUTS, 4 chains x 1,000 draws after 1,500 tuning steps,
  target_accept 0.95, seed 20261027.
- Gates: 0 divergences, r-hat <= 1.01 and bulk ESS >= 400, on every
  parameter except the raw non-centred z's (cycle effects, hyper-
  parameters, nu).
- A failing fit gets one retry at tune 3,000 and target_accept 0.99. A
  fold that still fails is reported and its cycle is graded as a failure
  of the arm.

All nine fits passed on the first run, and so did the three nested
variants below: 0 divergences, r-hat at most 1.004, bulk ESS at least
1,310.

**Prior predictive checks** (2,000 draws on the full record's design; no
outcome used; observed values in brackets):
- the sd of beta across eight cycles: median 3.2, 90% interval 0.4-10.3
  [record's NB-total sd 2.99];
- |e| (median / 90th / 99th percentile):
  - lists < 4 u: 0.66 / 2.9 / 9.7 [0.46 / 1.36 / 1.61];
  - 4-12 u: 1.1 / 4.4 / 12.0 [0.82 / 2.19 / 5.67];
  - > 12 u: 2.5 / 8.5 / 26 [1.1 / 4.2 / 6.4];
- the share of simulated |e| above 20 u is 0.7% (above 10 u, 2.9%);
- nu: 5.6 / 18.6 / 48 (5th / 50th / 95th).

The priors cover the record with room on both sides. They put little mass
on errors a Knesset poll has never made.

**Estimation inputs** (computed before registration; no harness run of any
arm). Full-sample posterior means [90% HDI]:
- mu_beta +0.38 [-1.81, 2.33], sigma_beta 1.40 [0.01, 2.99];
- mu_h -1.14 [-2.44, 0.15], sigma_h 0.91;
- a 0.26, b 0.65 [0.45, 0.85], gamma 0.42 [0.05, 0.86] (first-cycle
  scale x1.52);
- nu 16.5 [2.7, 32.4], mostly prior.

Posterior-predictive sds for a new election (u = seats):

| | shipped (production) | H1, full sample | H1, LOO fold range |
|---|---|---|---|
| bloc beta | 4.34 (t(5) x 3.36) | 2.20 (mean +0.38) | 1.85-2.58 |
| haredi family | 2.28 (t x 1.77), mean -0.98 | 1.39, mean -1.14 | 1.20-1.61 |
| residual, 4 seats | 1.81 | 0.94 | 0.88-1.05 |
| residual, 25 seats | 2.63 | 3.13 | 2.62-3.62 |
| residual, 4 / 25, first-cycle | 2.44 / 3.55 (x1.35) | 1.51 / 5.03 | |

- **Before any grade, the model says:**
  - The correlated bloc error is SMALLER than the moment estimate.
    Once the residual scale rises with size (b 0.65), the NB-side total's
    variance is mostly the large lists' own misses: Likud 2015 -7.0,
    2019a -4.4. The moment estimator assigns that variance to the swing
    and then also measures it in the residual.
  - The small-list residual is about half the shipped one, as in cal_B.
  - Large and first-cycle lists are wider than shipped.
- **This is not the verifier's prediction.** The verifier's 4.1-4.2
  figure is a predictive sd of the eight NB-side totals themselves, with
  the bloc as the only correlated term. Here that total's variance is
  split between beta and the lists' residuals.

**Arms.**
- `H1` (primary). The hierarchical errors replace the bloc, haredi family
  and residual layers, at width 1.0 (hier_width = bm.HIER_RESID_SCALE),
  leave-one-cycle-out.
- `H2` (secondary, reported). H1 plus the s.48 nested width selection:
  - The grid is hier_width 0.4 to 1.6 in steps of 0.1, multiplying the
    hierarchical residual.
  - For each held-out cycle, the width is the one with the lowest mean
    interval score over the other seven cycles. Each cycle's score is
    its seed mean, and the per-horizon pooled scores are averaged with
    equal weight over eve, D-7 and D-21 (three seeds at every horizon,
    s.55).
  - The held-out cycle is then graded at that width.
  - The production width is the same rule's choice on all eight cycles.
  - The error-model fit is the held-out cycle's LOO fit throughout, as
    s.48 did with the decompose() parameters.

**Grading.** The s.50 LOO-scorecard caches (the shared harness cache, read
only); outputs in scratch; at most four processes; the shipped list mask
(`*_fixed`).
- **H1 at the eve:** `HARNESS_ABLATIONS=shipped,hier_H1
  HARNESS_SKIP_WIDTH=1 python src/validate_bayes.py`, with
  HARNESS_SEED_OFFSET 0 / 100 / 200.
- **H1 at D-7 and D-21:** `HORIZONS=7,21 HORIZON_SKIP_GRID=1
  HORIZON_LAYERS='hier_H1:{"error_model": "hierarchical"}' python
  src/validate_horizon.py`, offsets 0 / 100 / 200, against "calendar".
- **H2:** `python src/calibration_arms.py run OUT --arms H1 --horizons
  eve,7,21 --seeds 0,100,200`. These are the same streams as above:
  SEED + 11 + offset at the eve, SEED + h + offset at D-h, calendar
  weeks.
  - The nested picks are calibration_arms' nested_choice.
  - H2's held-out rows are graded under the rule below against the base
    rows of the same run.
  - The runner's base rows must equal the validate_bayes /
    validate_horizon shipped rows, and its H1 rows at width 1.0 must
    equal the hier_H1 rows.
- **Pooling:** per seed, the mean over the eight cycles, then the mean
  over the three seeds. A fold is a cycle, and its value is the
  three-seed mean.
- **Reproduction gate:** the shipped rows must equal the s.57 / s.60
  baselines:
  - eve 1.4927 / 1.6291 / .9807 / .0475 / 9.217;
  - D-7 1.4866 / 1.6478 / .9896 / .0490 / 9.360;
  - D-21 1.6211 / 1.7943 / .9896 / .0541 / 9.690.

**Rule (the s.53 / s.55 rule, unchanged).** An arm passes if, at EACH of
eve, D-7 and D-21 (offsets 0/100/200 pooled):
- it wins or ties median MAE in every leave-one-cycle-out fold (fold
  delta < +0.1 seat);
- pooled mean MAE, threshold Brier and interval score are not worse than
  shipped by more than .010 / .0010 / .05;
- pooled 90% coverage is not further from .90 than shipped's.

H1 is the decision. If H1 passes, H1 is recommended. If H1 fails and H2
passes, H2 is recommended at its all-eight-cycles width. If both fail,
nothing ships.

**Reported, not decisive.**
- **CRPS** for the discrete seat distribution: sum over k of (F(k) -
  1{y <= k})^2, averaged over the list mask, then cycles, then seeds.
- **The PIT histogram:** the randomised PIT F(y-1) + V (F(y) - F(y-1)),
  V ~ U(0, 1), in 10 bins, pooled over lists, cycles and seeds.
- **The reliability rows** for 10-30% and 50-90%, binned on each arm's
  own probabilities with n, stated and realised, plus the fixed set (the
  lists shipped puts in 50-90%).
- **The bloc Brier** for P(NB >= 61).

These come from a scratch runner on exactly the graded streams, which must
reproduce the graded rows.

**Also reported:**
- posterior summaries;
- posterior predictive coverage of each cycle's errors, both in-sample
  and from the leave-the-cycle-out new-election predictive;
- LOO-PSIS (arviz.loo, pointwise) against nested variants on the full
  record: no size slope (b = 0), Gaussian residual, no first-cycle term.
  These justify the structure. They do not change the graded arm.

**2026 effect.** The run is BAYES_PROJECT_ONLY on a scratch copy of main's
m3_idata.nc (16 Oct 18:54), with bayes_model.PROCESSED_DIR on a scratch
copy and seeds +0 / +1 / +2.
- With the flag off, the run must reproduce the committed
  bayes_forecast_2026.csv and bayes_forecast_blocs.csv.
- Reported:
  - p_pass for RZP-Zehut, Otzma, Ra'am, Amcha, the Reservists and Blue
    and White;
  - the bloc probabilities and central seats;
  - the posterior-predictive bloc sd and the residual sd at 4 and 25
    seats, against the shipped values.

**Amendment 1 (18 Oct, after a first grade; on the coordinator's relay).**
- **What happened.** Main's shipped configuration moved at 91bc933
  (s.62.5): RESID_SPACE "seat_fix" ships. That is decompose()'s
  index-collision fix at width 0.9, line 1.484 + 0.0408 x seats, and the
  harness ALL_LAYERS resid_space now reads bm.RESID_SPACE.
- **Disclosure.** H1 and H2 had already been graded once on the 2a8477f
  code, against the old shipped "seat" line. The registered commands were
  used, and that reproduction gate passed to the digit. Neither arm passed
  that grade.
- **What the amendment changes.** The rule's comparator is the shipped
  configuration, so the verdict is taken against the NEW shipped.
  - The worktree is rebased onto 91bc933. Section 61 now sits after s.62
    with its text unchanged.
  - Every registered command is re-run on the rebased code.
  - The reproduction gate becomes s.62.2's Bfix rows (median / mean /
    coverage / Brier / IS):
    - eve 1.4858 / 1.6253 / .972 / .0447 / 9.011;
    - D-7 1.4860 / 1.6424 / .960 / .0465 / 9.389;
    - D-21 1.6249 / 1.7795 / .968 / .0519 / 9.599.
  - The flag-off 2026 check is against the 91bc933 bayes_forecast files.
  - Both comparisons are reported.
- **What it does not change.** The arms, the model, the fits, the rule
  and the decision order are unchanged. H1 replaces the residual whatever
  line ships, so its own draws do not depend on the base. They are the
  same parent stream, and only the shipped list mask moves.
- **New shipped residual sds** (in place of the "shipped" column above):
  1.48 at 4 seats and 2.25 at 25 (first-cycle x1.35: 2.00 / 3.04).

### 61.2 Results

**Provenance.**
- **Pre-registration.** 61.1, up to amendment 1, was committed alone
  before any harness run of either arm: worktree commit 5410b80 on
  2a8477f, 17 Oct 23:48. Its text sha256 is
  0a85652b707265fc2dc31fb642a34a832bc4e6dbed16b393dac0d84c5d40063f.
  Rebased onto 91bc933 it is afe173e, with the same text, placed after
  s.62.
- **Implementation.** It was committed next (922f8cf, rebased 2d7a62d).
  The harness was first run on it.
- **Amendment 1.** It was committed alone after the first grade and
  before the re-grade: 8e34297, text sha256 3b7bc34d515fa0e1....
- **Runs.**
  - The registered commands on the shared s.50 LOO-scorecard cache, read
    only.
  - HARNESS_OUT_DIR in scratch, at most four harness processes.
  - The error-model posteriors in data/processed/error_model/
    (gitignored; `python src/error_model.py fit` rebuilds them).

**Sampler gates: passed in every fit, on the first run.**

| fit | n | divergences | max r-hat | min bulk ESS |
|---|---|---|---|---|
| full sample (production) | 95 | 0 | 1.004 | 1,655 |
| LOO folds (8) | 81-86 | 0 | 1.002-1.004 | 1,411-1,946 |
| full sample: no size slope / Gaussian / no first-cycle term | 95 | 0 | 1.003-1.004 | 1,311-1,717 |

**Posterior summaries.**
- The full-sample values are in 61.1.
- Across the eight LOO fits, the posterior means are:
  - sigma_beta 1.10-1.67 (the 95th percentiles reach 2.9-4.3);
  - b 0.54-0.77;
  - gamma 0.17 (without 2013, whose Yesh Atid -7.5 carries it) to 0.47;
  - nu 10-21, which is prior-dominated (90% intervals about 4-45).
- **The cycle bloc effects beta_c are all shrunk to -0.5..+0.8** (sd about
  1.7 each). The NB-side totals range from -4.0 to +5.7, but the model
  attributes most of that range to the bloc's own lists, whose misses run
  in OPPOSITE directions inside it:
  - 2015: Likud -7.0, Jewish Home +4.0;
  - 2019a: Likud -4.4, URWP +1.8, New Right +2.0.

  The pattern is the gevalt transfer, which a common bloc factor does
  not describe. The moment estimator books it as swing and then measures
  it again in the residual.
- **The haredi effects phi^h_c are -0.7 to -1.8 in all eight cycles.**
  The polls under-count the haredi family every time.

**Posterior predictive checks against the record.**
- **In-sample 90% coverage** (each cycle's own effects): 87 of 95 errors
  (.916). By cycle it runs from .82 (2015) to 1.00 (2019s, 2022).
- **Leave-the-cycle-out new-election 90% coverage**: 85 of 95 (.895).
  - 2009 .90, 2013 .93, 2015 .82, 2019a .71, 2019s 1.00, 2020 .89, 2021
    .93, 2022 1.00.
  - 2019a is the weak cycle. Its misses are the large lists (Likud -4.4,
    Blue and White -4.1), Labor +3.8 and Shas -2.2.
- **The NB-side total** under the LOO predictive has PIT .63 / .82 / .28
  / .10 / .65 / .55 / .39 / .47 (2009 to 2022). None is outside (.05,
  .95).
- **The largest standardised LOO miss** is 3.4 (Yesh Atid 2013). The t
  tail carries it.

**LOO-PSIS** (arviz.loo, pointwise, full record):

| model | elpd_loo | p_loo | d_elpd vs full | se of d | Pareto k > .7 |
|---|---|---|---|---|---|
| full (size slope, t, first-cycle) | -177.9 | 12.4 | 0 | - | 0 |
| no first-cycle term | -178.2 | 10.9 | -0.3 | 1.8 | 0 |
| Gaussian residual | -179.1 | 12.0 | -1.1 | 1.0 | 1 |
| no size slope | -187.1 | 21.3 | -9.2 | 5.0 | 0 |

- **The size slope is what the record supports most:** 9.2 elpd, 1.8
  se.
- **The Student-t is a small gain:** 1.1 elpd (1.1 se). The Gaussian
  fit has one influential point (k > .7, Yesh Atid 2013) that the t
  absorbs.
- **The first-cycle term is a wash on the record:** 0.3 elpd, 0.2 se.
  It stays as registered, because the stack H1 replaces carries a
  first-cycle width term (NEW_LIST_MULT).
- Pointwise LOO conditions on each cycle's effects, so it scores the
  residual structure. The leave-cycle-out PPC above checks the
  cycle-level predictive.

**Reproduction gates: passed.**
- **Old shipped** (2a8477f, "seat"): the shipped rows equal the s.57 /
  s.60 baselines to the digit (eve 1.4927 / 1.6291 / .9807 / .0475 /
  9.2173; D-7 1.4866 / 1.6478 / .9896 / .0490 / 9.3600; D-21 1.6211 /
  1.7943 / .9896 / .0541 / 9.6900). At offset 0, model_validation_bayes
  .csv and model_validation_bayes_lists.csv are byte-identical to main's.
- **New shipped** (91bc933, "seat_fix"): the shipped rows equal s.62.2's
  Bfix rows (eve 1.4858 / 1.6253 / .9717 / .0447 / 9.0108; D-7 1.4860 /
  1.6424 / .9604 / .0465 / 9.3891; D-21 1.6249 / 1.7795 / .9683 / .0519
  / 9.5994).
- **calibration_arms runner:** its base rows and its H1 rows at width
  1.0 equal the registered rows, 144 of 144 with max difference 0, on
  both bases.

**H1 against the NEW shipped (the verdict).** Pooled over three seeds.
Each cell is median / mean / coverage / Brier / IS, then the bloc Brier
for P(NB >= 61); folds are W/T/L at |d| < .1.

| horizon | shipped (seat_fix) | H1 | folds | result |
|---|---|---|---|---|
| eve | 1.4858 / 1.6253 / .972 / .0447 / 9.011; .0388 | 1.5393 / 1.6105 / .972 / .0405 / 8.672; .0277 | 0/8/0 | passes |
| D-7 | 1.4860 / 1.6424 / .960 / .0465 / 9.389; .0375 | 1.4827 / 1.6382 / .958 / .0437 / 9.087; .0280 | 2/5/1 | fails: 2015 +.121 |
| D-21 | 1.6249 / 1.7795 / .968 / .0519 / 9.599; .0558 | 1.6753 / 1.7695 / .975 / .0498 / 9.244; .0425 | 0/7/1 | fails: 2015 +.182; coverage .975 vs .968 |

**H1 against the OLD shipped** (seat; the first grade, reported):

| horizon | shipped (seat) | H1 | folds | result |
|---|---|---|---|---|
| eve | 1.4927 / 1.6291 / .981 / .0475 / 9.217; .0428 | as above | 0/5/3 | fails: 2019s +.100, 2021 +.119, 2022 +.103 |
| D-7 | 1.4866 / 1.6478 / .990 / .0490 / 9.360; .0410 | as above | 1/6/1 | fails: 2015 +.121 |
| D-21 | 1.6211 / 1.7943 / .990 / .0541 / 9.690; .0593 | as above | 0/6/2 | fails: 2015 +.182, 2020 +.185 |

The H1 rows are the same on both bases. The hierarchical branch does not
read the residual line, so on the shipped list mask the cells are
identical.

- **Where H1 fails.** Against the new shipped it passes every eve test,
  with all eight folds ties (largest +.095, 2021), and every pooled test
  at D-7. It fails three tests:
  - the 2015 fold at D-7;
  - the 2015 fold at D-21;
  - the D-21 coverage test: .975 against .968. Shipped's seat_fix had
    already brought D-21 coverage from .990 to .968.
- **Beyond the floors, H1 improves at the eve / D-7 / D-21:**
  - mean MAE -.015 / -.004 / -.010;
  - threshold Brier -.0042 / -.0028 / -.0021;
  - interval score -.34 / -.30 / -.36;
  - bloc Brier -.0111 / -.0095 / -.0133 (-29% / -25% / -24%).
- **The pooled median is worse** at the eve (+.053; by seed +.075 /
  +.039 / +.047) and at D-21 (+.050), and level at D-7 (-.003).
- **The 2015 fold** is one-seat median flips on large lists, the
  mechanism s.60.2 described:
  - At D-7 the Joint List goes 13 -> 14 (actual 13) in all three seeds,
    and Labor-Hatnuah 24 -> 25 (actual 24) in one.
  - At D-21 Labor-Hatnuah goes 24 -> 25 (actual 24) and Likud 26 -> 25
    (actual 30) in all three seeds.
  - Meanwhile the small lists' pass probabilities move under the
    narrower small-list residual (D-7: Meretz .75 -> .83, Yisrael
    Beytenu .71 -> .74, Kulanu .99 -> .97, Otzma-Yachad .45 -> .43).
  - The Likud move is consistent with the predictive bloc mean (+0.38
    seats of NB over-polling) and the narrower swing.
- **Against the old shipped,** the eve folds 2019s / 2021 / 2022 lose too.
  Blue and White goes 32 -> 31 (2019s); New Hope, the Joint List and Yesh
  Atid gain a seat (2021); Yesh Atid and UTJ gain one (2022). These are
  the cal_B / hybrid flips of s.57.3 and s.60.2. Against seat_fix,
  which narrows every list a little, they become ties.

**H2 (the nested width).**
- **The picks** (held-out cycle -> hier_width) are 2009 0.6, 2013 0.8,
  2015 / 2019a / 2019s / 2020 0.9, 2021 0.6, 2022 0.9. They are the
  same on both bases.
- **The all-eight choice is 0.9.** The training interval score, averaged
  over the three horizons, is lowest at 0.9 (8.81, against 9.00 at 1.0).
  The horizons differ: eve 0.9, D-7 0.7, D-21 0.8.

| horizon | shipped (seat_fix) | H2 (held-out widths) | folds | result |
|---|---|---|---|---|
| eve | 1.4858 / 1.6253 / .972 / .0447 / 9.011; .0388 | 1.5308 / 1.6019 / .931 / .0395 / 9.321; .0248 | 0/8/0 | fails: IS +.310 |
| D-7 | 1.4860 / 1.6424 / .960 / .0465 / 9.389; .0375 | 1.4925 / 1.6367 / .934 / .0436 / 9.596; .0257 | 2/5/1 | fails: 2015 +.167; IS +.207 |
| D-21 | 1.6249 / 1.7795 / .968 / .0519 / 9.599; .0558 | 1.6758 / 1.7677 / .923 / .0501 / 9.732; .0400 | 0/7/1 | fails: 2015 +.182; IS +.132 |

- **H2 fails at every horizon.** The held-out picks of 0.6 for 2009 and
  2021 are too narrow for those two cycles.
  - The 2021 fold's interval score rises by +3.9 at every horizon, and
    2009's by +1.7 / +1.6 at the eve and D-7.
  - The pooled loss is beyond the floor in every seed at the eve and D-7
    (D-21 by seed: +.20 / +.18 / +.01).
  - Coverage falls to .92-.93.
- **Against the old shipped H2 also fails:**
  - eve: the 2019s fold +.100 and IS +.104;
  - D-7: 2015 +.167 and IS +.236;
  - D-21: the 2015 and 2020 folds.
- **Reported, not an arm under the rule: H1 at the all-eight width 0.9.**
  It passes the eve (IS 8.382, -.63) and fails D-7 and D-21 on the 2015
  fold alone.

**Reported, not decisive.** These come from the scratch runner on the
graded streams. It reproduces all 216 graded rows (arm x horizon x cycle
x seed) exactly.

| | eve | D-7 | D-21 |
|---|---|---|---|
| CRPS, shipped / H1 / H2 | 1.0848 / 1.0807 / 1.0847 | 1.1171 / 1.1169 / 1.1310 | 1.1941 / 1.1943 / 1.2062 |
| bloc Brier, shipped / H1 / H2 | .0388 / .0277 / .0248 | .0375 / .0280 / .0257 | .0558 / .0425 / .0400 |
| mean 90% width, shipped / H1 / H2 | 7.61 / 7.24 / 6.57 | 7.55 / 7.24 / 6.53 | 7.92 / 7.52 / 6.97 |

- **CRPS is a tie for H1** (-.004 / -.000 / +.000). The fold differences
  are within ±.05. H2 is worse at D-7 and D-21 (+.014 / +.012).
- **PIT** (randomised, 10 bins, about 94 lists per seed). Under
  calibration the outer two bins hold .20 and the middle four (.3-.7)
  hold .40.

  | horizon | arm | outer two bins | middle four |
  |---|---|---|---|
  | eve | shipped / H1 / H2 | .117 / .170 / .202 | .440 / .418 / .383 |
  | D-7 | shipped / H1 / H2 | .117 / .181 / .213 | .447 / .408 / .383 |
  | D-21 | shipped / H1 / H2 | .144 / .200 / .207 | .421 / .372 / .340 |

  - Shipped's PIT is hump-shaped (over-dispersed forecasts).
  - H1's is close to uniform at the eve and D-7, and slightly U-shaped
    at D-21.
  - H2's is uniform to slightly U-shaped.
- **Reliability** (lists per seed, stated -> realised, each arm's own
  bins). The fixed set is the lists shipped puts in 50-90%.

  | horizon | arm | 10-30% | 50-90% | fixed set |
  |---|---|---|---|---|
  | eve | shipped | 8.0, .193 -> .125 | 19.7, .677 -> .847 | .677 -> .847 |
  | eve | H1 | 5.0, .189 -> .200 | 17.7, .697 -> .830 | .725 -> .847 |
  | eve | H2 | 6.0, .202 -> .333 | 15.3, .686 -> .804 | .745 -> .847 |
  | D-7 | shipped | 9.0, .181 -> .111 | 18.3, .704 -> .891 | .704 -> .891 |
  | D-7 | H1 | 6.0, .211 -> .333 | 14.0, .681 -> .857 | .751 -> .891 |
  | D-21 | shipped | 10.0, .200 -> .100 | 17.3, .731 -> .885 | .731 -> .885 |
  | D-21 | H1 | 7.0, .206 -> .286 | 12.7, .726 -> .842 | .778 -> .885 |

  - On the fixed set H1 closes 28% / 25% / 31% of the near-threshold
    underconfidence gap that s.57 diagnosed.
  - Its 10-30% band goes from over-stated to calibrated at the eve
    (.19 -> .20). At D-7 and D-21 it is under-stated (.21 -> .33, .21 ->
    .29), on 6-7 lists per seed.
  - The Brier on shipped's [.1, .9) lists is .150 / .147 / .162 for
    shipped and .138 / .139 / .156 for H1.

### 61.3 2026 effect (frozen production posterior; outputs in scratch)

**Setup.**
- The posterior is main's m3_idata.nc of 16 Oct 18:54 (sha256
  654a4414...), copied to scratch. It is the same posterior as s.57.4,
  s.60.3 and s.62.3.
- The run is the BAYES_PROJECT_ONLY path of bayes_model.main with
  bayes_model.PROCESSED_DIR on a scratch copy of data/processed, so the
  repo's data/processed was never written. The seeds are the production
  seed, +1 and +2.
- The full-sample error-model fit is the one the harness LOO fits sit
  beside.
- **Reproduction.** With the flag off, the rebased code is byte-identical
  to 91bc933's committed bayes_forecast_2026.csv, bayes_forecast_blocs.csv
  and bayes_draws.parquet. Before the rebase it was byte-identical to
  2a8477f's.
- **H1's draws** are byte-identical on both bases: the hierarchical
  branch does not read the residual line.

| (seeds +0 / +1 / +2) | shipped (seat_fix, 91bc933) | H1 | change, seed mean | old shipped (seat), seed mean |
|---|---|---|---|---|
| RZP-Zehut pass | .581 / .578 / .584 | .610 / .621 / .616 | .581 -> .616 | .561 |
| Otzma pass | .822 / .813 / .821 | .839 / .856 / .847 | .819 -> .847 | .796 |
| Ra'am pass | .795 / .797 / .796 | .877 / .871 / .872 | .796 -> .873 | .764 |
| Amcha pass | .241 / .242 / .235 | .225 / .228 / .227 | .239 -> .227 | .249 |
| Reservists pass | .216 / .218 / .214 | .216 / .199 / .203 | .216 -> .206 | .223 |
| Blue and White pass | .006 / .006 / .004 | .000 / .000 / .000 | .005 -> .000 | .016 |
| P(NB >= 61) | .113 / .102 / .108 | .059 / .065 / .060 | .108 -> .061 | .124 |
| P(change bloc >= 61) | .056 / .055 / .056 | .034 / .038 / .042 | .056 -> .038 | .064 |
| P(neither) | .831 / .843 / .836 | .907 / .896 / .898 | .837 -> .900 | .813 |
| NB seats, mean [90%] | 52.9 [43-63] | 52.5 [44-61] | sd 6.4 -> 5.25 | 53.0 [42-64] |

**Predictive sds** (seats; 61.1's table, against both shipped lines):

| | shipped seat_fix | old shipped seat | H1 |
|---|---|---|---|
| bloc error | 4.34 (t(5) x 3.36) | 4.34 | 2.20 (mean +0.38) |
| residual, 4 seats | 1.48 | 1.81 | 0.94 |
| residual, 25 seats | 2.25 | 2.63 | 3.13 |
| first-cycle, 4 / 25 seats | 2.00 / 3.04 | 2.44 / 3.55 | 1.51 / 5.03 |

- Production adds the event walk (EVENT_RISK_HORIZON) to the bloc under
  both models. It is unchanged.
- The NB total's seat sd falls from 6.4 to 5.25, because the swing is
  half as wide. The wider large-list residual does not make up for it.

**Central seats are unchanged.**
- Likud 25, Yashar 23, Together 11 (12 at seed +0 under H1), the
  Democrats 9, the Joint List 9, UTJ 9, YB 8, Otzma 6, Ra'am 5,
  RZP-Zehut 4, Amcha and the Reservists 0.
- Shas is 9 in every H1 seed, against 9 / 8 / 8 shipped.

**Intervals.**
- Small and middle lists narrow: YB 5-12 -> 6-11, the Joint List 6-13
  -> 6-12/13, RZP-Zehut 0-8 -> 0-7, Amcha 0-8 -> 0-7.
- Yashar widens (16-29 -> 15-30). It is first-cycle and large, so it
  takes the widest residual (sd 4.75 at 23 seats, against 2.9 shipped).

**The first-cycle rule** flags Yashar, the Reservists, Amcha, Unity
(withdrawn, held at zero) and the micro-lists. It does not flag the
Democrats (Labor + Meretz) or Together (with Yesh Atid).

**Reading.**
- H1 halves P(NB >= 61) again, from .108 to .061. The bloc's central
  count is about 8 seats below 61, and two things thin the tail:
  - the posterior-predictive swing is half as wide (2.2 vs 4.3);
  - its mean is +0.38 seats of NB over-polling, not zero.
- The satellites move toward the markets: Ra'am .80 -> .87, Otzma .82 ->
  .85, RZP-Zehut .58 -> .62. This is the cal_B / hybrid direction
  (s.57.4, s.60.3), from a model that estimates the small-list width
  instead of choosing a record.
- Blue and White's pass probability goes to zero. At 1 seat of polled
  share, the estimated residual (sd 0.41 at 1 u, against 1.37 shipped)
  no longer reaches the threshold.

### 61.4 Recommendation under the rule

- **Nothing ships from s.61.** Under the pre-registered s.53 / s.55 rule,
  as amended, against the shipped seat_fix stack:
  - H1 fails at D-7 (the 2015 fold, +.121) and at D-21 (the 2015 fold,
    +.182, and coverage .975 against .968).
  - H2 fails at every horizon (interval score +.31 / +.21 / +.13, and the
    2015 fold at D-7 and D-21).
  - Against the old "seat" stack both fail as well.

  ERROR_MODEL stays "moments". The module (src/error_model.py), the flag,
  the harness layers (error_model, hier_width), the hier_H1 arm and the
  calibration_arms H1 / H2 arms stay in the code, off. The headline is
  unchanged.
- **What the grade establishes.**
  - **The joint model is well posed on its own record.** Every fit passes
    the gates on the first run. The leave-cycle-out predictive covers
    85 of 95 errors at 90%, and every cycle's NB-side total sits inside
    its predictive.
  - **Structure.** The residual's size slope carries most of the
    record's information (9 elpd). Fat tails are a small gain, and the
    first-cycle term is neutral.
  - **The correlated bloc error is about half the shipped swing.** The
    predictive sd is 2.2 seats against 4.34. The NB-side total moves
    mostly through Likud and its own satellites moving in opposite
    directions; the moment estimator books that as swing and measures it
    again in the residual. The verifier's 4.1-4.2 is not what a joint
    model with a size-dependent residual gives.
  - **On the harness, H1 beats the shipped stack beyond the floor on
    every pooled score at every horizon:**
    - mean MAE, threshold Brier and interval score;
    - the bloc Brier for P(NB >= 61), by 24-29%.

    CRPS is level and the PIT is closer to uniform. It closes 25-31% of
    the established-list underconfidence gap of s.57.
  - **What it loses is the whole-seat median.** The pooled median is
    +.05 at the eve and D-21, and one fold (2015) is lost at D-7 and
    D-21, through one-seat flips on large lists. This is the pattern of
    cal_B and resid_hybrid (s.57.3, s.60.4): any narrowing of the
    small-list residual meets the fold test on the large lists.
- **For the owner** (not decisions this rule can make):
  - **The fold test.** Three graded residual candidates now win the
    pooled mean MAE, Brier and interval score at every horizon and fail
    on the whole-seat median fold test: cal_B, resid_hybrid and H1. H1
    also fails the D-21 coverage test, by .006. Whether the fold test
    should bind a change of the uncertainty layer is an owner decision.
    s.60.4 raised it.
  - **The 2026 stake.** If H1 shipped:
    - P(NB >= 61) would go from .108 to .061;
    - deadlock from .837 to .900;
    - Ra'am's pass probability from .80 to .87, Otzma's from .82 to
      .85, RZP-Zehut's from .58 to .62;
    - central seats unchanged.
  - **The site** can state that a full hierarchical model of the error
    record puts the correlated bloc error at about 2 seats (sd). It can
    also say that the shipped swing (4.3 seats with the t tail) is the
    conservative choice on these eight outcomes.

### 61.5 Not established

- **A within-bloc (gevalt) factor in the error model.** The record's
  NB-side errors are negatively correlated between Likud and its
  satellites, which the model treats as independent residuals. The
  projection's GEVALT_SD coupling still runs on top under H1, so part of
  Likud's variance may be counted twice. A bloc-internal zero-sum factor
  is the natural next term.
- **The Arab family is not predicted by the model.** A regime covariate
  (unified vs split) on phi^a would let the hierarchical model own it.
  The record has two split cycles.
- **nu is prior-dominated** (posterior 90% about 4-40). The t-vs-normal
  choice is a small effect on the record.
- **The first-cycle rule uses four hand-entered lineage facts.** The
  first-cycle term is neutral on the record.
- **The vote record's actual side for winners is seat-implied**
  (d'Hondt rounding). Using CEC vote shares for every list that ran is
  not done.
- **Not run:** D-56; the registration mixture, official forecast and
  formation chain for 2026.
- **The production-only layers** have no harness analogue and were not
  graded: the event walk, the certainty churn and the kalpi caps.
- **The nested width (H2)** was chosen on the harness's interval score
  with each held-out cycle's own LOO fit, as s.48 did. Re-fitting the
  error model inside the nested loop (fully nested LOO) was not done.

## 63. Model explorer, and the trailing-Likud layer re-checked (18 Oct, D-9)

The site's "Choose a model" panel (src/model_variants.py,
src/build_variants.py) shows the official forecast beside the graded
alternatives (hierarchical s.61, stacked s.62, vote residual s.57, hybrid
s.60, t-scale narrow s.48, the pre-fix residual, no trailing-Likud layer,
the simple average), each through the same chain on the same posterior
and seeds, with its backtest row on the official row's basis (s.50 LOO
caches, shipped mask, offsets 0/100/200). The official variant reproduces
the published headline exactly (the builder exits 1 otherwise); formation
groups use 50 of production's 200 parameter vectors and are shown as the
published figure plus the paired difference.

**no_trail on the current configuration** (the s.57.1 runner with the
trailing-Likud layer off; its shipped rows reproduce the seat_fix rows
exactly). Median / mean / coverage / threshold Brier / interval score:

| horizon | shipped (seat_fix) | no_trail |
|---|---|---|
| eve | 1.4858 / 1.6253 / .972 / .0447 / 9.011 | 1.5657 / 1.6688 / .960 / .0505 / 9.414 |
| D-7 | see s.62.2 | 1.6205 / 1.7240 / .949 / .0509 / 9.589 |
| D-21 | see s.62.2 | 1.7345 / 1.8456 / .968 / .0514 / 9.542 |

The layer still earns its place on the current harness: switching it off
worsens median and mean MAE and Brier at every horizon. In 2026 it is the
whole difference between the official central seats (Likud 26, Otzma 6,
RZP-Zehut 4) and the poll-level view (Likud 23, Otzma 8, RZP-Zehut 5)
that prediction markets lean towards (EVT-F25).

## 64. Where Blue and White's withdrawn vote goes (20 Oct, D-7)

Blue and White withdrew on 19 Oct (Gantz: no endorsement; a closing
message against "only not Bibi" and for a unity government;
registration_scenarios RESOLVED blue_white_folds True). Its withdrawn vote
(about 1-1.4% in the last polls) is routed by FOLD_TRANSFER["blue_white"].

**Search for measured data (20 Oct).** None exists yet: Hebrew and English
press, the verified research desks, and every CEC filing's crosstabs (the
only Blue and White breakdown, Channel 13 filing 4193 of 5 Oct, n = 7,
asks vote certainty, not second choice). Israel Hayom (19 Oct) says the
destinations are "estimates only, not a trend proven in polling data".
Commentary, none with numbers: JDN's Barometer - mostly the opposition,
mainly Eisenkot, a small share to Hendel; Filber (Channel 14's pollster) -
unpublished internal polls show Gantz's remaining supporters prefer
Netanyahu as PM; Ynet, Srugim, Israel Hayom - Hendel-Zelekha as the
natural home of a unity message.

**Decision: owner ruling, 20 Oct ("Gantz voters lean unity").** The
official vector changes from the measured 2022 absorbed-list pattern
(Yashar .60 / Together .25 / abstain .15; Kolot Nodedim 2021->2022) to
Yashar .35 / Together .10 / Reservists-Economic .25 / Likud .15 / abstain
.15. This is an editorial judgment on qualitative evidence, outside the
backtest (a 2026 registration event has no harness analogue). The 2022
vector stays in the code (BW_TRANSFER_2022) and on the site as the model
explorer's "Blue and White voters: 2022 pattern" variant. Replace both with
a measured flow as soon as a pollster publishes one. Note: the
Reservists-Economic list polls at 2.1-2.8%, so its share of this vote moves
its threshold odds, and with Likud and Yashar a seat apart the vector also
touches the trailing-Likud gate (registration_scenarios comment of 8 Oct).

## 65. Channel 14's weighting, and the SMS pair out of the centre (20 Oct, D-7)

### 65.1 The critique, and what the model already does

A chart circulated on 20 Oct alongside Michael Gilead's post on the
petition over Channel 14's polls. It says Data Next (Next Data, Shlomo
Filber; Channel 14) weights 2022 voters 54% coalition / 46% opposition
against an actual 50.3 / 49.7, and that re-weighting its 19 polls of 29 Jul
- 18 Oct gives a Netanyahu bloc of 59.0 seats on average, not 62.8 (Likud
29.8, not 30.9). The baseline checks against the official 2022 result: the
coalition lists plus Jewish Home took 49.57% of valid votes, the opposition
lists 48.92%, micro-lists 1.51%, so 50.3 / 49.7 without micro-lists. The
filings we hold (4212 of 14 Oct, 4228 of 18 Oct) do not state the 54 / 46
figure. In 4212 the total column is not a mix of the two 2022 groups alone
(it includes 2022 non-voters); the rows with a large gap between the
groups imply a coalition weight of 0.50-0.56.

The fit does not take Data Next at face value. Each firm has a house effect
on each list, centred on the unweighted mean over the window's firms (s.53).
On the 19 Oct posterior, at the window's end, Filber's effect on the
Netanyahu-bloc lists is +10.8 seats (90% +9.6 to +12.0; Likud +8.1) and
Direct Polls' +8.0 (Likud +5.1). The model already subtracts about three
times the chart's 3.8-seat correction. What remains is the centring: Filber
is one of the eight national firms in the centre, Direct Polls a second.

### 65.2 Pre-registration (written before any harness run of this arm)

**Arm `house_drop_sms`.** The SMS operation (pollster_meta correlation_group
sms_likud: Filber, Direct Polls) weighs 0 in the house-effect centre and
every other firm 1, as an exact re-parameterisation of the fitted posterior
at projection (bayes_model.drop_operation_weights; HOUSE_CENTRE "drop_sms").
In the eight past cycles it drops Direct Polls in 2019a, 2019s, 2020, 2021
and 2022 (4-26 polls each) and is the shipped arm in 2013 and 2015.

**2026 effect (computed before the harness, not a grading input).** Through
the full chain on the 19 Oct posterior: P(NB >= 61) 9.3 -> 5.4, change
6.8 -> 13.3, change + Ra'am 28.4 -> 40.3, NB mean 52.4 -> 50.5, Likud 26 ->
23. With Filber alone out: 7.5 / 10.0 / 34.5, NB mean 51.5, Likud 24.

**Grading.** The standing rule (s.53/s.55): eve on seed offsets 0/100/200
pooled, D-7 and D-21 on offset 0; ships if it wins or ties (|d| < 0.1
seat) median MAE in every leave-one-cycle-out fold, with mean MAE,
threshold Brier and interval score not worse beyond .010 / .0010 / .05 and
coverage not further from .90, D-7 and D-21 not contradicting. Otherwise
not shipped, and the site says so beside the critique.

## 66. The Reservists-Economic pledge restated by both co-leaders (20 Oct, D-7)

Since 10 Oct the formation tree counts the Reservists-Economic list's seats
only in coalitions with no haredi and no Arab partner (ZIONIST_ONLY, from
Hendel's statement of 23 Aug, JPost 906335), and res_right is the
probability that the list breaks that pledge to close Netanyahu + Shas +
UTJ (every feasible right-side close). On 20 Oct, at a joint event, both
co-leaders restated it: Zelekha - "we will not complete a government for
Netanyahu"; the haredim "are our brothers, but parties that lead a line of
separatism and draft evasion are not Zionist, and we will not sit with
them"; Hendel - a draft for everyone as the condition for forming a
government (INN 708908, 12:44; HM News 663174, 13:52). The Srugim report of
the same week (101013605) adds that they will not be the 61st seat of an
Eisenkot government resting on the Arab parties, which ZIONIST_ONLY
already encodes.

**Decision (fact update, not a method change).** res_right 0.12 -> 0.08,
NEFF 12 kept. 0.12 was set on 10 Oct to the generic pledge-break gate of
the day; s.59 recalibrated that gate to 0.08 on the formation record (17
Oct) and res_right was not moved with it. The restatement by the second
co-leader is the occasion, not a reason to go below the record's rate:
Israeli pledges of this kind have broken (Gantz 2020, Bennett 2021), and a
joint list of two parties can split after the vote. A 2026 list's
parameter has no analogue in the formation harness, so the record-graded
rate is the anchor. The effect, on the 19 Oct posterior through the full
chain: government led by Netanyahu 26.6 -> 26.6, change 29.8 -> 30.1,
Netanyahu + unaligned / Amcha 0.4% -> 0.3%; inside the simulation error,
because the list passes in about a quarter of the draws and is rarely the
closing seats. Sensitivity rows at 0.12 / 0.20 / 0.30 stay in the annex.

### 65.3 Result: does not pass

Eve, offsets 0/100/200 pooled, against the shipped arm on the same seeds:
median MAE 1.5235 vs 1.4858 (+.038); per fold 2009 +.091, 2013 0, 2015
+.121 (a loss), 2019a -.048, 2019s -.033, 2020 +.074, 2021 +.071, 2022
+.026; mean MAE 1.6352 vs 1.6253 (+.010, at the floor, worse in every
seed); coverage .972 both; threshold Brier .0450 vs .0447; interval score
9.043 vs 9.011 (+.032). The cycle with the most Direct Polls polls, 2022
(26), is worse in all three seeds (mean MAE +.040): its lean was to the
right and the result was further right than the field (eve P(NB >= 61)
.705 shipped, .685 without the pair; the bloc won 64). D-7: mean MAE
+.0025, interval score 9.480 vs 9.397 (+.083, beyond the .05 floor).
D-21: mean MAE +.005, interval +.030, threshold Brier -.0005. Fails on the
2015 fold, on mean MAE at the floor, and on the D-7 interval score. (In
2009, 2013 and 2015, with no SMS firm, the arm still differs slightly from
the shipped one: like s.53 it centres each list on the firms that poll it.)

**Not shipped**; HOUSE_CENTRE stays "firm". What the record says: in the
five cycles where the SMS operation polled, taking it out of the centre
made the eve forecast slightly worse, not better. The house effect already
removes Channel 14's lean relative to the field (+10.8 seats on the
Netanyahu bloc in 2026, three times the chart's re-weighting); whether the
field's centre is itself too far right or left is what the bloc-error
layer, calibrated on eight cycles, prices. The site states the critique,
the house effect, and this result (EN/HE), and the explorer does not get a
variant: an arm that fails on the record is not offered as an alternative
model.

## 67. What the filings say beyond seats (22 Oct, D-5)

Every CEC filing fielded since 1 Oct (37, refs 4175-4241) was read for its
non-seat questions; the numbers used below were checked against the PDF
text. Two inputs change; the rest is recorded and not used.

**Used 1: the undecided lean (data/undecided_leans.csv).** Channel 13's
HaMidgam filings ask undecided respondents which list they lean to now
(raw, unweighted, Jewish adults; 4182 29-30 Sep n=67, 4193 6-7 Oct n=68,
4210 13 Oct n=70, 4235 18 Oct n=60). Mapped to blocs (Amcha with the
Netanyahu bloc, as in the bloc totals; the Reservists-Economic list and
Blue and White unaligned, so "none"): change bloc .284 / .339 / .300 /
.350, Netanyahu bloc .254 / .249 / .188 / .233, the rest still undecided.
The estimator was built to pool each new wave by its leaned n (s.41); the
four waves (about 146 leaned respondents) join Channel 12's 30 July
measurement (about 43). The posterior mean of the change-bloc share of the
leaned pool moves .647 -> .604 against the proportional .52, so the
expected break of the undecided toward the change bloc shrinks by about a
third. Caveat: Arab respondents are not in these tables; the comparison
base .52 is the decided Jewish-list electorate's change share, so the
like-for-like holds.

**Used 2: certainty of the two lists with no record (CERTAINTY).** 4193
also tabulates "how sure are you that you will vote for the list you
named" by list (pooled samples, unweighted). The M entries of the layer
use a "locked" scale; mapping very sure + w x fairly sure onto it with
the two lists measured on both scales gives w = .28 (Together: .47 = 31.0
+ w 57.7) and .34 (Amcha: .38 = 20.5 + w 52.2), mean .31. Applied only
where the layer had a declared placeholder and no record: Yashar .65 ->
.56 (39.3 / 52.1, n=117), Reservists-Economic .40 -> .26 (8.7 / 56.5,
n=23). Lists with an election record keep their tiers: Shas reads 61.7%
very sure but has never missed downward by more than half a seat, and the
tiers were set on that record (LOYAL_SD), which is what election-day
movement follows. Walla/Lazar 4207 (12 Oct) asks the same by list but its
small-list cells disagree with 4193 by up to 40 points (UTJ, Ra'am, RZP),
so it is not used.

**Effect** (21 Oct posterior, full chain, 200 formation vectors): refit
alone P(NB >= 61) 8.1, change 6.0, + Ra'am 28.8; with the lean 8.5 / 5.7 /
27.2; with both 8.9 / 5.5 / 26.7; government led by Netanyahu 26.3 ->
27.4, change 29.5 -> 27.8; central seats unchanged; Reservists-Economic
passes .238 -> .225. Neither input has a harness analogue (2026
measurements, like s.64 and s.66); both enter mechanisms built to take
them.

**Recorded, not used.**
- Where Gantz's voters go: Next Data 4238 (20 Oct, n=2,116) asked everyone
  to guess ("where do you think Gantz's voters will go"): Yashar 38, Likud
  12, Together 11, Reservists 8, Amcha 5, Democrats 3, other / don't know
  23. A perception question, not a measured flow; the s.64 ruling stands.
  (The press reported it as "Yashar absorbs 38% of his voters".)
- Second choice (4235, all respondents, not by first choice) and Accord's
  pairings of undecided young voters (4183, 22-34): no flow table by
  first choice exists for Amcha or the Reservists.
- Turnout intention: Rosner's "certain to vote" (Jewish 73-75, Haredi
  66-71, Arab 73-81) and Next Data's 96% are not calibrated to turnout
  (Arab turnout was about 53% in 2022). Channel 12 (21 Oct) has 76% of
  Netanyahu-bloc and 82% of change-bloc respondents intending to vote;
  the seat estimates are already among intending voters.
- Certainty by bloc (Lazar: totally sure, coalition 54 / opposition 35 on
  12 Oct; Kantar: decided 86 / 74 on 18 Oct): the asymmetry is already in
  the layer through the record-based tiers and CHURN_SPLIT.
- Coalition acceptability (Kantar 4217: 30-35% of Together and Yashar
  voters reject every role for an Arab party; Lazar 4197) and
  withdrawal opinion (47-58% want Winter to withdraw): voter opinion, not
  party behaviour; the formation tree's gates are set on party records.
- The IDI Israeli Voice Index (early Oct, reported by Calcalist 20-21
  Oct): traditional-religious voters 46% Netanyahu bloc now against 76% in
  2022, 17% undecided; traditional non-religious 39% against 60%. A pool of
  2022 Netanyahu-bloc voters among the undecided is the mechanism behind
  the trailing-Likud layer (s.63), which is measured on the record and
  stays as it is.

## 68. Final-week momentum, tested on the record (22 Oct, D-5)

**Question.** Does movement in the polls over the final week (or three
weeks) carry on past the last polls, so the eve forecast should
extrapolate it?

**Design.** The eight harness cycles (2009-2022), 94 list-cycles. Momentum
per list = the model's own latent share (house effects removed) at the eve
fit minus the same at the D-7 fit (m7) or the D-21 fit (m21), from the
harness posterior caches, in seats. Error = the result minus the shipped
eve forecast (mean seats, model_validation_bayes_lists, offset 0). Slope
of error on momentum within cycle; permutation within cycle (5,000);
leave-one-cycle-out: the slope from seven cycles applied to the eighth
(pred + b x momentum). A positive slope = momentum continues; negative =
reversal. Robustness: raw within-firm momentum (each firm's final-7-day
mean minus its days 8-21 mean, averaged over firms) against the raw
final-week average and against the model; and the Netanyahu bloc total.

**Results.**
- Lists, m7: slope -0.10 (r -.02, permutation p .83); per cycle +2.9
  (2013) to -3.0 (2015), no stable sign. LOO: mean MAE 1.621 -> 1.668;
  better in no fold, worse in two (2013 +.28, 2019a +.05). Lists of 4+
  seats: the same (-0.10, p .85; MAE 1.710 -> 1.770).
- Lists, m21: slope -0.13 (p .56); LOO 1.621 -> 1.662, better in none.
- Raw polls, within-firm: slope -0.22 against the raw final-week average
  (r -.08), -0.10 against the model; per-cycle signs flip.
- Netanyahu bloc, m7: r -.09 with the bloc's eve error.
- Netanyahu bloc, m21: r -.51, opposite signs in 7 of 8 (the bloc gained
  over the final three weeks in 2019s and 2021 and fell short, slid in
  2015 and 2019a and beat the forecast); exact permutation p .20; LOO bloc
  MAE 2.00 -> 1.57, better in 5, worse in 3 (2013, 2020, 2021).

**Reading.** No momentum: at the list level, final-week movement does not
continue past the polls, and adding it makes the out-of-sample forecast
worse. The one pattern is a weak three-week reversal of the bloc total, the
"coming home" mechanism the trailing-Likud and gevalt layers already carry;
it is one of five tests run, on eight points, at p .20, so it does not meet
the bar and is not applied. For 2026 it would barely matter: on the 21 Oct
posterior the Netanyahu bloc's latent total moved -0.41 seats over three
weeks (90% -1.18 to +0.37) and -0.08 over the last week, so the full-sample
reversal slope (-0.62) would add about +0.25 seat. The fall in P(NB >= 61)
since mid-October came from model changes and Blue and White's withdrawal,
not from the polls.

**Decision.** No change; the model's random walk (no drift) stands. Site:
one sentence in the limitations (EN/HE).
