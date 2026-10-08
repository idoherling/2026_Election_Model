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
"""
import sys
import pandas as pd
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "data" / "processed"


def main(cand: str, hmode: str | None = None) -> None:
    a = pd.read_csv(P / "model_validation_ablation.csv")
    cols = ["seat_mae_median", "seat_mae", "coverage_90", "threshold_brier"]
    base = a[a.ablation == "shipped"].set_index("cycle")[cols]
    c = a[a.ablation == cand].set_index("cycle")[cols]
    if c.empty:
        print(f"no ablation named {cand!r}; have {sorted(a.ablation.unique())}")
        return
    d = (c - base).round(3)
    print(f"=== eight-cycle harness: {cand} vs shipped (candidate - shipped) ===")
    print(pd.concat({"shipped": base.round(3), "cand": c.round(3), "delta": d}, axis=1).to_string())
    pooled = pd.DataFrame({"shipped": base.mean(), "cand": c.mean(), "delta": (c.mean() - base.mean())}).round(3)
    print("\npooled:"); print(pooled.to_string())
    wins = int((d["seat_mae_median"] < -1e-9).sum()); ties = int((d["seat_mae_median"].abs() <= 1e-9).sum())
    losses = int((d["seat_mae_median"] > 1e-9).sum())
    print(f"\nLOO median-MAE folds: wins {wins} / ties {ties} / losses {losses}")
    if hmode:
        h = pd.read_csv(P / "model_validation_horizon.csv")
        hc = ["seat_mae", "coverage_90", "threshold_brier", "interval_score"]
        for hz in sorted(h.horizon.unique()):
            b = h[(h["mode"] == "calendar") & (h.horizon == hz)].set_index("cycle")[hc]
            x = h[(h["mode"] == hmode) & (h.horizon == hz)].set_index("cycle")[hc]
            if x.empty:
                print(f"\nD-{hz}: no horizon mode {hmode!r}"); continue
            print(f"\n=== horizon D-{hz}: {hmode} vs calendar ===")
            print(pd.DataFrame({"calendar": b.mean(), "cand": x.mean(), "delta": x.mean() - b.mean()}).round(3).to_string())
            dd = (x["seat_mae"] - b["seat_mae"])
            print(f"per-cycle MAE wins {int((dd < -1e-9).sum())} / ties {int((dd.abs() <= 1e-9).sum())} / losses {int((dd > 1e-9).sum())}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
