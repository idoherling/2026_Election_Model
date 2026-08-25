"""Weighted polling average for the live 2026 cycle.

Method (v1, pre-house-effects): as of a given day, take each pollster's
latest poll fielded within WINDOW days, weight it by recency (exponential
decay, HALFLIFE-day half-life) and sample size (sqrt(n / 600), n capped,
median-ish default when unreported), and average seats.

Two aggregation spaces:
  * per-list snapshot — polls and lists aggregated to the finest common
    partition of list components (joint lists merge and split mid-cycle);
  * daily bloc series — each poll reduced to Netanyahu-bloc /
    anti-Netanyahu-bloc / Arab-party seat totals, which is immune to list
    reconfigurations and is the headline number.

Outputs:
    data/processed/average_2026_snapshot.csv   per-list average, today
    data/processed/average_2026_blocs.csv      daily bloc series
    output/figures/bloc_race_2026.png
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import (
    FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE,
    merge_blocks, short_name,
)
from normalize import load_party_registry
from scrape_polls import PROCESSED_DIR

HALFLIFE = 14  # days
WINDOW = 45    # days a poll stays in the average
DEFAULT_N = 500
CAP_N = 2000

BLOC_NAME = {
    "netanyahu_bloc": "Netanyahu bloc",
    "opposition_bloc": "Anti-Netanyahu bloc",
    "other": "Arab parties",
}
# Categorical slots 1-3 of the reference palette (validated all-pairs).
BLOC_COLOR = {
    "Netanyahu bloc": "#2a78d6",
    "Anti-Netanyahu bloc": "#eb6834",
    "Arab parties": "#1baf7a",
}


def load_2026() -> pd.DataFrame:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    return polls[(polls["cycle"] == "2026") & polls["sums_ok"]].copy()


def poll_weights(meta: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
    """Weight for each pollster's latest poll in the window; 0 otherwise.

    meta: one row per poll_id with pollster, fieldwork_end, sample_size.
    """
    m = meta[
        (meta["fieldwork_end"] <= asof)
        & (meta["fieldwork_end"] > asof - pd.Timedelta(days=WINDOW))
    ]
    m = m.sort_values(["pollster", "fieldwork_end", "poll_id"],
                      ascending=[True, False, True])
    m = m.groupby("pollster").head(1).copy()
    age = (asof - m["fieldwork_end"]).dt.days
    n = m["sample_size"].fillna(DEFAULT_N).clip(upper=CAP_N)
    w = 0.5 ** (age / HALFLIFE) * np.sqrt(n / 600.0)
    return pd.Series(w.values, index=m["poll_id"].values)


def snapshot(polls: pd.DataFrame, asof: pd.Timestamp) -> pd.DataFrame:
    """Per-list weighted average in the finest common partition."""
    names = dict(zip(load_party_registry()["party_id"],
                     load_party_registry()["name_en"]))
    meta = polls[["poll_id", "pollster", "fieldwork_end", "sample_size"]]
    w = poll_weights(meta.drop_duplicates("poll_id"), asof)
    live = polls[polls["poll_id"].isin(w.index)].copy()

    blocks = merge_blocks(live["party_id"].unique())
    block_of = {comp: i for i, b in enumerate(blocks) for comp in b}
    live["block"] = live["party_id"].map(lambda p: block_of[p.split("+")[0]])

    per_poll = live.pivot_table(index="block", columns="poll_id",
                                values="seats", aggfunc="sum")
    ww = w.reindex(per_poll.columns)
    avg = (per_poll * ww).sum(axis=1, skipna=True) / per_poll.notna().mul(ww).sum(axis=1)

    out = pd.DataFrame({
        "list": [short_name("+".join(sorted(blocks[b])), names) for b in avg.index],
        "avg_seats": avg.round(1).values,
        "n_polls": per_poll.notna().sum(axis=1).values,
    }).sort_values("avg_seats", ascending=False)
    out["asof"] = asof.date().isoformat()
    return out


def bloc_of_row(party_id: str, bloc: dict[str, str]) -> str:
    comps = party_id.split("+")
    blocs = {bloc.get(c, "other") for c in comps}
    return blocs.pop() if len(blocs) == 1 else "other"


def daily_bloc_series(polls: pd.DataFrame) -> pd.DataFrame:
    reg = load_party_registry()
    bloc = dict(zip(reg["party_id"], reg["bloc"]))
    polls = polls.copy()
    polls["bloc"] = polls["party_id"].map(lambda p: bloc_of_row(p, bloc))
    per_poll = polls.pivot_table(index="poll_id", columns="bloc",
                                 values="seats", aggfunc="sum").fillna(0)
    per_poll = per_poll.rename(columns=BLOC_NAME)
    # Lists the registry can't place count as neither bloc's seats; they are
    # rare and small in this cycle, so fold them out of the race chart.
    per_poll = per_poll[[c for c in BLOC_NAME.values() if c in per_poll]]

    meta = polls[["poll_id", "pollster", "fieldwork_end", "sample_size"]]
    meta = meta.drop_duplicates("poll_id")
    days = pd.date_range(polls["fieldwork_end"].min() + pd.Timedelta(days=30),
                         polls["fieldwork_end"].max(), freq="D")
    rows = []
    for day in days:
        w = poll_weights(meta, day)
        if len(w) < 3:
            continue
        sub = per_poll.reindex(w.index)
        rows.append({"date": day, "n_polls": len(w),
                     **((sub.mul(w, axis=0)).sum() / w.sum()).round(2)})
    return pd.DataFrame(rows)


def plot(series: pd.DataFrame, per_poll_blocs: pd.DataFrame,
         meta: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    dots = per_poll_blocs.join(meta.set_index("poll_id")["fieldwork_end"])
    for name, color in BLOC_COLOR.items():
        if name not in series.columns:
            continue
        ax.scatter(dots["fieldwork_end"], dots[name], s=9, color=color,
                   alpha=0.18, linewidths=0, zorder=2)
        ax.plot(series["date"], series[name], color=color, lw=2, zorder=3,
                label=name)
        last = series.iloc[-1]
        ax.annotate(f"{name}  {last[name]:.0f}",
                    (last["date"], last[name]),
                    textcoords="offset points", xytext=(8, 0),
                    va="center", fontsize=9, color=color, fontweight="bold")

    ax.axhline(61, color=BASELINE, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.text(series["date"].iloc[2], 61.6, "61 for a majority",
            fontsize=8, color=MUTED)

    ax.set_xlim(series["date"].iloc[0], series["date"].iloc[-1]
                + pd.Timedelta(days=170))
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_ylabel("Projected seats (weighted average)", fontsize=9, color=INK_2)
    ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor=INK_2)
    ax.set_title("The 2026 bloc race — weighted polling average, one dot per poll",
                 fontsize=11, color=INK, loc="left", pad=12)
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / "bloc_race_2026.png", facecolor=SURFACE)


def main() -> None:
    polls = load_2026()
    asof = polls["fieldwork_end"].max()

    snap = snapshot(polls, asof)
    snap.to_csv(PROCESSED_DIR / "average_2026_snapshot.csv", index=False)
    print(f"Weighted average as of {asof.date()} "
          f"(halflife {HALFLIFE}d, window {WINDOW}d):\n")
    print(snap.to_string(index=False))

    series = daily_bloc_series(polls)
    series.to_csv(PROCESSED_DIR / "average_2026_blocs.csv", index=False)

    reg = load_party_registry()
    bloc = dict(zip(reg["party_id"], reg["bloc"]))
    polls = polls.assign(bloc=polls["party_id"].map(lambda p: bloc_of_row(p, bloc)))
    per_poll = (polls.pivot_table(index="poll_id", columns="bloc",
                                  values="seats", aggfunc="sum")
                .fillna(0).rename(columns=BLOC_NAME))
    meta = polls[["poll_id", "fieldwork_end"]].drop_duplicates("poll_id")
    plot(series, per_poll, meta)

    last = series.iloc[-1]
    print(f"\nBloc race today: " + ", ".join(
        f"{c} {last[c]:.1f}" for c in BLOC_NAME.values() if c in series))
    print(f"wrote average_2026_snapshot.csv, average_2026_blocs.csv, "
          f"{FIG_DIR / 'bloc_race_2026.png'}")


if __name__ == "__main__":
    main()
