"""Backtest: final-poll averages vs official results, 2009-2022.

For each completed cycle, take every pollster's last poll fielded within
FINAL_WINDOW days of election day, aggregate poll and result lines to the
finest common partition of party components (joint lists merge and split
across polls), and score the average and each pollster against the official
seat outcome.

Outputs:
    data/processed/backtest_blocks.csv     per cycle x party-block errors
    data/processed/backtest_summary.csv    per cycle headline metrics
    data/processed/backtest_pollsters.csv  pollster scorecard seed
    output/figures/backtest_final_polls.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from normalize import load_party_registry
from scrape_polls import ELECTION_DAY, PROCESSED_DIR

FIG_DIR = Path(__file__).resolve().parent.parent / "output" / "figures"

FINAL_WINDOW = 21  # days before election day
SEAT_SUM_RANGE = (108, 122)  # drop scenario variants and broken rows

# Reference dataviz palette (light mode)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"

CYCLE_LABEL = {
    "2009": "2009", "2013": "2013", "2015": "2015",
    "2019a": "Apr 2019", "2019s": "Sep 2019",
    "2020": "2020", "2021": "2021", "2022": "2022",
}


def merge_blocks(party_ids) -> list[set[str]]:
    """Finest partition where every poll/result line falls in one block."""
    blocks: list[set[str]] = []
    for pid in party_ids:
        merged = set(pid.split("+"))
        keep = []
        for b in blocks:
            if b & merged:
                merged |= b
            else:
                keep.append(b)
        blocks = keep + [merged]
    return blocks


def short_name(party_id: str, names: dict[str, str]) -> str:
    return " + ".join(names.get(p, p) for p in sorted(party_id.split("+")))


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    names = dict(zip(load_party_registry()["party_id"], load_party_registry()["name_en"]))

    block_rows, summary_rows, pollster_rows = [], [], []

    for cycle, res in results.groupby("cycle"):
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        window = polls[
            (polls["cycle"] == cycle)
            & (polls["fieldwork_end"] <= eday)
            & (polls["fieldwork_end"] >= eday - pd.Timedelta(days=FINAL_WINDOW))
        ].copy()
        totals = window.groupby("poll_id")["seats"].sum()
        ok = totals[(totals >= SEAT_SUM_RANGE[0]) & (totals <= SEAT_SUM_RANGE[1])]
        window = window[window["poll_id"].isin(ok.index)]

        # Each pollster's last poll in the window ("a" variant on ties).
        meta = window[["pollster", "poll_id", "fieldwork_end"]].drop_duplicates()
        meta = meta.sort_values(
            ["pollster", "fieldwork_end", "poll_id"],
            ascending=[True, False, True],
        )
        chosen = meta.groupby("pollster").head(1)["poll_id"]
        final = window[window["poll_id"].isin(chosen)].copy()

        blocks = merge_blocks(
            list(final["party_id"].unique()) + list(res["party_id"])
        )
        block_of = {comp: i for i, b in enumerate(blocks) for comp in b}
        block_id = lambda pid: block_of[pid.split("+")[0]]

        final["block"] = final["party_id"].map(block_id)
        res = res.assign(block=res["party_id"].map(block_id))
        actual = res.groupby("block")["seats"].sum()
        # Label each block by its result lines (what actually ran).
        label = {
            b: short_name("+".join(sorted(set().union(
                *[g.split("+") for g in grp["party_id"]]))), names)
            for b, grp in res.groupby("block")
        }

        per_poll = final.pivot_table(
            index="block", columns="poll_id", values="seats", aggfunc="sum"
        )
        polled = per_poll.mean(axis=1)

        idx = sorted(set(actual.index) | set(polled.index))
        for b in idx:
            a = int(actual.get(b, 0))
            p = float(polled.get(b, 0.0))
            if a == 0 and p < 0.5:
                continue
            block_rows.append({
                "cycle": cycle,
                "block": label.get(b, short_name("+".join(sorted(blocks[b])), names)),
                "polled_avg": round(p, 1),
                "actual": a,
                "error": round(p - a, 1),
            })

        cyc = [r for r in block_rows if r["cycle"] == cycle]
        abs_errs = [abs(r["error"]) for r in cyc]
        worst = max(cyc, key=lambda r: abs(r["error"]))
        summary_rows.append({
            "cycle": cycle,
            "n_pollsters": final["poll_id"].nunique(),
            "n_blocks": len(cyc),
            "mae": round(sum(abs_errs) / len(abs_errs), 2),
            "total_abs_error": round(sum(abs_errs), 1),
            "worst_block": worst["block"],
            "worst_error": worst["error"],
        })

        # Pollster scorecard seed: each final poll vs the result partition.
        for pid_, g in final.groupby("poll_id"):
            by_block = g.groupby("block")["seats"].sum()
            errs = [
                abs(float(by_block.get(b, 0)) - int(actual.get(b, 0)))
                for b in set(actual.index) | set(by_block.index)
            ]
            pollster_rows.append({
                "cycle": cycle,
                "pollster": g["pollster"].iloc[0],
                "poll_id": pid_,
                "total_abs_error": sum(errs),
            })

    blocks_df = pd.DataFrame(block_rows)
    summary = pd.DataFrame(summary_rows)
    by_poll = pd.DataFrame(pollster_rows)
    scorecard = (
        by_poll[by_poll["pollster"] != "Unattributed"]
        .groupby("pollster")
        .agg(cycles=("cycle", "nunique"), mean_abs_error=("total_abs_error", "mean"))
        .round(1)
        .sort_values(["cycles", "mean_abs_error"], ascending=[False, True])
    )

    blocks_df.to_csv(PROCESSED_DIR / "backtest_blocks.csv", index=False)
    summary.to_csv(PROCESSED_DIR / "backtest_summary.csv", index=False)
    scorecard.to_csv(PROCESSED_DIR / "backtest_pollsters.csv")

    print(summary.to_string(index=False))
    print()
    print(scorecard[scorecard["cycles"] >= 3].to_string())

    plot(blocks_df, summary)
    print(f"\nwrote backtest CSVs and {FIG_DIR / 'backtest_final_polls.png'}")


def plot(blocks_df: pd.DataFrame, summary: pd.DataFrame) -> None:
    order = list(CYCLE_LABEL)
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    for y, cycle in enumerate(order):
        cyc = blocks_df[blocks_df["cycle"] == cycle]
        ax.scatter(
            cyc["error"], [y] * len(cyc),
            s=42, color=BLUE, alpha=0.75, linewidths=0, zorder=3,
        )
        worst = cyc.loc[cyc["error"].abs().idxmax()]
        ax.annotate(
            f"{worst['block']} {worst['error']:+.0f}",
            (worst["error"], y), textcoords="offset points",
            xytext=(0, 9), ha="center", fontsize=8, color=INK_2, zorder=4,
        )
        mae = summary.loc[summary["cycle"] == cycle, "mae"].iloc[0]
        ax.text(
            1.01, y, f"MAE {mae:.1f}", transform=ax.get_yaxis_transform(),
            va="center", fontsize=8, color=MUTED,
        )

    ax.axvline(0, color=BASELINE, lw=1.2, zorder=2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([CYCLE_LABEL[c] for c in order], fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel(
        "Seat error of the final-poll average  (polled − actual)",
        fontsize=9, color=INK_2,
    )
    ax.tick_params(axis="x", labelsize=8, colors=MUTED)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=1)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.set_title(
        "How wrong were the final polls? Eight Israeli elections, one dot per list",
        fontsize=11, color=INK, loc="left", pad=14,
    )
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / "backtest_final_polls.png", facecolor=SURFACE)


if __name__ == "__main__":
    main()
