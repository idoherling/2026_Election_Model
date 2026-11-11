"""The nine-cycle regrade (dossier s.76): what the 2026 result changes in
the model for the next election.

Pools the harness runs over the three seeds, applies the standing shipping
rule (s.53, amended s.55) and writes, under data/processed/record9/:

  regrade_rows.csv   one row per record x horizon x cycle x seed x arm
  constants_8.json   the record-derived constants on eight cycles
  constants_9.json   the same on nine (RECORD_2026=1)
  regrade.json       baselines, verdicts, the chosen set and its path, the
                     constants side by side (the insights page reads it)

The runs (each writes model_validation_ablation.csv or
model_validation_horizon.csv into its own directory; about 2.5 minutes per
seed at the eve and 4.5 at the horizons for ten arms):

  eve       RECORD_2026=1 HARNESS_SEED_OFFSET=<0|100|200> HARNESS_SKIP_WIDTH=1
            HARNESS_ABLATIONS=shipped,<arm>,... HARNESS_OUT_DIR=<dir>/eve_s<offset>
            python src/validate_bayes.py
  D-7, D-21 RECORD_2026=1 HARNESS_SEED_OFFSET=<offset> HORIZONS=7,21 HORIZON_SKIP_GRID=1
            HORIZON_LAYERS="$(RECORD_2026=1 python src/regrade9.py --layers <arm>,...)"
            HARNESS_OUT_DIR=<dir>/hz_s<offset> python src/validate_horizon.py

  without RECORD_2026 the same commands grade the eight-cycle record; with
  MODEL_CONFIG=next as well, "shipped" is the next-election configuration.

Then:

  python src/regrade9.py --collect 9=<dir> [9=<dir> ...] 8=<dir> 9next=<dir>
  python src/regrade9.py --constants            (once without RECORD_2026)
  RECORD_2026=1 python src/regrade9.py --constants
  python src/regrade9.py                        (regrade.json from the rows)

The rule, as s.70.3 applied it: at each of the eve, D-7 and D-21, pooled
over seed offsets 0 / 100 / 200 on the shipped list mask, a candidate must
win or tie (|d| < 0.1 seat) median MAE in every leave-one-cycle-out fold,
with mean MAE, threshold Brier and interval score not worse beyond 0.010
seat, 0.0010 and 0.05, and coverage no further from 0.90.
"""
from __future__ import annotations   # the venv is Python 3.9

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import record

OUT = record.RECORD9_DIR
ROWS = OUT / "regrade_rows.csv"
M = {"med": "seat_mae_median_fixed", "mean": "seat_mae_fixed", "cov": "coverage_90_fixed",
     "brier": "threshold_brier_fixed", "isc": "interval_score_fixed"}
FLOOR = {"mean": 0.010, "brier": 0.0010, "isc": 0.05}
TIE = 0.1
HZ = ["eve", "D-7", "D-21"]

