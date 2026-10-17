"""Evidence registry: what the site cites is verified.

data/forecast_sources.json and data/forecast_findings.json are built by
src/build_sources.py from the research desks in
data/processed/forecast_research (<desk>.json findings, verify_<desk>.json
verdicts). Only "verified" and "corrected" findings may enter.
"""
from __future__ import annotations

import json

import pytest

import build_sources as bs
import site_checks as chk


@pytest.fixture(scope="module")
def html(root):
    page = root / "output" / "site" / "index.html"
    if not page.exists():
        pytest.skip("output/site/index.html not built")
    return page.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sources(root):
    return chk.load_sources(root / "data" / "forecast_sources.json")


@pytest.fixture(scope="module")
def findings(root):
    return json.loads((root / "data" / "forecast_findings.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verdicts():
    return chk.desk_verdicts()


def test_every_finding_cited_on_the_site_is_verified_or_corrected(html, sources):
    assert chk.check_registry(html, sources) == []


def test_cited_findings_by_their_own_status(html, sources, findings, verdicts):
    """The same claim from the registry's side: every finding behind a cited
    source carries verified/corrected in forecast_findings.json, agreeing
    with its desk verdict."""
    idx = chk.source_index(sources)
    own = chk.own_measurements()
    checked = 0
    for cid in chk.cited_ids(html):
        for f in idx[cid]["findings"]:
            if f in own:
                continue
            assert findings[f]["status"] in chk.OK_VERDICTS, f
            assert findings[f]["status"] == verdicts[f], f
            checked += 1
    assert checked > 100


def test_registry_holds_no_unverified_finding(findings, verdicts):
    bad = {f: v["status"] for f, v in findings.items() if v["status"] not in chk.OK_VERDICTS}
    assert bad == {}
    stale = {f: (v["status"], verdicts.get(f)) for f, v in findings.items()
             if verdicts.get(f) != v["status"]}
    assert stale == {}


def test_decision_log_citations_point_at_sections(sources):
    sections = chk.dossier_sections()
    for s in sources:
        if s["id"].startswith("DL-"):
            assert int(s["url"].rsplit("#s", 1)[1]) in sections, s["id"]


def test_year_suffixes_go_past_ten():
    assert [bs._year_suffix(k) for k in (0, 9, 10, 25, 26, 27)] == ["a", "j", "k", "z", "aa", "ab"]


def test_build_sources_completes(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(bs, "ROOT", tmp_path)        # write the registry elsewhere
    bs.main()
    assert (tmp_path / "data" / "forecast_sources.json").exists()


# Was xfail until 17 Oct: the build_sources suffix IndexError hid the
# polls_beyond_vote findings; fixed (more than ten same-label sources).
def test_registry_holds_every_verified_finding(findings, verdicts):
    missing = sorted(f for f, st in verdicts.items()
                     if st in chk.OK_VERDICTS and f not in findings)
    assert missing == []
