"""The post-election scorecard (src/scorecard.py).

Proper-score maths on known distributions; the freeze and its sha256; the
result readers; a rehearsal on 2022 (a freeze rebuilt from the harness's
2022 eve projection, scored against the official 2022 result, reproduces
the record's 2022 row); the 2026 freeze from the published files; and the
owner's content rules on the built pages.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

import election_night as en
import scorecard as sc
import site_checks as chk


# --- proper scores on known distributions ------------------------------------

def brute_crps(lo, p, y):
    """E|X - y| - E|X - X'| / 2 (Gneiting & Raftery's kernel form)."""
    k = np.arange(lo, lo + len(p))
    return float((p * np.abs(k - y)).sum()
                 - 0.5 * (p[:, None] * p[None, :] * np.abs(k[:, None] - k[None, :])).sum())


def test_point_mass():
    lo, p = sc.pmf_probs(sc.point_mass(7))
    assert sc.log_score(lo, p, 7, 1e-4) == 0.0
    assert sc.log_score(lo, p, 9, 1e-4) == pytest.approx(math.log(1e-4))
    for y in (0, 5, 7, 12):
        assert sc.crps(lo, p, y) == pytest.approx(abs(7 - y))      # CRPS of a certain forecast = |error|
    assert (sc.pit(lo, p, 6), sc.pit(lo, p, 7), sc.pit(lo, p, 8)) == (0.0, 0.5, 1.0)


def test_crps_matches_the_kernel_form():
    rng = np.random.default_rng(1)
    for _ in range(20):
        lo = int(rng.integers(0, 10))
        p = rng.dirichlet(np.ones(int(rng.integers(1, 15))))
        for y in (0, lo, lo + len(p) // 2, lo + len(p) + 3, 40):
            assert sc.crps(lo, p, y) == pytest.approx(brute_crps(lo, p, y), abs=1e-12)


def test_counts_and_probabilities_give_the_same_pmf():
    a = sc.pmf_probs([3, 2, 5, 3])
    b = sc.pmf_probs([3, 0.2, 0.5, 0.3])
    assert a[0] == b[0] == 3 and np.allclose(a[1], b[1])


def test_log_score_and_crps_are_proper():
    """The expected score under the truth q is best when the forecast is q
    (strictly, for these alternatives)."""
    q = np.array([0.1, 0.2, 0.4, 0.2, 0.1])
    alts = [np.array([0.2, 0.2, 0.2, 0.2, 0.2]), np.array([0.05, 0.15, 0.6, 0.15, 0.05]),
            np.array([0.0, 0.1, 0.3, 0.4, 0.2]), np.roll(q, 1)]

    def exp_score(fn, p):
        return sum(q[y] * fn(0, p, y) for y in range(len(q)))

    log = lambda lo, p, y: sc.log_score(lo, p, y, 1e-9)
    for p in alts:
        assert exp_score(log, q) > exp_score(log, p)
        assert exp_score(sc.crps, q) < exp_score(sc.crps, p)


def test_mid_pit_has_mean_one_half_under_the_forecast():
    rng = np.random.default_rng(2)
    for _ in range(10):
        p = rng.dirichlet(np.ones(9))
        assert sum(p[y] * sc.pit(0, p, y) for y in range(9)) == pytest.approx(0.5)


def test_binary_scores():
    assert sc.brier(0.7, True) == pytest.approx(0.09)
    assert sc.brier(0.7, False) == pytest.approx(0.49)
    assert sc.binary_log(0.7, False) == pytest.approx(math.log(0.3))
    assert sc.binary_log(0.0, True) == pytest.approx(math.log(sc.FLOOR_P))   # published 0.000


def test_self_expectation_is_the_expected_score():
    m = {"n_sims": 4, "pmf": {"a": [2, 1, 2, 1], "b": [0, 3, 1]}, "central": {"a": 3, "b": 0},
         "interval": {"a": [2, 4], "b": [0, 0]}, "blocs": {"nb": 0.3}}
    e = sc.self_expectation(m, ["a", "b"])
    pa, pb = np.array([.25, .5, .25]), np.array([.75, .25])
    log = (np.sum(pa * np.log(pa)) + np.sum(pb * np.log(pb))) / 2
    crps = (sum(pa[i] * brute_crps(2, pa, 2 + i) for i in range(3))
            + sum(pb[i] * brute_crps(0, pb, i) for i in range(2))) / 2
    assert e["log"]["mean"] == pytest.approx(log, abs=1e-4)
    assert e["crps"]["mean"] == pytest.approx(crps, abs=1e-4)
    assert e["abs_err"]["mean"] == pytest.approx((0.5 + 0.25) / 2, abs=1e-4)
    assert e["coverage"]["mean"] == pytest.approx((1 + 0.75) / 2, abs=1e-4)
    assert e["brier"]["mean"] == pytest.approx((0 + 0.25 * 0.75) / 2, abs=1e-4)
    assert e["nb_brier"]["mean"] == pytest.approx(0.21)


def test_record_pmf_is_a_distribution_matching_the_summaries():
    lo, p = sc.record_pmf(mean=12.0, median=12, p05=8, p95=16, p_pass=1.0)
    k = np.arange(lo, lo + len(p))
    assert p.sum() == pytest.approx(1) and (k * p).sum() == pytest.approx(12, abs=0.3)
    F = np.cumsum(p)
    assert k[np.searchsorted(F, 0.05)] in (7, 8, 9) and k[np.searchsorted(F, 0.95)] in (15, 16, 17)
    lo, p = sc.record_pmf(mean=3.0, median=4, p05=0, p95=8, p_pass=0.55)
    assert p[0] == pytest.approx(0.45) and p[1:4].sum() == 0      # nothing between 0 and 4 seats


# --- freeze and sha256 -----------------------------------------------------------

def test_frozen_file_verifies_and_detects_tampering(tmp_path):
    payload = sc.frozen_2022()
    path, sha = sc.write_frozen(payload, tmp_path / "frozen.json")
    doc, _ = sc.load_frozen(path)
    assert doc["sha256"] == sha and sc.verify_doc(doc)
    assert sc.payload_sha256(json.loads(json.dumps(doc["payload"]))) == sha   # key order irrelevant
    k = next(iter(doc["payload"]["models"][0]["pmf"]))
    doc["payload"]["models"][0]["pmf"][k][1] += 1                               # one draw moved
    assert not sc.verify_doc(doc)


# --- the 2022 rehearsal ------------------------------------------------------------

@pytest.fixture(scope="module")
def rehearsal(tmp_path_factory):
    payload = sc.frozen_2022()
    res = sc.read_result(sc.result_2022_csv(tmp_path_factory.mktemp("r") / "r.csv"), payload)
    return payload, res, sc.score_frozen(payload, res["seats"], government="netanyahu", pm="Netanyahu")


def test_rehearsal_result_is_the_official_2022_knesset(rehearsal):
    payload, res, scores = rehearsal
    assert sum(res["seats"].values()) == 120
    assert {k: v for k, v in res["seats"].items() if v} == {
        "likud": 32, "yesh_atid": 24, "rzp": 14, "blue_white": 12, "shas": 11, "utj": 7,
        "yisrael_beytenu": 6, "raam": 5, "hadash_taal": 5, "labor": 4}
    assert scores["blocs_actual"]["nb"] == 64


def test_rehearsal_reproduces_the_records_2022_row(rehearsal):
    """Scored against the official result, the freeze rebuilt from the
    harness's 2022 eve projection gives back the record's own 2022 scores."""
    payload, res, scores = rehearsal
    rec = sc.record_expectations()["cycles"]["2022"]
    s = scores["models"][0]["summary"]
    assert s["n"] == rec["n"] == 13
    assert s["abs_err"] == pytest.approx(rec["abs_err"], abs=1e-4)
    assert s["coverage"] == rec["coverage"] == 1.0
    assert s["brier"] == pytest.approx(rec["brier"], abs=2e-4)
    assert s["log"] == pytest.approx(rec["log"], abs=0.01)
    assert s["crps"] == pytest.approx(rec["crps"], abs=0.01)
    nb = scores["models"][0]["blocs"]["nb"]
    assert nb["o"] is True and nb["brier"] == pytest.approx((1 - 0.684) ** 2, abs=1e-4)
    assert scores["models"][0]["formation"] is None                # no 2022 formation probabilities
    assert payload["record"]["excluded"] == ["2022"] and "2022" not in payload["record"]["cycles"]


def test_rehearsal_accepts_the_election_night_final_count(rehearsal, tmp_path):
    """election_night.py's page data for the final 2022 count scores the same."""
    payload, res, scores = rehearsal
    c = pd.read_csv(en.COUNTS, dtype={"cycle": str})
    c = c[c["cycle"] == "2022"]
    count = en.Count(votes=dict(zip(c["ballot"].str.strip(), c["votes"].astype(int))),
                     level="manual", source="cec_final_counts", fetched_utc="2022-11-03T00:00:00Z")
    p = tmp_path / "election-night.json"
    p.write_text(json.dumps(en.build_payload(count, en.cycle_2022(), mode="rehearsal"),
                            default=en._json_default), encoding="utf-8")
    res2 = sc.read_result(p, payload)
    assert res2["seats"] == res["seats"]
    s2 = sc.score_frozen(payload, res2["seats"], "netanyahu", "Netanyahu")
    assert s2["models"][0]["summary"] == scores["models"][0]["summary"]


