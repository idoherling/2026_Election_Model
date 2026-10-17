"""Formation tree (government_formation.simulate_formation) on synthetic Knessets.

The seat draws are synthetic: a central 2026-like vote, a wide bloc swing
and per-list noise, pushed through the real seat law (3.25% threshold,
d'Hondt) so every draw is a legal 120-seat Knesset, and wide enough that
majorities, deadlocks and every gate occur.
"""
from __future__ import annotations

import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import government_formation as gf
import simulate as sim

VOTE = {"Likud": .215, "Otzma Yehudit": .05, "Shas": .065, "United Torah Judaism": .07,
        "Religious Zionist Party": .034, "Noam": .004, "Zehut": 0.0,
        "Yashar": .19, "Bennett 2026 + Yesh Atid": .095, "The Democrats": .075,
        "Yisrael Beytenu": .068, "Balad + Hadash-Ta'al": .07, "Ra'am": .04,
        "Amcha Yisrael": .03, "Blue and White": .012, "Unity": 0.0,
        "Reservists – Economic Party": .03, "The Haredi Public": .005}
NB = ["Likud", "Otzma Yehudit", "Shas", "United Torah Judaism", "Religious Zionist Party", "Noam"]
CH = ["Yashar", "Bennett 2026 + Yesh Atid", "The Democrats", "Yisrael Beytenu"]


