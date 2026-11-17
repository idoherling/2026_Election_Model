"""Derived numbers for the strategy page (data/processed/targeting/research/content_tok_strategy.json).

Everything is computed from the pipeline outputs through ctx/get; no model value is hard-coded.

Forecast pass rates and central seats (official_forecast.csv):
    change_min_pass       lowest threshold pass chance among the four change lists (percent)
    rec_change            central seats of the four change lists (one change candidate's recommendations)
    rec_nb_core           central seats of Likud, Otzma and RZP (Netanyahu's recommendations without
                          Shas and UTJ)
    rec_nb_haredi         rec_nb_core plus Shas and UTJ
    near_line_nb          Netanyahu-bloc lists whose pass chance is between 10% and 90%
    near_line_other       other lists whose pass chance is between 10% and 90%
Conditional draws (cond.*):
    res_chseats_gap       expected change seats where the Reservists fail minus where they pass
    raam_swing_top3       1 if Ra'am, RZP and Amcha are the three lists (pass chance 5-95%) whose
                          pass/fail moves P(NB >= 61) the most, else 0
Levers (levers.json) and realistic plans (bud.*):
    switcher_ratio        value per vote of a Likud-to-change switcher over a new change vote
                          (change-led objective)
    likud_per_switcher    projected Likud voters per voter in the half-point Likud scenario
                          ("one Likud voter in N")
    tenth_switchers       a tenth of the half-point Likud scenario's voters
    tenth_vs_field        a tenth of the half-point Likud effect over the 400k/30% field plan (points/points)
    haredi_vs_likud       half a point from Shas/UTJ over half a point from Likud (change-led effect)
    ch25k_pct             25,000 extra change votes as a percent of the change lists' projected vote
    field_mult_25k, field_mult_50k   25,000 / 50,000 extra change votes over the 400k/30% field plan
                          (change-led points)
    nb_vs_ch_turnout      25,000 extra NB votes' change-led cost over 25,000 extra change votes' gain
Break-even counter-mobilisation (D11-F34), from segments.csv: a one-point turnout rise in a segment
nets eligible x 0.01 x (p26_nb - p26_change) votes for the Netanyahu bloc:
    nb_net_per_point      Netanyahu-leaning segments (p26_nb > p26_change), NB net votes
    ch_net_per_point      change-leaning Jewish segments (no Arab segments, no Druze), change net votes
    national_net_per_point  all segments (positive = a uniform rise favours the NB)
    breakeven_lo, breakeven_hi  rise (points) across NB-leaning segments that cancels the change-led
                          plan at 150k/0% and at 400k/30% (bud.govt.*.ve / nb_net_per_point)
Blue and White exit under the coordination desk's split (D7-F24 run (a), corrected split reproduced
from the desk's own script: 54% to change lists as Yashar 36 / Together 15 / Yisrael Beytenu 3,
26% to Likud, 20% stay home), run through the seat law on the forecast's draws:
    bw_desk_seats         expected change seats gained
    bw_desk_ratio         bw_desk_seats over the model's own split (lev.bw_withdraws.seats)
    (both NaN when Blue and White, Likud or a receiving change list is missing from the share draws;
    bw_desk_ratio also NaN when lev.bw_withdraws.seats does not exist)
res_chseats_gap is NaN when the Reservists are missing from the draws (no cond.Reservists.* keys).
A NaN fails its watch entry instead of stopping every page's x.* tokens from rendering.
"""
from __future__ import annotations

import numpy as np

import targeting_marginal as tmg

CHANGE_SHORT = ["Yashar", "Together", "Democrats", "YB"]
NB_SHORT = ["Likud", "Shas", "UTJ", "Otzma", "RZP", "Amcha", "Noam", "HarediPublic"]
NEAR_LINE = (0.10, 0.90)
SWING_RANGE = (5.0, 95.0)          # cond.<list>.pass in percent
# D7-F24 run (a): the coordination desk's assumed split of Blue and White's voters (research input,
# corrected split from verify_coordination.json: Yashar 36 / Together 15 / Yisrael Beytenu 3).
DESK_SPLIT = {"change": 0.54, "Likud": 0.26}           # the remaining 20% stay home
DESK_CHANGE_W = {"Yashar": 0.36, "Bennett 2026 + Yesh Atid": 0.15, "Yisrael Beytenu": 0.03}


