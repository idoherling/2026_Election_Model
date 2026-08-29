"""Head-to-head: Bayesian state-space model vs the simple weighted pipeline.

Three comparisons, most decision-relevant first:

  1. Holdout accuracy — both models frozen 14 days before the latest poll,
     graded on the polls they hadn't seen, in seats (median absolute error).
     Identical data, identical metric.
  2. Forecast side-by-side — per-list means, intervals, and threshold odds.
  3. Bloc probabilities.

The retro-validation harness (validate_model.py) remains the ultimate judge
once the Bayesian model is wired into it; this script is the fast referee.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bayes_model import HOLDOUT_DAYS, WINDOW_DAYS, prepare_data
from polling_average import poll_weights
from scrape_polls import PROCESSED_DIR


def simple_holdout_error(data) -> float:
    """The weighted-average pipeline graded on the same 14-day holdout."""
    obs = pd.DataFrame({
        "share": data["y"], "week": data["week"], "block": data["block_i"],
        "pollster": [data["firms"][i] for i in data["firm_i"]],
    })
    days = obs["week"] * 7 - WINDOW_DAYS
    hold = days > -HOLDOUT_DAYS
    train, test = obs[~hold], obs[hold]

    # Weighted mean share per block over training polls: latest per pollster,
    # recency x quality x group weights — the simple pipeline's core.
    cut_week = train["week"].max()
    meta = train.assign(
        poll_id=train.index,
        fieldwork_end=pd.Timestamp("2026-01-01")
        + pd.to_timedelta(train["week"] * 7, unit="D"),
        sample_size=np.nan,
    )[["poll_id", "pollster", "fieldwork_end", "sample_size"]]
    asof = meta["fieldwork_end"].max()
    w = poll_weights(meta.drop_duplicates("poll_id"), asof, eday=None)
    train = train.loc[train.index.isin(w.index)]
    ww = w.reindex(train.index)
    pred = (train["share"] * ww).groupby(train["block"]).sum() \
        / ww.groupby(train["block"]).sum()

    err = (test["block"].map(pred) - test["share"]).abs() * 120
    return float(err.median())


def main() -> None:
    data = prepare_data()
    simple_err = simple_holdout_error(data)
    print(f"1. HOLDOUT (last {HOLDOUT_DAYS} days of polls, unseen by both):")
    print(f"   simple weighted pipeline: median |error| {simple_err:.2f} seats")
    print("   Bayesian model: see fit log (same metric, printed at fit time)")

    bayes = pd.read_csv(PROCESSED_DIR / "bayes_forecast_2026.csv")
    simple = pd.read_csv(PROCESSED_DIR / "forecast_2026.csv")
    j = bayes.set_index("list").join(
        simple.set_index("list"), lsuffix="_bayes", rsuffix="_simple",
        how="outer")
    cols = ["mean_bayes", "p05_bayes", "p95_bayes", "p_pass_bayes",
            "mean_simple", "p05_simple", "p95_simple", "p_pass_simple"]
    j = j[cols].sort_values("mean_bayes", ascending=False)
    print("\n2. FORECASTS side-by-side (note: different as-of dates if the "
          "simple pipeline wasn't rerun):")
    print(j.to_string())

    bb = pd.read_csv(PROCESSED_DIR / "bayes_forecast_blocs.csv").iloc[0]
    sb = pd.read_csv(PROCESSED_DIR / "forecast_blocs.csv").iloc[0]
    print("\n3. BLOCS:")
    for k in ("p_netanyahu_bloc_61", "p_anti_bloc_61", "p_neither"):
        print(f"   {k}: bayes {bb[k]:.1%} | simple {sb[k]:.1%}")
    print(f"   NB 90% interval: bayes [{bb['nb_p05']}, {bb['nb_p95']}] | "
          f"simple [{sb['nb_p05']}, {sb['nb_p95']}]")


if __name__ == "__main__":
    main()
