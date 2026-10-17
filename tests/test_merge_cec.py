"""bayes_model._merge_cec: CEC filings displace the table poll they report.

Synthetic frames only. The table polls are seat-derived observations as
implied_share_obs builds them (poll_id x block shares); the filings are
cec_party_pcts.csv / cec_filings.csv rows written to a temporary
PROCESSED_DIR. Rules under test (16 Oct, one-to-one matching):
  * a filing displaces at most one table poll, and a table poll is
    displaced at most once;
  * same-day pairs are matched before 1-3 day pairs;
  * a 1-3 day match needs the two vectors within CEC_MATCH_TOL (no list
    more than 3 points apart once both are normalised);
  * a filing replaces only the lists it reports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import bayes_model as bm

BLOCK_OF = {"likud": 0, "yashar": 1, "bennett_2026": 2, "yesh_atid": 2, "democrats": 3,
            "shas": 4, "utj": 5, "otzma": 6}
# seat-derived shares (they sum below 1: the pie above the threshold)
SHARES = {"likud": .22, "yashar": .18, "bennett_2026": .11, "democrats": .08,
          "shas": .08, "utj": .07, "otzma": .06}
ASOF = pd.Timestamp("2026-10-16")


def table_poll(poll_id, firm, day, shares=SHARES, n=600):
    return pd.DataFrame([{"poll_id": poll_id, "block": BLOCK_OF[p], "share": s, "pollster": firm,
                          "fieldwork_end": pd.Timestamp(day), "n": n} for p, s in shares.items()])


def filing(ref, firm, day, shares=SHARES, drop=()):
    tot = sum(v for k, v in shares.items() if k not in drop)
    pid = {"bennett_2026": "together"}          # filings name the merged list
    return [{"ref": ref, "pollster": firm, "fieldwork_end": day, "party_id": pid.get(p, p),
             "raw_pct": round(100 * s / tot, 2), "shown_passing": True}
            for p, s in shares.items() if p not in drop]


def merge(tmp_path, monkeypatch, polls, filings):
    rows = [r for f in filings for r in f]
    pd.DataFrame(rows).to_csv(tmp_path / "cec_party_pcts.csv", index=False)
    refs = sorted({r["ref"] for r in rows})
    pd.DataFrame({"ref": refs, "undecided_pct": np.nan, "n": 600.0,
                  "initial_sample": 600.0}).to_csv(tmp_path / "cec_filings.csv", index=False)
    monkeypatch.setattr(bm, "PROCESSED_DIR", tmp_path)
    bm.LAST_CEC_MERGE.clear()
    obs = pd.concat(polls, ignore_index=True)
    out = bm._merge_cec(obs, BLOCK_OF, ASOF)
    return out, dict(bm.LAST_CEC_MERGE)


def ids(out):
    return set(out["poll_id"])


def test_one_filing_displaces_one_poll(tmp_path, monkeypatch):
    """Lazar polls twice in three days with the same numbers: the filing of
    12 Oct takes the 12 Oct table poll only (the old rule took both)."""
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("lazar_1012", "Lazar", "2026-10-12"),
                      table_poll("lazar_1014", "Lazar", "2026-10-14")],
                     [filing("9001", "Lazar", "2026-10-12")])
    assert log["polls_displaced"] == 1 and log["cec_filings_merged"] == 1
    assert ids(out) == {"lazar_1014", "cec9001"}
    assert len(out[out["poll_id"] == "lazar_1014"]) == len(SHARES)
    # the filed shares are renormalised to the filing's own party sum
    f = out[out["poll_id"] == "cec9001"]
    assert np.isclose(f["share"].sum(), 1.0, atol=1e-3)
    assert set(f["n"]) == {600.0}


def test_a_poll_is_displaced_at_most_once(tmp_path, monkeypatch):
    """Two same-firm filings, one table poll: the second filing enters as a
    poll of its own instead of displacing the same table poll again."""
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("lazar_1012", "Lazar", "2026-10-12")],
                     [filing("9001", "Lazar", "2026-10-12"),
                      filing("9002", "Lazar", "2026-10-13",
                             shares=dict(SHARES, likud=.23))])
    assert log["polls_displaced"] == 1
    assert ids(out) == {"cec9001", "cec9002"}


def test_same_day_pairs_match_first(tmp_path, monkeypatch):
    """Filings of 11 and 12 Oct, one table poll of 12 Oct that agrees with
    both. Alone, the 11 Oct filing would take it (1-day gap); with the
    12 Oct filing present the same-day pass gives it to that one. The 12 Oct
    filing omits Otzma, so the table poll's Otzma row is kept beside it -
    which shows which filing displaced the poll."""
    poll = table_poll("lazar_1012", "Lazar", "2026-10-12")
    f11 = filing("9001", "Lazar", "2026-10-11")
    f12 = filing("9002", "Lazar", "2026-10-12", drop=("otzma",))

    alone, log1 = merge(tmp_path, monkeypatch, [poll], [f11])
    assert log1["polls_displaced"] == 1 and "lazar_1012" not in ids(alone)

    out, log = merge(tmp_path, monkeypatch, [poll], [f11, f12])
    assert log["polls_displaced"] == 1
    kept = out[out["poll_id"] == "lazar_1012"]
    assert list(kept["block"]) == [BLOCK_OF["otzma"]]          # retained beside 9002
    assert log["table_rows_retained"] == 1
    assert {"cec9001", "cec9002"} <= ids(out)                    # 9001 enters as its own poll


def test_different_poll_two_days_apart_is_not_displaced(tmp_path, monkeypatch):
    """Same firm, 2 days apart, Likud more than 3 points apart once both
    vectors are normalised: a different survey, so both stay."""
    far = dict(SHARES, likud=SHARES["likud"] + 0.06)            # normalised gap ~5 points
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("lazar_1014", "Lazar", "2026-10-14", shares=far)],
                     [filing("9001", "Lazar", "2026-10-12")])
    assert log["polls_displaced"] == 0
    assert ids(out) == {"lazar_1014", "cec9001"}
    assert len(out[out["poll_id"] == "lazar_1014"]) == len(SHARES)


def test_close_poll_two_days_apart_is_displaced(tmp_path, monkeypatch):
    """The control: the same layout within the tolerance is the same poll."""
    near = dict(SHARES, likud=SHARES["likud"] + 0.015)          # normalised gap ~1.3 points
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("lazar_1014", "Lazar", "2026-10-14", shares=near)],
                     [filing("9001", "Lazar", "2026-10-12")])
    assert log["polls_displaced"] == 1
    assert ids(out) == {"cec9001"}


def test_another_firm_is_never_displaced(tmp_path, monkeypatch):
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("filber_1012", "Filber", "2026-10-12")],
                     [filing("9001", "Direct Polls", "2026-10-12")])
    assert log["polls_displaced"] == 0
    assert ids(out) == {"filber_1012", "cec9001"}


def test_gap_above_three_days_is_never_matched(tmp_path, monkeypatch):
    out, log = merge(tmp_path, monkeypatch,
                     [table_poll("lazar_1008", "Lazar", "2026-10-08")],
                     [filing("9001", "Lazar", "2026-10-12")])
    assert log["polls_displaced"] == 0
    assert ids(out) == {"lazar_1008", "cec9001"}


def test_tolerances_are_the_shipped_ones():
    assert bm.CEC_MATCH_TOL == pytest.approx(0.03)
    assert bm.CEC_MATCH_TOL_SAME == pytest.approx(0.04)
