# Live model numbers in the Victory Guide content

The forecast is refitted almost daily until 27 Oct. Every model number in the site's prose must
therefore be a token that the builder fills from the current pipeline outputs, so a forecast update
needs no rewrite. Engine: `src/targeting_facts.py` (read its docstring first: key families, ops,
formats, CLI). Run it from `src/` with the project interpreter: `../.venv/bin/python targeting_facts.py ...`.

## The reference state
Tokenise against the archived 13 Oct 19:46 state: always pass `--root archive_1013pm`
(data/processed/targeting/archive_1013pm, with its forecast CSVs in forecast/). The live directory
is about to be rebuilt on a newer forecast, so never validate against it. The content files were
written and checked against this archived state, so rendering the tokenised file with
`--root archive_1013pm` must reproduce the original text exactly.

## What to tokenise
Tokenise every number that is computed by the forecast or the atlas pipeline and would change if the
forecast changed:
- forecast seats, intervals, pass chances, largest-list chances; bloc probabilities (NB>=61, change
  alone, with Ra'am, neither); government outcomes and their sums; PM probabilities
- atlas baselines; lever effects and lever vote counts (levers.json); exchange rates per 10,000 votes;
  the net-vote conversions (points per 1,000 net votes, votes per expected seat)
- realistic plans (net votes, ranges, points, Druze add-on, localities, contacts by programme),
  saturation totals, tier counts, station counts
- segment and locality projections and potentials (2026 projected shares, lead lists' numbers,
  potentials, efficiencies, persuadable and rescue pools, ranks)
- numbers computed from the forecast's draws (conditional NB>=61 when a list passes or fails,
  expected change seats, wasted vote, surplus-pair effects)
- any number derived from the above (ratios, differences, "N times the field programme", vote
  equivalents, arithmetic on segment tables, planner results for one town)
Do NOT tokenise: research findings and their effect sizes, poll results quoted from the press,
official past results (2022 and earlier, including eligible voters and 2022 turnout), dates, legal
amounts, model constants that do not depend on the forecast (1.5-point lift, hump multipliers, 35%
cap, 30% identified, 0.3% switch rate, x1.3 household), counts of studies, page structure numbers.

## How
1. Find candidate keys: `../.venv/bin/python targeting_facts.py --root archive_1013pm find 3.05`
   lists keys whose value prints as the text under common formats. `get KEY` shows a value. The full
   static list is in data/processed/targeting/archive_1013pm/facts_static.json. CHECK THE MEANING:
   a value can match a wrong key by coincidence. The key must mean what the sentence says.
2. Choose ops so the rendered text equals the original exactly: e.g. `{{lev.pers_likud_0.5.govt|f:.1f}}`,
   `{{bud.govt.400k.30.ve|sig2|f:,.0f}}`, `{{fc.Raam.pass|x100|f:.0f}}%`, `{{fc.Raam.pass|nolead}}`,
   `{{lev.nb_turnout_25000.govt|abs|f:.1f}}` (when the sentence carries the sign in words).
   Keep units and signs in the surrounding text exactly as they were.
3. Derived numbers: write `src/targeting_facts_extra/<page>.py` with
   `def facts(ctx, get): return {"name": value, ...}` and use `{{x.<page>.name|...}}`. Compute from
   `get(...)` (any non-extra fact) and `ctx` (data frames: ctx.loc, ctx.seg, ctx.kal, ctx.mv, ctx.lev,
   ctx.fc, ctx.gov; ctx.plan(obj, budget, ident) for planner runs, which returns
   {"ve", "contacts", "localities", "alloc": {loc_index: {...}}} with loc_index into ctx.loc_sorted;
   ctx.draws, ctx.seats for the 8,000 draws). Never hard-code a model number in an extra. Name keys
   plainly. Each page owns only its own extras file.
