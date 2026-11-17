# Review brief: Change Bloc Field Atlas (Israel 2026 election targeting site)

Repo: /Users/idoherling/Polling:Consulting Firm/2026_Election_Model  (Python venv: .venv/bin/python; run scripts from src/)
Today is 2026-10-11; election 27 Oct 2026.

Pipeline (all new, written today):
- src/targeting_data.py      harmonised CEC locality results 2013-2022 (7 elections), CBS/census metadata -> data/processed/targeting/{panel.parquet, locality_cycle.parquet, locality_meta.csv, national.csv}
- src/targeting_marginal.py  marginal value of a vote per list via perturbing the forecast's 8,000 share draws through seat law + formation model -> marginal_values.csv
- src/targeting_model.py     segments, 2026 projection (lineage transfers + IPF), openness index (out-of-sample spec choice), marginal-voter composition test, kalpi-level per-contact values for GOTV/persuasion/rescue, potentials, tiers, validation -> localities.csv, kalpi_all.parquet, segments.csv, validation.json
- src/targeting_sensitivity.py  rank robustness over 11 parameter scenarios
- src/build_targeting_site.py  payload JSON + single HTML page
- site/targeting_template.html (CSS + HTML skeleton), site/targeting_app.js (all front-end JS: summary, map, rankings, profile, segments, playbook, planner, methodology, sources), site/targeting_content.json (segment playbooks, playbook page, sources)
- Built site: output/targeting/index.html (artifact version) and output/targeting/preview.html (local); payload output/targeting/site_data.json
- Local server: http://localhost:8614/preview.html (routes: #summary #map #rankings #segments #playbook #planner #method #sources #loc-<CBS code>)
- Existing forecast model (context, not under review): src/bayes_model.py, src/government_formation.py, docs/priors_dossier.md
- Research files with verified literature findings: /private/tmp/claude-501/-Users-idoherling-Polling-Consulting-Firm-2026-Election-Model/ad628d13-0e78-4650-8e77-28f2e2f4dba8/scratchpad/research/*.json (desks + verify_*.json) and MODEL_BRIEF.md
