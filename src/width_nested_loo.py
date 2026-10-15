"""Nested leave-one-cycle-out test of the residual-shock width (RESID_SCALE).

The harness's width grid re-projects every cycle under several width factors
(validate_bayes WIDTH_GRID -> model_validation_width.csv). Choosing the width
that minimises the pooled interval score over ALL cycles and then grading it
on the same cycles would select and grade on the same record. Here each
cycle is held out in turn: the width is chosen on the other seven cycles
(minimum mean interval score, Gneiting & Raftery 2007), and the held-out
cycle is scored at that width. The result is compared with the shipped
width (bayes_model.RESID_SCALE) scored on the same held-out cycles.

    python src/width_nested_loo.py [path/to/model_validation_width.csv ...]

Several CSVs (one per harness seed) are averaged cycle by cycle first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
METRICS = ["interval_score", "coverage_90", "seat_mae", "threshold_brier"]


def main(paths: list[str]) -> None:
    import bayes_model as bm
    files = [Path(p) for p in paths] or [ROOT / "data" / "processed" / "model_validation_width.csv"]
    w = pd.concat([pd.read_csv(p, dtype={"cycle": str}) for p in files])
    w = w.groupby(["cycle", "width"], as_index=False)[METRICS].mean()
    shipped = float(bm.RESID_SCALE)
    widths = sorted(w["width"].unique())
    cycles = sorted(w["cycle"].unique())
    if shipped not in widths:
        print(f"shipped width {shipped} is not on the grid {widths}")
        return
    rows = []
    for c in cycles:
        train = w[w["cycle"] != c].groupby("width")["interval_score"].mean()
        pick = float(train.idxmin())
        held = w[w["cycle"] == c].set_index("width")
        rows.append({"cycle": c, "picked": pick,
                     **{f"{m}_nested": float(held.loc[pick, m]) for m in METRICS},
                     **{f"{m}_shipped": float(held.loc[shipped, m]) for m in METRICS}})
    r = pd.DataFrame(rows)
    print(f"grid {widths}; shipped {shipped}; {len(files)} harness file(s) averaged")
    print(r[["cycle", "picked"] + [f"{m}_{k}" for m in METRICS for k in ("shipped", "nested")]]
          .round(3).to_string(index=False))
    print("\npooled held-out (nested pick vs shipped):")
    for m in METRICS:
        a, b = r[f"{m}_shipped"].mean(), r[f"{m}_nested"].mean()
        print(f"  {m:16s} shipped {a:.4f}  nested {b:.4f}  delta {b - a:+.4f}")
    d = r["interval_score_nested"] - r["interval_score_shipped"]
    print(f"interval-score folds: wins {(d < -1e-9).sum()} / ties {(d.abs() <= 1e-9).sum()} / losses {(d > 1e-9).sum()}")
    print("picked widths by fold:", dict(zip(r.cycle, r.picked)))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    main(sys.argv[1:])
