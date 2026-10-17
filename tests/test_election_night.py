"""Tests for src/election_night.py (unittest; pytest also collects them).

    python -m unittest tests/test_election_night.py -v
    python tests/test_election_night.py
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

import election_night as en                         # noqa: E402
import simulate as sim                              # noqa: E402
from validate_model import CYCLE_THRESHOLD, REGISTERED_PAIRS   # noqa: E402

COUNTS = pd.read_csv(en.COUNTS, dtype={"cycle": str})
OFFICIAL_2022 = {"מחל": 32, "פה": 24, "ט": 14, "כן": 12, "שס": 11, "ג": 7, "ל": 6,
                 "עם": 5, "ום": 5, "אמת": 4}
HAVE_RAW = (en.KALPI_DIR / "expb_25.csv").exists() and (en.KALPI_DIR / "expc_24.csv").exists()
GOVIL_ERROR = ('<!DOCTYPE html><html dir="rtl"><head> <title>שגיאה</title> <meta charset="utf-8">'
               '</head><body><div class="title"> האתר המבוקש אינו נמצא </div></body></html>')


def letters_2022():
    d = COUNTS[COUNTS["cycle"] == "2022"]
    return dict(zip(d["ballot"].str.strip(), d["votes"].astype(int)))


class SeatEngine(unittest.TestCase):
    def test_reproduces_every_official_allocation(self):
        """Registered surplus agreements + the engine = the official seats, 2009-2022."""
        for cycle, g in COUNTS.groupby("cycle", sort=False):
            g = g.reset_index(drop=True)
            keys = [p if isinstance(p, str) and p else f"_row{i}" for i, p in enumerate(g["party_id"])]
            idx, _, _ = sim.resolve_pairs(REGISTERED_PAIRS[cycle], [set(k.split("+")) for k in keys],
                                          fixed=True)
            thr = Fraction(1, 50) if CYCLE_THRESHOLD.get(cycle) == 0.02 else en.THRESHOLD
            a = en.allocate(dict(zip(keys, g["votes"].astype(int))),
                            [(keys[x], keys[y]) for x, y in idx], threshold=thr)
            self.assertEqual(a.seats, dict(zip(keys, g["seats_official"].astype(int))), cycle)
            self.assertEqual(sum(a.seats.values()), 120)

    def test_2022_replay_final_reproduces_official(self):
        """The 2022 rehearsal cycle (ballot letters, registered pairs) on the final count."""
        cyc = en.cycle_2022()
        pairs, dropped = cyc.letter_pairs()
        self.assertEqual(set(pairs), {("פה", "כן"), ("אמת", "מרצ"), ("ג", "שס"), ("מחל", "ט")})
        self.assertEqual(dropped, [("yesh_kivun", "pirates")])   # unnamed sub-threshold lists
        a = en.allocate(letters_2022(), pairs)
        self.assertEqual({k: v for k, v in a.seats.items() if v}, OFFICIAL_2022)
        self.assertEqual(set(a.pooled), {("פה", "כן"), ("ג", "שס"), ("מחל", "ט")})  # Meretz failed

    @unittest.skipUnless(HAVE_RAW, "raw CEC station files not present (data/raw/kalpi)")
    def test_2022_station_file_sums_to_final_counts(self):
        df = en._read_cec_file(en.KALPI_DIR / "expb_25.csv")
        c = en.count_from_frame(df, "expb_25.csv", en.utc_iso())
        self.assertEqual(c.votes, {k: v for k, v in letters_2022().items() if k in c.votes})
        self.assertEqual(c.valid, 4_764_742)
        self.assertEqual(c.stations, 11_707)
        self.assertEqual(c.envelope_valid, 458_714)
        p = en.build_payload(c, en.cycle_2022(), mode="rehearsal")
        self.assertEqual({r["letter"]: r["seats_raw"] for r in p["lists"] if r["seats_raw"]}, OFFICIAL_2022)
        self.assertEqual({r["letter"]: r["seats_adj"] for r in p["lists"] if r["seats_adj"]}, OFFICIAL_2022)

    def test_threshold_is_exact_on_all_valid_votes(self):
        # 400 x 13 / 400: a list with exactly 3.25% of all valid votes passes, one vote less fails
        v = {"א": 13_000, "ב": 200_000, "ג": 187_000}           # valid 400,000 -> line 13,000
        self.assertIn("א", en.allocate(v).passed)
        v2 = {"א": 12_999, "ב": 200_000, "ג": 187_001}
        self.assertNotIn("א", en.allocate(v2).passed)
        self.assertEqual(en.allocate(v2).needed, 13_000)

    def test_unitemised_rest_counts_in_denominator_only(self):
        v = {"א": 40_000, "ב": 500_000, en.REST: 460_000}
        a = en.allocate(v)
        self.assertEqual(a.seats[en.REST], 0)
        self.assertIn("א", a.passed)                            # 4.0% of 1,000,000
        v[en.REST] = 760_000                                     # 3.1% of 1,300,000
        self.assertNotIn("א", en.allocate(v).passed)

    def test_2026_surplus_pairs_map_to_letters(self):
        pairs, dropped = en.cycle_2026().letter_pairs()
        self.assertEqual(pairs, [("מחל", "ט"), ("רק", "ל"), ("דרך", "אמת"), ("שס", "ג"), ("ודם", "עם")])
        self.assertEqual(dropped, [])


def synthetic_cycle():
    cyc = en.cycle_2026()
    cyc.baseline = pd.DataFrame({"expected": [600_000.0, 400_000.0], "sector": ["centre_left", "arab"],
                                 "name": ["A", "B"]}, index=[100, 200])
    cyc.locality_prior = None
    cyc.sector_prior = {"centre_left": {"מחל": .5, "דרך": .5},
                        "arab": {"ודם": .5, "עם": .5}}
    return cyc


def station_frame(rows):
    cols = ["סמל ועדה", "ברזל", "שם ישוב", "סמל ישוב", "קלפי", "ריכוז", "שופט", "בזב", "מצביעים",
            "פסולים", "כשרים"]
    letters = sorted({k for r in rows for k in r["v"]})
    lines = [",".join(cols + letters)]
    for i, r in enumerate(rows):
        valid = sum(r["v"].values())
        meta = [1, i + 1, r.get("name", "x"), r["code"], f"{i + 1}.0", 1, 0, valid * 2, valid + 3, 3, valid]
        lines.append(",".join(str(x) for x in meta + [r["v"].get(l, 0) for l in letters]))
    return "﻿" + "\n".join(lines) + "\n"


class ThresholdWatch(unittest.TestCase):
    def test_synthetic_partial_count(self):
        """Lists within 0.5 points of 3.25% are watched, with exact vote margins and the
        TRN-F03 envelope direction; lists further out are not."""
        cyc = en.cycle_2026()
        votes = {"מחל": 300_000, "דרך": 274_000, "ט": 30_000,       # RZP 3.00%: watched, up
                 "שס": 34_000,                                         # Shas 3.40%: watched, down
                 "עם": 37_600,                                         # Ra'am 3.76%: outside the band
                 "ני": 27_400,                                         # Noam 2.74%: outside the band
                 "די": 28_000,                                         # Reservists 2.80%: watched, no lean
                 "ודם": 37_500,                                        # JL 3.75%: on the band's edge
                 "ל": 231_500}
        self.assertEqual(sum(votes.values()), 1_000_000)
        c = en.Count(votes=votes, level="national", source="test", fetched_utc=en.utc_iso())
        p = en.build_payload(c, cyc)
        w = {r["letter"]: r for r in p["watch"]}
        self.assertEqual(set(w), {"ט", "שס", "די", "ודם"})
        self.assertEqual(p["threshold_votes"], 32_500)
        self.assertEqual(w["ט"]["margin"], -2_500)
        self.assertFalse(w["ט"]["passes"])
        self.assertEqual(w["שס"]["margin"], 1_500)
        self.assertEqual(w["ודם"]["margin"], 5_000)
        self.assertEqual(w["ט"]["lean"], {"dir": "up", "basis": "direct", "family": "rz"})
        self.assertEqual(w["שס"]["lean"]["dir"], "down")
        self.assertEqual(w["ודם"]["lean"]["dir"], "down")
        self.assertIsNone(w["די"]["lean"])
        self.assertEqual(p["sectors"], [])            # national table: (b) not computed
        self.assertIsNone(w["ט"]["share_adj"])
        # surplus pairs only pool lists that pass: Likud-RZP is not pooled here
        pr = {(x["a"], x["b"]): x for x in p["pairs"]}
        self.assertFalse(pr[("מחל", "ט")]["pooled_raw"])
        self.assertTrue(pr[("דרך", "אמת")]["pooled_raw"] is False)   # Democrats absent

    def test_nowcast_weights_remaining_votes_by_sector(self):
        """Only the Jewish locality has reported: the raw count shuts the Arab lists
        out; (b) casts the Arab locality's expected votes at its prior and seats them."""
        cyc = synthetic_cycle()
        df = en.parse_results_csv(station_frame([
            {"code": 100, "v": {"מחל": 150_000, "דרך": 150_000, "ודם": 0, "עם": 0}},
        ]))
        c = en.count_from_frame(df, "test", en.utc_iso())
        raw = en.allocate(c.votes, cyc.letter_pairs()[0])
        self.assertEqual(raw.seats["ודם"], 0)
        nc = en.nowcast(c, cyc, cyc.letter_pairs()[0])
        self.assertAlmostEqual(nc.expected_valid, 1_000_000, delta=1)
        self.assertAlmostEqual(nc.pct_votes, 0.30, places=3)
        # remaining 300k Jewish votes at the counted 50/50; 400k Arab votes at the 50/50 prior
        self.assertAlmostEqual(nc.votes["ודם"], 200_000, delta=1)
        self.assertAlmostEqual(nc.votes["מחל"], 300_000, delta=1)
        self.assertGreater(nc.alloc.seats["ודם"], 20)
        arab = next(s for s in nc.sectors if s["sector"] == "arab")
        self.assertEqual((arab["counted"], arab["reporting"]), (0, 0))

    def test_ratio_swing_uses_locality_priors(self):
        """Two Arab localities with different priors: the reported one swings, and the
        swing carries to the other at ITS prior, not at the reported one's make-up."""
        cyc = synthetic_cycle()
        cyc.baseline = pd.DataFrame({"expected": [100_000.0, 100_000.0], "sector": ["arab", "arab"],
                                     "name": ["N", "S"]}, index=[300, 400])
        cyc.locality_prior = pd.DataFrame({"ודם": [0.8, 0.2], "עם": [0.2, 0.8]}, index=[300, 400])
        df = en.parse_results_csv(station_frame([{"code": 300, "v": {"ודם": 40_000, "עם": 10_000}}]))
        nc = en.nowcast(en.count_from_frame(df, "t", en.utc_iso()), cyc, [])
        # no swing (counted = prior); locality 400's 100k cast 20/80
        self.assertAlmostEqual(nc.votes["עם"], 10_000 + 50_000 * 0.2 + 80_000, delta=600)


