"""RECORD_2026 (src/record.py): 2026 as the ninth graded cycle, behind one
switch. Unset, the record is the eight cycles 2009-2022 and nothing reads
the 2026 rows; set (in a subprocess: the switch is read at import), there
are nine cycles, the 2026 eve window builds and the certified count gives
the official seats under the five filed surplus agreements."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pandas as pd

import record

EIGHT = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]


def test_default_record_is_eight_cycles():
    import error_decomposition as ed
    import error_model as em
    import scrape_polls as sp
    import validate_bayes as vb
    import validate_model as vm
    assert not record.RECORD_2026 and record.CYCLES == EIGHT
    assert vm.ORDER == ed.ORDER == em.ORDER == vb.ORDER == EIGHT
    assert sp.ELECTION_DAY["2026"] is None
    for tab in (vm.PAST_PAIRS, vm.REGISTERED_PAIRS, vb.DECOMP, vb.WITHDRAWALS,
                vb.UNMODELLED_REC, vb.ARAB_TURNOUT_REC, vb.KNOWN_ESTABLISHED):
        assert "2026" not in tab
    assert "2026" not in vb.ARAB_REGIMES["B"]
    assert record.TABLE_DIR == record.PROCESSED_DIR and vb.OUT_DIR == record.PROCESSED_DIR
    assert set(record.results(dtype={"cycle": str})["cycle"]) == set(EIGHT)
    assert "2026" not in set(record.ran_vote_shares(dtype={"cycle": str})["cycle"])
    assert "2026" not in set(record.cec_final_counts(dtype={"cycle": str})["cycle"])
    assert not {"hared_off", "arab_off", "trail_field", "tramp_AB", "cfg_2026"} & {a for a, _ in vb.ABLATIONS}
    # the 2026 configuration: the next-election flags are off (record.NEXT_CONFIG)
    import bayes_model as bm
    assert record.MODEL_CONFIG == "2026" and not record.NEXT
    assert (bm.T_UNIT_VAR, bm.RESID_SPACE, bm.TRAIL_RAMP_ON) == (False, "seat_fix", False)
    assert bm.TRAIL_RAMP == {"lo": -1.0, "hi": 2.0, "mode": "mean", "mu": 5.58, "sd": 4.15}
    assert {k: vb.ALL_LAYERS[k] for k in record.NEXT_CONFIG["harness_2026"]} == record.NEXT_CONFIG["harness_2026"]


def test_2026_rows_are_the_certified_result():
    """data/record_2026/ is what record.build_2026() derives from the
    certified result: 120 seats, every vote on a list, non-runners out."""
    built = record.build_2026()
    for name, df in built.items():
        disk = pd.read_csv(record.RECORD_2026_DIR / name, dtype=str)
        fresh = pd.read_csv(pd.io.common.StringIO(df.to_csv(index=False)), dtype=str)
        assert disk.equals(fresh), name
    res, cnt = built["results.csv"], built["cec_final_counts.csv"]
    assert int(res["seats"].sum()) == 120 and int(cnt["seats_official"].sum()) == 120
    assert int(cnt["votes"].sum()) == int(cnt["valid_votes"].iloc[0]) == 5_691_426
    assert not {"blue_white", "ahi"} & set(res["party_id"])          # withdrew, no votes
    assert res.loc[res["seats"] == 0, "vote_pct"].notna().all()       # ran and failed: a share
    assert dict(zip(res["party_id"], res["seats"]))["likud"] == 27


SWITCHED = r"""
import json, sys, warnings
sys.path.insert(0, sys.argv[1])       # src/ (the repo path holds a colon: no PYTHONPATH)
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import record, scrape_polls as sp, simulate as sim
import validate_bayes as vb, validate_model as vm, error_decomposition as ed, error_model as em
from polling_average import quality_from_scorecard, quality_map
polls = pd.read_csv(sp.PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
eday = pd.Timestamp(sp.ELECTION_DAY["2026"])
asof = eday - pd.Timedelta(days=1)
d = vb.harness_prepare(vb.harness_frame(polls, "2026", eday, asof, verbose=False), asof)
idx, comp_of, dropped = sim.resolve_pairs(vm.REGISTERED_PAIRS["2026"], d["components"],
                                          aliases=vb._decomp_map("2026"), fixed=True)
res = vb.apply_decomp(record.results()[lambda r: r["cycle"] == "2026"], "2026")
actual = np.zeros(len(d["components"])); unmatched = 0
for r in res.itertuples():
    hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
    if len(hit) == 1:
        actual[hit.pop()] += r.seats
    else:
        unmatched += r.seats
c = record.cec_final_counts(dtype={"cycle": str})
c = c[c["cycle"] == "2026"].reset_index(drop=True)
ids = [p if isinstance(p, str) and p else f"_unlisted_{i}" for i, p in enumerate(c["party_id"])]
pidx, _, _ = sim.resolve_pairs(vm.REGISTERED_PAIRS["2026"], ids, aliases=vb._decomp_map("2026"), fixed=True)
seats = vb.allocate_vector(c["votes"].values / c["valid_votes"].iloc[0], sim.THRESHOLD, pidx, raw=True)
full8 = quality_from_scorecard(pd.read_csv(record.PROCESSED_DIR / "backtest_pollsters.csv"))
print("JSON" + json.dumps({
    "cycles": record.CYCLES, "orders_equal": vm.ORDER == ed.ORDER == em.ORDER == vb.ORDER == record.CYCLES,
    "eday": sp.ELECTION_DAY["2026"], "table_dir": record.TABLE_DIR.name, "out_dir": vb.OUT_DIR.name,
    "n_polls": int(d["n_polls"]), "n_lists": len(d["components"]), "scorecard": vb.scorecard_tag(d),
    "pairs": len(idx), "dropped": dropped, "seats_matched": int(actual.sum()), "unmatched": int(unmatched),
    "withdrawn_in_window": sorted({"blue_white", "ahi"} & set(d["components"])),
    "seat_law": bool((seats == c["seats_official"].values).all()),
    "frames": sorted(ed._frames()), "loo_2026_is_the_eight_cycle_scorecard": quality_map(exclude_cycle="2026") == full8,
    "new_arms": sorted({"hared_off", "hared_e1", "arab_off", "trail_field"} & {a for a, _ in vb.ABLATIONS}),
    "arab_2026": vb.ARAB_TURNOUT_REC["2026"], "regime_B": "2026" in vb.ARAB_REGIMES["B"],
    "regime_A": "2026" in vb.ARAB_REGIMES["A"]}))
"""


def test_switch_on_adds_2026_and_the_eve_window_builds(root):
    env = dict(os.environ, RECORD_2026="1")
    out = subprocess.run([sys.executable, "-c", SWITCHED, str(root / "src")], cwd=root, env=env,
                         capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(next(ln for ln in out.stdout.splitlines() if ln.startswith("JSON"))[4:])
    assert got["cycles"] == EIGHT + ["2026"] and got["orders_equal"]
    assert got["eday"] == "2026-10-27"
    assert got["table_dir"] == got["out_dir"] == "record9"            # never the top-level tables
    assert (got["n_polls"], got["n_lists"]) == (238, 16)             # the eve window
    assert got["scorecard"] == "loo:2026" and got["loo_2026_is_the_eight_cycle_scorecard"]
    assert got["pairs"] == 5 and got["dropped"] == []                 # the five filed agreements
    assert got["seats_matched"] == 120 and got["unmatched"] == 0
    assert got["withdrawn_in_window"] == []                           # Blue and White, Ahi
    assert got["seat_law"]                                            # certified count -> official seats
    assert got["frames"] == EIGHT + ["2026"]
    assert got["new_arms"] == ["arab_off", "hared_e1", "hared_off", "trail_field"]
    assert got["arab_2026"] == 0.77 and got["regime_B"] and not got["regime_A"]


NEXT = r"""
import json, sys, warnings
sys.path.insert(0, sys.argv[1])
warnings.filterwarnings("ignore")
import pandas as pd
import record, scrape_polls as sp, bayes_model as bm, validate_bayes as vb, error_decomposition as ed
arms = dict(vb.ABLATIONS)
polls = pd.read_csv(sp.PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
ramp = vb.trail_ramp_params(vb.trailing_likud_params(polls, record.results()), -1.0, 2.0)
vote = ed.decompose_vote()
print("JSON" + json.dumps({
    "next": record.NEXT, "cycles": len(record.CYCLES),
    "flags": [bm.T_UNIT_VAR, bm.RESID_SPACE, bm.TRAIL_RAMP_ON], "ramp": bm.TRAIL_RAMP,
    "ramp_record": [round(ramp["mu"], 2), round(ramp["sd"], 2)],
    "resid_line": [round(float(x), 6) for x in bm.resid_line()],
    "vote_line": [round(float(vote["resid_base"]), 6), round(float(vote["resid_slope"]), 6)],
    "mirror": {k: vb.ALL_LAYERS[k] for k in record.NEXT_CONFIG["harness"]},
    "chosen_arm_is_shipped": dict(vb.ALL_LAYERS, **arms["tramp_AB"]) == vb.ALL_LAYERS,
    "cfg_2026": arms["cfg_2026"]}))
"""


def _run_next(root, **env):
    out = subprocess.run([sys.executable, "-c", NEXT, str(root / "src")], cwd=root,
                         env=dict(os.environ, **env), capture_output=True, text=True, timeout=300)
    return out


def test_next_config_needs_the_nine_cycle_record(root):
    env = {k: v for k, v in os.environ.items() if k != "RECORD_2026"}
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import record",
                          str(root / "src")], cwd=root, env=dict(env, MODEL_CONFIG="next"),
                         capture_output=True, text=True, timeout=60)
    assert out.returncode != 0 and "RECORD_2026=1" in out.stderr


def test_nine_cycles_alone_keep_the_2026_configuration(root):
    out = _run_next(root, RECORD_2026="1")
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(next(ln for ln in out.stdout.splitlines() if ln.startswith("JSON"))[4:])
    assert got["cycles"] == 9 and not got["next"]
    assert got["flags"] == [False, "seat_fix", False]
    assert got["cfg_2026"] == record.NEXT_CONFIG["harness_2026"] and not got["chosen_arm_is_shipped"]


def test_next_config_sets_production_and_the_harness_mirror(root):
    """RECORD_2026=1 MODEL_CONFIG=next: the three flags of dossier s.76 in
    bayes_model, the same configuration as the harness's "shipped", and the
    ramp's size equal to the same-weight record on nine cycles."""
    out = _run_next(root, RECORD_2026="1", MODEL_CONFIG="next")
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(next(ln for ln in out.stdout.splitlines() if ln.startswith("JSON"))[4:])
    prod = record.NEXT_CONFIG["production"]
    assert got["next"] and got["cycles"] == 9
    assert got["flags"] == [True, "vote", True] and got["ramp"] == prod["TRAIL_RAMP"]
    assert got["ramp_record"] == [prod["TRAIL_RAMP"]["mu"], prod["TRAIL_RAMP"]["sd"]]
    assert got["resid_line"] == got["vote_line"]                      # the vote-share residual line
    assert got["mirror"] == record.NEXT_CONFIG["harness"] and got["chosen_arm_is_shipped"]


def test_regrade_summary_follows_from_the_committed_rows():
    """regrade.json is what regrade9.build() derives from regrade_rows.csv:
    the chosen set passes the rule against the 2026 configuration at every
    horizon, each step of its path passes, and the two interval fixes
    without the ramp do not."""
    import regrade9
    disk = json.loads((regrade9.OUT / "regrade.json").read_text())
    assert json.loads(json.dumps(regrade9.build())) == disk
    ch = disk["chosen"]
    assert ch["arm"] == "tramp_AB" and ch["flags"] == json.loads(json.dumps(record.NEXT_CONFIG))
    assert ch["vs_2026"]["pass"] and ch["vs_2026"]["graded"] == ["eve", "D-7", "D-21"]
    assert all(g["pass"] for g in ch["path"]) and ch["own_vs_2026"]["pass"]
    by = {a["arm"]: a for a in disk["arms"]}
    assert not by["cal_AB"]["pass"] and by["cal_A"]["pass"] and by["cal_B"]["pass"]
    for kept in ("hared_off", "arab_off", "no_trail", "trail_field", "no_nstrad"):
        assert not by[kept]["pass"]                                   # the 2026 layers stay
    assert disk["baseline"]["nine"]["eve"]["med"] == 1.4651 and disk["baseline"]["eight"]["eve"]["med"] == 1.4858
