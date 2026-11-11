"""Compare a candidate configuration with the shipped baseline on both
harnesses, from the CSVs they write.

    python src/harness_compare.py <ablation_name> [<horizon_mode>]

Prints pooled and per-cycle deltas (median-seat MAE, mean MAE, 90%
coverage, threshold Brier) from model_validation_ablation.csv against the
"shipped" row, and - if a horizon mode name is given - the D-56/D-21
deltas (MAE, coverage, Brier, interval score) from
model_validation_horizon.csv against "calendar". Leave-one-cycle-out win
counts are the standing shipping rule: a layer ships when it wins (or
ties) the median-seat MAE in every fold, or wins the pooled score on every
metric without losing coverage.

    python src/harness_compare.py <ablation_name> [<horizon_mode>] --fixed

grades both configurations on the SHIPPED configuration's list mask (the
*_fixed columns) - needed when the candidate moves lists across the 0.5%
scoring cutoff (2026-10-10, dossier s.41).
"""
from __future__ import annotations   # the venv is Python 3.9 (str | None)

import sys
import pandas as pd
from pathlib import Path

import os
import record
P = Path(os.environ.get("HARNESS_OUT_DIR") or record.TABLE_DIR)   # HARNESS_OUT_DIR: ballot-fidelity runs write apart; record9/ under RECORD_2026


def main(cand: str, hmode: str | None = None, fixed: bool = False) -> None:
    sfx = "_fixed" if fixed else ""
    a = pd.read_csv(P / "model_validation_ablation.csv")
    cols = [c + sfx for c in ["seat_mae_median", "seat_mae", "coverage_90", "threshold_brier"]]
    base = a[a.ablation == "shipped"].set_index("cycle")[cols]
    c = a[a.ablation == cand].set_index("cycle")[cols]
    if c.empty:
        print(f"no ablation named {cand!r}; have {sorted(a.ablation.unique())}")
        return
    common = base.index.intersection(c.index)
    if len(common) < len(base.index):
        print(f"WARNING: {cand} is scored in {len(common)} of {len(base.index)} cycles; "
              f"comparing on the common cycles only: {sorted(common)}")
        base, c = base.loc[common], c.loc[common]
    d = (c - base).round(3)
    print(f"=== {record.N_WORD}-cycle harness: {cand} vs shipped (candidate - shipped) ===")
    print(pd.concat({"shipped": base.round(3), "cand": c.round(3), "delta": d}, axis=1).to_string())
    pooled = pd.DataFrame({"shipped": base.mean(), "cand": c.mean(), "delta": (c.mean() - base.mean())}).round(3)
    print("\npooled:"); print(pooled.to_string())
    dm = d["seat_mae_median" + sfx]
    wins = int((dm < -1e-9).sum()); ties = int((dm.abs() <= 1e-9).sum())
    losses = int((dm > 1e-9).sum())
    print(f"\nLOO median-MAE folds: wins {wins} / ties {ties} / losses {losses}")
    if hmode:
        h = pd.read_csv(P / "model_validation_horizon.csv")
        hc = [c + sfx for c in ["seat_mae", "coverage_90", "threshold_brier", "interval_score"]]
        for hz in sorted(h.horizon.unique()):
            b = h[(h["mode"] == "calendar") & (h.horizon == hz)].set_index("cycle")[hc]
            x = h[(h["mode"] == hmode) & (h.horizon == hz)].set_index("cycle")[hc]
            if x.empty:
                print(f"\nD-{hz}: no horizon mode {hmode!r}"); continue
            print(f"\n=== horizon D-{hz}: {hmode} vs calendar ===")
            print(pd.DataFrame({"calendar": b.mean(), "cand": x.mean(), "delta": x.mean() - b.mean()}).round(3).to_string())
            dd = (x["seat_mae" + sfx] - b["seat_mae" + sfx])
            print(f"per-cycle MAE wins {int((dd < -1e-9).sum())} / ties {int((dd.abs() <= 1e-9).sum())} / losses {int((dd > 1e-9).sum())}")


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if x != "--fixed"]
    main(args[0], args[1] if len(args) > 1 else None, fixed="--fixed" in sys.argv)
