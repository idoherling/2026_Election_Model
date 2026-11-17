"""Derived numbers for the sources page (data/processed/targeting/research/content_tok_sources.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.

Expected wasted vote by list (D7-F01), from the forecast's share draws (ctx.draws), in points of
the valid vote, computed exactly as targeting_facts' waste.* family (share counted when below the
threshold, averaged over all draws):
    waste_RZP, waste_HarediPublic, waste_Amcha, waste_Otzma, waste_Noam
    waste_nb_rest         the other Netanyahu-bloc lists (Likud, Shas, UTJ) together
    (a list missing from the share draws, withdrawn or merged, gives NaN, so the D7-F01 watch flags)

Blue and White withdrawal (D7-F07): the levers.json "bw_withdraws" move (targeting_levers._bw: 60% to
Yashar, 25% to Together, 15% abstain) re-run through the seat law on the same draws; change in
expected seats per list (seats):
    bw_dseats_Yashar, bw_dseats_Together, bw_dseats_Democrats, bw_dseats_YB
    bw_dseats_change      the four change lists together
    (all NaN when Blue and White or one of the four lists is missing from the share draws)

Within-change split sensitivity of the collapse scenarios (D7-F07, D7-F24, D7-F26): how much the
change in P(NB>=61) (points, from the seat law on the same draws) moves when the change-camp share
is split differently among the four change lists:
    split_sens_bw         Blue and White withdrawal: the levers.json split (60% Yashar, 25% Together,
                          15% abstain) against the same 85% split in proportion to the change lists'
                          mean shares (15% abstain)
    split_sens_res        Reservists-Economic collapse 60/40: the levers.json "res_withdraws" split
                          (60% to change lists in proportion to size, 40% Likud; its delta read from
                          lev.res_withdraws.deny) against the research desk's split (Yashar 40,
                          Together 15, Yisrael Beytenu 5, Likud 40)
    split_sens            the larger of the two (NaN when either scenario cannot be run)

Break-even counter-mobilisation (D11-F34), from segments.csv: a one-point turnout rise in a segment
nets eligible x 0.01 x (p26_nb - p26_change) votes for the Netanyahu bloc:
    nb_net_per_point      sum over Netanyahu-leaning segments (p26_nb > p26_change), NB net votes
    ch_net_per_point      sum over change-leaning Jewish segments (p26_change > p26_nb, excluding
                          the Arab segments and the Druze), change-bloc net votes (positive)
    national_net_per_point  sum over all segments (positive = a uniform rise favours the NB)
    breakeven_lo, breakeven_hi  turnout rise (points) across Netanyahu-leaning segments that cancels
                          the realistic change-led-government plan at 150k contacts / 0% identified
                          and at 400k / 30% identified (bud.govt.*.ve / nb_net_per_point)
"""
from __future__ import annotations

import numpy as np

import targeting_marginal as tmg

WASTE_LISTS = {"RZP": "Religious Zionist Party", "HarediPublic": "The Haredi Public",
               "Amcha": "Amcha Yisrael", "Otzma": "Otzma Yehudit", "Noam": "Noam"}
CHANGE_SHORT = {"Yashar": "Yashar", "Together": "Bennett 2026 + Yesh Atid",
                "Democrats": "The Democrats", "YB": "Yisrael Beytenu"}


def _waste(S, i):
    x = S[:, i]
    return 100 * float((x * (x < tmg.THRESHOLD)).mean())


def facts(ctx, get):
    out = {}
    S, labels = ctx.draws
    labels = list(labels)

    # --- expected waste by list
    for k, lab in WASTE_LISTS.items():
        out[f"waste_{k}"] = _waste(S, labels.index(lab)) if lab in labels else float("nan")
    rest = [x for x in tmg.NB if x not in WASTE_LISTS.values() and x in labels]
    out["waste_nb_rest"] = sum(_waste(S, labels.index(x)) for x in rest)

    # --- Blue and White withdrawal: seat change by change list
    # Blue and White (or a change list) can leave the share draws under the ballot-aware
    # withdrawn rule; then the scenario does not exist and the keys are NaN, so the D7-F07
    # watches flag instead of every x.* token on every page failing to render.
    need = ["Blue and White", *CHANGE_SHORT.values()]
    pairs = tmg.label_pairs(labels)
    nb_ix = [labels.index(x) for x in tmg.NB if x in labels]

    def nb61(seats):
        return 100 * float((seats[:, nb_ix].sum(axis=1) >= 61).mean())

    base_nb61 = nb61(ctx.seats)
    out["split_sens_bw"] = out["split_sens_res"] = float("nan")
    if all(x in labels for x in need):
        import targeting_levers as tlv
        base = ctx.seats.mean(axis=0)
        bw_seats = tmg.allocate(tlv._bw(S, labels), pairs)
        bw = bw_seats.mean(axis=0)
        tot = 0.0
        for k, lab in CHANGE_SHORT.items():
            d = float(bw[labels.index(lab)] - base[labels.index(lab)])
            out[f"bw_dseats_{k}"] = d
            tot += d
        out["bw_dseats_change"] = tot

        # --- within-change split sensitivity (see the docstring)
        ch_w = {lab: float(S[:, labels.index(lab)].mean()) for lab in CHANGE_SHORT.values()}
        prop, _ = tlv._split_move(S, labels, "Blue and White", [(0.85, ch_w)])
        out["split_sens_bw"] = abs(nb61(bw_seats) - nb61(tmg.allocate(prop, pairs)))
        res = "Reservists – Economic Party"
        if res in labels and "Likud" in labels:
            try:
                lever = -get("lev.res_withdraws.deny")
            except KeyError:
                lever = float("nan")
            desk, _ = tlv._split_move(S, labels, res, [
                (0.60, {"Yashar": .40, "Bennett 2026 + Yesh Atid": .15, "Yisrael Beytenu": .05}),
                (0.40, {"Likud": 1})])
            out["split_sens_res"] = abs(nb61(tmg.allocate(desk, pairs)) - base_nb61 - lever)
    else:
        for k in CHANGE_SHORT:
            out[f"bw_dseats_{k}"] = float("nan")
        out["bw_dseats_change"] = float("nan")
    out["split_sens"] = max(out["split_sens_bw"], out["split_sens_res"]) \
        if not np.isnan(out["split_sens_bw"]) and not np.isnan(out["split_sens_res"]) else float("nan")

    # --- net votes per point of turnout by segment group
    seg = ctx.seg.set_index("segment")
    net = seg["eligible"] * 0.01 * (seg["p26_nb"] - seg["p26_change"])
    jewish = ~(seg.index.str.startswith("arab") | (seg.index == "druze"))
    out["nb_net_per_point"] = float(net[net > 0].sum())
    out["ch_net_per_point"] = float(-net[(net < 0) & jewish].sum())
    out["national_net_per_point"] = float(net.sum())
    out["breakeven_lo"] = get("bud.govt.150k.0.ve") / out["nb_net_per_point"]
    out["breakeven_hi"] = get("bud.govt.400k.30.ve") / out["nb_net_per_point"]
    return out