def test_result_reader_rules(tmp_path):
    payload = sc.frozen_2022()
    good = "list,votes,seats\nLikud,1,32\nפה,1,24\nrzp,1,14\nNational Unity,1,12\nש״ס,1,11\n" \
           "UTJ,1,7\nל,1,6\nRa'am,1,5\nHadash-Taal,1,5\nLabor,1,4\nsmall parties,9,0\nNobody,1,0\n"
    (tmp_path / "ok.csv").write_text(good, encoding="utf-8")
    r = sc.read_result(tmp_path / "ok.csv", payload)
    assert r["seats"]["yesh_atid"] == 24 and r["seats"]["shas"] == 11 and r["unmatched"] == ["Nobody"]
    (tmp_path / "sum.csv").write_text(good.replace("Labor,1,4", "Labor,1,5"), encoding="utf-8")
    with pytest.raises(sc.ScorecardError, match="sum"):
        sc.read_result(tmp_path / "sum.csv", payload)
    (tmp_path / "unk.csv").write_text(good.replace("Labor,1,4", "Labour Party,1,4"), encoding="utf-8")
    with pytest.raises(sc.ScorecardError, match="matches no forecast list"):
        sc.read_result(tmp_path / "unk.csv", payload)


def test_ranking_and_floors():
    """Two synthetic models on one list: the sharper correct one ranks first; a
    count no draw reached is scored at half a draw; formation and PM are
    scored by log score with the published-zero floor."""
    payload = {"lists": {"a": {"share": 0.5, "bloc": "nb"}, "b": {"share": 0.5, "bloc": "anti"}},
               "raam": None, "rules": sc.RULES, "record": {},
               "models": [
                   {"id": "wide", "n_sims": 10, "pmf": {"a": [58, 5, 5], "b": [60, 5, 5]},
                    "central": {"a": 58, "b": 60}, "interval": {"a": [58, 59], "b": [60, 61]},
                    "blocs": {"nb": 0.2, "anti": 0.5}, "groups": {"netanyahu": 0.25, "change": 0.75},
                    "pm": [["Eisenkot", 1.0]]},
                   {"id": "sharp", "n_sims": 10, "pmf": {"a": [59, 10], "b": [61, 10]},
                    "central": {"a": 59, "b": 61}, "interval": {"a": [59, 59], "b": [61, 61]},
                    "blocs": {"nb": 0.0, "anti": 1.0}, "groups": {"change": 1.0}, "pm": [["Eisenkot", 1.0]]}]}
    s = sc.score_frozen(payload, {"a": 59, "b": 61}, government="netanyahu", pm="Netanyahu")
    assert s["ranking"] == ["sharp", "wide"]
    wide = next(m for m in s["models"] if m["id"] == "wide")
    assert wide["lists"]["b"]["log"] == pytest.approx(math.log(0.5), abs=1e-4)
    assert s["blocs_actual"] == {"nb": 59, "anti": 61, "antiRaam": 61}
    s2 = sc.score_frozen(payload, {"a": 57, "b": 63})
    sharp = next(m for m in s2["models"] if m["id"] == "sharp")
    assert sharp["lists"]["a"]["log"] == pytest.approx(math.log(0.5 / 10), abs=1e-4)
    sharp = next(m for m in s["models"] if m["id"] == "sharp")
    assert sharp["formation"]["log"] == pytest.approx(math.log(sc.FLOOR_P), abs=1e-4)
    assert sharp["pm"]["log"] == pytest.approx(math.log(sc.FLOOR_P), abs=1e-4)
    assert wide["formation"]["log"] == pytest.approx(math.log(0.25), abs=1e-4)
    with pytest.raises(sc.ScorecardError):
        sc.score_frozen(payload, {"a": 59, "b": 61}, government="coalition")