def _dhondt_rows(V, seats):
    """D'Hondt on every row of V at once, same steps and tie-breaking as simulate.dhondt.
    `seats` is an int or an array with one seat total per row."""
    n, k = V.shape
    seats = np.broadcast_to(np.asarray(seats, dtype=int), (n,))
    alloc = np.zeros((n, k), dtype=int)
    quot = V.astype(float).copy()
    rows = np.arange(n)
    for step in range(int(seats.max()) if n else 0):
        act = rows[seats > step]
        i = quot[act].argmax(axis=1)
        alloc[act, i] += 1
        quot[act, i] = V[act, i] / (alloc[act, i] + 1)
    return alloc


def _allocate(S, pairs):
    """targeting_marginal.allocate, vectorised over draws (threshold, surplus pairs, Bader-Ofer)."""
    passed = S >= tmg.THRESHOLD
    votes = np.where(passed, S, 0.0)
    fv = votes.copy()
    merged = []
    for a, b in pairs:
        m = passed[:, a] & passed[:, b]
        fv[m, a] = votes[m, a] + votes[m, b]
        fv[m, b] = 0.0
        merged.append((a, b, m))
    seats = _dhondt_rows(fv, 120)
    for a, b, m in merged:
        if m.any():
            inner = _dhondt_rows(np.stack([votes[m, a], votes[m, b]], axis=1), seats[m, a])
            seats[m, a], seats[m, b] = inner[:, 0], inner[:, 1]
    seats[~passed.any(axis=1)] = 0
    return seats


def _change_seats(S, labels, pairs, exact=False):
    seats = tmg.allocate(S, pairs) if exact else _allocate(S, pairs)
    return float(seats[:, [labels.index(x) for x in tmg.CHANGE]].sum(axis=1).mean())


