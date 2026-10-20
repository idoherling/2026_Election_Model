"""CEC filing parser (scrape_cec.parse_pdf) and filing discovery
(scrape_cec --discover) on four real filings in tests/fixtures/cec.

Expected values are read off each PDF's own text (the vote-intention table);
each case carries the extraction quirk it guards:
  4207 Lazar / Walla, 12 Oct    the plain case, small lists itemised to 0.2%
  4211 Direct Polls / i24       a list name wrapped over three lines
                                ("המילואימניקים" / "והכלכלית" / "2.2% 2.2%")
                                and a "below 1%" line naming six lists with
                                no percentage of their own
  4212 Next Data / Channel 14   the "נועם" spelling of Noam, and a which-
                                government question ("ממשלת אחדות 21.8%")
                                that must not parse as the Unity list
  4202 Midgam / Channel 12      the undecided share on its own line
                                ("לא החליטו 8.1%")
"""
from __future__ import annotations

import pandas as pd
import pytest

import scrape_cec as sc

EXPECTED = {
    "4207": {"yashar": 15.9, "likud": 14.9, "together": 11.2, "democrats": 8.5,
             "yisrael_beytenu": 7.2, "otzma": 6.3, "utj": 6.2, "balad+hadash_taal": 6.4,
             "shas": 5.5, "rzp": 5.4, "raam": 3.9, "zionist_home": 3.5,
             "amcha_yisrael": 2.8, "blue_white": 1.1, "haredi_public": 1.0, "noam": 0.2},
    "4211": {"likud": 20.5, "yashar": 16.4, "together": 9.7, "otzma": 7.2, "democrats": 7.1,
             "utj": 5.8, "yisrael_beytenu": 5.7, "shas": 5.4, "balad+hadash_taal": 5.2,
             "raam": 5.0, "rzp": 4.7, "amcha_yisrael": 3.1, "zionist_home": 2.2},
    "4212": {"likud": 22.1, "yashar": 15.6, "together": 8.5, "shas": 7.7,
             "balad+hadash_taal": 7.0, "democrats": 6.4, "utj": 6.1, "otzma": 5.9, "rzp": 5.5,
             "raam": 3.6, "yisrael_beytenu": 4.0, "zionist_home": 3.1, "amcha_yisrael": 2.7,
             "blue_white": 1.2, "noam": 0.8, "haredi_public": 0.4, "ahi": 0.2},
    "4202": {"yashar": 18.2, "likud": 16.1, "together": 10.4, "democrats": 7.3,
             "yisrael_beytenu": 7.2, "otzma": 6.4, "shas": 6.3, "balad+hadash_taal": 6.2,
             "utj": 5.6, "rzp": 4.8, "raam": 4.1, "zionist_home": 3.4, "amcha_yisrael": 1.8},
}
EXPECTED_META = {   # methodology fields the parser reads; None = not reported
    "4207": {"initial_sample": 600, "moe": 4.0, "undecided_pct": None},
    "4211": {"initial_sample": 1000, "moe": 2.8, "undecided_pct": None},
    "4212": {"initial_sample": 650, "moe": 4.1, "undecided_pct": None},
    "4202": {"initial_sample": 500, "moe": 4.4, "undecided_pct": 8.1},
}


@pytest.fixture(scope="module")
def parsed(cec_fixtures):
    return {ref: sc.parse_pdf(cec_fixtures / f"{ref}.pdf") for ref in EXPECTED}


@pytest.fixture(scope="module")
def texts(cec_fixtures):
    return {ref: sc.pdf_lines(cec_fixtures / f"{ref}.pdf") for ref in EXPECTED}


@pytest.mark.parametrize("ref", sorted(EXPECTED))
def test_party_table_exact(parsed, ref):
    meta, rows = parsed[ref]
    assert meta["national_table"] is True
    assert {r["party_id"]: r["raw_pct"] for r in rows} == EXPECTED[ref]
    assert all(r["shown_passing"] for r in rows)
    assert len(rows) == len({r["party_id"] for r in rows})        # one line per list