# what was graded, by the question 2026 raised (s.74 "Where the model missed")
GROUPS = {
    "haredi": ["hared_alloc", "hared_off", "hared_e1"],
    "arab": ["arab_add_e0", "arab_turnA", "arab_turnB", "arab_e1_prev", "arab_off"],
    "trail": ["no_trail", "trail_full", "trail_field", "trail_ramp_sat", "tramp_m", "tramp05_m"],
    "width": ["cal_A", "cal_B", "cal_AB", "cal_D", "resid_hybrid", "hier_H1"],
    "straddler": ["no_nstrad", "nstrad_ran", "nstrad_fixed"],
    "sets": ["ramp_A", "ramp_B", "ramp_AB", "tramp_A", "tramp_B", "tramp_AB"],
}
CHOSEN = "tramp_AB"
# the order in which each step passes the rule against the one before it
PATH = [("tramp_m", "shipped"), ("tramp_B", "tramp_m"), ("tramp_AB", "tramp_B")]
# comparisons reported beside the choice (none of them a shipping test)
ASIDES = [("tramp_A", "tramp_m"), ("tramp_AB", "tramp_A"), ("tramp_AB", "ramp_AB"),
          ("ramp_AB", "tramp_AB"), ("tramp_m", "trail_ramp_sat"), ("trail_ramp_sat", "tramp_m"),
          ("cal_B", "cal_A"), ("cal_A", "cal_B"), ("tramp_AB", "cal_AB")]


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------
def _read(run_dir: str) -> pd.DataFrame:
    ev, hz = [], []
    for f in sorted(glob.glob(f"{run_dir}/eve_s*/model_validation_ablation.csv")):
        ev.append(pd.read_csv(f, dtype={"cycle": str}).assign(seed=int(f.split("eve_s")[1].split("/")[0])))
    for f in sorted(glob.glob(f"{run_dir}/hz_s*/model_validation_horizon.csv")):
        hz.append(pd.read_csv(f, dtype={"cycle": str}).assign(seed=int(f.split("hz_s")[1].split("/")[0])))
    cols = ["hz", "cycle", "seed", "arm", "p_nb61", "nb_actual"] + list(M.values())
    out = []
    if ev:
        out.append(pd.concat(ev).rename(columns={"ablation": "arm"}).assign(hz="eve")[cols])
    if hz:
        h = pd.concat(hz).rename(columns={"mode": "arm"})
        h = h[h["arm"] != "plain"].assign(hz=lambda d: "D-" + d["horizon"].astype(str))
        out.append(h.replace({"arm": {"calendar": "shipped"}})[cols])
    if not out:
        raise SystemExit(f"no harness output under {run_dir}")
    return pd.concat(out, ignore_index=True).rename(columns={v: k for k, v in M.items()})


def collect(specs: list) -> pd.DataFrame:
    """specs: ["9=<dir>", "8=<dir>", "9next=<dir>", ...]. An arm run in two
    directories of one record must agree (same seeds, same code)."""
    frames = []
    for spec in specs:
        rec, run_dir = spec.split("=", 1)
        frames.append(_read(run_dir).assign(record=rec))
    d = pd.concat(frames, ignore_index=True)
    key = ["record", "hz", "cycle", "seed", "arm"]
    spread = d.groupby(key)[list(M) + ["p_nb61"]].agg(lambda x: x.max() - x.min()).max().max()
    if spread > 1e-9:
        raise SystemExit(f"the same arm differs between run directories (max spread {spread:.2e})")
    d = d.drop_duplicates(key).sort_values(key).reset_index(drop=True)
    return d[key + ["p_nb61", "nb_actual"] + list(M)].round(6)


# ---------------------------------------------------------------------------
# the rule
# ---------------------------------------------------------------------------
def folds(rows: pd.DataFrame, rec: str) -> pd.DataFrame:
    """Three-seed mean per (hz, arm, cycle) on one record."""
    d = rows[rows["record"] == rec].copy()
    d["bloc_brier"] = (d["p_nb61"] - (d["nb_actual"] >= 61)) ** 2
    return d.groupby(["hz", "arm", "cycle"], sort=True)[list(M) + ["bloc_brier", "p_nb61"]].mean()


def versus(f: pd.DataFrame, hz: str, arm: str, base: str = "shipped") -> dict:
    """One horizon of the rule: arm against base."""
    b, x = f.loc[(hz, base)], f.loc[(hz, arm)]
    common = b.index.intersection(x.index)
    b, x = b.loc[common], x.loc[common]
    dm, pb, px = x - b, b.mean(), x.mean()
    dp = px - pb
    why = []
    lost = dm["med"][dm["med"] >= TIE - 1e-9]
    if len(lost):
        why.append("fold " + ", ".join(f"{c} {v:+.3f}" for c, v in lost.items()))
    for k, fl in FLOOR.items():
        if dp[k] > fl + 1e-9:
            why.append(f"{k} {dp[k]:+.4f}")
    if abs(px["cov"] - 0.90) > abs(pb["cov"] - 0.90) + 1e-9:
        why.append(f"coverage {pb['cov']:.3f} to {px['cov']:.3f}")
    return {"pass": not why, "why": "; ".join(why),
            "d": {k: round(float(dp[k]), 4) for k in ("med", "mean", "brier", "isc", "bloc_brier")},
            "cov": [round(float(pb["cov"]), 4), round(float(px["cov"]), 4)],
            "folds": {"win": int((dm["med"] <= -TIE).sum()), "tie": int((dm["med"].abs() < TIE).sum()),
                      "loss": int((dm["med"] >= TIE - 1e-9).sum())}}


