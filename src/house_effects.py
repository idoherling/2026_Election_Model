"""Pollster house effects for the 2026 cycle, with a past-cycle persistence check.

A house effect here is a pollster's systematic deviation from the
contemporaneous consensus: for every poll, the baseline is built from the
OTHER pollsters' nearest polls within +/-CONSENSUS_WINDOW days (recency- and
sample-weighted), and the pollster's deviations are then shrunk toward zero
with a closed-form empirical-Bayes estimator — a firm with 4 noisy polls gets
pulled hard to zero, a firm with 40 consistent ones keeps its lean.

Deviations are measured against the consensus, so bloc-assignment choices
cancel (they shift every pollster's total identically); the same machinery
therefore runs unchanged on past cycles as a persistence check.

Outputs:
    data/processed/house_effects_blocs.csv     pollster x cycle bloc effects
    data/processed/house_effects_lists_2026.csv pollster x list effects (90d)
    data/processed/average_2026_corrected.csv  house-effect-corrected snapshot
    output/figures/house_effects_2026.png
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE, merge_blocks, short_name
from normalize import load_party_registry
from polling_average import (
    BLOC_NAME, DEFAULT_N, CAP_N, bloc_of_row, load_2026, poll_weights,
)
from scrape_polls import PROCESSED_DIR

CONSENSUS_WINDOW = 14   # days each side when building the baseline
CONSENSUS_HALFLIFE = 7
MIN_OTHERS = 3          # pollsters needed for a baseline
LIST_WINDOW = 90        # days of stable list configuration for list effects
SNAPSHOT_WINDOW = 45

BLUE = "#2a78d6"
ORANGE = "#eb6834"


def per_poll_values(polls: pd.DataFrame, value_space: str) -> pd.DataFrame:
    """One row per poll: meta plus seat totals per bloc or per list-block."""
    polls = polls[polls["pollster"] != "Unattributed"].copy()
    if value_space == "bloc":
        reg = load_party_registry()
        bloc = dict(zip(reg["party_id"], reg["bloc"]))
        polls["unit"] = polls["party_id"].map(lambda p: bloc_of_row(p, bloc))
    else:
        blocks = merge_blocks(polls["party_id"].unique())
        block_of = {c: i for i, b in enumerate(blocks) for c in b}
        polls["unit"] = polls["party_id"].map(lambda p: block_of[p.split("+")[0]])
        names = dict(zip(load_party_registry()["party_id"],
                         load_party_registry()["name_en"]))
        per_poll_values.block_labels = {
            i: short_name("+".join(sorted(b)), names) for i, b in enumerate(blocks)
        }
    wide = polls.pivot_table(index="poll_id", columns="unit",
                             values="seats", aggfunc="sum").fillna(0)
    meta = polls[["poll_id", "pollster", "fieldwork_end", "sample_size"]]
    return meta.drop_duplicates("poll_id").set_index("poll_id").join(wide)


def deviations(wide: pd.DataFrame, units) -> pd.DataFrame:
    """Each poll's deviation from its leave-own-pollster-out consensus."""
    rows = []
    for pid, poll in wide.iterrows():
        others = wide[wide["pollster"] != poll["pollster"]].copy()
        others["gap"] = (others["fieldwork_end"] - poll["fieldwork_end"]).dt.days.abs()
        others = others[others["gap"] <= CONSENSUS_WINDOW]
        others = others.sort_values("gap").groupby("pollster").head(1)
        if len(others) < MIN_OTHERS:
            continue
        n = others["sample_size"].fillna(DEFAULT_N).clip(upper=CAP_N)
        w = 0.5 ** (others["gap"] / CONSENSUS_HALFLIFE) * np.sqrt(n / 600.0)
        base = (others[units].mul(w, axis=0)).sum() / w.sum()
        rows.append({"poll_id": pid, "pollster": poll["pollster"],
                     **(poll[units] - base)})
    return pd.DataFrame(rows)


def eb_shrink(dev: pd.DataFrame, units) -> pd.DataFrame:
    """Empirical-Bayes shrinkage of per-pollster mean deviations, per unit."""
    out = []
    for unit in units:
        g = dev.groupby("pollster")[unit]
        m, n = g.mean(), g.size()
        resid = dev[unit] - dev["pollster"].map(m)
        dof = max(len(dev) - len(m), 1)
        var_within = float((resid ** 2).sum()) / dof
        var_between = max(float(m.var()) - var_within * float((1 / n).mean()), 1e-6)
        lam = var_between / (var_between + var_within / n)
        out.append(pd.DataFrame({
            "pollster": m.index, "unit": unit,
            "raw_mean": m.values.round(2), "n_polls": n.values,
            "house_effect": (lam * m).values.round(2),
        }))
    return pd.concat(out, ignore_index=True)


def bloc_effects(polls: pd.DataFrame, cycle: str) -> pd.DataFrame:
    wide = per_poll_values(polls, "bloc")
    units = [u for u in BLOC_NAME if u in wide.columns]
    dev = deviations(wide, units)
    if dev.empty:
        return pd.DataFrame()
    eff = eb_shrink(dev, units)
    eff["unit"] = eff["unit"].map(BLOC_NAME)
    eff["cycle"] = cycle
    return eff


