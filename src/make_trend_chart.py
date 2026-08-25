"""Party seat trends for the 2026 cycle — the database's first checkpoint chart.

Last 12 months of published polls: faint per-poll dots plus a 14-day rolling
mean per list. The eight largest lists carry the categorical palette in fixed
slot order; smaller lists recede to gray. The top four are direct-labeled at
the right edge.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "output" / "figures"

# Categorical slots (validated light-mode palette, fixed order).
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GRAY = "#b3b1aa"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

DISPLAY = {
    "likud": "Likud",
    "together": "Together (Bennett–Lapid)",
    "yashar": "Yashar (Eisenkot)",
    "democrats": "The Democrats",
    "shas": "Shas",
    "utj": "UTJ",
    "otzma": "Otzma Yehudit",
    "rzp": "Religious Zionism",
    "yisrael_beytenu": "Yisrael Beytenu",
    "blue_white": "Blue & White",
    "unity": "Unity",
    "zionist_home": "Zionist Home",
    "raam": "Ra'am",
    "hadash_taal": "Hadash-Ta'al",
    "balad": "Balad",
    "winter": "Winter",
    "balad+hadash_taal+raam": "Joint List",
    "balad+hadash_taal": "Joint List (excl. Ra'am)",
}


def display_name(party_id: str) -> str:
    return DISPLAY.get(party_id, party_id.replace("_", " ").title())


def main() -> None:
    polls = pd.read_csv(ROOT / "data/processed/polls.csv", parse_dates=["fieldwork_end"])
    polls = polls[polls["sums_ok"]]
    end = polls["fieldwork_end"].max()
    start = end - pd.DateOffset(months=12)
    window = polls[polls["fieldwork_end"] >= start]

    recent = window[window["fieldwork_end"] >= end - pd.Timedelta(days=60)]
    ranking = (
        recent.groupby("party_id")["seats"].mean().sort_values(ascending=False)
    )
    ranked = [p for p in ranking.index if ranking[p] >= 1]
    colored, small = ranked[: len(SLOTS)], ranked[len(SLOTS) :]

    fig, ax = plt.subplots(figsize=(12, 7.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    def trend(g: pd.DataFrame) -> pd.Series:
        s = g.set_index("fieldwork_end")["seats"].sort_index()
        return s.rolling("14D", min_periods=2).mean()

    handles, labels = [], []
    end_labels = []  # (y, text, color) — collision-adjusted after the loop
    for rank, party in enumerate(ranked):
        g = window[window["party_id"] == party]
        if g["fieldwork_end"].nunique() < 3:
            continue
        color = SLOTS[rank] if party in colored else GRAY
        lw = 2.2 if party in colored else 1.2
        z = 3 if party in colored else 2
        ax.scatter(
            g["fieldwork_end"], g["seats"],
            s=9, color=color, alpha=0.18, linewidths=0, zorder=z,
        )
        t = trend(g)
        (line,) = ax.plot(
            t.index, t.values, color=color, linewidth=lw, zorder=z + 1,
            solid_capstyle="round",
        )
        handles.append(line)
        labels.append(display_name(party))
        if rank < 4:  # direct labels: top four only
            y = t.dropna().iloc[-1]
            end_labels.append((y, f"{display_name(party)}  {y:.0f}", color))

    end_labels.sort()
    for i in range(1, len(end_labels)):  # push apart colliding labels
        y_prev = end_labels[i - 1][0]
        if end_labels[i][0] - y_prev < 1.6:
            end_labels[i] = (y_prev + 1.6, *end_labels[i][1:])
    for y, text, color in end_labels:
        ax.annotate(
            text, xy=(end, y), xytext=(8, 0), textcoords="offset points",
            va="center", fontsize=9.5, fontweight="bold", color=color,
        )

    ax.axhline(4, color=BASELINE, linewidth=1, linestyle=(0, (4, 4)), zorder=1)
    ax.annotate(
        "electoral threshold ≈ 4 seats", xy=(0.005, 4), xycoords=("axes fraction", "data"),
        xytext=(0, 5), textcoords="offset points", fontsize=8.5, color=MUTED,
    )

    n_polls = window["poll_id"].nunique()
    ax.set_title(
        "The race for the 26th Knesset",
        loc="left", fontsize=16, fontweight="bold", color=INK, pad=18,
    )
    ax.text(
        0, 1.015, f"Projected seats in {n_polls} published polls, "
        f"{start:%b %Y} – {end:%b %Y} · 14-day rolling mean",
        transform=ax.transAxes, fontsize=10.5, color=INK_2,
    )

    ax.set_ylim(0, None)
    ax.set_ylabel("Projected seats", fontsize=10, color=INK_2)
    ax.yaxis.set_major_locator(plt.MultipleLocator(5))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.margins(x=0.01)
    ax.set_xlim(right=end + pd.Timedelta(days=5))

    legend = ax.legend(
        handles, labels, loc="upper left", bbox_to_anchor=(0, -0.09),
        ncol=4, frameon=False, fontsize=8.5, labelcolor=INK_2,
        handlelength=1.4, columnspacing=1.4,
    )
    for line in legend.get_lines():
        line.set_linewidth(2.5)

    fig.text(
        0.99, 0.005,
        "Data: published polls, collected from Wikipedia's 2026 cycle pages · sums-validated polls only",
        fontsize=8, color=MUTED, ha="right",
    )

    fig.subplots_adjust(left=0.055, right=0.82, top=0.9, bottom=0.24)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "seat_trends_2026.png"
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