def test_rehearsal_page_follows_the_owner_rules(tmp_path):
    page = sc.rehearse("2022", out=tmp_path / "sc.html")
    html = (tmp_path / "sc.html").read_text(encoding="utf-8")
    assert page["frozen"]["sha256"] in html
    assert chk.check_hebrew_seats(html) == [] and chk.check_others(html) == []
    assert "מנדטים" in html
    if chk.find_node():
        assert chk.check_js(html) == []


# --- 2026 ---------------------------------------------------------------------------

def _has_pmfs(root) -> bool:
    p = root / "data" / "processed" / "model_variants.json"
    return p.exists() and all("pmf" in v for v in json.loads(p.read_text(encoding="utf-8"))["variants"])


def test_2026_freeze_is_the_published_forecast(root):
    if not _has_pmfs(root):
        pytest.skip("model_variants.json has no seat pmfs (python src/build_variants.py)")
    p = sc.build_frozen_2026()
    ids = [m["id"] for m in p["models"]]
    mv = json.loads((root / "data" / "processed" / "model_variants.json").read_text(encoding="utf-8"))
    assert ids == [v["id"] for v in mv["variants"]] and ids[0] == "official"
    draws = pd.read_parquet(root / "data" / "processed" / "mixture_draws.parquet")
    off = p["models"][0]
    for name, spec in off["pmf"].items():                  # exact: the published draws
        v = draws[name].to_numpy()
        assert spec[0] == v.min() and spec[1:] == np.bincount(v - v.min()).tolist()
    mb = pd.read_csv(root / "data" / "processed" / "mixture_blocs.csv").iloc[0]
    assert off["blocs"]["nb"] == mb.p_nb_61 and off["blocs"]["anti"] == mb.p_anti_61
    for m in p["models"]:
        assert all(sum(s[1:]) == m["n_sims"] for s in m["pmf"].values())
        assert set(sc.GROUPS) <= set(m["groups"]) and m["pm"]
    # the official central count as the "result": no count error for the official model
    seats = {k: v for k, v in off["central"].items() if v}
    s = sc.score_frozen(p, seats)
    assert next(m for m in s["models"] if m["id"] == "official")["summary"]["abs_err"] == 0
    assert sc.BLACKOUT_FROM.isoformat() == "2026-10-23"