def grade(f: pd.DataFrame, arm: str, base: str = "shipped") -> dict:
    hz = {h: versus(f, h, arm, base) for h in HZ if (h, arm) in f.index and (h, base) in f.index}
    return {"arm": arm, "vs": base, "pass": len(hz) == len(HZ) and all(v["pass"] for v in hz.values()),
            "graded": sorted(hz, key=HZ.index), "hz": hz}


def pooled(f: pd.DataFrame, arm: str = "shipped") -> dict:
    return {h: {k: round(float(v), 4) for k, v in f.loc[(h, arm)][list(M) + ["bloc_brier"]].mean().items()}
            for h in HZ if (h, arm) in f.index}


# ---------------------------------------------------------------------------
# the record-derived constants
# ---------------------------------------------------------------------------
CONSTANTS = [   # (key, what it is, units)
    ("bloc_sd", "Bloc swing, standard deviation", "seats"),
    ("haredi_e0_mean", "Haredi family error, mean (the lift is its negative)", "seats"),
    ("haredi_e1_sd", "Haredi family error, standard deviation", "seats"),
    ("haredi_s_shas", "Share of the haredi lift given to Shas by its lineage record", "share"),
    ("arab_e0_mean", "Arab lists, mean final-poll error", "seats"),
    ("arab_e1_sd", "Arab lists, standard deviation", "seats"),
    ("arab_reg_k", "Arab turnout pass-through", "ratio"),
    ("arab_reg_se_k", "Arab turnout pass-through, standard error", "ratio"),
    ("arab_reg_a", "Arab turnout regression, intercept", "seats"),
    ("arab_T_mean_regime_B", "Arab turnout, mean of the cycles with a joint list", "share"),
    ("trail_mu", "Trailing-Likud beat, cliff record: mean", "seats"),
    ("trail_sd", "Trailing-Likud beat, cliff record: standard deviation", "seats"),
    ("trail_ramp_mu", "Trailing-Likud beat, ramp record: mean", "seats"),
    ("trail_ramp_sd", "Trailing-Likud beat, ramp record: standard deviation", "seats"),
    ("trail_ramp_n_eff", "Trailing-Likud ramp record, effective cycles", "cycles"),
    ("nstrad_seat_mu", "New list near the threshold, drift: mean", "points"),
    ("nstrad_seat_sd", "New list near the threshold, drift: standard deviation", "points"),
    ("nstrad_seat_n", "New list near the threshold, cases", "lists"),
    ("resid_seat_fix_base", "Per-list residual, seat record: base", "seats"),
    ("resid_seat_fix_slope", "Per-list residual, seat record: slope per seat", "ratio"),
    ("resid_vote_base", "Per-list residual, vote-share record: base", "seats"),
    ("resid_vote_slope", "Per-list residual, vote-share record: slope per seat", "ratio"),
    ("unmodelled_mean", "Vote share outside the modelled lists, mean", "share"),
]