@pytest.mark.parametrize("ref", sorted(EXPECTED_META))
def test_methodology_fields(parsed, ref):
    meta, _ = parsed[ref]
    for key, want in EXPECTED_META[ref].items():
        assert meta.get(key) == want, key


@pytest.mark.parametrize("ref", sorted(EXPECTED))
def test_filed_table_is_trusted_by_the_merge(parsed, ref):
    """_merge_cec trusts a filing whose parties sum to 90-105% (or 95-105%
    with the undecided line); all four fixtures qualify on their own."""
    _, rows = parsed[ref]
    total = sum(r["raw_pct"] for r in rows)
    und = parsed[ref][0].get("undecided_pct") or 0.0
    assert 90 <= total <= 105 or 95 <= total + und <= 105


def test_4211_three_line_wrap_and_below_one_percent_line(parsed, texts):
    lines = texts["4211"]
    i = lines.index("המילואימניקים")
    assert lines[i + 1] == "והכלכלית" and lines[i + 2].startswith("2.2%")
    assert any("מתחת ל-1%" in ln and "כחול לבן" in ln for ln in lines)
    got = {r["party_id"] for r in parsed["4211"][1]}
    assert got.isdisjoint({"blue_white", "code_black", "noam", "ahi", "haredi_public",
                           "israel_first"})
    assert dict((r["party_id"], r["raw_pct"]) for r in parsed["4211"][1])["zionist_home"] == 2.2


def test_4212_government_question_is_not_unity(parsed, texts):
    assert any(ln.startswith("ממשלת אחדות 21.8%") for ln in texts["4212"])
    got = {r["party_id"] for r in parsed["4212"][1]}
    assert "unity" not in got
    assert any("נועם לישראל" in ln for ln in texts["4212"])     # the Noam spelling
    assert "noam" in got


def test_4202_undecided_line(parsed, texts):
    assert any(ln.startswith("לא החליטו") and "8.1%" in ln for ln in texts["4202"])
    assert parsed["4202"][0]["undecided_pct"] == 8.1


# Was xfail until 17 Oct (the Haredi Public list's vote line was read as the
# haredi sample share); fixed in scrape_cec.parse_pdf.
@pytest.mark.parametrize("ref", ["4207", "4212"])
def test_haredi_sample_share_is_not_a_party_line(parsed, ref):
    meta, rows = parsed[ref]
    hp = {r["party_id"]: r["raw_pct"] for r in rows}.get("haredi_public")
    assert meta.get("haredi_sample_pct") is None or meta.get("haredi_sample_pct") != hp


# --- discovery: index rows from the PDF text ------------------------------

HAND_ROWS = ("4202", "4207", "4211", "4212")


@pytest.fixture(scope="module")
def index_before_16oct():
    """The filings index as it stood before the 16 Oct hand-added rows (and
    before any row the discovery itself appended later)."""
    idx = sc.load_index()
    later = idx["notes"].str.contains("index row added 16 Oct|proposed by scrape_cec --discover",
                                      na=False)
    return idx[~later].reset_index(drop=True)


@pytest.mark.parametrize("ref", HAND_ROWS)
def test_proposed_row_matches_the_16_oct_hand_row(texts, index_before_16oct, ref):
    hand = sc.load_index().set_index("ref").loc[ref]
    row = sc.propose_row(ref, hand["urlname"], hand["fname"], texts[ref],
                         index_before_16oct, today="2026-10-16")
    assert row["editor"] == hand["editor"]
    assert row["survey_date"] == hand["survey_date"]          # fieldwork - 1 day
    assert row["transfer_date"] == hand["transfer_date"]      # approximate, as entered
    # 4207: the PDF and Lazar's three earlier Walla filings say "וואלה תקשורת בע"מ";
    # the hand row shortened it (both match site_ledger's "וואלה")
    want_pub = 'וואלה תקשורת בע"מ' if ref == "4207" else hand["publisher"]
    assert row["publisher"] == want_pub
    assert row["flags"] == []
    assert "transfer date approximate" in row["notes"]
    fields = sc.row_psv(row).split("|")
    assert fields[:7] == [ref, hand["urlname"], hand["fname"], hand["editor"], want_pub,
                          hand["survey_date"], hand["transfer_date"]]
    assert len(fields) == len(sc.INDEX_COLUMNS)


