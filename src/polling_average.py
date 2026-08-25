"""Weighted polling average for the live 2026 cycle.

Each pollster's latest poll in the window enters the average with weight
    recency x sqrt(sample size) x accuracy x 1/sqrt(correlation-group size)
where
  * recency decay sharpens as election day nears (half-life days_out/4,
    clamped to 5-14 days);
  * accuracy comes from the backtest scorecard (backtest_pollsters.csv):
    firms with a better final-poll record count more, gently (sqrt, clipped);
    firms with no record are neutral. "Lazar" inherits the Panels Politics
    record — same operation, two bylines (docs/pollsters.md);
  * the correlation-group discount (data/pollster_meta.csv) stops related
    firms — e.g. the two halves of the former Direct Polls — from counting
    as independent voices.

Poll values are trendline-adjusted before averaging: a stale poll is shifted
by the consensus movement since its fieldwork, so it informs today's level
rather than its own week's.

Two aggregation spaces:
  * per-list snapshot — the finest common partition of list components;
  * daily bloc series — per-poll bloc totals, immune to list reconfigurations.

Outputs:
    data/processed/average_2026_snapshot.csv   per-list average, today
    data/processed/average_2026_blocs.csv      daily bloc series
    output/figures/bloc_race_2026.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import (
    FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE,
    merge_blocks, short_name,
)
from normalize import load_party_registry
from scrape_polls import PROCESSED_DIR

HALFLIFE_RANGE = (5.0, 14.0)   # days; halflife = days_to_election / 4, clamped
WINDOW = 45                    # days a poll stays in the average
TREND_SPAN = 14                # days of rolling consensus for the trendline
DEFAULT_N = 500
CAP_N = 2000
ELECTION_DAY_2026 = pd.Timestamp("2026-10-27")

QUALITY_ALIAS = {"Lazar": "Panels Politics"}

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

_QUALITY: dict[str, float] | None = None
_GROUP: dict[str, str] | None = None


def load_2026() -> pd.DataFrame:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    return polls[(polls["cycle"] == "2026") & polls["sums_ok"]].copy()


def quality_map() -> dict[str, float]:
    global _QUALITY
    if _QUALITY is None:
        try:
            sc = pd.read_csv(PROCESSED_DIR / "backtest_pollsters.csv")
            med = sc["mean_abs_error"].median()
            q = (med / sc["mean_abs_error"]).pow(0.5).clip(0.7, 1.3)
            _QUALITY = dict(zip(sc["pollster"], q.round(3)))
        except FileNotFoundError:
            _QUALITY = {}
    return _QUALITY


def group_map() -> dict[str, str]:
    global _GROUP
    if _GROUP is None:
        try:
            meta = pd.read_csv(PROCESSED_DIR.parent / "pollster_meta.csv")
            _GROUP = dict(zip(meta["pollster"], meta["correlation_group"]))
        except FileNotFoundError:
            _GROUP = {}
    return _GROUP


def poll_weights(meta: pd.DataFrame, asof: pd.Timestamp,
                 eday: pd.Timestamp | None = ELECTION_DAY_2026) -> pd.Series:
    """Weight for each pollster's latest poll in the window; 0 otherwise.

    meta: one row per poll_id with pollster, fieldwork_end, sample_size.
    """
    days_out = max((eday - asof).days, 0) if eday is not None else 60
    halflife = float(np.clip(days_out / 4.0, *HALFLIFE_RANGE))

    m = meta[
        (meta["fieldwork_end"] <= asof)
        & (meta["fieldwork_end"] > asof - pd.Timedelta(days=WINDOW))
    ]
    m = m.sort_values(["pollster", "fieldwork_end", "poll_id"],
                      ascending=[True, False, True])
    m = m.groupby("pollster").head(1).copy()

    age = (asof - m["fieldwork_end"]).dt.days
    n = m["sample_size"].fillna(DEFAULT_N).clip(upper=CAP_N)
    w = 0.5 ** (age / halflife) * np.sqrt(n / 600.0)

    qmap = quality_map()
    w *= m["pollster"].map(lambda p: qmap.get(QUALITY_ALIAS.get(p, p), 1.0)).values
    gmap = group_map()
    groups = m["pollster"].map(lambda p: gmap.get(p, p))
    w /= np.sqrt(groups.map(groups.value_counts()).values)

    return pd.Series(w.values, index=m["poll_id"].values)


def trend_adjust(values: pd.DataFrame, dates: pd.Series,
                 asof: pd.Timestamp) -> pd.DataFrame:
    """Shift each poll's numbers by the consensus movement since its fieldwork.

    values: poll_id x unit. The per-unit trend is a TREND_SPAN-day rolling
    mean of the daily poll consensus; each poll gets (trend at asof - trend
    at its date) added, so stale polls speak at today's level. Polls earlier
    than the trend's reach are left unshifted.
    """
    out = values.copy()
    d = dates.reindex(values.index)
    for u in values.columns:
        s = pd.Series(values[u].values, index=d.values).dropna()
        if s.empty:
            continue
        daily = (s.groupby(level=0).mean().asfreq("D")
                 .interpolate(limit_area="inside"))
        trend = daily.rolling(TREND_SPAN, min_periods=3).mean().dropna()
        if trend.empty:
            continue
        t_asof = trend.asof(min(asof, trend.index[-1]))
        shifts = d.map(lambda t: t_asof - trend.asof(t)
                       if t >= trend.index[0] else 0.0)
        out[u] = values[u] + shifts.fillna(0.0)
    return out


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

    per_poll = live.pivot_table(index="poll_id", columns="block",
                                values="seats", aggfunc="sum")
    dates = live.drop_duplicates("poll_id").set_index("poll_id")["fieldwork_end"]
    per_poll = trend_adjust(per_poll, dates, asof)

    ww = w.reindex(per_poll.index)
    avg = (per_poll.mul(ww, axis=0).sum(skipna=True)
           / per_poll.notna().mul(ww, axis=0).sum())

    out = pd.DataFrame({
        "list": [short_name("+".join(sorted(blocks[b])), names) for b in avg.index],
        "avg_seats": avg.round(1).values,
        "n_polls": per_poll.notna().sum().values,
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
    print(f"Weighted average as of {asof.date()} (quality- and "
          f"group-weighted, trend-adjusted):\n")
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
