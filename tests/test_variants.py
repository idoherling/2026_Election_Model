"""The model explorer: src/model_variants.py (registry, flag context manager)
and src/build_variants.py (the variants through the production chain).

The chain test runs the official variant on the production posterior
(data/processed/m3_idata.nc, not in git; skipped without it), about 10 s.
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import pytest

import bayes_model as bm
import government_formation as gf
import model_variants as mv
import site_checks as chk


# --- the flag context manager ------------------------------------------------

def test_variant_flags_apply_and_restore():
    before = (bm.RESID_SPACE, bm.T_UNIT_VAR, bm.RESID_SCALE, gf.POST_DEADLOCK_STAGE)
    flags = {"bayes_model": {"RESID_SPACE": "vote", "T_UNIT_VAR": not bm.T_UNIT_VAR,
                             "RESID_SCALE": 0.123},
             "government_formation": {"POST_DEADLOCK_STAGE": not gf.POST_DEADLOCK_STAGE}}
    with mv.variant_flags(flags):
        assert bm.RESID_SPACE == "vote" and bm.RESID_SCALE == 0.123
        assert bm.T_UNIT_VAR is (not before[1])
        assert gf.POST_DEADLOCK_STAGE is (not before[3])
    assert (bm.RESID_SPACE, bm.T_UNIT_VAR, bm.RESID_SCALE, gf.POST_DEADLOCK_STAGE) == before


def test_variant_flags_restore_after_an_exception():
    before = (bm.RESID_SPACE, bm.TRAIL_ON)
    with pytest.raises(RuntimeError):
        with mv.variant_flags({"bayes_model": {"RESID_SPACE": "hybrid", "TRAIL_ON": False}}):
            assert bm.TRAIL_ON is False
            raise RuntimeError("boom")
    assert (bm.RESID_SPACE, bm.TRAIL_ON) == before


def test_unknown_flag_raises_before_anything_changes():
    before = bm.RESID_SPACE
    with pytest.raises(AttributeError):
        with mv.variant_flags({"bayes_model": {"RESID_SPACE": "vote", "NO_SUCH_FLAG_XYZ": 1}}):
            pass
    assert bm.RESID_SPACE == before and not hasattr(bm, "NO_SUCH_FLAG_XYZ")


def test_nested_contexts_unwind_in_order():
    before = bm.RESID_SPACE
    with mv.variant_flags({"bayes_model": {"RESID_SPACE": "vote"}}):
        with mv.variant_flags({"bayes_model": {"RESID_SPACE": "hybrid"}}):
            assert bm.RESID_SPACE == "hybrid"
        assert bm.RESID_SPACE == "vote"
    assert bm.RESID_SPACE == before


# --- the registry -------------------------------------------------------------

def test_registry_shape():
    ids = [v.id for v in mv.VARIANTS]
    assert len(ids) == len(set(ids)) and ids[0] == "official"
    assert all(re.fullmatch(r"[a-z0-9_]+", i) for i in ids)
    off = mv.get("official")
    # the official variant is production as committed: no override at all
    assert off.resolved_flags() == {} and off.status == "official"
    for v in mv.VARIANTS:
        assert v.desc_en and v.desc_he and v.name_en and v.name_he
        assert set(v.backtest) == set(mv.BASIS["horizons"])
        for row in v.backtest.values():
            assert row is None or set(row) == set(mv.BASIS["metrics"])


def test_texts_follow_the_house_rules(root):
    reg = json.loads((root / "data" / "forecast_sources.json").read_text(encoding="utf-8"))
    ids = {s["id"] for s in reg} | {a for s in reg for a in s.get("aliases", [])}
    sections = chk.dossier_sections()
    for v in mv.VARIANTS:
        if not mv.available(v)[0]:
            continue       # a placeholder cites the section its own work adds
        assert mv.cited_ids(v) <= ids, (v.id, mv.cited_ids(v) - ids)
        assert mv.dl_sections(v) <= sections, v.id
        assert "מושבים" not in v.desc_he + v.verdict_he
        assert not re.search(r"\bOthers\b", v.desc_en + v.verdict_en)
    for txt in (mv.BASIS["en"], mv.BASIS["he"]):
        assert {int(n) for n in re.findall(r"#s(\d+)", txt)} <= sections


def test_a_placeholder_appears_once_its_flag_exists(monkeypatch):
    h = mv.get("hierarchical")
    if hasattr(bm, "ERROR_MODEL"):
        assert mv.available(h)[0]
        return
    ok, why = mv.available(h)
    assert not ok and "ERROR_MODEL" in why
    monkeypatch.setattr(bm, "ERROR_MODEL", None, raising=False)
    assert mv.available(h) == (True, "")


def test_the_stack_runs_in_the_configuration_s62_graded():
    st = mv.get("stacked")
    if not hasattr(bm, "ERROR_STACK_WEIGHTS"):
        assert not mv.available(st)[0]
        return
    f = st.resolved_flags()["bayes_model"]
    assert f["ERROR_STACK"] == bm.ERROR_STACK_WEIGHTS
    assert f["RESID_SPACE"] == "seat" and f["T_UNIT_VAR"] is False


# --- the built file -------------------------------------------------------------

@pytest.fixture(scope="module")
def built(root):
    p = root / "data" / "processed" / "model_variants.json"
    if not p.exists():
        pytest.skip("data/processed/model_variants.json not built (python src/build_variants.py)")
    return json.loads(p.read_text(encoding="utf-8"))


def test_official_variant_reproduces_the_published_headline(built, root):
    """Same code, posterior and seed: the mixture's bloc odds and the central
    count are the published ones exactly; the formation run (fewer parameter
    vectors) sits within Monte Carlo noise, and its paired figure is the
    published one."""
    proc = root / "data" / "processed"
    off = next(v for v in built["variants"] if v["id"] == "official")
    mb = pd.read_csv(proc / "mixture_blocs.csv").iloc[0]
    for k, col in (("nb", "p_nb_61"), ("anti", "p_anti_61"), ("antiRaam", "p_anti_raam_61"),
                   ("neither", "p_neither"), ("nb_mean", "nb_mean")):
        assert off["blocs"][k] == pytest.approx(float(mb[col]), abs=1e-9), k
    pub = pd.read_csv(proc / "official_forecast.csv")
    assert {r["name"]: r["seats"] for r in off["lists"]} == dict(zip(pub["list"], pub["central_seats"]))
    gg = pd.read_csv(proc / "government_groups.csv").set_index("group")["probability"]
    for g, p in gg.items():
        assert off["groups_paired"][g] == pytest.approx(float(p), abs=1e-9)
        tol = max(3 * off["groups_se"][g], 0.01)
        assert abs(off["groups"][g][0] - float(p)) <= tol, g
    assert built["check"]["ok"] is True
    assert built["settings"]["formation_vectors"] < built["settings"]["production_vectors"]


def test_every_variant_is_a_complete_forecast(built):
    for v in built["variants"]:
        assert sum(r["seats"] for r in v["lists"]) == 120, v["id"]
        b = v["blocs"]
        assert 0 <= b["nb"] <= 1 and 0 <= b["neither"] <= 1
        assert b["anti"] <= b["antiRaam"] + 1e-9        # Ra'am only adds seats
        assert sum(v["groups"][g][0] for g in ("netanyahu", "change", "unity", "repeat")) \
            == pytest.approx(1, abs=0.005)
        assert all(r["lo"] <= r["hi"] for r in v["lists"])


@pytest.mark.skipif(not (mv.PROCESSED / "m3_idata.nc").exists(),
                    reason="production posterior data/processed/m3_idata.nc not present")
def test_the_chain_reproduces_the_official_mixture(tmp_path, root):
    """The official variant through registration_scenarios / official_forecast
    with outputs redirected: identical to the committed mixture and central
    count, and nothing written to data/processed."""
    import io
    import build_variants as bv
    proc = root / "data" / "processed"
    stamp = {p.name: p.stat().st_mtime for p in proc.glob("*.csv")}
    res = bv.run_bayes({}, tmp_path / "official", 5, io.StringIO())
    mb = pd.read_csv(proc / "mixture_blocs.csv").iloc[0]
    assert res["blocs"]["nb"] == pytest.approx(float(mb["p_nb_61"]), abs=1e-9)
    assert res["blocs"]["neither"] == pytest.approx(float(mb["p_neither"]), abs=1e-9)
    pub = pd.read_csv(proc / "official_forecast.csv")
    assert {r["name"]: r["seats"] for r in res["lists"]} == dict(zip(pub["list"], pub["central_seats"]))
    assert {p.name: p.stat().st_mtime for p in proc.glob("*.csv")} == stamp
    assert (tmp_path / "official" / "mixture_blocs.csv").exists()


def test_formation_loop_reads_the_production_streams():
    """The explorer's loop on synthetic Knessets equals government_formation's
    own per-vector draws: the same parameter vectors and seeds, M at a time."""
    import build_variants as bv
    rng = np.random.default_rng(5)
    cols = gf.NB_CORE + gf.CENTRE + [gf.JOINT_LIST, gf.RAAM, gf.AMCHA, "Blue and White"]
    d = pd.DataFrame(rng.integers(0, 14, size=(300, len(cols))), columns=cols)
    a = bv.formation_summary(d, 4)
    b = bv.formation_summary(d, 4)
    assert a["groups"] == b["groups"] and a["vectors"] == 4
    # vector m uses seed SEED + m and the m-th draw of the SEED + 7 stream: the
    # first vector alone, by hand
    prng = np.random.default_rng(gf.SEED + 7)
    beh, pa = gf.draw_behavior(prng), gf.draw_pm_alloc(prng)
    r = gf.stage_draws(1, gf.POST_DEADLOCK_STAGE)[0]
    if r is not None:
        beh["repeat_deadlock"] = r
    oc, _ = gf.simulate_formation(bv.formation_frame(d), beh, seed=gf.SEED, pm_alloc=pa)
    one = bv.formation_summary(d, 1)
    grp = np.array([["netanyahu", "change", "unity", "repeat"].index(gf.OUTCOME_GROUP[o])
                    for o in range(len(gf.OUTCOMES))])[oc]
    assert one["groups"]["netanyahu"][0] == pytest.approx(round(float((grp == 0).mean()), 3))


# --- the publish check sees the explorer's citations ------------------------------

def test_citations_inside_the_json_payload_are_checked(root):
    sources = chk.load_sources(root / "data" / "forecast_sources.json")
    good = '<script>const D = {"desc":"see <a class=\\"cite\\" data-s=\\"ERR-F24\\"></a>"};</script>'
    bad = good.replace("ERR-F24", "XXX-F99")
    assert "ERR-F24" in chk.cited_ids(good)
    assert chk.check_citations(good, sources) == []
    assert chk.check_citations(bad, sources) != []