class Feed(unittest.TestCase):
    def test_govil_error_page_is_rejected(self):
        with self.assertRaises(en.FeedFormatError):
            en.parse_results_csv(GOVIL_ERROR)
        r = en.validate_body("station", GOVIL_ERROR.encode("utf-8"))
        self.assertFalse(r["ok"])

    def test_windows_1255_and_bom(self):
        text = station_frame([{"code": 5000, "v": {"מחל": 10, "פה": 7}}])
        for raw in (text.encode("utf-8"), text.lstrip("﻿").encode("cp1255")):
            t, _ = en.decode_bytes(raw)
            df = en.parse_results_csv(t)
            self.assertEqual(df.attrs["letters"], ["מחל", "פה"])
            self.assertEqual(int(df["כשרים"].sum()), 17)

    def test_unknown_columns_are_not_lists(self):
        text = station_frame([{"code": 5000, "v": {"מחל": 10}}]).replace("כשרים,", "כשרים,ת. עדכון,", 1)
        text = text.replace(",10,10\n", ",10,22:15,10\n")
        df = en.parse_results_csv(text)
        self.assertEqual(df.attrs["letters"], ["מחל"])

    def test_national_html_2022_format(self):
        html = ("<html><body><p>נספרו 37.5% מהקלפיות</p><table class='TableData'><tbody>"
                "<tr><td>הליכוד</td><td>מחל</td><td>23.41%</td><td class='Last'>1,115,336</td></tr>"
                "<tr><td>הציונות הדתית</td><td>ט</td><td>10.84%</td><td class='Last'>516,470</td></tr>"
                "</tbody></table></body></html>")
        votes, pct, names = en.parse_national_html(html)
        self.assertEqual(votes, {"מחל": 1_115_336, "ט": 516_470})
        self.assertEqual(pct, 37.5)
        self.assertEqual(names["ט"], "הציונות הדתית")

    def test_manual_csv(self):
        cyc = en.cycle_2026()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "night.csv"
            p.write_text("list,votes\nLikud,\"1,000,000\"\nש\"ס,300000\nרק,500000\nRa'am,150000\n"
                         "small parties,50000\n", encoding="utf-8")
            c = en.parse_manual_csv(p, cyc)
            self.assertEqual(c.votes, {"מחל": 1_000_000, "שס": 300_000, "רק": 500_000, "עם": 150_000,
                                       en.REST: 50_000})
            q = Path(d) / "bad.csv"
            q.write_text("list,votes\nLikkud,5\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                en.parse_manual_csv(q, cyc)
            r = Path(d) / "partial.csv"
            r.write_text("list,votes\nמחל,100\nט,40\n", encoding="utf-8")
            c = en.parse_manual_csv(r, cyc, valid=1000)
            self.assertEqual(c.votes[en.REST], 860)

    def test_snapshot_cache_dedupes_and_flags_bad_bodies(self):
        csv = station_frame([{"code": 5000, "v": {"מחל": 100, "פה": 80}}]).encode("utf-8")

        def fake(url):
            if url.endswith("expb.csv"):
                return en.Fetched(url, 200, csv, {"ETag": "x"}, None, 1)
            if url.endswith("expc.csv"):
                return en.Fetched(url, 200, GOVIL_ERROR.encode(), {}, None, 1)
            return en.Fetched(url, 404, b"", {}, None, 1)

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = en.take_snapshot("https://example.test/files/", "https://example.test/", root=root,
                                 stamp="20261027T200000Z", fetch=fake)
            b = en.take_snapshot("https://example.test/files/", "https://example.test/", root=root,
                                 stamp="20261027T200300Z", fetch=fake)
            ma = json.loads((a / "meta.json").read_text())
            mb = json.loads((b / "meta.json").read_text())
            items = {i["level"]: i for i in ma["items"]}
            self.assertTrue(items["station"]["ok"])
            self.assertFalse(items["locality"]["ok"])           # HTML with HTTP 200
            self.assertEqual(items["national"]["problem"], "not published yet (404)")
            self.assertEqual({i["level"]: i.get("same_as") for i in mb["items"]}["station"], a.name)
            self.assertFalse((b / "expb.csv.gz").exists())
            c = en.load_snapshot(b)
            self.assertEqual((c.level, c.votes), ("station", {"מחל": 100, "פה": 80}))
            self.assertEqual(en.last_good_snapshot(root), b)


class Page(unittest.TestCase):
    def render(self, lang_payload):
        return en.render_page(lang_payload)

    def test_page_contract_and_hebrew_rules(self):
        cyc = en.cycle_2026()
        votes = {l: 50_000 for l in cyc.names}
        votes.update({"מחל": 1_000_000, "דרך": 900_000, "רק": 400_000})
        c = en.Count(votes=votes, level="national", source="t", fetched_utc=en.utc_iso())
        p = en.build_payload(c, cyc)
        html = en.render_page(p)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn('name="viewport"', html)
        self.assertIn("--p-likud", html)                      # tokens from site/template.html
        self.assertNotIn("__EN_", html)
        self.assertNotIn("מושבים", html)
        self.assertIn("מנדטים", html)
        self.assertNotIn("Others", html)
        self.assertIn("Small parties", html)
        self.assertIn("המפלגות הקטנות", html)
        self.assertNotRegex(html, r'ש"ס|רע"ם')
        rows = {r["letter"]: r for r in p["lists"]}
        self.assertEqual(rows["רק"]["he"], "ביחד")
        self.assertEqual(rows["שס"]["he"], "ש״ס")
        self.assertEqual(rows["כן"]["bloc"], "una")             # Blue and White: unaligned
        self.assertEqual(rows["די"]["bloc"], "una")             # the Reservists: unaligned
        bl = {b["key"]: b for b in p["blocs"]}
        raam = rows["עם"]["seats_raw"]
        self.assertEqual(bl["antiRaam"]["raw"], bl["anti"]["raw"] + raam)   # Ra'am whole, once
        self.assertEqual(sum(r["seats_raw"] for r in p["lists"]), 120)

    def test_header_only_file_at_poll_close(self):
        """In 2022 the files were published header-only at 22:00 (no stations yet)."""
        text = station_frame([{"code": 5000, "v": {"מחל": 0, "דרך": 0}}]).splitlines()[0] + "\n"
        c = en.count_from_frame(en.parse_results_csv(text), "t", en.utc_iso())
        self.assertEqual((c.valid, c.stations), (0, 0))
        p = en.build_payload(c, en.cycle_2026())
        self.assertEqual(p["watch"], [])
        self.assertEqual(p["progress"]["pct_votes"], 0.0)
        self.assertTrue(all((r["seats_raw"] or 0) == 0 for r in p["lists"]))
        self.assertIn("<!doctype html>", en.render_page(p))

    def test_waiting_page_shows_forecast(self):
        p = en.build_payload(None, en.cycle_2026(), mode="waiting")
        self.assertEqual(p["mode"], "waiting")
        self.assertTrue(all(r["ref"] for r in p["lists"]))
        self.assertIn("<!doctype html>", en.render_page(p))


if __name__ == "__main__":
    unittest.main(verbosity=2)
