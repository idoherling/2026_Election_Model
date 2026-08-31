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
