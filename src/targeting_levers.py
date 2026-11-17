"""Targeting layer, part 5: strategic levers beyond the field.

Moves votes between lists on every one of the forecast's 8,000 election-day
share draws, then re-runs the full seat law (threshold, the six surplus
pairs, Bader-Ofer) and the government-formation model with the same 60
behaviour vectors and common random numbers as targeting_marginal.py. The
results are exact under the model, not straight-line approximations, so
threshold effects (a list falling out or getting in) are captured.

Each scenario states what moves and where it goes. These are model
arithmetic: they show how much a lever is worth IF it happens, not how
likely it is to happen.

Output: data/processed/targeting/levers.json
"""

from __future__ import annotations

import json

import numpy as np

import targeting_marginal as tmg

N = tmg.VALID_VOTES_2026
CH = ["Yashar", "Bennett 2026 + Yesh Atid", "The Democrats", "Yisrael Beytenu"]
NBL = ["Likud", "Shas", "United Torah Judaism", "Otzma Yehudit",
       "Religious Zionist Party", "Amcha Yisrael"]


def col(labels, name):
    return labels.index(name)


def move(s, labels, src, dst, amount=None, frac=None):
    """Move votes from `src` lists to `dst` (dict list -> weight, or 'abstain').
    `amount` is a share of the national vote taken from src in proportion to
    their shares; `frac` takes that fraction of each src list. Shares are
    renormalised at the end (abstention lowers the total)."""
    s = s.copy()
    ix = [col(labels, x) for x in src]
    base = s[:, ix]
    if frac is not None:
        take = base * frac
    else:
        tot = base.sum(axis=1, keepdims=True)
        take = base / np.maximum(tot, 1e-12) * np.minimum(amount, tot)
    s[:, ix] -= take
    moved = take.sum(axis=1)
    if dst != "abstain":
        w = np.array(list(dst.values()), float)
        w = w / w.sum()
        for (name, _), wi in zip(dst.items(), w):
            s[:, col(labels, name)] += moved * wi
    return s / s.sum(axis=1, keepdims=True), float(moved.mean())


def add(s, labels, dst, amount):
    """Add `amount` (share of the 2026 vote) of new votes to `dst` lists."""
    s = s.copy()
    w = np.array(list(dst.values()), float)
    w = w / w.sum()
    for (name, _), wi in zip(dst.items(), w):
        s[:, col(labels, name)] += amount * wi
    return s / s.sum(axis=1, keepdims=True), amount


