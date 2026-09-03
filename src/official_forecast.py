"""The official forecast: one distribution, one point estimate from it.

The published object is the registration MIXTURE (the Bayesian posterior
projected through the measured shock stack and mixed over the open
registration events). Intervals, pass probabilities and bloc odds are
read off its draws. The CENTRAL seat count is the mixture's own point
forecast: its MEDIAN vote-share vector (renormalised) passed once through
the real seat law - the 3.25% threshold and Bader-Ofer with the surplus-vote pairs - so
the table sums to 120 by construction, with no rounding, floors or
remainder hand-outs.

History: an earlier design gave the point estimate to the simple
final-window pipeline (better election-eve MAE on the harness, 1.42 vs
1.66). A name mismatch meant that never actually happened, the fallback
rounded the baseline means and reconciled to 120 by handing seats to the
highest-pass-probability lists (UTJ at 9 with a mean of 7.9). Retired
2026-09-03: the mixture carries information the simple pipeline never
sees (merger backcasts, the unified-list regime, resolved events).

Outputs: data/processed/official_forecast.csv (+ printed summary)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR
from simulate import SURPLUS_PAIRS, THRESHOLD, dhondt


def allocate_central(shares: pd.DataFrame) -> dict:
    """Seats for the mean share vector: threshold, surplus pairs, d'Hondt."""
    names = shares["list"].tolist()
    comps = [set(str(c).split("+")) for c in shares["components"]]
    # median share vector: the harness grades the median as the better point
    # estimate (MAE 1.57 vs 1.67); renormalised so the pie sums to one
    col = "share_median" if "share_median" in shares.columns else "share_mean"
    v = shares[col].values.astype(float)
    v = v / v.sum()
    passed = v >= THRESHOLD
    comp_of = {c: i for i, cs in enumerate(comps) for c in cs}
    pair_idx = [(comp_of[a], comp_of[b]) for a, b in SURPLUS_PAIRS
                if a in comp_of and b in comp_of and comp_of[a] != comp_of[b]]
    fvotes, fmembers, used = [], [], set()
    for a, b in pair_idx:
        if passed[a] and passed[b]:
            fvotes.append(v[a] + v[b]); fmembers.append([a, b]); used |= {a, b}
    for j in np.nonzero(passed)[0]:
        if j not in used:
            fvotes.append(v[j]); fmembers.append([int(j)])
    seats = {n: 0 for n in names}
    if not fvotes:
        return seats
    alloc = dhondt(np.array(fvotes), 120)
    for members, k in zip(fmembers, alloc):
        if len(members) == 1:
            seats[names[members[0]]] = int(k)
        else:
            a, b = members
            inner = dhondt(np.array([v[a], v[b]]), int(k))
            seats[names[a]], seats[names[b]] = int(inner[0]), int(inner[1])
    return seats


def main() -> None:
    bayes = pd.read_csv(PROCESSED_DIR / "bayes_forecast_2026.csv")
    mdist = pd.read_csv(PROCESSED_DIR / "bayes_forecast_mixture.csv")
    shares = pd.read_csv(PROCESSED_DIR / "mixture_shares.csv")
    mix = pd.read_csv(PROCESSED_DIR / "mixture_blocs.csv").iloc[0]

    central = allocate_central(shares)
    m = {r.list: r for r in mdist.itertuples()}
    pl = dict(zip(bayes["list"], bayes["p_largest"]))
    rows = []
    for r in mdist.itertuples():
        rows.append({
            "list": r.list,
            "central_seats": central.get(r.list, 0),
            "interval_90": f"{r.p05}-{r.p95}",
            "p_pass": r.p_pass,
            "p_largest": pl.get(r.list, 0.0),
            "center_source": "mixture",
        })
    out = pd.DataFrame(rows).sort_values(["central_seats", "p_pass"], ascending=False)
    assert out["central_seats"].sum() == 120, out["central_seats"].sum()
    out["asof"] = bayes["asof"].iloc[0]
    out.to_csv(PROCESSED_DIR / "official_forecast.csv", index=False)

    print(f"OFFICIAL FORECAST as of {out['asof'].iloc[0]} "
          f"(centres: Bader-Ofer on the mixture's median shares; distributions: mixture)\n")
    for r in out[out["central_seats"] > 0].itertuples():
        print(f"  {r.central_seats:>3}  {r.list:<32} [{r.interval_90}]  pass {r.p_pass:.0%}")
    print(f"\n  Bloc probabilities (registration mixture): "
          f"P(NB>=61) {mix['p_nb_61']:.1%} | P(anti>=61) {mix['p_anti_61']:.1%} | "
          f"P(neither) {mix['p_neither']:.1%}")


if __name__ == "__main__":
    main()
