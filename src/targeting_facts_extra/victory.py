"""Derived numbers for the Victory page (data/processed/targeting/research/content_tok_victory.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.
"""
from __future__ import annotations

import math

import targeting_marginal as tmg

# D11-F34's segment grouping (desk calculation on the atlas segment table). The watch file checks
# that each group still leans the way the page describes it.
NB_LEAN_SEGMENTS = ["haredi", "jerusalem", "periphery_likud", "russian_speaking", "religious_zionist",
                    "settlement_rz", "settlement_secular", "mixed_city"]
CHANGE_LEAN_JEWISH_SEGMENTS = ["liberal_urban", "kibbutz", "moshav_rural", "mixed_urban"]
HAREDI_LISTS = ["Shas", "United Torah Judaism"]


def facts(ctx, get):
    out = {}

    # Recommendations to the President on the forecast's central (median) seats.
    seats = ctx.fc.set_index("list")["central_seats"]
    s = lambda labels: int(sum(int(seats.get(x, 0)) for x in labels))
    out["change_recs"] = s(tmg.CHANGE)                                        # the four change lists
    out["nb_recs_all"] = s(tmg.NB)                                            # every NB list recommends Netanyahu
    out["nb_recs_no_haredi"] = s([x for x in tmg.NB if x not in HAREDI_LISTS])  # Shas and UTJ recommend no one

    # Points of change-led government that need a partner beyond the four lists
    # (with Ra'am, with a haredi party, with unaligned/Amcha, centre minority backed by the Joint List).
    out["partner_pts"] = get("gov.change_led") - get("gov.change_alone")

    # Lowest pass chance (%) among the three smaller change lists.
    out["allies_min_pass"] = 100 * min(get("fc.Democrats.pass"), get("fc.Together.pass"), get("fc.YB.pass"))

    # Largest deny-61 exchange rate (points per 10,000 votes) among lists other than Ra'am.
    mv = ctx.mv
    out["max_other_deny"] = 100 * float(mv.loc[mv["list"] != "Ra'am", "block_nb"].max())

    # D11-F34 arithmetic: net votes from a 1-point turnout rise = eligible x 0.01 x (p26_nb - p26_change).
    seg = ctx.seg.set_index("segment")
    net = seg["eligible"] * 0.01 * (seg["p26_nb"] - seg["p26_change"])
    out["nb_lean_net"] = float(net.loc[NB_LEAN_SEGMENTS].sum())                      # net NB votes
    out["ch_lean_net"] = float(-net.loc[CHANGE_LEAN_JEWISH_SEGMENTS].sum())         # net change votes
    out["national_net"] = float(net.sum())                                           # net NB votes, uniform rise
    # Smallest lean (share points, 0-1 scale) within each group, so the watch file can check that every
    # "Netanyahu-leaning" segment still leans NB and every "change-leaning" one still leans change.
    lean = seg["p26_nb"] - seg["p26_change"]
    out["nb_lean_min_margin"] = float(lean.loc[NB_LEAN_SEGMENTS].min())
    out["ch_lean_min_margin"] = float((-lean.loc[CHANGE_LEAN_JEWISH_SEGMENTS]).min())
    # Turnout rise (points) across the NB-leaning segments that cancels the largest realistic
    # field programme (central plan at 400,000 contacts with 30% identified, any objective).
    top_plan = max(get(f"bud.{k}.400k.30.ve") for k in ("govt", "deny", "seats"))
    out["breakeven_nb_pts"] = top_plan / out["nb_lean_net"]
    # The next tenth strictly above it, for "a rise of under N points" in donts[0].
    out["breakeven_nb_pts_bound"] = (math.floor(out["breakeven_nb_pts"] * 10) + 1) / 10

    # donts[2]: how Otzma's cost per 10,000 votes (change-led chance) compares with Likud's, as words,
    # judged on the two figures as the page prints them (two decimals). "About the same" within 0.05 points.
    otz = round(abs(get("mv.Otzma.govt")), 2)
    lik = round(abs(get("mv.Likud.govt")), 2)
    if abs(otz - lik) <= 0.05 + 1e-9:
        out["otzma_vs_likud"] = "about the same as Likud's"
    elif otz > lik:
        out["otzma_vs_likud"] = "more than Likud's"
    else:
        out["otzma_vs_likud"] = "less than Likud's"
    return out
