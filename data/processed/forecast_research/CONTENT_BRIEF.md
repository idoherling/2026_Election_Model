# Forecast site: evidence rewrite brief (15 Oct 2026)

Goal: every method and empirical claim on the forecast site (site/template.html, EN inline text +
Hebrew HE_CH / HE_LEDE / HE_NOTES / HE_STATIC maps) is backed by a VERIFIED finding, the same
standard as the field atlas. Numbers that change with each build come from the data payload, never
hard-coded prose.

## Inputs
- data/forecast_sources.json - the registry (built by src/build_sources.py from the eight desks
  and their verify_*.json; only verified/corrected findings enter). Each source has `id` (its first
  finding id, e.g. EVAL-F01, or DL-43 for the decision log), `aliases` (its other finding ids),
  `short` (author-year label), `citation`, `url`, `note`.
- data/forecast_findings.json - finding id -> claim, quant (corrected numbers where the verifier
  corrected them), source id, model_link.
- data/processed/forecast_research/<desk>.json + verify_<desk>.json - the desks, their challenges
  and the verifiers' challenge_checks (use corrected_quant where given; never cite a finding whose
  verdict is rejected or unverifiable).
- docs/priors_dossier.md and the published decision log page (decision-log.html#sN) for the model's
  own measurements (cite them as DL-nn ids from data/processed/forecast_research/own_measurements.json).

## Citation mechanism
`<a class="cite" data-s="ID1,ID2"></a>` anywhere in EN or HE text renders as [Author Year; ...],
links to the Sources chapter entry and shows the full citation on hover. Use finding ids or source
ids (aliases resolve). Put citations at the end of the sentence they back. Same ids in EN and HE.

## Rules (owner rules are binding)
- Everything on the site hyperlinks to its source. Hebrew seats = מנדטים. Never "Others" - say
  "small parties". Builder presets: exactly three plus Clear. Blue and White and the
  Reservists-Economic list are UNALIGNED. Segalovitz's seat counts only with Ra'am. Never infer
  per-list numbers from bloc totals. Together's letters are רק.
- Do not overclaim: say what a source shows, at the strength it shows it (verifier notes flag
  overreach). Where the literature challenges a model choice that has NOT been changed, say so
  plainly in the limitations chapter rather than hiding it.
- Numbers that vary by build: use existing data-fit / data-count spans or add payload fields in
  src/build_site.py; no hard-coded live numbers.
- EN and HE must say the same thing; Hebrew natural, gershayim (ש״ס), numbers/ranges LTR-isolated.

## Required edits (from the desks' site_use fields, challenges and verifier notes)
1. Methodology chapters: add citations to every method claim (state-space aggregation, house
   effects, CLR latent, poll-error structure, Bader-Ofer law, surplus agreements, threshold,
   strategic desertion, sector turnout, formation theory, evaluation and computation).
2. Correct claims the desks/verifiers found wrong, e.g.: surplus-pair value (+0.4 seat per pair,
   not "+0.5 to +0.9"); double envelopes do not add "+0.5-1 seat to the right"; "the largest list
   supplied the PM in 7 of 10 governments" (not "largest-party logic is not Israeli logic"); Peres's
   Nov 1995 government started below 61; ideological-core lists "held their polling" is true for
   Arab/haredi lists, not right-flank lists in wasted-vote races; "0.9 wins every fold" and
   "conservative" interval wording (intervals over-cover); "using only the polls published before
   each date" needs the leave-one-cycle-out qualifier (later cycles inform some parameters); the
   formation harness log-score sentence ("-0.93 vs -0.92") is not a grade of the shipped tree;
   bulk-ESS / r-hat wording vs the actual refit gates; the 2% threshold era (2006-2013).
3. New chapter "The evidence behind each layer": a table, one row per model layer: what it does |
   evidence class (graded on the backtest / measured on the record / judgment with cited
   post-filing evidence) | citations | validation result (decision-log section) | open challenge.
4. New chapter "Limitations and open questions": the challenges the literature raises that the model
   has not adopted, the verifier caveats, the 8-cycle record's thinness, Monte Carlo precision of the
   headline (round probabilities), the Israeli-specific evidence gaps.
5. The Sources chapter is rendered from the registry; its intro states counts by status.