def corrected_snapshot(polls: pd.DataFrame, list_effects: pd.DataFrame,
                       labels: dict) -> pd.DataFrame:
    """The polling_average snapshot with each poll's house effect removed."""
    asof = polls["fieldwork_end"].max()
    wide = per_poll_values(
        polls[polls["fieldwork_end"] > asof - pd.Timedelta(days=LIST_WINDOW)],
        "list",
    )
    units = [c for c in wide.columns
             if c not in ("pollster", "fieldwork_end", "sample_size")]
    h = list_effects.pivot(index="pollster", columns="unit",
                           values="house_effect")
    adj = wide.copy()
    adj[units] = wide[units] - h.reindex(wide["pollster"])[units].fillna(0).values

    w = poll_weights(adj.reset_index()[["poll_id", "pollster", "fieldwork_end",
                                        "sample_size"]], asof)
    live = adj.loc[adj.index.isin(w.index)]
    ww = w.reindex(live.index)
    raw_live = wide.loc[live.index]
    avg = live[units].mul(ww, axis=0).sum() / ww.sum()
    raw_avg = raw_live[units].mul(ww, axis=0).sum() / ww.sum()
    out = pd.DataFrame({
        "list": [labels[u] for u in units],
        "avg_seats_raw": raw_avg.round(1).values,
        "avg_seats_corrected": avg.round(1).values,
    }).sort_values("avg_seats_corrected", ascending=False)
    out["asof"] = asof.date().isoformat()
    return out


def plot(blocs: pd.DataFrame) -> None:
    cur = blocs[(blocs["cycle"] == "2026") & (blocs["unit"] == "Netanyahu bloc")]
    cur = cur.sort_values("house_effect")
    past = blocs[(blocs["cycle"].isin(["2021", "2022"]))
                 & (blocs["unit"] == "Netanyahu bloc")]
    past = past.groupby("pollster")["house_effect"].mean()

    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ys = range(len(cur))
    ax.axvline(0, color=BASELINE, lw=1.2, zorder=1)
    for y, row in zip(ys, cur.itertuples()):
        if row.pollster in past.index:
            ax.scatter(past[row.pollster], y, s=46, facecolors="none",
                       edgecolors=ORANGE, linewidths=1.6, zorder=2)
        ax.scatter(row.house_effect, y, s=52, color=BLUE, zorder=3)
        ax.text(1.01, y, f"n={row.n_polls}", transform=ax.get_yaxis_transform(),
                va="center", fontsize=7.5, color=MUTED)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(cur["pollster"], fontsize=9, color=INK)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(axis="x", labelsize=8, colors=MUTED)
    ax.set_xlabel("Netanyahu-bloc house effect, seats vs consensus  "
                  "(shrunken estimate)", fontsize=9, color=INK_2)
    handles = [
        plt.Line2D([], [], marker="o", ls="", color=BLUE, ms=7,
                   label="2026 cycle"),
        plt.Line2D([], [], marker="o", ls="", markerfacecolor="none",
                   markeredgecolor=ORANGE, markeredgewidth=1.6, ms=7,
                   label="2021-22 cycles (mean)"),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False,
              fontsize=8, labelcolor=INK_2)
    ax.set_title("Who leans which way — pollster house effects, 2026 cycle",
                 fontsize=11, color=INK, loc="left", pad=12)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "house_effects_2026.png", facecolor=SURFACE)


def main() -> None:
    polls26 = load_2026()

    # Bloc-level effects: full 2026 cycle plus recent past cycles.
    all_polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                            parse_dates=["fieldwork_end"])
    frames = [bloc_effects(polls26, "2026")]
    for cyc in ("2022", "2021", "2020", "2019s", "2019a"):
        sub = all_polls[(all_polls["cycle"] == cyc) & all_polls["sums_ok"]]
        frames.append(bloc_effects(sub, cyc))
    blocs = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    blocs.to_csv(PROCESSED_DIR / "house_effects_blocs.csv", index=False)

    nb26 = blocs[(blocs["cycle"] == "2026") & (blocs["unit"] == "Netanyahu bloc")]
    print("Netanyahu-bloc house effects, 2026 cycle (seats vs consensus):")
    print(nb26.sort_values("house_effect", ascending=False)
          [["pollster", "n_polls", "raw_mean", "house_effect"]]
          .to_string(index=False))

    # List-level effects over the stable recent window, then the corrected
    # snapshot.
    asof = polls26["fieldwork_end"].max()
    recent = polls26[polls26["fieldwork_end"]
                     > asof - pd.Timedelta(days=LIST_WINDOW)]
    wide = per_poll_values(recent, "list")
    labels = per_poll_values.block_labels
    units = [c for c in wide.columns
             if c not in ("pollster", "fieldwork_end", "sample_size")]
    dev = deviations(wide, units)
    lists = eb_shrink(dev, units)
    lists_out = lists.assign(list=lists["unit"].map(labels))
    lists_out.to_csv(PROCESSED_DIR / "house_effects_lists_2026.csv", index=False)

    snap = corrected_snapshot(polls26, lists, labels)
    snap.to_csv(PROCESSED_DIR / "average_2026_corrected.csv", index=False)
    print(f"\nSnapshot as of {asof.date()}, raw vs house-effect-corrected:")
    print(snap.to_string(index=False))

    plot(blocs)
    print(f"\nwrote house_effects_blocs.csv, house_effects_lists_2026.csv, "
          f"average_2026_corrected.csv, {FIG_DIR / 'house_effects_2026.png'}")


if __name__ == "__main__":
    main()
