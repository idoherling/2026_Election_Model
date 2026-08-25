"""Systematic-bias audit of Israeli final polls, 2009-2022.

Runs every testable bias hypothesis against the eight graded cycles, using
the same final-window / block-partition machinery as the backtest:

  1. Party size      — are small parties overstated, big parties understated?
  2. Party family    — signed error for Arab, haredi, right, centre-left lists
  3. Largest party   — is the seat-leader systematically under-polled?
  4. New lists       — are first-time lists harder to poll?
  5. Threshold zone  — what a final polling average of ~4 actually means,
                       including the "parked at 4" pattern
  6. Herding         — is final-week cross-pollster dispersion smaller than
                       sampling error alone would produce?
  7. Late swing      — do 3-6-week-out averages miss worse than final-week
                       ones (real movement) or the same (static bias)?

Outputs:
    data/processed/bias_family.csv, bias_size.csv, bias_threshold.csv,
    bias_herding.csv, bias_late_swing.csv
    output/figures/bias_family.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import (
    FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE,
    FINAL_WINDOW, SEAT_SUM_RANGE, CYCLE_LABEL, merge_blocks,
)
from scrape_polls import ELECTION_DAY, PROCESSED_DIR

BLUE = "#2a78d6"

FAMILY = {
    "arab": {"raam", "hadash_taal", "balad", "joint_list", "raam_taal",
             "raam_balad"},
    "haredi": {"shas", "utj", "deri"},
    "right": {"likud", "yisrael_beytenu", "jewish_home", "national_union",
              "urwp", "yamina", "new_right", "otzma", "otzma_noam",
              "otzma_leyisrael", "rzp", "yachad_yishai", "zionist_spirit",
              "am_shalem", "zehut", "new_hope", "tnufa", "derekh_eretz"},
    "centre_left": {"labor", "meretz", "kadima", "yesh_atid", "hatnuah",
                    "zionist_union", "blue_white", "gil", "hosen", "telem",
                    "hosen_telem", "yesh_atid_telem", "dem_union", "gesher",
                    "labor_gesher", "labor_meretz", "labor_gesher_meretz",
                    "kulanu", "democrats", "greens", "israelis", "idp", "nep",
                    "unity", "zionist_home", "yashar", "together",
                    "bennett_2026"},
}
FAMILY_OF = {p: f for f, ps in FAMILY.items() for p in ps}


def family_of_block(components: set[str]) -> str:
    fams = [FAMILY_OF.get(c, "other") for c in components]
    return max(set(fams), key=fams.count)


def window_polls(polls, cycle, eday, start_days, end_days):
    """Latest poll per pollster with fieldwork in (eday-start, eday-end]."""
    w = polls[
        (polls["cycle"] == cycle)
        & (polls["fieldwork_end"] <= eday - pd.Timedelta(days=end_days))
        & (polls["fieldwork_end"] > eday - pd.Timedelta(days=start_days))
    ]
    totals = w.groupby("poll_id")["seats"].sum()
    ok = totals[(totals >= SEAT_SUM_RANGE[0]) & (totals <= SEAT_SUM_RANGE[1])]
    w = w[w["poll_id"].isin(ok.index)]
    meta = w[["pollster", "poll_id", "fieldwork_end"]].drop_duplicates()
    meta = meta.sort_values(["pollster", "fieldwork_end", "poll_id"],
                            ascending=[True, False, True])
    return w[w["poll_id"].isin(meta.groupby("pollster").head(1)["poll_id"])]


def block_frame(final, res):
    """Per-block: polled average, per-poll values, actual, components."""
    blocks = merge_blocks(list(final["party_id"].unique())
                          + list(res["party_id"]))
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    final = final.assign(block=final["party_id"].map(
        lambda p: block_of[p.split("+")[0]]))
    res = res.assign(block=res["party_id"].map(
        lambda p: block_of[p.split("+")[0]]))
    per_poll = final.pivot_table(index="block", columns="poll_id",
                                 values="seats", aggfunc="sum")
    actual = res.groupby("block")["seats"].sum()
    idx = sorted(set(per_poll.index) | set(actual.index))
    per_poll = per_poll.reindex(idx)
    return pd.DataFrame({
        "polled": per_poll.mean(axis=1),
        "actual": actual.reindex(idx).fillna(0).astype(int),
        "n_polls": per_poll.notna().sum(axis=1),
        "spread": per_poll.std(axis=1),
        "family": [family_of_block(blocks[b]) for b in idx],
        "components": ["+".join(sorted(blocks[b])) for b in idx],
    }).fillna({"polled": 0.0, "n_polls": 0})


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")

    frames, early_frames = {}, {}
    for cycle, res in results.groupby("cycle"):
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        frames[cycle] = block_frame(
            window_polls(polls, cycle, eday, FINAL_WINDOW, 0), res)
        early_frames[cycle] = block_frame(
            window_polls(polls, cycle, eday, 42, 21), res)

    allb = pd.concat([f.assign(cycle=c) for c, f in frames.items()])
    allb["error"] = allb["polled"] - allb["actual"]
    ran = allb[(allb["actual"] > 0) | (allb["polled"] >= 0.5)]

    # 1. Size bias -----------------------------------------------------------
    bins = pd.cut(ran["actual"], [-1, 0, 6, 12, 20, 40],
                  labels=["died (0)", "1-6", "7-12", "13-20", "21+"])
    size = ran.groupby(bins, observed=True)["error"].agg(["mean", "count"])
    slope = np.polyfit(ran["actual"], ran["error"], 1)[0]
    size.to_csv(PROCESSED_DIR / "bias_size.csv")
    print("1. SIZE: mean signed error by actual seats")
    print(size.round(2).to_string())
    print(f"   slope of error on size: {slope:+.3f} seats of error "
          f"per actual seat\n")

    # 2. Family bias ---------------------------------------------------------
    fam = ran.groupby(["family", "cycle"])["error"].sum().unstack()
    fam["pooled_mean"] = fam.mean(axis=1)
    fam.to_csv(PROCESSED_DIR / "bias_family.csv")
    print("2. FAMILY: total signed error (seats) per cycle")
    print(fam.round(1).to_string(), "\n")

    # 3. Largest party -------------------------------------------------------
    flat = allb.reset_index(drop=True)
    largest = flat.loc[flat.groupby("cycle")["actual"].idxmax()]
    print("3. LARGEST LIST: signed error per cycle")
    print(largest.set_index("cycle")[["components", "polled", "actual",
                                      "error"]].round(1).to_string())
    print(f"   mean {largest['error'].mean():+.2f}, "
          f"under-polled in {int((largest['error'] < 0).sum())}/8 cycles\n")

    # 4. New lists (first cycle a component set appears) ---------------------
    order = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
    seen: set[str] = set()
    debut_flags = []
    for cyc in order:
        f = frames[cyc]
        comps = [set(c.split("+")) for c in f["components"]]
        debut_flags.extend(not (s & seen) for s in comps)
        seen |= set().union(*comps) if comps else set()
    allb = allb.assign(debut=debut_flags)
    ran2 = allb[(allb["actual"] > 0) | (allb["polled"] >= 0.5)]
    print("4. NEW LISTS: |error| for debut lists vs veterans")
    print(ran2.groupby("debut")["error"]
          .agg(mean_abs=lambda s: s.abs().mean(), mean="mean", count="count")
          .round(2).to_string(), "\n")

    # 5. Threshold zone ------------------------------------------------------
    zone = allb[(allb["polled"] >= 0.5) | (allb["actual"].isin([4, 5]))]
    zbins = pd.cut(zone["polled"], [0.5, 3.5, 4.5, 5.5, 7.5],
                   labels=["0.5-3.5", "3.5-4.5 (parked at 4)",
                           "4.5-5.5", "5.5-7.5"])
    thr = zone.groupby(zbins, observed=True).agg(
        died=("actual", lambda s: (s == 0).mean()),
        mean_actual=("actual", "mean"), n=("actual", "count"))
    thr.to_csv(PROCESSED_DIR / "bias_threshold.csv")
    ghosts = allb[(allb["polled"] < 0.5) & (allb["actual"] >= 4)]
    print("5. THRESHOLD ZONE: fate of lists by final polling average")
    print(thr.round(2).to_string())
    print(f"   lists polled ~0 that WON seats: {len(ghosts)} "
          f"({', '.join(ghosts['components'] + ' ' + ghosts['cycle'])})\n")

    # 6. Herding -------------------------------------------------------------
    herd_rows = []
    for cyc, f in frames.items():
        big = f[(f["actual"] >= 4) & (f["n_polls"] >= 5)]
        exp = np.sqrt(big["polled"] / 120 * (1 - big["polled"] / 120) / 500) * 120
        herd_rows.append({
            "cycle": cyc,
            "observed_spread": big["spread"].mean(),
            "sampling_spread_n500": exp.mean(),
            "ratio": (big["spread"] / exp).mean(),
        })
    herd = pd.DataFrame(herd_rows).set_index("cycle").sort_index()
    herd.to_csv(PROCESSED_DIR / "bias_herding.csv")
    print("6. HERDING: final-week cross-pollster spread vs pure sampling "
          "spread (ratio < 1 = herding)")
    print(herd.round(2).to_string(), "\n")

    # 7. Late swing vs static bias ------------------------------------------
    swing_rows = []
    for cyc in order:
        # Align the two windows on list components — their block partitions
        # are numbered independently, so a positional join would misalign.
        fin = frames[cyc].set_index("components")
        ear = (early_frames[cyc].set_index("components")[["polled"]]
               .rename(columns={"polled": "polled_early"}))
        j = fin.join(ear, how="inner")
        j = j[(j["actual"] > 0) | (j["polled"] >= 0.5)]
        swing_rows.append({
            "cycle": cyc,
            "mae_3to6wk": (j["polled_early"] - j["actual"]).abs().mean(),
            "mae_final": (j["polled"] - j["actual"]).abs().mean(),
        })
    swing = pd.DataFrame(swing_rows).set_index("cycle")
    swing["late_movement_helped"] = swing["mae_3to6wk"] - swing["mae_final"]
    swing.to_csv(PROCESSED_DIR / "bias_late_swing.csv")
    print("7. LATE SWING: MAE at 3-6 weeks out vs final week")
    print(swing.round(2).to_string())

    plot_family(fam.drop(columns="pooled_mean"))
    print(f"\nwrote bias_*.csv and {FIG_DIR / 'bias_family.png'}")


def plot_family(fam: pd.DataFrame) -> None:
    order = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
    fam = fam[order]
    label = {"arab": "Arab lists", "haredi": "Haredi lists",
             "right": "Right lists", "centre_left": "Centre-left lists",
             "other": "Other"}
    fam = fam.rename(index=label).drop(index="Other", errors="ignore")
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for y, (name, row) in enumerate(fam.iterrows()):
        ax.axhline(y, color=GRID, lw=0.7, zorder=1)
        ax.scatter(range(len(order)), [y] * len(order), s=0)  # anchor row
        for x, cyc in enumerate(order):
            v = row[cyc]
            ax.scatter(x, y, s=min(abs(v) * 55 + 20, 420), color=BLUE,
                       alpha=0.85 if v < 0 else 0.35, zorder=3,
                       edgecolors=BLUE, linewidths=1.2)
            ax.annotate(f"{v:+.0f}", (x, y), ha="center", va="center",
                        fontsize=7.5, zorder=4,
                        color=SURFACE if abs(v) > 3 and v < 0 else INK_2)
    ax.set_yticks(range(len(fam)))
    ax.set_yticklabels(fam.index, fontsize=9.5, color=INK)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([CYCLE_LABEL[c] for c in order], fontsize=8.5,
                       color=MUTED)
    ax.invert_yaxis()
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Final-poll signed error by party family, in seats "
                 "(dark = polls understated the family)",
                 fontsize=10.5, color=INK, loc="left", pad=14)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "bias_family.png", facecolor=SURFACE)


if __name__ == "__main__":
    main()
