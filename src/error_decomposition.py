"""Sequential decomposition of historical final-poll errors, 2009-2022.

The projection layer applies election-day shocks in a fixed order (bloc
swing, family totals, party-anchored means, per-list residual). This module
calibrates ALL of them from the same sequential decomposition of the
eight-cycle record, so no component is counted twice:

  e0  raw signed error (final-poll average - actual), per cycle x list
  e1  = e0 minus the cycle's bloc swing, distributed proportionally
  e2  = e1 minus the cycle's Arab/haredi family totals (own family)
  e3  = e2 minus the party anchors:
          likud    - lists containing Likud (its record: polls understate it)
          leader   - the cycle's largest remaining list
      residual -> per-list shock scale (fit vs list size)

get_error_params(exclude_cycle=...) returns everything the projection needs,
leave-one-cycle-out for validation. Full-sample values are written to
data/processed/error_decomposition.csv by running this module directly.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from backtest import FINAL_WINDOW
from bias_audit import block_frame, window_polls
from scrape_polls import ELECTION_DAY, PROCESSED_DIR

ORDER = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
NB_FAMILIES = {"right", "haredi"}


@lru_cache(maxsize=1)
def _frames():
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    frames = {}
    for cycle, res in results.groupby("cycle"):
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        f = block_frame(window_polls(polls, cycle, eday, FINAL_WINDOW, 0), res)
        f = f[(f["actual"] > 0) | (f["polled"] >= 0.5)].copy()
        f["error"] = f["polled"] - f["actual"]
        f["is_nb"] = f["family"].isin(NB_FAMILIES)
        f["has_likud"] = f["components"].str.split("+").map(
            lambda cs: "likud" in cs)
        frames[cycle] = f
    return frames


@lru_cache(maxsize=16)
def decompose(exclude_cycle: str | None = None):
    """Per-cycle component estimates plus pooled residual rows."""
    rows_resid, bloc_totals = [], {}
    fam_totals = {"arab": {}, "haredi": {}}
    likud_e2, leader_e2 = {}, {}

    for cycle, f0 in _frames().items():
        f = f0.copy()
        w = f["polled"].clip(lower=0.1)

        # 1. bloc swing: NB-side total error, removed proportionally both ways
        nb, rest = f["is_nb"], ~f["is_nb"]
        delta = float(f.loc[nb, "error"].sum())
        bloc_totals[cycle] = delta
        f["e1"] = f["error"] - np.where(
            nb, delta * w / w[nb].sum(), -delta * w / w[rest].sum())

        # 2. family totals (own family only)
        f["e2"] = f["e1"]
        for fam in ("arab", "haredi"):
            in_f = f["family"] == fam
            if not in_f.any():
                continue
            t = float(f.loc[in_f, "e1"].sum())
            fam_totals[fam][cycle] = t
            f.loc[in_f, "e2"] = f.loc[in_f, "e1"] - t * w[in_f] / w[in_f].sum()

        # 3. party anchors: Likud, then the largest remaining list
        f["e3"] = f["e2"]
        lk = f["has_likud"]
        if lk.any():
            likud_e2[cycle] = float(f.loc[lk, "e2"].mean())
        others = f[~lk]
        if len(others):
            lead = others["actual"].idxmax()
            leader_e2[cycle] = float(f.loc[lead, "e2"])
        rows_resid.append(f.assign(cycle=cycle))

    use = [c for c in ORDER if c != exclude_cycle]
    resid = pd.concat(rows_resid)
    anchors = {
        "likud": float(np.mean([likud_e2[c] for c in use if c in likud_e2])),
        "leader": float(np.mean([leader_e2[c] for c in use if c in leader_e2])),
    }
    # 4. residual, after removing the anchors from their own rows
    resid = resid[resid["cycle"].isin(use)].copy()
    resid.loc[resid["has_likud"], "e3"] -= anchors["likud"]
    for c in use:
        f = resid[resid["cycle"] == c]
        others = f[~f["has_likud"]]
        if len(others):
            resid.loc[others["actual"].idxmax(), "e3"] -= anchors["leader"]

    small = resid[resid["actual"] <= 8]["e3"]
    big = resid[resid["actual"] > 8]["e3"]
    sd_small, sd_big = float(small.std(ddof=1)), float(big.std(ddof=1))
    mean_small = float(resid[resid["actual"] <= 8]["actual"].mean())
    mean_big = float(resid[resid["actual"] > 8]["actual"].mean())
    slope = max((sd_big - sd_small) / max(mean_big - mean_small, 1.0), 0.0)
    base = max(sd_small - slope * mean_small, 0.4)

    return {
        "bloc_sd": float(np.std([bloc_totals[c] for c in use], ddof=1)),
        "family": {
            fam: (float(np.mean([d[c] for c in use if c in d])),
                  float(np.std([d[c] for c in use if c in d], ddof=1)))
            for fam, d in fam_totals.items()
        },
        "anchors": anchors,
        "resid_base": float(base), "resid_slope": float(slope),
    }


def main() -> None:
    p = decompose()
    print("Full-sample error decomposition (8 cycles):")
    print(f"  bloc swing sd:      {p['bloc_sd']:.2f} seats")
    for fam, (m, s) in p["family"].items():
        print(f"  {fam:7} family:     mean {m:+.2f}, sd {s:.2f}")
    print(f"  Likud anchor:       {p['anchors']['likud']:+.2f} seats "
          f"(polls' systematic miss on Likud, after bloc removal)")
    print(f"  seat-leader anchor: {p['anchors']['leader']:+.2f} seats")
    print(f"  residual sd:        {p['resid_base']:.2f} + "
          f"{p['resid_slope']:.3f} x seats")
    flat = {"bloc_sd": p["bloc_sd"], "anchor_likud": p["anchors"]["likud"],
            "anchor_leader": p["anchors"]["leader"],
            "resid_base": p["resid_base"], "resid_slope": p["resid_slope"]}
    for fam, (m, s) in p["family"].items():
        flat[f"family_{fam}_mean"], flat[f"family_{fam}_sd"] = m, s
    pd.Series(flat).round(3).to_csv(
        PROCESSED_DIR / "error_decomposition.csv")
    print("\nwrote error_decomposition.csv")

    print("\nLeave-one-out anchors (stability check):")
    for c in ORDER:
        q = decompose(exclude_cycle=c)
        print(f"  without {c}: likud {q['anchors']['likud']:+.2f}, "
              f"leader {q['anchors']['leader']:+.2f}, "
              f"bloc sd {q['bloc_sd']:.2f}")


if __name__ == "__main__":
    main()
