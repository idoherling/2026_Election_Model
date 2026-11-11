"""The graded record: which elections the model is graded on, and where
the record's tables live.

The record is the eight elections 2009-2022. RECORD_2026=1 (environment)
adds the 2026 election as a ninth graded cycle (dossier s.74):

  * CYCLES gains "2026" (validate_model.ORDER, error_decomposition.ORDER and
    error_model.ORDER are this list), scrape_polls.ELECTION_DAY gets its
    date, and the per-cycle tables of validate_model / validate_bayes gain
    their 2026 entries;
  * results(), ran_vote_shares() and cec_final_counts() append the 2026 rows
    kept in data/record_2026/ (built from the certified result,
    data/processed/result_2026_certified.csv: `python src/record.py --build`).
    They are never written into data/processed/results.csv, which the
    scraper rewrites and which every default reader loads;
  * every record table derived from nine cycles is read from and written to
    data/processed/record9/ (table()): the pollster scorecard and its
    per-cycle file (backtest.py), the straddler record, the full-sample
    error decomposition, the harnesses' outputs when HARNESS_OUT_DIR is
    unset, and the error-model posteriors. The top-level files stay the
    eight-cycle ones.

Unset (the default) every module is bit-identical to the eight-cycle code:
the import-time constants of bayes_model (decompose(), the scorecard
priors), every generated table and the test suite. The frozen 2026
forecast, which the tests re-run, depends on that. Modules that are not
part of the harness (bias_audit, house_effects, the site, the scorecard)
read the top-level files directly and do not see the switch.
"""
from __future__ import annotations   # the venv is Python 3.9

import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

RECORD_2026 = os.environ.get("RECORD_2026", "0") == "1"
PAST_CYCLES = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
CYCLES = PAST_CYCLES + (["2026"] if RECORD_2026 else [])
N_WORD = "nine" if RECORD_2026 else "eight"      # for the harnesses' headings
ELECTION_DAY_2026 = "2026-10-27"

RECORD_2026_DIR = DATA_DIR / "record_2026"      # the 2026 rows (committed)
RECORD9_DIR = PROCESSED_DIR / "record9"         # nine-cycle record tables
# where a record table is read and written: the top-level directory, or
# record9/ under the switch
TABLE_DIR = RECORD9_DIR if RECORD_2026 else PROCESSED_DIR


def table(name: str) -> Path:
    """Path of a record table (backtest_pollsters.csv, ...)."""
    return TABLE_DIR / name


# ---------------------------------------------------------------------------
# The configuration for the next election (dossier s.76).
#
# MODEL_CONFIG=2026 (the default) is the configuration of the frozen 2026
# forecast of record. MODEL_CONFIG=next, which needs RECORD_2026=1, is the
# model for the next election: the nine-cycle record with the changes that
# passed the shipping rule (s.53 / s.55) on it. bayes_model sets its flags
# from NEXT_CONFIG["production"] and validate_bayes.ALL_LAYERS mirrors them
# with NEXT_CONFIG["harness"], so under the two variables "shipped" is the
# next-election model in production and in the harness alike, and the arm
# cfg_2026 is the configuration it replaced.
#
#   RECORD_2026=1                    nine cycles, the 2026 configuration
#                                    (the baseline s.76 grades against)
#   RECORD_2026=1 MODEL_CONFIG=next  the model for the next election
# ---------------------------------------------------------------------------
MODEL_CONFIG = os.environ.get("MODEL_CONFIG", "2026")
if MODEL_CONFIG not in ("2026", "next"):
    raise SystemExit(f"MODEL_CONFIG={MODEL_CONFIG!r}: use 2026 or next")
if MODEL_CONFIG == "next" and not RECORD_2026:
    raise SystemExit("MODEL_CONFIG=next was graded on the nine-cycle record: set RECORD_2026=1 with it")
NEXT = MODEL_CONFIG == "next"
NEXT_CONFIG = {
    # bayes_model flags
    "production": {
        "T_UNIT_VAR": True,     # cal_A (s.48): every t shock at its measured sd
        "RESID_SPACE": "vote",  # cal_B (s.57): the vote-share residual line
        # tramp_m (s.46): the trailing-Likud ramp instead of the 0.5-seat
        # cliff - weight 1 where Likud trails by a seat or more, 0 where it
        # leads by two; mu / sd are the same-weight record on nine cycles
        # (validate_bayes.trail_ramp_params; 2026 enters at weight 0.29),
        # asserted in tests/test_record9.py
        "TRAIL_RAMP_ON": True,
        "TRAIL_RAMP": {"lo": -1.0, "hi": 2.0, "mode": "mean", "mu": 5.49, "sd": 3.86},
    },
    # the same three changes as validate_bayes layer flags (the arm tramp_AB)
    "harness": {"t_unit": True, "resid_space": "vote", "trail_mode": "ramp",
                "trail_lo": -1.0, "trail_hi": 2.0, "trail_wcal": True},
    # the configuration it replaces, as layer flags (the arm cfg_2026)
    "harness_2026": {"t_unit": False, "resid_space": "seat_fix", "trail_mode": "mean",
                     "trail_lo": 0.5, "trail_hi": 2.0, "trail_wcal": False},
}