def test_committed_freeze_and_page(root):
    files = sorted((root / "data" / "processed").glob("frozen_forecast_*.json"))
    if not files:
        pytest.skip("no frozen forecast committed yet (python src/scorecard.py --freeze)")
    doc, path = sc.load_frozen()
    assert sc.verify_doc(doc), f"{path}: sha256 mismatch"
    page = root / "output" / "site" / "scorecard.html"
    html = page.read_text(encoding="utf-8")
    data = json.loads((root / "output" / "site" / "scorecard.json").read_text(encoding="utf-8"))
    assert data["frozen"]["sha256"] in html and data["frozen"]["verified"]
    assert chk.check_hebrew_seats(html) == [] and chk.check_others(html) == []
    if chk.find_node():
        assert chk.check_js(html) == []


def test_final_poll_comparison(root):
    page = root / "output" / "site" / "scorecard.json"
    data = json.loads(page.read_text(encoding="utf-8")) if page.exists() else {}
    if not data.get("result") or not (root / "data" / "processed" / "polls.csv").exists():
        pytest.skip("no scored 2026 page")
    pc = sc.poll_comparison(data["frozen"]["payload"], data["result"]["seats"])
    y, off = pc["result"], data["frozen"]["payload"]["models"][0]
    model = next(r for r in pc["rows"] if r["kind"] == "model")
    assert model["seats"] == {k: off["central"].get(k, 0) for k in pc["lists"]}
    assert model["err"] == sum(abs(model["seats"][k] - y[k]) for k in y)
    polls = [r for r in pc["rows"] if r["kind"] != "model"]
    assert len(polls) == pc["n_polls"] and all(sum(r["seats"].values()) == 120 for r in polls)
    assert [r["err"] for r in pc["rows"]] == sorted(r["err"] for r in pc["rows"])
    assert all(r["share_mae"] is not None for r in pc["rows"] + [pc["average"]])
    for k in pc["lists"]:                                   # the reference row averages the polls
        assert pc["average"]["seats"][k] == pytest.approx(np.mean([r["seats"][k] for r in polls]), abs=0.05)
    import build_insights as bi                              # the insights page grades them the same way
    rk = bi.ranking(bi.final_polls(bi._polls()), data)
    assert sorted(r["err"] for r in rk["rows"]) == [r["err"] for r in pc["rows"]]
    assert data["polls"]["rows"] == pc["rows"], "rebuild the page: python src/scorecard.py --page"


def test_blackout_matches_the_projection_and_pages_are_published():
    import bayes_model as bm
    import pipeline
    assert sc.BLACKOUT_DAYS == bm.EVENT_BLACKOUT_DAYS
    assert {"scorecard.html", "scorecard.json"} <= set(pipeline.SUPPORTING_FILES)
