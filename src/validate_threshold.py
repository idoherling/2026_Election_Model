"""Threshold calibration on the graded record (accuracy round four, #1).

Uses the horizon harness's cached posteriors (data/processed/harness_cache/
<cycle>_D<h>.nc) to project every cycle as of D-56 and D-21 under the shipped
layer configuration, then grades PASS PROBABILITIES for the lists that
mattered: those whose projected share sat within a band around the
threshold. Outputs a reliability table (predicted pass probability bins vs
realised pass rate), the straddler Brier score, and the realised drift of
straddlers between the projection date and the result, by horizon.

Writes data/processed/model_validation_threshold.csv (one row per
cycle x horizon x straddling list).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import bayes_model as bm
import os as _os
import validate_bayes as _vb
from validate_bayes import (ORDER, ELECTION_DAY, CYCLE_THRESHOLD, PAST_PAIRS,
                            VAL_BLOC_OVERRIDES, apply_decomp, decompose,
                            project_cycle, trailing_likud_params, SEED,
                            new_lists_for_cycle, new_straddler_params,
                            harness_frame, harness_prepare)
from validate_horizon import CACHE, calendar_weeks
from scrape_polls import PROCESSED_DIR
from simulate import THRESHOLD

BAND_LO, BAND_HI = -0.75, 1.50     # percentage points around the threshold
# The straddler record is a D-56/D-21 measurement: inheriting HORIZONS=56,21,7
# from a horizon run would put D-7 rows into the new-straddler estimate.
HORIZONS = [int(x) for x in _os.environ.get("THRESHOLD_HORIZONS", "56,21").split(",")]
# Ballot fidelity (HARNESS_FIDELITY=1, dossier s.46): grade on the vote
# share each list actually won (data/ran_vote_shares.csv, CEC record via the
# cited result tables), never seats/120 for a list that ran and failed (that
# scores it at 0% and turns its drift into -proj); passed = seats > 0; a
# `ran` flag marks blocks a ballot line grades. Written to
# model_validation_threshold_ran_{off,on}.csv in HARNESS_OUT_DIR (layer off /
# on) so the harness's new-straddler LOO
# parameters (read from model_validation_threshold.csv) stay the shipped ones.
RAN_SHARES = PROCESSED_DIR.parent / "ran_vote_shares.csv"


def main(layers: dict | None = None) -> pd.DataFrame:
    import arviz as az
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    rows = []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        thr = CYCLE_THRESHOLD.get(cycle, THRESHOLD)
        res = results[results["cycle"] == cycle]
        if _vb.FIDELITY:
            rv = pd.read_csv(RAN_SHARES)
            rv = rv[rv["cycle"].astype(str) == cycle]
            res = res.drop(columns="vote_pct").merge(rv[["party_id", "vote_pct"]], on="party_id", how="left")
            extra = rv[~rv["party_id"].isin(res["party_id"])]
            res = pd.concat([res, extra[["cycle", "party_id", "seats", "vote_pct"]]], ignore_index=True)
        res = apply_decomp(res, cycle)
        params = decompose(exclude_cycle=cycle)
        params["trail"] = trailing_likud_params(polls, results, exclude_cycle=cycle)
        params["new_lists"] = new_lists_for_cycle(polls, cycle)
        params["nstrad"] = new_straddler_params(exclude_cycle=cycle)
        # the shipped harness projects Arab lists through the turnout term
        # (s.43); without its LOO table project_cycle raised KeyError here
        # since 15 Oct. Pair aliases as in the other two harnesses, under
        # fidelity only (the shipped straddler record was made without them)
        params["arab_tab"] = _vb.arab_turnout_params(cycle)
        params["registered_pairs"] = _vb.REGISTERED_PAIRS[cycle]   # dossier s.47
        params["cycle"] = cycle
        if _vb.FIDELITY:
            params["pair_alias"] = _vb._decomp_map(cycle)
        for h in HORIZONS:
            nc = CACHE / f"{cycle}_D{h}.nc"
            if not nc.exists():
                continue
            asof = eday - pd.Timedelta(days=h)
            cyc = harness_frame(polls, cycle, eday, asof, verbose=False)
            data = harness_prepare(cyc, asof)
            idata = az.from_netcdf(nc)
            _vb.check_signature(idata, data, nc)   # components / n_obs / latent width
            project_cycle.job = f"{cycle}_D{h}"     # layer 'posterior' (refit arms)
            L = dict({"anchors": False}, **(layers or {}))
            seats, blocs, base, comp_of = project_cycle(
                data, idata, eday, thr, PAST_PAIRS[cycle], params,
                VAL_BLOC_OVERRIDES.get(cycle), np.random.default_rng(SEED + h),
                resid_scale=bm.RESID_SCALE, weeks_override=calendar_weeks(h), layers=L)
            actual_share = np.zeros(seats.shape[1])
            act_seats = np.zeros(seats.shape[1])
            ran = np.zeros(seats.shape[1], bool)
            for r in res.itertuples():
                hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
                if len(hit) == 1:
                    j = hit.pop()
                    if _vb.FIDELITY and pd.isna(r.vote_pct) and r.seats == 0:
                        raise ValueError(f"{cycle} {r.party_id}: ran and failed, no vote share")
                    v = r.vote_pct if pd.notna(r.vote_pct) else r.seats / 120 * 100
                    actual_share[j] += float(v)
                    act_seats[j] += r.seats
                    ran[j] = True
            pp = (seats >= 1).mean(axis=0)
            for i, comp in enumerate(data["components"]):
                proj = base[i] * 100
                if (proj - thr * 100) < BAND_LO or (proj - thr * 100) > BAND_HI:
                    continue
                rows.append({"cycle": cycle, "horizon": h, "list": comp,
                             "new": bool(set(comp.split("+")) <= params["new_lists"]),
                             "threshold": thr * 100, "proj_share": proj,
                             "p_pass": float(pp[i]), "actual_share": actual_share[i],
                             "passed": bool(act_seats[i] > 0) if _vb.FIDELITY
                             else bool(actual_share[i] >= thr * 100),
                             "ran": bool(ran[i]),
                             "drift": actual_share[i] - proj})
    df = pd.DataFrame(rows)
    if _vb.FIDELITY:
        tag = "off" if (layers or {}).get("new_straddler") is False else "on"
        df.to_csv(_vb.OUT_DIR / f"model_validation_threshold_ran_{tag}.csv", index=False)
    elif not (layers or {}).get("new_straddler"):
        # model_validation_threshold.csv is the committed straddler record
        # that new_straddler_params reads (LOO). Since the arab_tab fix this
        # harness projects with the Arab term on, so a casual run would move
        # those inputs silently: rewriting it takes THRESHOLD_WRITE=1 (a
        # graded re-measurement); otherwise the run goes to HARNESS_OUT_DIR.
        if _os.environ.get("THRESHOLD_WRITE") == "1":
            df.to_csv(PROCESSED_DIR / "model_validation_threshold.csv", index=False)
        else:
            df.to_csv(_vb.OUT_DIR / "model_validation_threshold_run.csv", index=False)
    if df.empty:
        print("no cached horizon posteriors yet - run validate_horizon first")
        return df
    print(df.round(3).to_string(index=False))
    for h, g in df.groupby("horizon"):
        brier = np.mean((g["p_pass"] - g["passed"]) ** 2)
        print(f"\nD-{h}: {len(g)} straddlers | Brier {brier:.3f} | realised pass {g['passed'].mean():.2f} "
              f"vs mean p_pass {g['p_pass'].mean():.2f} | mean drift {g['drift'].mean():+.2f} pp "
              f"(sd {g['drift'].std():.2f})")
        bins = pd.cut(g["p_pass"], [0, 0.25, 0.5, 0.75, 1.0], include_lowest=True)
        print(g.groupby(bins, observed=True).agg(n=("passed", "size"), p_pred=("p_pass", "mean"),
                                                 p_real=("passed", "mean")).round(2).to_string())
    return df


if __name__ == "__main__":
    # ALL_LAYERS carries new_straddler=True, so the "without" run must turn
    # it off explicitly (the old comparison set the layer against itself)
    base = main(layers={"new_straddler": False} if _vb.FIDELITY else None)
    if not base.empty and base["new"].any():
        print("\n=== with the new-straddler layer (LOO parameters) ===")
        lay = main(layers={"new_straddler": True})
        for h in sorted(base["horizon"].unique()):
            b = base[base.horizon == h]; l = lay[lay.horizon == h]
            print(f"D-{h}: Brier all {np.mean((b.p_pass-b.passed)**2):.3f} -> {np.mean((l.p_pass-l.passed)**2):.3f} | "
                  f"new only {np.mean((b[b.new].p_pass-b[b.new].passed)**2):.3f} -> {np.mean((l[l.new].p_pass-l[l.new].passed)**2):.3f} | "
                  f"established {np.mean((b[~b.new].p_pass-b[~b.new].passed)**2):.3f} -> {np.mean((l[~l.new].p_pass-l[~l.new].passed)**2):.3f}")
