"""Seat law: the 3.25% threshold, Bader-Ofer (d'Hondt) and surplus agreements.

The allocation under test is the production one, simulate.simulate_core,
run as a single deterministic draw (no bloc swing, no family shocks, no
noise): threshold -> resolve_pairs -> form_factions -> d'Hondt over factions
-> d'Hondt inside each pooled pair. bayes_model.project and
official_forecast.allocate_central run the same steps on their own share
vectors; validate_bayes.allocate_vector is the harness copy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import official_forecast as of
import simulate as sim
import validate_bayes as vb
from validate_model import CYCLE_THRESHOLD, ORDER, REGISTERED_PAIRS


def allocate(shares, components, pairs, threshold=sim.THRESHOLD):
    """One draw of simulate_core with every shock switched off."""
    shares = np.asarray(shares, float)
    avg = pd.DataFrame({"components": list(components), "share": shares,
                        "avg_seats": shares * 120, "debut": False,
                        "bloc": "other", "family": "other"})
    return sim.simulate_core(avg, pairs, threshold=threshold, scale=0.0, bloc_swing_sd=0.0,
                             family_shock={}, anchors=None, n_sims=1, seed=0)[0]


def cycle_counts(root, cycle):
    d = pd.read_csv(root / "data" / "cec_final_counts.csv", dtype={"cycle": str})
    d = d[d["cycle"] == cycle].reset_index(drop=True)
    # lists the registry does not name (no seats in any cycle) get unique ids
    d["party_id"] = [p if isinstance(p, str) and p else f"_unlisted_{i}"
                     for i, p in enumerate(d["party_id"])]
    return d


def random_vector(rng, k):
    """Share vectors with several lists near the threshold."""
    big = rng.dirichlet(np.ones(k) * rng.uniform(0.6, 3.0))
    small = rng.uniform(0.015, 0.045, size=rng.integers(1, 4))
    v = np.concatenate([big * (1 - small.sum()), small])
    return v / v.sum()


# --- the official record --------------------------------------------------

def test_2022_official_allocation(root):
    """Official 2022 vote counts -> the official 2022 Knesset, list by list."""
    d = cycle_counts(root, "2022")
    valid = int(d["valid_votes"].iloc[0])
    assert d["votes"].sum() == valid          # every valid vote is on some list
    seats = allocate(d["votes"] / valid, d["party_id"], REGISTERED_PAIRS["2022"])
    got = dict(zip(d["party_id"], seats.tolist()))

    assert seats.sum() == 120
    assert (seats == d["seats_official"].values).all()
    res = pd.read_csv(root / "data" / "processed" / "results.csv", dtype={"cycle": str})
    res = res[res["cycle"] == "2022"].set_index("party_id")["seats"]
    assert {p: got[p] for p in res.index} == res.astype(int).to_dict()
    assert {p for p, s in got.items() if s > 0} == {p for p, s in res.items() if s > 0}
    # the two lists that fell short: Meretz 3.16%, Balad 2.90% of valid votes
    for pid in ("meretz", "balad"):
        share = float(d.loc[d["party_id"] == pid, "votes"].iloc[0]) / valid
        assert share < sim.THRESHOLD and got[pid] == 0


def test_2022_needs_the_registered_agreements(root):
    """Without the surplus agreements the same votes give a different
    Knesset: the pairs are doing real work in the reproduction."""
    d = cycle_counts(root, "2022")
    no_pairs = allocate(d["votes"] / d["valid_votes"], d["party_id"], [])
    assert no_pairs.sum() == 120
    assert (no_pairs != d["seats_official"].values).any()


@pytest.mark.parametrize("cycle", ORDER)
def test_every_graded_cycle_reproduces(root, cycle):
    """All eight graded Knessets from their final counts (2% threshold in
    2009/2013), the registered pairs resolved through the harness's era
    aliases as validate_seat_law does."""
    d = cycle_counts(root, cycle)
    comps = list(d["party_id"])
    idx, _, _ = sim.resolve_pairs(REGISTERED_PAIRS[cycle], comps,
                                  aliases=vb._decomp_map(cycle), fixed=True)
    pairs = [(comps[a], comps[b]) for a, b in idx]
    thr = CYCLE_THRESHOLD.get(cycle, sim.THRESHOLD)
    seats = allocate(d["votes"] / d["valid_votes"], comps, pairs, threshold=thr)
    assert (seats == d["seats_official"].values).all()


# --- invariants on random share vectors -----------------------------------

def test_seats_sum_to_120_under_the_shock_stack():
    """simulate_core with its full shock stack: every draw seats 120."""
    rng = np.random.default_rng(11)
    for trial in range(5):
        v = random_vector(rng, 12)
        k = len(v)
        comps = [f"l{i}" for i in range(k)]
        avg = pd.DataFrame({"components": comps, "share": v, "avg_seats": v * 120,
                            "debut": rng.random(k) < 0.3,
                            "bloc": np.where(np.arange(k) % 2 == 0, "netanyahu_bloc", "opposition_bloc"),
                            "family": np.where(np.arange(k) < 2, "haredi",
                                               np.where(np.arange(k) < 4, "arab", "other"))})
        pairs = [("l0", "l1"), ("l2", "l3"), ("l5", "l9")]
        seats = sim.simulate_core(avg, pairs, scale=1.5, n_sims=1500, seed=trial)
        assert (seats.sum(axis=1) == 120).all()
        assert (seats >= 0).all()


def test_seats_sum_to_120_and_threshold_deterministic():
    """Every list below 3.25% gets 0, every list at or above it gets at
    least 3 (d'Hondt's lower quota at >= 3.9 seats of quota), and the
    total is 120 - with and without surplus pairs."""
    rng = np.random.default_rng(5)
    for _ in range(400):
        k = int(rng.integers(5, 18))
        v = random_vector(rng, k)
        comps = [f"l{i}" for i in range(len(v))]
        passing = np.nonzero(v >= sim.THRESHOLD)[0]
        pairs = []
        if len(passing) >= 2:
            a, b = rng.choice(len(v), 2, replace=False)
            pairs = [(comps[a], comps[b])]
        for pr in ([], pairs):
            seats = allocate(v, comps, pr)
            assert seats.sum() == 120
            assert (seats[v < sim.THRESHOLD] == 0).all()
            assert (seats[v >= sim.THRESHOLD] >= 3).all()


def test_pair_with_a_failing_partner_changes_nothing():
    """A surplus agreement pools only when both partners pass."""
    rng = np.random.default_rng(8)
    n = 0
    for _ in range(300):
        v = random_vector(rng, int(rng.integers(6, 14)))
        comps = [f"l{i}" for i in range(len(v))]
        below = np.nonzero(v < sim.THRESHOLD)[0]
        above = np.nonzero(v >= sim.THRESHOLD)[0]
        if not len(below) or not len(above):
            continue
        a, b = int(rng.choice(above)), int(rng.choice(below))
        with_pair = allocate(v, comps, [(comps[a], comps[b])])
        assert (with_pair == allocate(v, comps, [])).all()
        assert with_pair[b] == 0
        n += 1
    assert n > 100


def test_surplus_pair_moves_the_pair_total_by_at_most_one():
    """Pooling two passing lists changes their combined seats by 0 or +1
    (d'Hondt never penalises a pooled pair, and one remainder is all a
    pair can gain)."""
    rng = np.random.default_rng(3)
    gained = n = 0
    for _ in range(1500):
        v = random_vector(rng, int(rng.integers(5, 16)))
        comps = [f"l{i}" for i in range(len(v))]
        passing = np.nonzero(v >= sim.THRESHOLD)[0]
        if len(passing) < 2:
            continue
        a, b = (int(x) for x in rng.choice(passing, 2, replace=False))
        s1 = allocate(v, comps, [(comps[a], comps[b])])
        s0 = allocate(v, comps, [])
        delta = int(s1[a] + s1[b] - s0[a] - s0[b])
        assert abs(delta) <= 1
        assert delta >= 0
        gained += delta
        n += 1
    assert n > 1000 and 0 < gained < n          # the pair matters sometimes, not always


def test_registered_2022_pairs_each_move_at_most_one_seat(root):
    d = cycle_counts(root, "2022")
    comps = list(d["party_id"])
    v = d["votes"] / d["valid_votes"]
    base = allocate(v, comps, [])
    for a, b in REGISTERED_PAIRS["2022"]:
        if a not in comps or b not in comps:
            continue
        s = allocate(v, comps, [(a, b)])
        ia, ib = comps.index(a), comps.index(b)
        assert abs(int(s[ia] + s[ib] - base[ia] - base[ib])) <= 1


def test_a_list_is_never_pooled_twice():
    """Pair resolver fix (s.40): first occurrence wins, and a list already
    pooled in a draw is not pooled again."""
    comps = ["a", "b", "c", "d"]
    idx, _, dropped = sim.resolve_pairs([("a", "b"), ("b", "c")], comps, fixed=True)
    assert idx == [(0, 1), (1, 2)] and dropped == []
    votes = np.array([0.4, 0.3, 0.2, 0.1])
    fv, fm = sim.form_factions(idx, np.ones(4, bool), votes, fixed=True)
    members = [m for f in fm for m in f]
    assert sorted(members) == [0, 1, 2, 3]              # each list exactly once
    assert [0, 1] in fm and [1, 2] not in fm
    # an appended duplicate column cannot capture an id from an earlier block
    idx2, comp_of, _ = sim.resolve_pairs([("balad", "raam")],
                                         ["balad+hadash_taal", "raam", "balad"], fixed=True)
    assert comp_of["balad"] == 0 and idx2 == [(0, 1)]


def test_harness_allocator_matches_production():
    """validate_bayes.allocate_vector (the harness) and simulate_core give
    the same seats for the same vector and disjoint pairs."""
    rng = np.random.default_rng(21)
    for _ in range(300):
        v = random_vector(rng, int(rng.integers(5, 16)))
        comps = [f"l{i}" for i in range(len(v))]
        order = rng.permutation(len(v))
        pairs_idx = [(int(order[0]), int(order[1])), (int(order[2]), int(order[3]))]
        pairs = [(comps[a], comps[b]) for a, b in pairs_idx]
        assert (vb.allocate_vector(v, sim.THRESHOLD, pairs_idx) == allocate(v, comps, pairs)).all()


def test_official_central_count_obeys_the_seat_law():
    """official_forecast.allocate_central on 2026-shaped median vectors:
    120 seats, 0 below the threshold, the signed 2026 pairs resolved."""
    lists = [("Likud", "likud"), ("Yashar", "yashar"),
             ("Bennett 2026 + Yesh Atid", "bennett_2026+yesh_atid"),
             ("The Democrats", "democrats"), ("Yisrael Beytenu", "yisrael_beytenu"),
             ("Shas", "shas"), ("United Torah Judaism", "utj"), ("Otzma Yehudit", "otzma"),
             ("Religious Zionist Party", "rzp"), ("Ra'am", "raam"),
             ("Balad + Hadash-Ta'al", "balad+hadash_taal"), ("Amcha Yisrael", "amcha_yisrael"),
             ("Reservists – Economic Party", "zionist_home"), ("Blue and White", "blue_white")]
    base = np.array([.21, .19, .10, .075, .068, .065, .07, .05, .034, .04, .072, .02, .015, .01])
    rng = np.random.default_rng(4)
    for _ in range(200):
        v = np.clip(base * np.exp(rng.normal(0, 0.25, len(base))), 0, None)
        v = v / v.sum() * 0.96            # medians are not additive (s.47)
        frame = pd.DataFrame({"list": [n for n, _ in lists],
                              "components": [c for _, c in lists], "share_median": v})
        seats = of.allocate_central(frame)
        s = np.array([seats[n] for n, _ in lists])
        assert s.sum() == 120
        vn = v / v.sum()
        assert (s[vn < sim.THRESHOLD] == 0).all()
        pair_idx, _, dropped = sim.resolve_pairs(sim.SURPLUS_PAIRS, list(frame["components"]),
                                                 aliases=sim.PAIR_ALIASES_2026)
        assert dropped == []                              # every signed pair resolves
        assert len(of.allocate_central.last_pairs) == len(sim.SURPLUS_PAIRS)
        assert (vb.allocate_vector(v, sim.THRESHOLD, pair_idx) == s).all()
