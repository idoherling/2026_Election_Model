"""The insights page (src/build_insights.py, site/insights.html)."""
import json
import re
import shutil
import subprocess

import pytest

import build_insights as bi
import site_checks


@pytest.fixture(scope="module")
def payload():
    return bi.build()


def test_the_result_adds_up(payload):
    r = payload["result"]
    assert sum(b["seats26"] for b in r["blocs"].values()) == 120
    assert sum(b["seats22"] for b in r["blocs"].values()) == 120
    assert sum(x["seats"] for x in r["seats"]) == 120
    assert r["blocs"]["nb"]["seats26"] == 53 and r["blocs"]["arab"]["seats26"] == 19
    assert r["wasted_votes"] == sum(w["votes"] for w in r["wasted"].values())
    assert all(w["share"] < 3.25 for w in r["wasted"].values())


def test_no_poll_reached_the_arab_result(payload):
    a = payload["arab"]
    assert a["max"] < a["result"] and sum(a["hist"].values()) == a["n"]


def test_the_ranking_holds_the_model_and_ten_outlets(payload):
    rk = payload["ranking"]
    assert sum(r["kind"] == "model" for r in rk["rows"]) == 1 and rk["n"] == 10
    model = next(r for r in rk["rows"] if r["kind"] == "model")
    assert model["nb"] == 0 and model["thr"] == 0
    assert rk["rows"] == sorted(rk["rows"], key=lambda r: (r["err"], abs(r["nb"])))
    assert rk["share_mae"]["direct_polls"] < rk["share_mae"]["model"] < rk["share_mae"]["others"][0]


def test_the_agreements_moved_one_seat(payload):
    assert payload["pacts"]["moved"] == {"עם": [7, 8], "שס": [7, 6]}
    assert 0 < payload["pacts"]["closest"] < 10000


def test_the_forecast_sums_to_one(payload):
    pm = payload["next"]["now"]["pm"]
    assert sum(v["p"] for v in pm.values()) == pytest.approx(1, abs=0.02)
    assert all(e["url"].startswith("https://") for e in payload["next"]["ledger"])


def test_the_page_renders_and_follows_the_site_rules(payload):
    html = bi.render(payload)
    assert "__IN_DATA__" not in html and "__EN_TOKENS__" not in html
    assert "מושבים" not in html
    script = re.findall(r"<script>([\s\S]*?)</script>", html)[-1]
    text = script.split("const T = ", 1)[1]
    assert not re.search(r"\bOthers\b", text)
    # the English and Hebrew halves carry the same findings
    ids = re.findall(r'\{id: "(\w+)", nav:', text)
    half = len(ids) // 2
    assert half == 9 and ids[:half] == ids[half:]
    node = site_checks.find_node()
    if node:
        r = subprocess.run([node, "-e", "new Function(require('fs').readFileSync(0,'utf8'))"],
                           input=script, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-400:]


def test_the_next_model_section_reports_the_graded_set(payload):
    """The "model for the next election" section (dossier s.76): the set
    record.NEXT_CONFIG names, passing the rule on nine cycles, with narrower
    intervals and a smaller error than the 2026 configuration."""
    import record
    m = payload["model9"]
    assert m["arm"] == "tramp_AB" and m["passes"]
    assert record.NEXT_CONFIG["harness"]["resid_space"] == "vote" and record.NEXT_CONFIG["harness"]["t_unit"]
    assert (m["n_single"], m["n_sets"]) == (23, 6)
    for hz in ("eve", "D-7", "D-21"):
        assert m["next"][hz]["mean"] < m["cfg"][hz]["mean"] and m["next"][hz]["isc"] < m["cfg"][hz]["isc"]
        assert 0.90 < m["next"][hz]["cov"] <= m["cfg"][hz]["cov"]
    assert -m["const"]["haredi_e0_mean"][1] < -m["const"]["haredi_e0_mean"][0]     # the lift shrinks
    assert m["const"]["arab_reg_k"][1] > m["const"]["arab_reg_k"][0]               # the pass-through grows
    assert m["fold_2026"]["next"]["mean"] < m["fold_2026"]["cfg"]["mean"]
    tpl = bi.TEMPLATE.read_text(encoding="utf-8")
    assert 'id="model"' in tpl and "decision-log.html#s" in tpl and "DATA.model9" in tpl