def _with_2026(base: Path, name: str, kw: dict) -> pd.DataFrame:
    df = pd.read_csv(base, **kw)
    if RECORD_2026:
        kw2 = dict(kw)
        # "2026" must stay a string beside "2019a" whatever the caller asked
        kw2["dtype"] = dict(kw.get("dtype") or {}, cycle=str)
        df = pd.concat([df, pd.read_csv(RECORD_2026_DIR / name, **kw2)], ignore_index=True)
    return df


def results(**kw) -> pd.DataFrame:
    """data/processed/results.csv (+ the 2026 rows under the switch)."""
    return _with_2026(PROCESSED_DIR / "results.csv", "results.csv", kw)


def ran_vote_shares(**kw) -> pd.DataFrame:
    """data/ran_vote_shares.csv (+ the 2026 rows under the switch)."""
    return _with_2026(DATA_DIR / "ran_vote_shares.csv", "ran_vote_shares.csv", kw)


def cec_final_counts(**kw) -> pd.DataFrame:
    """data/cec_final_counts.csv (+ the 2026 rows under the switch)."""
    return _with_2026(DATA_DIR / "cec_final_counts.csv", "cec_final_counts.csv", kw)


# ---------------------------------------------------------------------------
# The 2026 rows. Ballot letters -> the ids polls.csv uses in the final
# window (the Together and Joint List tables' own ids, as results.csv does
# for every cycle: error_decomposition, backtest and trailing_likud_params
# match raw ids; the harnesses expand them through validate_bayes.DECOMP).
# Letters as approved by the CEC on 27 Sept 2026 (dossier s.38); the same
# pairing as election_night.site_lexicon()["HEB"] x mixture_shares.csv.
# Blue and White (כן) and Ahi (צבי) withdrew and have no votes: they stay
# in the CEC count, not in results / ran_vote_shares (non-runners).
# ---------------------------------------------------------------------------
LETTERS_2026 = {
    "מחל": "likud", "דרך": "yashar", "רק": "together", "ודם": "joint_list",
    "אמת": "democrats", "עם": "raam", "ל": "yisrael_beytenu", "ב": "otzma",
    "ג": "utj", "שס": "shas", "ט": "rzp", "די": "zionist_home",
    "ך": "amcha_yisrael", "נר": "code_black", "זך": "haredi_public",
    "ני": "noam", "בי": "beit_yisrael", "י": "israel_first",
    "כן": "blue_white", "צבי": "ahi",
}
CERTIFIED_2026 = PROCESSED_DIR / "result_2026_certified.csv"
SOURCE_2026 = ("CEC official final results, 26th Knesset (votes26.bechirot.gov.il/nationalresults, "
               "read 11 Nov 2026; repo copy data/processed/result_2026_certified.csv)")


def build_2026() -> dict:
    """The three data/record_2026 files as frames, from the certified
    result: results.csv (lists that won seats; lists that ran and failed
    with their vote share, as the 2021/2022 rows carry it), ran_vote_shares
    .csv (the CEC vote share of every named list that ran) and
    cec_final_counts.csv (all 38 lists, the format of data/cec_final_counts
    .csv)."""
    c = pd.read_csv(CERTIFIED_2026, comment="#", dtype={"list": str})
    c["party_id"] = c["list"].map(LETTERS_2026)
    valid = int(c["votes"].sum())
    c["pct"] = (c["votes"] / valid * 100).round(2)
    ran = c[c["party_id"].notna() & (c["votes"] > 0)]
    res = pd.DataFrame({"cycle": "2026", "party_id": ran["party_id"], "seats": ran["seats"].astype(int),
                        "vote_pct": ran["pct"].where(ran["seats"] == 0),
                        "source_row": "cec:certified:2026-11-11"}).sort_values("party_id")
    rvs = pd.DataFrame({"cycle": "2026", "party_id": ran["party_id"], "seats": ran["seats"].astype(int),
                        "vote_pct": ran["pct"],
                        "source": "https://votes26.bechirot.gov.il/nationalresults (certified, read 11 Nov 2026)"})
    names = dict(zip(*[pd.read_csv(DATA_DIR / "party_registry.csv")[k] for k in ("party_id", "name_en")]))
    cnt = pd.DataFrame({"cycle": "2026", "knesset": 26, "ballot": c["list"],
                        "list_name": c["party_id"].map(names), "party_id": c["party_id"],
                        "votes": c["votes"].astype(int), "valid_votes": valid,
                        "seats_official": c["seats"].astype(int), "source": SOURCE_2026})
    return {"results.csv": res, "ran_vote_shares.csv": rvs, "cec_final_counts.csv": cnt}


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--build"]:
        raise SystemExit("usage: python src/record.py --build   (rewrites data/record_2026/)")
    RECORD_2026_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in build_2026().items():
        df.to_csv(RECORD_2026_DIR / name, index=False)
        print(f"wrote {RECORD_2026_DIR / name} ({len(df)} rows)")
