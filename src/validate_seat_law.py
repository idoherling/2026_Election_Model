"""Seat-law fidelity checks on the official record (dossier s.47).

1. The statute (Knesset Elections Law ss.81-82: threshold on ALL valid
   votes, integer quota, floor seats, highest averages, surplus agreements
   pooled only when both partners pass, inner split by the same method),
   applied in exact arithmetic to the CEC final counts
   (data/cec_final_counts.csv) with the REGISTERED surplus agreements
   (validate_model.REGISTERED_PAIRS), must reproduce the official seats in
   every graded cycle - and so must the harness's own allocator
   (validate_bayes.allocate_vector). PAST_PAIRS, as listed and as the harness
   actually applied them, are scored the same way.
2. Pairs applied per harness window (eve, D-7, D-21) before (PAST_PAIRS,
   aliases off) and after (REGISTERED_PAIRS through the DECOMP map).
3. The realised vote share of the lists outside each cycle's modelled set
   (the eve window), the record behind validate_bayes.UNMODELLED_REC.
4. Seat-law error at perfect shares: the official votes aggregated to the
   harness's columns and passed through the harness's seat law, against the
   actual seats - the part of the graded seat error that no poll could fix.

    python src/validate_seat_law.py
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pandas as pd

import simulate as _sim
import validate_bayes as vb
from scrape_polls import PROCESSED_DIR
from validate_model import (CYCLE_THRESHOLD, ORDER, PAST_PAIRS, REGISTERED_PAIRS)

COUNTS = PROCESSED_DIR.parent / "cec_final_counts.csv"
THR = {c: Fraction(1, 50) if CYCLE_THRESHOLD.get(c) == 0.02 else Fraction(13, 400) for c in ORDER}


def statutory(votes: list, valid: int, pair_idx: list, thr: Fraction, seats: int = 120):
    """ss.81(a)-(d) + s.82 in exact integer arithmetic. votes: per-list
    integer votes; pair_idx: index pairs. Returns (seats per list, ties)."""
    n = len(votes)
    part = [i for i in range(n) if votes[i] >= thr * valid]          # 81(a)
    q = sum(votes[i] for i in part) // seats                          # 81(b)
    s = {i: votes[i] // q for i in part}                              # 81(c)
    units, used = [], set()
    for a, b in pair_idx:                                             # 82(a)
        if a in s and b in s and a not in used and b not in used:
            units.append((a, b)); used |= {a, b}
    units += [(i,) for i in part if i not in used]
    uv = {u: sum(votes[i] for i in u) for u in units}
    us = {u: sum(s[i] for i in u) for u in units}
    ties = 0
    while sum(us.values()) < seats:                                   # 81(d)
        quo = {u: Fraction(uv[u], us[u] + 1) for u in units}
        m = max(quo.values()); best = [u for u in units if quo[u] == m]
        ties += len(best) > 1
        us[best[0]] += 1
    out = np.zeros(n, dtype=int)
    for u in units:
        if len(u) == 1:
            out[u[0]] = us[u]; continue
        k = us[u]; qi = sum(votes[i] for i in u) // k                 # 82(b)
        si = {i: votes[i] // qi for i in u}
        while sum(si.values()) < k:
            quo = {i: Fraction(votes[i], si[i] + 1) for i in u}
            m = max(quo.values()); best = [i for i in u if quo[i] == m]
            ties += len(best) > 1
            si[best[0]] += 1
        for i in u:
            out[i] = si[i]
    return out, ties


def list_frame(cycle: str) -> pd.DataFrame:
    d = pd.read_csv(COUNTS, dtype={"cycle": str})
    d = d[d["cycle"] == cycle].reset_index(drop=True).copy()
    d["party_id"] = [p if isinstance(p, str) and p else f"_unmodelled_{i}"
                     for i, p in enumerate(d["party_id"])]
    # the era's DECOMP identities, as the harness applies them
    d["comp"] = vb.apply_decomp(d[["party_id"]].copy(), cycle)["party_id"].values
    return d


def window_components(cycle: str, job: str) -> list:
    import xarray as xr
    with xr.open_dataset(vb.CACHE_DIR / f"{cycle}_{job}.nc", group="posterior") as ds:
        return ds.attrs["components"].split("|")


def to_columns(d: pd.DataFrame, comps: list) -> np.ndarray:
    """Column of each list in a window (-1 = not modelled)."""
    _, comp_of, _ = _sim.resolve_pairs([], comps, fixed=True)
    col = []
    for c in d["comp"]:
        hit = {comp_of.get(x) for x in c.split("+")}
        col.append(hit.pop() if len(hit) == 1 and None not in hit else -1)
    return np.array(col)


def main() -> None:
    results = pd.read_csv(PROCESSED_DIR / "results.csv", dtype={"cycle": str})
    rows, wrows, orows = [], [], []
    for cycle in ORDER:
        d = list_frame(cycle)
        valid = int(d["valid_votes"].iloc[0])
        votes = d["votes"].astype(int).tolist()
        off = d["seats_official"].values
        names = d["list_name"].fillna("").tolist()
        alias = vb._decomp_map(cycle)
        comps = list(d["comp"])
        reg_idx, _, reg_drop = _sim.resolve_pairs(REGISTERED_PAIRS[cycle], comps, aliases=alias, fixed=True)
        st, ties = statutory(votes, valid, reg_idx, THR[cycle])
        share = np.array(votes, float) / valid
        mod = vb.allocate_vector(share, float(THR[cycle]), reg_idx, raw=True)
        none, _ = statutory(votes, valid, [], THR[cycle])
        past_idx, _, past_drop = _sim.resolve_pairs(PAST_PAIRS[cycle], comps, aliases=alias, fixed=True)
        past, _ = statutory(votes, valid, past_idx, THR[cycle])
        # the pairs the shipped harness actually pooled (aliases off)
        eve_cols = window_components(cycle, "eve")
        eff_idx_w, _, _ = _sim.resolve_pairs(PAST_PAIRS[cycle], eve_cols, fixed=True)
        eff_pairs = [(eve_cols[a], eve_cols[b]) for a, b in eff_idx_w]
        col_of_list = {c: i for i, c in enumerate(comps)}
        eff_idx = []
        for a, b in eff_pairs:
            ia = next((i for i, c in enumerate(comps) if set(c.split("+")) <= set(a.split("+"))), None)
            ib = next((i for i, c in enumerate(comps) if set(c.split("+")) <= set(b.split("+"))), None)
            if ia is not None and ib is not None:
                eff_idx.append((ia, ib))
        eff, _ = statutory(votes, valid, eff_idx, THR[cycle])

        def diff(x):
            return {names[i] or d["party_id"][i]: int(x[i] - off[i]) for i in range(len(x)) if x[i] != off[i]}
        rows.append({"cycle": cycle, "registered==official": bool((st == off).all()),
                     "allocate_vector==statute": bool((mod == st).all()), "ties": ties,
                     "registered_inert": [p for p in reg_drop],
                     "no_pairs_vs_official": diff(none),
                     "past_listed_vs_official": diff(past), "past_listed_misalloc": int(np.abs(past - off).sum()),
                     "past_as_run_vs_official": diff(eff), "past_as_run_misalloc": int(np.abs(eff - off).sum())})

        # pairs applied per window
        for job in ("eve", "D7", "D21"):
            wc = window_components(cycle, job)
            before, _, bdrop = _sim.resolve_pairs(PAST_PAIRS[cycle], wc, fixed=True)
            after, _, adrop = _sim.resolve_pairs(REGISTERED_PAIRS[cycle], wc, aliases=alias, fixed=True)
            wrows.append({"cycle": cycle, "window": job, "n_before": len(before), "n_after": len(after),
                          "after": "; ".join(f"{wc[a]}~{wc[b]}" for a, b in after),
                          "dropped_before": "; ".join(f"{a}~{b}" for a, b in bdrop),
                          "not_applicable_after": "; ".join(f"{a}~{b}" for a, b in adrop)})

        # unmodelled share and the seat law at perfect shares (eve window)
        col = to_columns(d, eve_cols)
        B = len(eve_cols)
        vcol = np.zeros(B)
        for i, c in enumerate(col):
            if c >= 0:
                vcol[c] += votes[i]
        u_true = 1.0 - vcol.sum() / valid
        res = vb.apply_decomp(results[results["cycle"] == cycle], cycle)
        _, comp_of, _ = _sim.resolve_pairs([], eve_cols, fixed=True)
        actual = np.zeros(B)
        for r in res.itertuples():
            hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
            if len(hit) == 1:
                actual[hit.pop()] += r.seats
        sh = vcol / valid
        active = (sh >= 0.005) | (actual > 0)
        thr = float(THR[cycle])
        reg_w, _, _ = _sim.resolve_pairs(REGISTERED_PAIRS[cycle], eve_cols, aliases=alias, fixed=True)
        cases = {"past_as_run_renorm": vb.allocate_vector(sh, thr, eff_idx_w),
                 "registered_renorm": vb.allocate_vector(sh, thr, reg_w),
                 "registered_u0.01": vb.allocate_vector(sh / sh.sum(), thr, reg_w, raw=True, u=0.01),
                 "registered_all_valid": vb.allocate_vector(sh, thr, reg_w, raw=True)}
        o = {"cycle": cycle, "u_true": round(u_true, 5), "n_active": int(active.sum())}
        for k, s_ in cases.items():
            o[k + "_mae"] = round(float(np.abs(s_ - actual)[active].mean()), 4)
            o[k + "_misalloc"] = int(np.abs(s_ - actual).sum())
        orows.append(o)

    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
    rt = pd.DataFrame(rows)
    print("== 1. statute on the CEC final counts ==")
    print(rt[["cycle", "registered==official", "allocate_vector==statute", "ties",
              "past_listed_misalloc", "past_as_run_misalloc"]].to_string(index=False))
    for r in rows:
        print(f"  {r['cycle']}: no pairs {r['no_pairs_vs_official']} | PAST listed {r['past_listed_vs_official']}"
              f" | PAST as run {r['past_as_run_vs_official']} | inert registered pairs {r['registered_inert']}")
    print("\n== 2. pairs applied per harness window ==")
    print(pd.DataFrame(wrows).to_string(index=False))
    ot = pd.DataFrame(orows)
    print("\n== 3/4. unmodelled share and the seat law at perfect shares (eve window columns) ==")
    print(ot.to_string(index=False))
    rec = dict(zip(ot["cycle"], ot["u_true"]))
    print("\nUNMODELLED_REC =", {c: round(v, 4) for c, v in rec.items()},
          f"mean {np.mean(list(rec.values())):.4f}")
    if vb.UNMODELLED_REC and any(abs(vb.UNMODELLED_REC[c] - round(rec[c], 4)) > 1e-9 for c in rec):
        raise SystemExit("validate_bayes.UNMODELLED_REC is stale: update it from the table above")
    assert rt["registered==official"].all(), "registered pairs do not reproduce the official seats"
    assert rt["allocate_vector==statute"].all(), "harness allocator differs from the statute"
    print("\nOK: the registered agreements reproduce the official allocation in every cycle")


if __name__ == "__main__":
    main()
