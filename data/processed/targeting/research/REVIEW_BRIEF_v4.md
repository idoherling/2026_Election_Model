# Review brief v4: Change Bloc Victory Guide (Israel 2026 strategy site)

Repo: /Users/idoherling/Polling:Consulting Firm/2026_Election_Model  (Python: .venv/bin/python; run scripts from src/)
Today is Thu 15 Oct 2026 (D-12); election Tue 27 Oct 2026. Audience: change-bloc leadership, strategists, message and
field directors (Yashar/Eisenkot, Together = Bennett 2026 + Yesh Atid, The Democrats/Golan, Yisrael Beytenu/Liberman).

The site was a field atlas. It is now a holistic, evidence-based guide to winning: what moves the result (strategic levers
sized by the forecast's own simulations), what to say to whom and through which media, coalition signals and government
formation, and the field programme (map, rankings, segments, playbook, planner). Same standard throughout: every empirical
claim carries a cite to a verified research finding; model numbers come from the brief and levers.json; evidence is kept
separate from judgement; foreign evidence is labelled.

Pipeline:
- src/targeting_marginal.py    marginal value of a vote per list (8,000 forecast draws through seat law + formation model)
- src/targeting_model.py       segments, 2026 projection, station door values, list programmes, tiers, validation
- src/targeting_sensitivity.py 18 scenarios (ranges for budgets and rank stability)
- src/targeting_planner.py     tranche allocation (JS twin allocate() in site/targeting_app.js)
- src/targeting_levers.py      strategic-lever scenarios (exact, non-linear) -> data/processed/targeting/levers.json
- src/targeting_facts.py       live model numbers for the prose (+ src/targeting_facts_extra/<page>.py)
- src/build_targeting_site.py  payload + site/targeting_template.html + site/targeting_app.js + site/targeting_content.json
                               (--assemble-content pulls research/content_final_*.json, else content_v4_*)
- Outputs: output/targeting/index.html (artifact version), output/targeting/preview.html (local), localities.csv, kalpi_targets.csv
- Local server: http://localhost:8614/preview.html (append ?v=<random> to bust cache).
  Routes: #summary #strategy #messaging #coalition #playbook #map #rankings #segments #planner #method #sources
  #loc-<CBS code> #seg-<segment> #src-<n>. Objective selector: change_govt (default), block_nb, change_seats.

Numbers: the site runs on the forecast committed at a5bf54e (polls to 14 Oct; refitted 15 Oct). Model numbers in the
prose are live tokens ({{key|ops}}) filled at build time by src/targeting_facts.py from the pipeline outputs; value-
dependent wording is guarded by research/content_watch_*.json conditions (spec: research/TOKENS_SPEC.md). To check any
number: cd src && ../.venv/bin/python targeting_facts.py get <key> (or find <text>); the brief MODEL_BRIEF_v2.md is
regenerated for 15 Oct; levers.json has the lever effects. Archived earlier states: data/processed/targeting/archive_*/.

Research: data/processed/targeting/research/ - MODEL_BRIEF_v2.md (v4), CONTENT_SPEC_v4.md, desk JSONs (gotv, persuasion,
israeli-behaviour, israeli-turnout, israel-geography, context-2026, coordination, messaging, media, coalition,
turnout_scale, operations) with verify_*.json, content_final_*.json (content now on the site).

Mandatory content rules: never depress anyone's turnout; no deceptive or covert tactics; never call Arab/Druze towns
change-majority; no change-bloc-run/branded GOTV among Arab voters (Arab towns and Arab-led stations); Arab-sector turnout is a
leadership decision, any support independent, transparent, cleared by election counsel, no town-level Arab targeting values;
rescue = media/digital/insurance messaging around the final published polls (Fri 23 Oct) + list calls, not door-knocking;
no poll figures from Sat 24 Oct, and Friday poll creative carries the legally required survey details and ends before the
ban; reservists and soldiers reached as civilians only, never through IDF units, bases or employers; no organised rides or
gifts; no voter-level data sharing between lists without written counsel clearance; cross-list spending needs both lists'
counsel and treasurers; Reservists-Economic voters and every community described respectfully; "Netanyahu-bloc stronghold",
never "opposition stronghold"; Druze projections flagged low confidence and not headlined.
