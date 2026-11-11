"""The post-election formation tracker (src/formation_tracker.py, dossier s.74)."""
import math

import pytest

import formation_tracker as ft
import government_formation as gf


def test_ledger_items_are_well_formed():
    pri = ft.priors()
    for e in ft.LEDGER:
        assert e["param"] in pri, e["param"]
        assert e["dir"] in (+1, -1)
        assert e["strength"] in ft.STRENGTH
        assert e["src"] in ft.SRC and ft.SRC[e["src"]].startswith("https://")
        assert e["en"] and e["he"] and "מושבים" not in e["he"]
        assert e["date"] <= ft.AS_OF


def test_posterior_is_the_prior_moved_on_the_odds_scale():
    post = ft.posterior()
    # liberman_haredi_ok: 0.20 with one strong and one moderate item up: odds 0.25 x 5 x 2.5
    assert post["liberman_haredi_ok"]["posterior"] == pytest.approx(3.125 / 4.125, abs=1e-4)
    # an empty ledger leaves every prior where it was
    for k, v in ft.posterior(ledger=[]).items():
        assert v["posterior"] == pytest.approx(v["prior"], abs=1e-4)
    # direction: every parameter moves the way its net evidence points
    for k, v in post.items():
        assert math.copysign(1, v["posterior"] - v["prior"]) == math.copysign(1, v["log_odds_shift"])


def test_the_certified_knesset():
    seats = ft.knesset()
    assert sum(seats.values()) == 120
    assert seats["Likud"] == 27 and seats["Yashar"] == 21 and seats["Shas"] == 6
    assert sum(seats[k] for k in gf.CENTRE) == 48


def test_the_tree_state_is_restored():
    before = (dict(gf.BEHAVIOR), dict(gf.BEHAVIOR_NEFF), {k: list(v) for k, v in gf.PM_ALLOC.items()},
              gf.STAGE_RESOLUTION)
    with ft.tree(behavior={"utj_defects": 0.9}, neff={"shas_defects": 6}, pm_alloc={4: ft.MANDATE_PM},
                 resolution="mix"):
        assert gf.BEHAVIOR["utj_defects"] == 0.9 and gf.STAGE_RESOLUTION == "mix"
    assert (dict(gf.BEHAVIOR), dict(gf.BEHAVIOR_NEFF), {k: list(v) for k, v in gf.PM_ALLOC.items()},
            gf.STAGE_RESOLUTION) == before


def test_the_ledger_moves_the_tree_towards_the_route_being_negotiated(monkeypatch):
    monkeypatch.setattr(ft, "VECTORS", 40)
    frame = ft.knesset_frame(ft.knesset(), n=1500)
    base = ft.run(frame)
    b, n = ft.updated_behavior(ft.posterior())
    now = ft.run(frame, behavior=b, neff=n, pm_alloc={4: ft.MANDATE_PM})
    for r in (base, now):
        assert sum(v[0] for g, v in r["groups"].items() if g != "netanyahu_in_office") == pytest.approx(1, abs=0.01)
    oc = lambda r: dict((o, p) for o, p in r["outcomes"])
    haredi = "Change coalition with a haredi party"
    assert oc(base)[haredi] < 0.05 < 0.20 < oc(now)[haredi]
    # 48 change-bloc seats: no change government without a partner, no Netanyahu majority
    assert oc(now)["Change coalition (without Ra'am)"] == 0 and oc(now)["Netanyahu rightist coalition"] == 0
    # the deadlock stage keeps the repeat election on the record's rate, whatever the ledger says
    assert abs(base["groups"]["repeat"][0] - now["groups"]["repeat"][0]) < 0.05