def constants() -> dict:
    """The constants production derives from the record, on the record the
    environment selects (eight cycles, or nine under RECORD_2026=1)."""
    import contextlib
    import io
    import warnings
    warnings.filterwarnings("ignore")
    with contextlib.redirect_stdout(io.StringIO()):
        import bayes_model as bm
        import error_decomposition as ed
        import scrape_polls as sp
        import validate_bayes as vb
        from polling_average import quality_map
    polls = pd.read_csv(sp.PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = record.results()
    p, pf, pv = ed.decompose(), ed.decompose(index_fix=True), ed.decompose_vote()
    out = {"n_cycles": len(ed.ORDER), "bloc_sd": p["bloc_sd"],
           "haredi_e0_mean": p["family_e0"]["haredi"][0], "haredi_e0_sd": p["family_e0"]["haredi"][1],
           "haredi_e1_mean": p["family"]["haredi"][0], "haredi_e1_sd": p["family"]["haredi"][1],
           "arab_e0_mean": p["family_e0"]["arab"][0], "arab_e0_sd": p["family_e0"]["arab"][1],
           "arab_e1_mean": p["family"]["arab"][0], "arab_e1_sd": p["family"]["arab"][1],
           "resid_seat_fix_base": pf["resid_base"], "resid_seat_fix_slope": pf["resid_slope"],
           "resid_vote_base": pv["resid_base"], "resid_vote_slope": pv["resid_slope"]}
    hl = bm.haredi_lineage_share()
    out["haredi_s_shas"] = hl["s_shas"]
    # the Arab turnout regression on the full record: the family's final-poll
    # error on the error a turnout change alone implies (arab_turnout_params)
    prev = dict(zip(vb.ORDER, ["2006"] + list(vb.ORDER[:-1])))
    fr = ed._frames()
    e0, imp, rows = [], [], {}
    for c in vb.ORDER:
        a = fr[c][fr[c]["family"] == "arab"]
        if a.empty:
            continue
        r = vb.ARAB_TURNOUT_REC[c] / vb.ARAB_TURNOUT_REC[prev[c]]
        e0.append(float(a["error"].sum()))
        imp.append(-(r - 1.0) * float(a["polled"].sum()))
        rows[c] = {"error": round(e0[-1], 2), "implied": round(imp[-1], 2),
                   "turnout": vb.ARAB_TURNOUT_REC[c], "turnout_prev": vb.ARAB_TURNOUT_REC[prev[c]]}
    X = np.c_[np.ones(len(imp)), imp]
    (a_, k_), *_ = np.linalg.lstsq(X, np.array(e0), rcond=None)
    resid = np.array(e0) - X @ np.array([a_, k_])
    cov = float(resid @ resid) / (len(e0) - 2) * np.linalg.inv(X.T @ X)
    out.update({"arab_reg_a": float(a_), "arab_reg_k": float(k_), "arab_reg_se_a": float(np.sqrt(cov[0, 0])),
                "arab_reg_se_k": float(np.sqrt(cov[1, 1])), "arab_reg_rows": rows,
                "arab_T_mean_regime_B": float(np.mean([vb.ARAB_TURNOUT_REC[c] for c in vb.ORDER
                                                       if c in vb.ARAB_REGIMES["B"]]))})
    tp = vb.trailing_likud_params(polls, results)
    ramp = vb.trail_ramp_params(tp, -1.0, 2.0)
    out.update({"trail_mu": tp["mu"], "trail_sd": tp["sd"], "trail_n": tp["n"],
                "trail_record": {c: [round(float(v[0]), 2), round(float(v[1]), 2)] for c, v in tp["record"].items()},
                "trail_ramp_mu": ramp["mu"], "trail_ramp_sd": ramp["sd"], "trail_ramp_n_eff": ramp.get("n_eff")})
    for rec in ("seat", "ran", "fixed"):
        ns = vb.new_straddler_params(record=rec)
        out.update({f"nstrad_{rec}_mu": ns["mu"], f"nstrad_{rec}_sd": ns["sd"], f"nstrad_{rec}_n": ns["n"]})
    q = quality_map()
    out["scorecard_q"] = {k: float(q[k]) for k in sorted(q)}
    out["unmodelled_mean"] = float(np.mean(list(vb.UNMODELLED_REC.values())))
    return json.loads(json.dumps(out, default=float))


# ---------------------------------------------------------------------------
# regrade.json
# ---------------------------------------------------------------------------
def build() -> dict:
    rows = pd.read_csv(ROWS, dtype={"cycle": str, "record": str})
    f8, f9, fn = folds(rows, "8"), folds(rows, "9"), folds(rows, "9next")
    arms9 = set(f9.index.get_level_values(1))
    arms8 = set(f8.index.get_level_values(1))
    table = []
    for group, names in GROUPS.items():
        for a in names:
            if a not in arms9:
                continue
            g9 = grade(f9, a)
            g8 = grade(f8, a) if a in arms8 else None
            table.append({"arm": a, "group": group, "pass": g9["pass"], "hz": g9["hz"],
                          # the eight-cycle grade on today's code: None = not run;
                          # "graded" lists the horizons it was run at and
                          # "pass" is over those horizons only
                          "eight": None if g8 is None else {"pass": all(v["pass"] for v in g8["hz"].values()),
                                                            "graded": g8["graded"],
                                                            "why": {h: v["why"] for h, v in g8["hz"].items()}}})
    c8 = json.loads((OUT / "constants_8.json").read_text())
    c9 = json.loads((OUT / "constants_9.json").read_text())
    fold26 = {h: {k: round(float(v), 4) for k, v in f9.loc[(h, "shipped", "2026")].items()} for h in HZ}
    fold26_next = {h: {k: round(float(v), 4) for k, v in f9.loc[(h, CHOSEN, "2026")].items()} for h in HZ}
    return {
        "rule": {"tie": TIE, "floors": FLOOR, "seeds": [0, 100, 200], "horizons": HZ},
        "baseline": {"eight": pooled(f8), "nine": pooled(f9), "fold_2026": fold26},
        "arms": table,
        "passing": [r["arm"] for r in table if r["pass"]],
        "chosen": {"arm": CHOSEN, "flags": record.NEXT_CONFIG,
                   "vs_2026": grade(f9, CHOSEN), "pooled": pooled(f9, CHOSEN), "fold_2026": fold26_next,
                   "path": [grade(f9, a, b) for a, b in PATH],
                   "asides": [grade(f9, a, b) for a, b in ASIDES],
                   # the same configuration as "shipped" under MODEL_CONFIG=next,
                   # on its own list mask: the baseline for the next cycle
                   "own_baseline": pooled(fn), "own_vs_2026": grade(fn, "shipped", "cfg_2026")},
        "constants": [{"key": k, "label": lab, "unit": u, "eight": c8.get(k), "nine": c9.get(k)}
                      for k, lab, u in CONSTANTS],
        "arab_rows": c9["arab_reg_rows"], "trail_record": c9["trail_record"],
        "scorecard_q": {"eight": c8["scorecard_q"], "nine": c9["scorecard_q"]},
    }


def main(argv: list) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if argv[:1] == ["--layers"]:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            import validate_bayes as vb
        flags = dict(vb.ABLATIONS)
        print(";".join(f"{a}:{json.dumps(flags[a])}" for a in argv[1].split(",")))
        return 0
    if argv[:1] == ["--collect"]:
        d = collect(argv[1:])
        d.to_csv(ROWS, index=False)
        print(f"wrote {ROWS} ({len(d)} rows; "
              + ", ".join(f"record {r}: {g['arm'].nunique()} arms" for r, g in d.groupby("record")) + ")")
        return 0
    if argv[:1] == ["--constants"]:
        c = constants()
        path = OUT / f"constants_{c['n_cycles']}.json"
        path.write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {path}")
        return 0
    out = build()
    (OUT / "regrade.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    ch = out["chosen"]
    print(f"nine-cycle regrade: {len(out['arms'])} arms, passing {out['passing']}")
    print(f"chosen {ch['arm']}: " + "; ".join(
        f"{h} median {v['d']['med']:+.3f}, mean {v['d']['mean']:+.3f}, Brier {v['d']['brier']:+.4f}, "
        f"interval {v['d']['isc']:+.3f}, coverage {v['cov'][0]:.3f} to {v['cov'][1]:.3f}"
        for h, v in ch["vs_2026"]["hz"].items()))
    print("path: " + "; ".join(f"{g['arm']} vs {g['vs']} {'pass' if g['pass'] else 'FAIL'}" for g in ch["path"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