4. Value-dependent wording: where a word or phrase is only true for some values ("nearly half",
   "about one in eight", "the largest single route", "more than twice", "ahead of", "tops the list",
   "below the threshold in most draws", a named top-N list of towns), add an entry to
   `data/processed/targeting/research/content_watch_<page>.json` (a JSON list):
   {"where": "<JSON path>", "phrase": "<the words>", "condition": "<Python expression over F('key')>"}
   e.g. {"where": "coalition.repeat.text", "phrase": "nearly half", "condition": "42 <= F('gov.repeat') < 50"}.
   Pick the honest range in which the wording stays true. Where wording would be fragile, prefer
   rewording only if the original meaning and the rendered numbers stay identical; otherwise watch it.
5. Validate: `../.venv/bin/python targeting_facts.py --root archive_1013pm validate <tokenised> <original>`
   must report 0 differing strings, except numbers that were WRONG for the 13 Oct state (stale or
   miscomputed): fix those with the token and list each one in your report with the old and new text.
   `watch <watchfile>` must report 0 false conditions.

## Output per page
- `data/processed/targeting/research/content_tok_<page>.json` (same schema as content_final_<page>.json)
- `src/targeting_facts_extra/<page>.py` if needed
- `data/processed/targeting/research/content_watch_<page>.json` (may be an empty list)
Never edit content_final_*.json, targeting_facts.py or another page's files.

## Updating after a forecast refit (and keeping the text true over time)
The content files content_final_<page>.json now hold the tokens. The live directory
(data/processed/targeting, no --root) holds the current forecast state; archive_1015 is a copy of it;
archive_1013pm is the earlier state. The guide is read and rebuilt every day from Thu 15 Oct to election
day, Tue 27 Oct 2026, so its prose must stay true when numbers move and when days pass.
1. A false watch condition means the rendered sentence may now be wrong. Rewrite the sentence so it is
   true under the live state AND robust to the next refit: prefer wording whose truth does not hinge on
   a knife-edge (e.g. "one of the largest routes" only if it stays true; otherwise state the comparison
   with both tokens). Update or replace the watch entry so it is true now and catches the next break.
2. Data-driven sets and orderings (tier members, top-N towns, lead lists by town, "only", counts of
   stations or towns) should be generated, not typed: add a string extra in your page's extras file
   that builds the list from the data (e.g. "Netanya, Be'er Sheva and Eilat", with "and" before the last
   item and the English names from ctx.loc.name_en or the site's overrides), and a count with the
   `words` op ("{{x.playbook.n_list_towns|words}}"). Handle the empty case in the wording or with a
   watch (e.g. "count >= 1"). Never write a sentence that becomes ungrammatical when the list changes
   length; if it could be empty, watch it.
3. Time: do not tie the text to a date that passes. Replace "the 13 October forecast", "the 13 Oct
   forecast" with "the current forecast" or "the forecast (polls to {{fc.asof|date}})". Replace relative
   spans written for 13 Oct ("two weeks out", "in 14 days", "the last 14 days", "this week", "five days
   away", "ten days", "today") with absolute dates or deadlines ("before Sun 18 Oct", "by Fri 16 Oct",
   "between now and Tue 27 Oct", "in the final days") or durable phrasing. Keep dated historical facts
   ("Kan on 11 Oct", "the 13 Oct update") and research durations ("decays after about two weeks").
   Calendar and timeline items keep their dates; a label like "This week" becomes the dates; an action
   whose date has passed but which is still needed is phrased "now" or "by <date>".
4. Model-number wording: "about 1.0 point" when the number can become 1.2 needs "points"; avoid
   singular/plural traps by writing "points" after any token that can differ from exactly 1, or use the
   unit in the token's sentence robustly.
5. Check: `../.venv/bin/python targeting_facts.py render <file> > /dev/null` must succeed (no unknown
   key) under the live state AND `--root archive_1013pm` (robustness to other states), and
   `targeting_facts.py watch <watchfile>` must show 0 false under the live state. Read the fully
   rendered live text of every sentence you touched.