def main() -> None:
    shares, labels, _ = tmg.share_draws()
    labels = list(labels)
    pairs = tmg.label_pairs(labels)
    behaviors = tmg.behavior_vectors()
    mean = {l: float(shares[:, col(labels, l)].mean()) for l in labels}
    ch_w = {l: mean[l] for l in CH}
    nb_w = {l: mean[l] for l in NBL}

    def run(s):
        return tmg.objectives(tmg.allocate(s, pairs), labels, behaviors)

    base = run(shares)
    print("base", {k: round(v, 4) for k, v in base.items()})
    sc = []

    def scen(key, group, title, what, s_new, votes):
        r = run(s_new)
        sc.append({"key": key, "group": group, "title": title, "what": what,
                   "votes": round(votes * N), "result": r,
                   "delta": {k: r[k] - base[k] for k in base}})
        print(f"{key:28s} votes {votes * N:9,.0f}  dGovt {100 * (r['change_govt'] - base['change_govt']):+6.2f}  "
              f"dDeny61 {100 * (r['block_nb'] - base['block_nb']):+6.2f}  dSeats {r['change_seats'] - base['change_seats']:+.2f}")

    # --- agreements between lists (a list the forecast has withdrawn, e.g. Blue and White on
    # 19 Oct, has ~zero share in the draws; its scenarios are dropped rather than shown as zero)
    live = lambda name: mean.get(name, 0.0) > 0.001
    if live("Blue and White"):
        scen("bw_withdraws", "agreements", "Blue and White withdraws and endorses",
             "All Blue and White votes move: 60% to Yashar, 25% to Together, 15% abstain (its 2022 transfer pattern, dossier s.38).",
             _bw(shares, labels), mean["Blue and White"])
    s, v = _split_move(shares, labels, "Reservists – Economic Party", [(0.60, ch_w), (0.40, {"Likud": 1})])
    scen("res_withdraws", "agreements", "Reservists-Economic withdraws (60% to change lists)",
         "All Reservists votes move: 60% to change lists in proportion to their size, 40% to Likud (the atlas's rescue assumption).", s, v)
    s, v = _split_move(shares, labels, "Reservists – Economic Party", [(0.35, ch_w), (0.65, {"Likud": .7, "Otzma Yehudit": .3})])
    scen("res_withdraws_right", "agreements", "Reservists-Economic withdraws (mostly to the right)",
         "All Reservists votes move: 35% to change lists, 65% to Likud and Otzma. A pessimistic split for a right-of-centre list.", s, v)
    s, v = _split_move(shares, labels, "Amcha Yisrael", [(0.8, {"Likud": .5, "Otzma Yehudit": .5}), (0.2, ch_w)])
    scen("amcha_withdraws", "agreements", "Amcha withdraws (the opponent consolidates)",
         "All Amcha votes move: 80% to Likud and Otzma, 20% to change lists. Shows what consolidation on the other side would cost.", s, v)
    # --- persuasion: votes moved from the Netanyahu bloc to change lists
    for pt in (0.5, 1.0, 2.0):
        s, v = move(shares, labels, ["Likud"], ch_w, amount=pt / 100)
        scen(f"pers_likud_{pt}", "persuasion", f"{pt:g} point of the vote moves from Likud to change lists",
             f"{pt:g}% of the national vote leaves Likud for the four change lists, in proportion to their size.", s, v)
    s, v = move(shares, labels, ["Shas", "United Torah Judaism"], ch_w, amount=0.005)
    scen("pers_haredi_0.5", "persuasion", "0.5 point moves from Shas/UTJ to change lists",
         "0.5% of the vote leaves Shas and UTJ for the change lists (traditional voters on the draft).", s, v)
    # --- turnout
    for k in (25_000, 50_000):
        s, v = add(shares, labels, ch_w, k / N)
        scen(f"ch_turnout_{k}", "turnout", f"{k:,} extra change-list votes (turnout)",
             f"{k:,} new votes for the four change lists, in proportion to their size.", s, v)
    s, v = move(shares, labels, ["Shas", "United Torah Judaism"], "abstain", frac=0.10)
    scen("haredi_turnout_-10", "turnout", "Haredi turnout falls 10%",
         "Shas and UTJ lose 10% of their votes to abstention (UTJ's own reported fear after the draft-law failure).", s, v)
    s, v = add(shares, labels, nb_w, 25_000 / N)
    scen("nb_turnout_25000", "turnout", "25,000 extra Netanyahu-bloc votes (counter-mobilisation)",
         "25,000 new votes for the Netanyahu-bloc lists, in proportion to their size: the cost of triggering the other side's turnout.", s, v)
    jl, ra = mean["Balad + Hadash-Ta'al"], mean["Ra'am"]
    for k in (46_000, -46_000):
        if k > 0:
            s, v = add(shares, labels, {"Balad + Hadash-Ta'al": jl, "Ra'am": ra}, k / N)
        else:
            s, v = move(shares, labels, ["Balad + Hadash-Ta'al", "Ra'am"], "abstain", amount=-k / N)
        scen(f"arab_turnout_{'+' if k > 0 else '-'}5", "turnout", f"Arab turnout {'+' if k > 0 else '-'}5 points (~46,000 votes)",
             "Votes added to (or removed from) the Joint List and Ra'am in proportion to their size.", s, v)
    # --- allies and thresholds (within-bloc moves)
    s, v = move(shares, labels, ["Yashar"], {"The Democrats": 1}, amount=0.005)
    scen("yashar_to_dem_0.5", "allies", "0.5 point moves from Yashar to the Democrats",
         "Within-bloc move: 0.5% of the vote shifts from Yashar to the Democrats.", s, v)
    s, v = move(shares, labels, ["Balad + Hadash-Ta'al"], {"Ra'am": 1}, amount=0.005)
    scen("jl_to_raam_0.5", "allies", "0.5 point moves from the Joint List to Ra'am",
         "Within the Arab lists: 0.5% of the vote shifts from the Joint List to Ra'am (threshold insurance for Ra'am).", s, v)
    # --- combined
    if live("Blue and White"):
        s = _bw(shares, labels)
        s, v2 = move(s, labels, ["Likud"], ch_w, amount=0.005)
        scen("bw_plus_pers_0.5", "combined", "Blue and White withdraws, and 0.5 point moves from Likud",
             "The two largest realistic levers together.", s, mean["Blue and White"] + v2)

    out = {"base": base, "valid_votes": N, "pairs": [[labels[a], labels[b]] for a, b in pairs],
           "mean_shares": mean, "scenarios": sc,
           "note": "Exact under the forecast's seat law and formation model (8,000 draws, 60 behaviour vectors, common random numbers). Effects are model arithmetic for a lever that happens, not forecasts that it will."}
    (tmg.OUT / "levers.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", tmg.OUT / "levers.json")


def _bw(shares, labels):
    s, _ = move(shares, labels, ["Blue and White"], {"Yashar": .60, "Bennett 2026 + Yesh Atid": .25, "Blue and White": .15}, frac=1.0)
    # the 15% that abstain: remove what was parked back on Blue and White
    s2, _ = move(s, labels, ["Blue and White"], "abstain", frac=1.0)
    return s2


def _split_move(shares, labels, src, parts):
    """Move all of `src` to several destination groups with given weights."""
    s = shares.copy()
    i = col(labels, src)
    take = s[:, i].copy()
    s[:, i] = 0
    for w, dst in parts:
        tw = np.array(list(dst.values()), float)
        tw = tw / tw.sum()
        for (name, _), wi in zip(dst.items(), tw):
            s[:, col(labels, name)] += take * w * wi
    return s / s.sum(axis=1, keepdims=True), float(take.mean())


if __name__ == "__main__":
    main()
