"""Publish checks on the built site, output/site/index.html (src/site_checks.py).

The same checks pipeline.py runs after every build; each one also gets a
negative control on a synthetic page so a check that can never fail is
caught.
"""
from __future__ import annotations

import pytest

import site_checks as chk


@pytest.fixture(scope="module")
def html(root):
    page = root / "output" / "site" / "index.html"
    if not page.exists():
        pytest.skip("output/site/index.html not built (python src/build_site.py)")
    return page.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sources(root):
    return chk.load_sources(root / "data" / "forecast_sources.json")


def test_page_script_parses(html):
    node = chk.find_node()
    if node is None:
        pytest.skip("node not found (set NODE=/path/to/node)")
    assert chk.check_js(html, node) == []


def test_english_and_hebrew_chapter_counts_match(html):
    en, he = chk.chapter_counts(html)
    assert en > 0 and en == he


def test_every_citation_resolves(html, sources):
    assert chk.cited_ids(html), "no citations found"
    assert chk.check_citations(html, sources) == []


def test_hebrew_seats_are_mandatim(html):
    assert "מנדטים" in html
    assert chk.check_hebrew_seats(html) == []


def test_no_others_label(html):
    assert chk.check_others(html) == []


# --- negative controls -----------------------------------------------------

PAGE = ('<div class="chapter">a</div><div class="chapter">b</div>'
        '<a class="cite" data-s="AGG-F01, ERR-F13">1</a>'
        '<script>const HE_CH = [{t:"א"},{t:"ב"}];\nfunction trStatic(){}\n</script>')


def test_controls_pass_on_a_clean_page(sources):
    assert chk.check_chapters(PAGE) == []
    assert chk.check_citations(PAGE, sources) == []
    assert chk.check_hebrew_seats(PAGE) == [] and chk.check_others(PAGE) == []
    if chk.find_node():
        assert chk.check_js(PAGE) == []


def test_controls_fail_when_they_should(sources):
    assert chk.check_chapters(PAGE.replace('{t:"ב"}', "")) != []
    assert chk.check_citations(PAGE.replace("ERR-F13", "XXX-F99"), sources) != []
    assert chk.check_hebrew_seats(PAGE + "<p>32 מושבים</p>") != []
    assert chk.check_others(PAGE + "<td>Others</td>") != []
    assert chk.check_others(PAGE + '<script>{"label":"Others"}</script>') != []
    if chk.find_node():
        assert chk.check_js(PAGE.replace("function trStatic(){}", "function trStatic({}")) != []


def test_others_in_a_cited_title_is_exempt():
    page = PAGE + '{"citation":"Silver (2016). Why Our Model Is More Bullish Than Others","url":"x"}'
    assert chk.check_others(page) == []