def test_discover_probes_both_file_names_and_stops(tmp_path, cec_fixtures, index_before_16oct):
    """A fake blob store: four new filings at IDX 106-109, one of them named
    without the underscore; nothing at 110-111 -> two misses end the scan."""
    blob = sc.BLOB.format
    store = {
        blob(urlname="knesset_election106", fname="Survey_4202.pdf"): "4202",
        blob(urlname="knesset_election107", fname="Survey_4207.pdf"): "4207",
        blob(urlname="knesset_election108", fname="Survey4211.pdf"): "4211",
        blob(urlname="knesset_election109", fname="Survey_4212.pdf"): "4212",
    }
    calls = []

    def fake_fetch(url):
        calls.append(url)
        ref = store.get(url)
        return (cec_fixtures / f"{ref}.pdf").read_bytes() if ref else None

    assert sc.last_indexed(index_before_16oct) == (105, 4200)
    rows = sc.discover(index_before_16oct, fetch=fake_fetch, idx_span=12, ref_span=15,
                       max_misses=2, out_dir=tmp_path, today="2026-10-16", log=lambda m: None)
    assert [r["ref"] for r in rows] == ["4202", "4207", "4211", "4212"]
    assert [r["urlname"] for r in rows] == [f"knesset_election{i}" for i in range(106, 110)]
    assert rows[2]["fname"] == "Survey4211.pdf"
    assert "without the underscore" in rows[2]["notes"]
    assert all((tmp_path / f"{r['ref']}.pdf").exists() for r in rows)
    assert [r["editor"] for r in rows] == ["מדגם יעוץ ומחקר", 'ד"ר מנחם לזר',
                                           'דיירקט פולס בע"מ', "נקסט דאטה"]
    assert [r["survey_date"] for r in rows] == ["2026-10-11", "2026-10-11", "2026-10-12",
                                                "2026-10-13"]
    probed = {u.split("/")[-3] for u in calls}
    assert probed == {f"knesset_election{i}" for i in range(106, 112)}   # stopped after 111
    indexed = set(index_before_16oct["ref"])
    assert not any(f"Survey_{r}.pdf" in u or f"Survey{r}.pdf" in u for u in calls for r in indexed
                   if r.isdigit() and int(r) > 4200)


def test_append_rows_round_trip(tmp_path, texts, index_before_16oct):
    path = tmp_path / "index.psv"
    path.write_text("4200|knesset_election105|Survey_4200.pdf|x|y|2026-10-10|2026-10-11|", encoding="utf-8")
    row = sc.propose_row("4212", "knesset_election111", "Survey_4212.pdf", texts["4212"],
                         index_before_16oct, today="2026-10-16")
    sc.append_rows([row], path)
    back = sc.load_index(path)
    assert list(back["ref"]) == ["4200", "4212"]
    got = back.iloc[1].to_dict()
    assert {k: got[k] for k in sc.INDEX_COLUMNS} == {k: str(row[k]) for k in sc.INDEX_COLUMNS}


def test_dates_in_every_filed_format():
    yr = 2026
    p = sc._parse_dates
    assert p("מועד איסוף הנתונים 12/10/2026", yr) == [pd.Timestamp("2026-10-12")]
    assert p("תאריכי ביצוע הסקר  13 באוקטובר2026", yr) == [pd.Timestamp("2026-10-13")]
    assert max(p("08.10.2026 שעה12:30 עד 09.10.2026", yr)) == pd.Timestamp("2026-10-09")
    assert max(p("מתאריך 27-8-2026 שעה15:30 עד1-9-2026", yr)) == pd.Timestamp("2026-09-01")
    assert p("בהם בוצע הסקר 29.9.26 (7:00-12:00 )", yr) == [pd.Timestamp("2026-09-29")]
    assert max(p("11 באוקטובר(15:12 )– 11  באוקטובר(15:16)", yr)) == pd.Timestamp("2026-10-11")
    assert max(p("בתאריכים 5/8-ה עד 6/8-ה, 4.4% תקן סטיית", yr)) == pd.Timestamp("2026-08-06")
