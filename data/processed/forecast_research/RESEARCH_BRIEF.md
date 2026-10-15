# Forecast research desks - brief (15 Oct 2026, D-12)

Goal: hold the Knesset forecast (site: claude.ai/artifact/Vzs8UP91RRkVnELspHmzUM; template
site/template.html; decision log docs/priors_dossier.md) to the same evidence standard as the
field atlas (data/processed/targeting/research/: 12 desks, 345 sources, every finding verified).
Every methodological choice and every empirical claim on the forecast site must rest on (a) a
peer-reviewed or standard methodological source, (b) official data, or (c) the model's own
documented measurement (dossier section + harness numbers). Each desk also says where the
literature CHALLENGES a current model choice - those become model-improvement candidates.

## The model in one page (read docs/priors_dossier.md s.36-45 and src/bayes_model.py for detail)
- Data: Wikipedia poll archive 2009-2026 (1,919 polls), CEC legal poll filings 2026 (raw shares,
  103 parsed), manual press entries, Afkar Arab-sector poll; official CEC results 2009-2022;
  kalpi (polling-station) panel 2019-2022; party registry of lineages.
- Poll model: PyMC state-space. Weekly random-walk latent on additive-log-ratio scale (round
  three proposes centred-log-ratio, CLR), softmax to shares; pollster house effects with a
  linear drift; precision lam per firm with a prior from an 8-cycle accuracy scorecard; Student-t
  likelihood; sampling noise from n with design effects; undecided-share noise term; structural
  breaks for list mergers; CEC raw-share filings displace seat-derived table numbers.
- Projection to election day: calendar-scaled forward random walk; correlated bloc swing
  (t, df 5) x event-risk 1.2; family shocks (haredi additive; Arab lists via a graded turnout
  term: T~0.58, pass-through 0.247, intercept -0.634 seats); per-list residual shock
  (1.83+0.044 x seats) x 0.9, x1.35 for first-cycle lists; gevalt coupling (Likud <-> satellite
  zero-sum); trailing-Likud conditional (Likud's beat when it trails the largest non-bloc list,
  sourced from satellites); new-straddler desertion (-1.6 pp for first-cycle lists near the
  threshold); withdrawn-list rule; certainty layer (soft support churn, undecided lean); kalpi
  capacity bounds (sector arithmetic).
- Registration mixture (open events: Blue and White withdrawal 25%), 3.25% threshold, surplus
  agreements, Bader-Ofer (D'Hondt) seat allocation -> 8,000 simulated Knessets.
- Formation tree: explicit coalition gates with Beta/Dirichlet behavioural priors (haredi
  defection, Ra'am participation, unaligned lists, Amcha conditional), configuration-conditional
  logistic adjustments; PM allocation with rotation.
- Validation: eight-cycle leave-one-cycle-out harness (2009-2022) at eve, D-7, D-21, D-56;
  metrics: median/mean seat MAE, 90% coverage, threshold Brier, interval score; shipping rule.

## Output format (one JSON file per desk: data/processed/forecast_research/<desk>.json)
{
 "desk": "<id>", "summary": "<plain-language synthesis, 300-600 words>",
 "findings": [
   {"id": "<DESK-CODE>-F01", "claim": "<one empirical or methodological finding, specific>",
    "quant": "<the numbers, with units and population/period>",
    "source": {"authors": "...", "year": 0, "title": "...", "venue": "...", "doi_or_url": "...",
               "type": "peer-reviewed|book|book chapter|working paper|official data|report|reference work"},
    "model_link": "<which layer/parameter of the forecast this backs or challenges>",
    "stance": "supports|challenges|informs",
    "site_use": "<the sentence on the site it should back, or 'new claim'>"}
 ],
 "challenges": [ {"title": "...", "what_literature_says": "...", "current_model": "...",
                  "proposed_change": "...", "how_to_test": "harness / evidence class", "finding_ids": []} ],
 "parameters": [ {"name": "...", "current": "...", "literature_range": "...", "finding_ids": []} ],
 "open_questions": ["..."]
}
Rules: cite only sources you have actually located (search the web; prefer DOI links and
publisher pages; give the exact page/table when quoting numbers). Never invent a citation. Mark
anything you could not open as "unverified". 10-25 findings per desk. Prefer peer-reviewed work;
Israeli-specific evidence wherever it exists (Israel Democracy Institute, Israel National
Election Studies (INES), CEC, CBS, Dayan Center/KAP, academic work on Israeli elections).
Do not edit any repository file other than your own desk JSON.
