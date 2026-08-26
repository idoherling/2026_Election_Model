"""The Knesset-composition forecast: full-makeup view of the simulation.

Reads the simulation draws (forecast_draws.parquet) and renders the flagship
product graphic:
  * a hemicycle of the central scenario — simulation means rounded to 120 by
    largest remainder, seated left to right along the political spectrum;
  * per-list seat-probability strips — each list's full distribution as a
    discrete heat strip with its 90% interval and mean, colored by bloc.

Also prints P(largest list) — who gets first crack at forming a government —
and the central composition table.

Outputs:
    output/figures/knesset_2026.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE
from scrape_polls import PROCESSED_DIR

BLOC_COLOR = {
    "Netanyahu bloc": "#2a78d6",
    "Anti-Netanyahu bloc": "#eb6834",
    "Arab parties": "#1baf7a",
}
# Seating order, left to right, by political convention.
SPECTRUM = [
    "Balad + Hadash-Ta'al + Ra'am", "The Democrats", "Together", "Yashar",
    "Blue and White", "Zionist Home – The Reservists", "Unity",
    "Yisrael Beytenu", "Likud", "Religious Zionist Party", "Otzma Yehudit",
    "Shas", "United Torah Judaism",
]


def central_composition(draws: pd.DataFrame) -> pd.Series:
    """Median seats per list, topped up to exactly 120 by mean remainders.

    Medians (not rounded means) so the central scenario never shows an
    impossible 1-3 seat list — a sub-threshold list's median is 0.
    """
    comp = draws.median().astype(int)
    means = draws.mean()
    gap = 120 - comp.sum()
    eligible = (means - comp)[comp > 0].sort_values(ascending=False).index
    step = 1 if gap >= 0 else -1
    targets = eligible[: gap] if gap >= 0 else eligible[gap:]
    for name in targets:
        comp[name] += step
    return comp


def hemicycle_positions(n: int = 120, rows: int = 5):
    radii = np.linspace(1.0, 2.0, rows)
    weights = radii / radii.sum()
    per_row = np.floor(weights * n).astype(int)
    order = np.argsort(-(weights * n - per_row))
    for i in order[: n - per_row.sum()]:
        per_row[i] += 1
    pts = []
    for r, k in zip(radii, per_row):
        angles = np.linspace(np.pi, 0.0, k)
        pts += [(a, r) for a in angles]
    pts.sort(key=lambda p: (-p[0], p[1]))  # left to right, inner first
    return pts


def main() -> None:
    draws = pd.read_parquet(PROCESSED_DIR / "forecast_draws.parquet")
    dist = pd.read_csv(PROCESSED_DIR / "forecast_2026.csv")
    asof = dist["asof"].iloc[0]
    bloc = dict(zip(dist["list"], dist["bloc"]))
    stats = dist.set_index("list")

    comp = central_composition(draws)
    seating = [l for l in SPECTRUM if l in comp.index] + \
              [l for l in comp.index if l not in SPECTRUM]

    print(f"Knesset 26 forecast as of {asof} "
          f"({len(draws):,} simulations)\n")
    print("Central composition (medians, topped up to 120):")
    for l in seating:
        if comp[l] > 0:
            print(f"  {comp[l]:>3}  {l}")
    print("\nP(largest list):")
    top = stats.sort_values("p_largest", ascending=False)
    for l, row in top[top["p_largest"] >= 0.005].iterrows():
        print(f"  {row['p_largest']:>6.1%}  {l}")

    # ---- figure: hemicycle + probability strips -------------------------
    fig = plt.figure(figsize=(9.5, 9.2), dpi=200, facecolor=SURFACE)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.35], hspace=0.16)

    # Hemicycle of the central scenario.
    axh = fig.add_subplot(gs[0])
    axh.set_facecolor(SURFACE)
    pts = hemicycle_positions()
    colors, i = [], 0
    for l in seating:
        colors += [BLOC_COLOR[bloc[l]]] * int(comp[l])
    for (a, r), c in zip(pts, colors):
        axh.scatter(r * np.cos(a), r * np.sin(a), s=52, color=c,
                    linewidths=0)
    axh.set_xlim(-2.35, 2.35)
    axh.set_ylim(-0.28, 2.3)
    axh.set_aspect("equal")
    axh.axis("off")
    nb = int(sum(comp[l] for l in seating if bloc[l] == "Netanyahu bloc"))
    anti = int(sum(comp[l] for l in seating
                   if bloc[l] == "Anti-Netanyahu bloc"))
    arab = 120 - nb - anti
    axh.text(0, -0.02, f"{anti}   ·   {arab}   ·   {nb}", ha="center",
             fontsize=13, color=INK, fontweight="bold")
    axh.text(0, -0.24, "anti-Netanyahu bloc · Arab parties · Netanyahu bloc "
             "(central scenario)", ha="center", fontsize=8, color=MUTED)
    axh.set_title(f"Knesset 26 forecast — as of {asof}",
                  fontsize=13, color=INK, loc="left", pad=8)

    # Per-list probability strips.
    axs = fig.add_subplot(gs[1])
    axs.set_facecolor(SURFACE)
    shown = [l for l in stats.sort_values("mean", ascending=False).index
             if stats.loc[l, "mean"] > 0.2 or stats.loc[l, "p_pass"] > 0.05]
    xmax = int(max(np.percentile(draws[l], 99) for l in shown)) + 1
    for y, l in enumerate(shown):
        c = BLOC_COLOR[bloc[l]]
        probs = np.bincount(draws[l], minlength=xmax + 1)[: xmax + 1] / len(draws)
        pmax = probs.max()
        for s_val in np.nonzero(probs)[0]:
            axs.add_patch(plt.Rectangle(
                (s_val - 0.5, y - 0.33), 1.0, 0.66, linewidth=0,
                color=c, alpha=float(0.08 + 0.82 * probs[s_val] / pmax)))
        row = stats.loc[l]
        axs.plot([row["p05"], row["p95"]], [y + 0.41, y + 0.41], color=c,
                 lw=1.4, solid_capstyle="butt")
        axs.scatter(row["mean"], y + 0.41, s=16, color=c, zorder=3)
        label = f"{row['mean']:.0f}  ({row['p05']}–{row['p95']})"
        if row["p_pass"] < 0.995:
            label += f" · passes {row['p_pass']:.0%}"
        axs.text(xmax + 0.6, y, label, va="center", fontsize=8, color=INK_2,
                 fontvariant=None)
    axs.set_yticks(range(len(shown)))
    axs.set_yticklabels(shown, fontsize=9.5, color=INK)
    axs.invert_yaxis()
    axs.set_xlim(-0.6, xmax + 8.5)
    axs.set_ylim(len(shown) - 0.5, -0.8)
    axs.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    for side in ("top", "right", "left"):
        axs.spines[side].set_visible(False)
    axs.spines["bottom"].set_color(BASELINE)
    axs.tick_params(axis="x", labelsize=8, colors=MUTED)
    axs.tick_params(axis="y", length=0)
    axs.set_xlabel("Seats — shade is probability; line is the 90% interval, "
                   "dot the mean", fontsize=9, color=INK_2)

    fig.savefig(FIG_DIR / "knesset_2026.png", facecolor=SURFACE,
                bbox_inches="tight")
    print(f"\nwrote {FIG_DIR / 'knesset_2026.png'}")


if __name__ == "__main__":
    main()