def synthetic_draws(n=500, seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    names = list(VOTE)
    base = np.array([VOTE[c] for c in names])
    nb = np.isin(names, NB)
    ch = np.isin(names, CH)
    rows = []
    for _ in range(n):
        v = base * np.exp(rng.normal(0, 0.2, len(base)))
        swing = rng.normal(0, 0.06)
        v = v + swing * (np.where(nb, v, 0) / v[nb].sum() - np.where(ch, v, 0) / v[ch].sum())
        v = np.clip(v, 0, None)
        v = v / v.sum()
        passed = v >= sim.THRESHOLD
        seats = np.zeros(len(v), dtype=int)
        seats[passed] = sim.dhondt(v[passed], 120)
        rows.append(seats)
    d = pd.DataFrame(rows, columns=names)
    assert (d.sum(axis=1) == 120).all()
    return d


@pytest.fixture(scope="module")
def draws():
    return synthetic_draws()


def behaviour(**over):
    b = dict(gf.BEHAVIOR)
    b.update(over)
    return b


_ALPHA = gf.resolution_posterior()
# Post-deadlock stage (s.49): off; on with the shipped gate re-draws; on with
# the s.56 resolution-by-record variant (STAGE_RESOLUTION "record", not
# shipped) at the record's mean type shares. 0.3125 = the record's
# Beta(2.5, 5.5) mean.
STAGES = {"off": {"repeat_deadlock": None},
          "gates": {"repeat_deadlock": 0.3125},
          "record": {"repeat_deadlock": 0.3125,
                     "resolution_shares": tuple(_ALPHA / _ALPHA.sum())}}


@pytest.mark.parametrize("stage", STAGES)
def test_outcome_codes_and_pm_names(draws, stage):
    prng = np.random.default_rng(gf.SEED + 7)
    allowed_pm = set(gf.PM_NAMES[:-1]) | {gf.PM_OTHER_UNITY, gf.PM_OTHER, "Netanyahu",
                                          "none (repeat election)"}
    seen = set()
    for m in range(30):
        b = gf.draw_behavior(prng)
        b.update(STAGES[stage])
        oc, pm = gf.simulate_formation(draws, b, seed=gf.SEED + m, pm_alloc=gf.draw_pm_alloc(prng))
        assert oc.shape == (len(draws),)
        assert set(np.unique(oc)) <= set(range(len(gf.OUTCOMES)))
        assert set(pm) <= allowed_pm
        assert ((pm == "Netanyahu") == np.isin(oc, [0, 1, 9])).all()
        assert ((pm == "none (repeat election)") == (oc == 7)).all()
        seen |= set(np.unique(oc).tolist())
    assert len(gf.OUTCOMES) == 10 and set(gf.OUTCOME_GROUP) == set(range(10))
    assert seen >= {0, 1, 2, 3, 7, 9}


def test_every_branch_is_reachable(draws):
    """With the gates opened wide, all ten outcomes occur."""
    seen = set()
    for seed, over in enumerate([dict(shas_defects=.9, utj_defects=.9),
                                 dict(likud_sans_bibi=.95, centre_defects=.0),
                                 dict(jl_supports=1.0, raam_supports=1.0, liberman_minority_ok=1.0),
                                 dict(raam_joins=1.0), dict(centre_defects=.9)]):
        oc, _ = gf.simulate_formation(draws, behaviour(**over), seed=seed)
        seen |= set(np.unique(oc).tolist())
    assert seen == set(range(10))


def member_of(name):
    cols, member, support = gf.simulate_formation.last_member
    return member[:, cols.index(name)], support[:, cols.index(name)]


RECORD_YB_BUG = (
    "BUG (s.56 resolution-by-record path, STAGE_RESOLUTION='record', not shipped): "
    "type 4's reachability counts Yisrael Beytenu's seats whatever "
    "liberman_haredi_ok is, and the detail draw then sets lib_haredi=True in every "
    "deadlock that needs YB to reach 61. At liberman_haredi_ok=0 no detail "
    "combination has positive weight, and _pick's zero-row fallback takes the last "
    "column (shas, utj, lib_haredi all True), a combination of probability zero. "
    "On the synthetic draws, 77 draws end in outcome 4 and the 32 that need YB seat him "
    "at liberman_haredi_ok = 0, 1e-6 and 0.2 alike: Liberman's veto has no effect on "
    "this path. The shipped 'gates' path is unaffected.")


@pytest.mark.parametrize("stage", ["off", "gates",
                                   pytest.param("record", marks=pytest.mark.xfail(
                                       strict=True, reason=RECORD_YB_BUG))])
def test_yisrael_beytenu_never_sits_in_outcome_4_without_lib_haredi(draws, stage):
    """Liberman's haredi veto: in a change coalition with a haredi party
    (outcome 4) Yisrael Beytenu sits only when lib_haredi fired."""
    b = behaviour(shas_defects=.9, utj_defects=.9, liberman_haredi_ok=0.0, **STAGES[stage])
    oc, _ = gf.simulate_formation(draws, b, seed=3)
    yb, _ = member_of("Yisrael Beytenu")
    assert (oc == 4).sum() > 10
    assert not yb[oc == 4].any()
    # control: with the veto lifted YB sits in every outcome-4 government it has seats for
    b = behaviour(shas_defects=.9, utj_defects=.9, liberman_haredi_ok=1.0, **STAGES[stage])
    oc, _ = gf.simulate_formation(draws, b, seed=3)
    yb, _ = member_of("Yisrael Beytenu")
    has = draws["Yisrael Beytenu"].values > 0
    assert ((oc == 4) & has).sum() > 10
    assert yb[(oc == 4) & has].all()


@pytest.mark.parametrize("stage", STAGES)
def test_likud_sits_in_netanyahu_and_unity_governments(draws, stage):
    b = behaviour(likud_sans_bibi=.9, centre_defects=.5, **STAGES[stage])
    oc, _ = gf.simulate_formation(draws, b, seed=5)
    likud, _ = member_of("Likud")
    for code in (0, 1, 9, 6):
        assert (oc == code).any(), code
        assert likud[oc == code].all(), code
    # and nowhere else
    assert not likud[np.isin(oc, [2, 3, 4, 5, 7, 8])].any()


@pytest.mark.parametrize("stage", STAGES)
def test_the_pledge_breaker_is_never_named(draws, stage):
    """Outcome 9 (a change-bloc list joins Netanyahu): the record says that
    one happens, not which, so no change-bloc list is credited."""
    b = behaviour(centre_defects=.8, **STAGES[stage])
    oc, _ = gf.simulate_formation(draws, b, seed=9)
    nine = oc == 9
    assert nine.sum() > 10
    for name in gf.CENTRE:
        m, s = member_of(name)
        assert not m[nine].any(), name
        assert not s[nine].any(), name
    for name in (gf.RAAM, gf.JOINT_LIST):
        m, s = member_of(name)
        assert not (m[nine] | s[nine]).any(), name


def _pre_s52_module():
    """government_formation with the s.52 split undone: the pledge-break
    branch writes outcome 1 again, as it did before 16 Oct (the only change
    s.52 made to the tree's outcomes; compare 63b74b8^)."""
    path = Path(gf.__file__)
    src = path.read_text(encoding="utf-8")
    target = "outcome[(uu[:, 6] < p_defect) & feasible] = 9"
    assert src.count(target) == 1, "the pledge-break assignment moved: update this test"
    src = src.replace(target, "outcome[(uu[:, 6] < p_defect) & feasible] = 1")
    mod = types.ModuleType("government_formation_pre_s52")
    mod.__file__ = str(path)
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


@pytest.mark.parametrize("stage", ["off", "gates"])
def test_p_repeat_unchanged_by_the_s52_split(draws, stage):
    """Splitting outcome 9 out of outcome 1 relabels draws and nothing else:
    the repeat-election draws, every other outcome and the PM are identical,
    for the central behaviour and for behaviour vectors drawn as main() does.
    (The s.56 record variant draws type 9 directly and has no pre-s.52 form.)"""
    old = _pre_s52_module()
    prng = np.random.default_rng(gf.SEED + 7)
    for m in range(25):
        b = gf.draw_behavior(prng) if m else dict(gf.BEHAVIOR)
        b.update(STAGES[stage])
        pa = gf.draw_pm_alloc(prng)
        new_oc, new_pm = gf.simulate_formation(draws, b, seed=gf.SEED + m, pm_alloc=pa)
        old_oc, old_pm = old.simulate_formation(draws, b, seed=gf.SEED + m, pm_alloc=pa)
        assert ((new_oc == 7) == (old_oc == 7)).all()
        assert (new_oc == 7).mean() == (old_oc == 7).mean()
        keep = new_oc != 9
        assert (new_oc[keep] == old_oc[keep]).all()
        assert (old_oc[~keep] == 1).all()
        assert (new_pm == old_pm).all()


def test_main_writes_the_membership_rows(tmp_path, monkeypatch, draws):
    """main() on the synthetic draws: outcome probabilities sum to one, the
    groups add up, and the pledge-breaker appears only as its own unnamed
    row, equal to P(outcome 9)."""
    monkeypatch.setattr(gf, "load_draws", lambda: draws.copy())
    gf.main(out_dir=tmp_path)
    form = pd.read_csv(tmp_path / "government_formation.csv")
    assert len(form) == 10 and abs(form["probability"].sum() - 1) < 0.01
    groups = pd.read_csv(tmp_path / "government_groups.csv").set_index("group")["probability"]
    p = form.set_index("outcome")["probability"]
    nb = p[gf.OUTCOMES[0]] + p[gf.OUTCOMES[1]] + p[gf.OUTCOMES[9]]
    assert abs(groups["netanyahu"] - nb) < 0.003
    assert abs(groups["repeat"] - p[gf.OUTCOMES[7]]) < 0.002
    mem = pd.read_csv(tmp_path / "government_membership.csv").set_index("list")
    row = mem.loc["(a change-bloc list joining Netanyahu)", "p_in_government"]
    assert abs(row - p[gf.OUTCOMES[9]]) < 0.002
    assert set(gf.CENTRE) <= set(mem.index)
    assert (mem["p_in_government"].dropna() <= 1).all()
