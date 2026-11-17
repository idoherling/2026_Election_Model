# Content spec v4: Change Bloc Victory Guide

The site is now a holistic guide to winning the 27 Oct 2026 election, not only a field atlas. Pages:
Summary · Strategy (levers of victory) · Messaging (messages, audiences, media) · Coalition (signals and formation) ·
Field (playbook, map, rankings, segments, planner) · Methodology · Sources.

## Standard (applies to every sentence)
- Every empirical claim rests on a cited finding id from a research desk file (gotv, persuasion, israeli-behaviour,
  israeli-turnout, israel-geography, context-2026, coordination, messaging, media, coalition, turnout_scale, operations)
  that is verified or corrected in its verify_*.json (apply corrections; never cite rejected or unverifiable findings
  unless the text says the claim is unverified). Model numbers come only from MODEL_BRIEF_v2.md (now v4) and levers.json.
- Separate evidence from judgement: say what the research shows (with effect sizes) and then what it implies.
  Where evidence comes from other countries, say so. Where there is no evidence, say so.
- Never recommend depressing anyone's turnout, deceptive or covert tactics, change-bloc-run or branded GOTV among
  Arab voters, organised rides, gifts, or quoting polls during the ban (Sat 24 Oct onward). Arab-sector turnout is
  a leadership decision; any support is independent, transparent and cleared by election counsel. Reservists and
  soldiers are reached as civilians only. Describe Reservists-Economic voters and every community respectfully.
- House style: plain direct English, short sentences, no em-dash chains, no semicolon chains, no hype. Round
  model totals to two significant figures in prose.

## Files and schemas (write to data/processed/targeting/research/)

### content_v4_strategy.json
{"intro": "<3-4 sentences>",
 "principles": [{"title", "text", "cites": []}],            // 4-6: what wins a PR election with a 3.25% threshold
 "levers": [{"key": "<slug>", "group": "agreements|persuasion|turnout|allies|coalition|field|arab|risks",
             "title", "scenarios": ["<keys from levers.json, or 'field'>"],
             "summary": "<what it is and what the model says it is worth, 2-3 sentences>",
             "evidence": "<what the research shows, with effect sizes>", "cites": [],
             "feasibility": "high|medium|low", "feasibility_note": "<can it be done in 14 days, by whom, why>",
             "timing": "<dates>", "owner": "<who decides/executes>",
             "actions": ["..."], "risks": ["..."]}]}
levers.json keys: bw_withdraws, res_withdraws, res_withdraws_right, amcha_withdraws, pers_likud_0.5, pers_likud_1.0,
pers_likud_2.0, pers_haredi_0.5, ch_turnout_25000, ch_turnout_50000, haredi_turnout_-10 (context only: NEVER a
lever to pursue), nb_turnout_25000 (counter-mobilisation cost), arab_turnout_+5, arab_turnout_-5 (context only),
yashar_to_dem_0.5 (within-bloc moves are worth ~0), jl_to_raam_0.5 (Arab lists' own matter), bw_plus_pers_0.5, and "field".
Cover at least: Blue and White withdrawal/endorsement; Reservists-Economic; protecting allies and Ra'am above the
threshold (insurance) and why intra-bloc competition is worth ~0; national persuasion and issue salience;
national turnout beyond the field; avoiding counter-mobilisation; coalition clarity (link to Coalition page);
the field programme (link to Field); Arab-sector turnout as a leadership decision; vote protection and the count.

### content_v4_messaging.json
{"intro", "principles": [{"title","text","cites"}],
 "issues": [{"issue","who_it_moves","frame","owner","risk","cites"}],
 "audiences": [{"audience","size_note","what_moves","message","messenger","channel","avoid","cites"}],
 "media": [{"channel","role","evidence","rules","verdict":"core|use selectively|low value|avoid","cites"}],
 "rapid_response": [{"title","text","cites"}],
 "calendar": [{"when","dates","what","cites"}]}

### content_v4_coalition.json
{"intro", "outcomes_note": "<how to read the forecast's government outcomes>",
 "paths": [{"path","outcome_key": "<exact outcome name from government_formation.csv>","partners","how","obstacles","cites"}],
 "signals": [{"title","text","risk","cites"}],
 "formation": [{"step","when","what","cites"}],
 "prepare": [{"title","text","cites"}],
 "repeat": {"title","text","cites"}}
outcome names: "Netanyahu rightist coalition", "Netanyahu + unaligned / defector coalition",
"Change coalition (without Ra'am)", "Change coalition with unaligned / Amcha", "Change coalition with a haredi party",
"Centre minority backed by the Joint List", "Unity government (Likud without Netanyahu)", "Repeat election",
"Change coalition with Ra'am".

### content_v4_victory.json (Summary page)
{"lede": "<2-3 sentences>",
 "theory": [{"title","text","cites","go": "#strategy|#messaging|#coalition|#playbook|#method"}],   // 5-7
 "decisions": [{"key": "<slug; use 'rescue' or 'reservists' or 'arab' only if you cover those>", "h","when","owner","p","cites"}], // 5-8 leadership calls this week, most valuable first
 "donts": [{"title","text","cites"}]}

### content_v4_playbook.json and content_v4_segments.json
The current content_final_playbook.json and content_final_segments.json, with every number brought up to the v4
brief (13 Oct forecast: seats, pass chances, baselines, exchange rates, realistic budgets and ranges, saturation
totals, Druze add-on, tier lists and counts) and cross-links to the new pages where useful. Keep schemas.

### content_v4_sources.json
content_final_sources.json plus an entry for every verified or corrected finding in the six new desks
(coordination D7, messaging D8, media D9, coalition D10, turnout_scale D11, operations D12), merged with aliases
where several findings share one publication. New groups allowed: "Coordination and coalitions",
"Messaging and media", "Campaign law and operations". Every id cited anywhere must resolve via id or aliases.