def facts(ctx, get):
    out = {}
    fpass = lambda s: float(get(f"fc.{s}.pass"))

    # --- forecast pass rates and central seats
    out["change_min_pass"] = 100 * min(fpass(s) for s in CHANGE_SHORT)
    fc = ctx.fc.set_index("list")["central_seats"]
    cs = lambda labels: int(sum(int(fc.get(x, 0)) for x in labels))
    out["rec_change"] = cs(tmg.CHANGE)
    core = ["Likud", "Otzma Yehudit", "Religious Zionist Party"]
    out["rec_nb_core"] = cs(core)
    out["rec_nb_haredi"] = cs(core + ["Shas", "United Torah Judaism"])
    lo, hi = NEAR_LINE
    p = ctx.fc.set_index("list")["p_pass"]
    nb_long = set(tmg.NB)
    near = [x for x, v in p.items() if lo <= v <= hi]
    out["near_line_nb"] = sum(1 for x in near if x in nb_long)
    out["near_line_other"] = sum(1 for x in near if x not in nb_long)

    # --- conditional draws
    try:
        out["res_chseats_gap"] = get("cond.Reservists.chseats_fail") - get("cond.Reservists.chseats_pass")
    except KeyError:                    # the Reservists left the draws: no cond.Reservists.* keys
        out["res_chseats_gap"] = float("nan")
    swing = {}
    for s in ["Raam", "Reservists", "Amcha", "RZP", "Otzma", "Democrats", "YB", "Together", "BW", "JL"]:
        try:
            ps = get(f"cond.{s}.pass")
        except KeyError:
            continue
        if SWING_RANGE[0] <= ps <= SWING_RANGE[1]:
            swing[s] = abs(get(f"cond.{s}.nb61_fail") - get(f"cond.{s}.nb61_pass"))
    top3 = set(sorted(swing, key=swing.get, reverse=True)[:3])
    out["raam_swing_top3"] = 1.0 if top3 == {"Raam", "RZP", "Amcha"} else 0.0

    # --- levers and plans
    per_vote = lambda k: get(f"lev.{k}.govt") / get(f"lev.{k}.votes")
    out["switcher_ratio"] = per_vote("pers_likud_0.5") / per_vote("ch_turnout_25000")
    likud_votes = get("mv.Likud.share") / 100 * get("atlas.valid_votes")
    out["likud_per_switcher"] = likud_votes / get("lev.pers_likud_0.5.votes")
    out["tenth_switchers"] = get("lev.pers_likud_0.5.votes") / 10
    field_pp = get("bud.govt.400k.30.pp")
    out["tenth_vs_field"] = get("lev.pers_likud_0.5.govt") / 10 / field_pp
    out["haredi_vs_likud"] = get("lev.pers_haredi_0.5.govt") / get("lev.pers_likud_0.5.govt")
    ch_votes = sum(get(f"mv.{s}.share") for s in CHANGE_SHORT) / 100 * get("atlas.valid_votes")
    out["ch25k_pct"] = 100 * get("lev.ch_turnout_25000.votes") / ch_votes
    out["field_mult_25k"] = get("lev.ch_turnout_25000.govt") / field_pp
    out["field_mult_50k"] = get("lev.ch_turnout_50000.govt") / field_pp
    out["nb_vs_ch_turnout"] = abs(get("lev.nb_turnout_25000.govt")) / get("lev.ch_turnout_25000.govt")

    # --- net votes per point of turnout by segment group (D11-F34)
    seg = ctx.seg.set_index("segment")
    net = seg["eligible"] * 0.01 * (seg["p26_nb"] - seg["p26_change"])
    jewish = ~(seg.index.str.startswith("arab") | (seg.index == "druze"))
    out["nb_net_per_point"] = float(net[net > 0].sum())
    out["ch_net_per_point"] = float(-net[(net < 0) & jewish].sum())
    out["national_net_per_point"] = float(net.sum())
    out["breakeven_lo"] = get("bud.govt.150k.0.ve") / out["nb_net_per_point"]
    out["breakeven_hi"] = get("bud.govt.400k.30.ve") / out["nb_net_per_point"]

    # --- Blue and White exit under the coordination desk's split
    # Blue and White (this page's own lever 0) or a receiving list can leave the share draws under
    # the ballot-aware withdrawn rule; then the scenario does not exist and the keys are NaN, so the
    # watch entries flag instead of every x.* token on every page failing to render.
    S, labels = ctx.draws
    labels = list(labels)
    need = ["Blue and White", "Likud", *DESK_CHANGE_W, *tmg.CHANGE]
    if all(x in labels for x in need):
        pairs = tmg.label_pairs(labels)
        # the vectorised seat law must reproduce the forecast's own expected change seats; else use the exact one
        exact = abs(_change_seats(S, labels, pairs) - get("draws.ch_seats")) > 1e-9
        s = S.copy()
        i = labels.index("Blue and White")
        take = s[:, i].copy()
        s[:, i] = 0.0
        wsum = sum(DESK_CHANGE_W.values())
        for name, w in DESK_CHANGE_W.items():
            s[:, labels.index(name)] += take * DESK_SPLIT["change"] * w / wsum
        s[:, labels.index("Likud")] += take * DESK_SPLIT["Likud"]
        s = s / s.sum(axis=1, keepdims=True)
        out["bw_desk_seats"] = _change_seats(s, labels, pairs, exact) - get("draws.ch_seats")
        try:
            ref = get("lev.bw_withdraws.seats")
        except KeyError:
            ref = float("nan")
        out["bw_desk_ratio"] = out["bw_desk_seats"] / ref
    else:
        out["bw_desk_seats"] = out["bw_desk_ratio"] = float("nan")
    return out
