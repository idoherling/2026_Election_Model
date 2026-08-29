"""The official forecast: each instrument doing the job it validated for.

Four gated experiments (fine time grid, firm-reliability priors, a grading
comparability audit, and an ensemble test) established that the simple
final-window pipeline owns the election-eve POINT estimate (harness MAE
1.42 vs 1.66; blend curve monotone into it at error correlation 0.93),
while the Bayesian model owns DISTRIBUTIONS — intervals (97.3% coverage),
threshold and bloc probabilities, the registration mixture, and live
tracking (holdout 0.69-0.77 vs 1.09). This module assembles the published
object accordingly:

  central seats        simple pipeline snapshot (current configuration)
  intervals, P(pass),
  P(largest), blocs    Bayesian posterior + registration mixture

Outputs: data/processed/official_forecast.csv (+ printed summary)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR


def main() -> None:
    simple = pd.read_csv(PROCESSED_DIR / "forecast_2026.csv")
    bayes = pd.read_csv(PROCESSED_DIR / "bayes_forecast_2026.csv")
    mix = pd.read_csv(PROCESSED_DIR / "mixture_blocs.csv").iloc[0]

    # Match by component overlap (partitions differ slightly across models).
    def comps(x):
        return set(str(x).split("+"))

    rows = []
    for rb in bayes.itertuples():
        cb = comps(getattr(rb, "components", rb.list))
        match = None
        for rs in simple.itertuples():
            if comps(rs.components) & cb:
                match = rs
                break
        rows.append({
            "list": rb.list,
            "central_seats": (round(match.mean) if match else
                              int(round(rb.mean))),
            "interval_90": f"{rb.p05}-{rb.p95}",
            "p_pass": rb.p_pass,
            "p_largest": rb.p_largest,
            "center_source": "simple" if match else "bayes",
        })
    out = pd.DataFrame(rows).sort_values("central_seats", ascending=False)

    # Largest-remainder the centers onto exactly 120 among passing lists.
    passing = out["p_pass"] >= 0.5
    total = out.loc[passing, "central_seats"].sum()
    gap = 120 - int(total)
    if gap:
        idx = out[passing].sort_values("p_pass", ascending=False).index
        step = 1 if gap > 0 else -1
        for i in list(idx)[: abs(gap)]:
            out.loc[i, "central_seats"] += step
    out.loc[~passing, "central_seats"] = 0

    out["asof"] = bayes["asof"].iloc[0]
    out.to_csv(PROCESSED_DIR / "official_forecast.csv", index=False)

    print(f"OFFICIAL FORECAST as of {out['asof'].iloc[0]} "
          f"(centers: simple pipeline; distributions: Bayesian mixture)\n")
    show = out[out["central_seats"] > 0]
    for r in show.itertuples():
        print(f"  {r.central_seats:>3}  {r.list:<32} "
              f"[{r.interval_90}]  pass {r.p_pass:.0%}")
    print(f"\n  Bloc probabilities (registration mixture): "
          f"P(NB>=61) {mix['p_nb_61']:.1%} | "
          f"P(anti>=61) {mix['p_anti_61']:.1%} | "
          f"P(neither) {mix['p_neither']:.1%}")


if __name__ == "__main__":
    main()
