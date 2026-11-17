# Review brief v2: Change Bloc Field Atlas (Israel 2026 targeting site)

Repo: /Users/idoherling/Polling:Consulting Firm/2026_Election_Model  (Python: .venv/bin/python; run scripts from src/)
Today is Sun 11 Oct 2026 (D-16); election Tue 27 Oct 2026. Audience: change-bloc leadership and field directors
(Yashar, Together = Bennett 2026 + Yesh Atid, The Democrats, Yisrael Beytenu).

Pipeline (v2, rebuilt today after a first review round):
- src/targeting_data.py       harmonised CEC results 2013-2022 + CBS metadata -> data/processed/targeting/{panel,locality_cycle}.parquet, locality_meta.csv
- src/targeting_marginal.py   marginal value of a vote per list (forecast's 8,000 draws through seat law + formation model) -> marginal_values.csv
- src/targeting_model.py      segments; 2026 projection (coherent flow matrix + 50/50 uniform camp-swing blend + Druze non-Arab pooling + IPF);
                              per-station door value (turnout x hump + persuasion + rescue); list programmes in negative stations; flags; tiers;
                              validation -> localities.csv, kalpi_all.parquet, kalpi.csv, segments.csv, validation.json, planner_units.pkl
- src/targeting_sensitivity.py 16 scenarios -> sensitivity_ranks.csv, sensitivity_summary.json
- src/targeting_planner.py    capacity tranches + greedy allocation (reference implementation; JS twin allocate() in site/targeting_app.js)
- src/build_targeting_site.py  payload + site/targeting_template.html + site/targeting_app.js + site/targeting_content.json
                              (python build_targeting_site.py --assemble-content pulls research/content_final_*.json)
- Outputs: output/targeting/index.html (artifact version, no doctype), output/targeting/preview.html (local, with skeleton),
  site_data.json, localities.csv, kalpi_targets.csv
- Local server already running: http://localhost:8614/preview.html (append ?v=<random> to bust cache).
  Routes: #summary #map #rankings #segments #playbook #planner #method #sources #loc-<CBS code> #seg-<segment> #src-<n>
- Objective selector (top bar): change_govt (default), block_nb, change_seats; stored in localStorage key atlas.obj.

Research: data/processed/targeting/research/ - MODEL_BRIEF_v2.md (numbers + content rules), desk JSONs (gotv, persuasion,
israeli-behaviour, israeli-turnout, israel-geography, context-2026) with verify_*.json, reviews.json (first-round reviews),
content_final_{segments,playbook,sources}.json (checked content now on the site).

Mandatory content rules: never call Arab/Druze towns change-majority; no change-bloc-run/branded GOTV in Arab localities - Arab-sector
turnout is a leadership decision, any support independent, transparent, cleared by election counsel; no covert-sounding language;
rescue = media/digital/insurance messaging around the final published polls (Fri 23 Oct) + list calls, not door-knocking; blackout from
Sat 24 Oct; Reservists voters described respectfully; no organised rides; "Netanyahu-bloc stronghold" not "opposition stronghold";
Druze projections flagged low confidence and not headlined.
