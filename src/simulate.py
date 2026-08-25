"""Seat simulation: from corrected polling average to P(bloc >= 61).

Pipeline per simulation draw:
  1. start from the house-effect-corrected, trend-adjusted weighted average
     (block space of the last 90 days), converted to vote shares —
     sub-threshold lists enter at their polled vote percentages;
  2. add correlated errors calibrated on the 2009-2022 backtest and bias
     audit: a bloc-level swing (t-distributed, sd from historical bloc
     errors), Arab and haredi family shocks (historical mean AND spread —
     polls have understated both in 6 of 8 cycles), and per-list noise,
     widened x1.5 for debut lists. All sds scale with time to election:
     sqrt(1 + days_out / 25), anchored on the audit's finding that 3-6-week
     averages miss ~1.5x worse than final-week ones;
  3. apply the electoral threshold;
  4. allocate 120 seats by Bader-Ofer (D'Hondt) with surplus-vote pairs
     pooled when both partners pass;
  5. tally bloc outcomes.

The audit's largest-list understatement (-2.3 mean) is deliberately NOT
applied as a deterministic correction — it stays inside the uncertainty.
Surplus pairs are pre-filing assumptions; update SURPLUS_PAIRS when the
real agreements are registered with the CEC.

The core functions take explicit inputs so validate_model.py can rerun the
identical pipeline as-of past elections.

Outputs:
    data/processed/forecast_2026.csv     per-list seat distribution
    data/processed/forecast_blocs.csv    bloc probability summary
    output/figures/forecast_2026.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from backtest import FIG_DIR, SURFACE, INK, INK_2, MUTED, GRID, BASELINE, merge_blocks, short_name
from bias_audit import FAMILY_OF
from house_effects import LIST_WINDOW, deviations, eb_shrink
from normalize import load_party_registry
from polling_average import (
    ELECTION_DAY_2026, load_2026, poll_weights, trend_adjust,
)
from scrape_polls import PROCESSED_DIR

N_SIMS = 20_000
SEED = 20261027
THRESHOLD = 0.0325
T_DF = 5  # fat tails, per the backtest's outlier cycles

# Calibration (seats), from bias_family.csv / backtest_blocks.csv:
BLOC_SWING_SD = 3.5          # sd of right+haredi total error across cycles
FAMILY_SHOCK = {             # (mean, sd) of family signed error, seats
    "arab": (-0.7, 1.2),
    "haredi": (-1.0, 1.6),
}
LIST_SD_BASE = 1.0           # idiosyncratic per-list sd, seats
LIST_SD_SLOPE = 0.05         # + per polled seat
DEBUT_FACTOR = 1.5           # audit: debut lists ~50% harder to poll
DEBUT = {"yashar", "together", "democrats", "unity", "zionist_home"}
SUB_THRESHOLD_DEFAULT = 0.015  # share for 0-seat lists with no polled pct

# ASSUMED pre-filing surplus-vote pairs (by dominant component); the 2022
# pattern adapted to 2026 lists. Replace with the registered agreements.
SURPLUS_PAIRS = [
    ("likud", "rzp"),
    ("shas", "utj"),
    ("together", "yashar"),
    ("democrats", "yisrael_beytenu"),
]

BLOC_LABEL = {"netanyahu_bloc": "Netanyahu bloc",
              "opposition_bloc": "Anti-Netanyahu bloc", "other": "Arab parties"}
BLUE = "#2a78d6"


def uncertainty_scale(days_out: int) -> float:
    return float(np.sqrt(1.0 + max(days_out, 0) / 25.0))


def corrected_average(polls: pd.DataFrame | None = None,
                      asof: pd.Timestamp | None = None,
                      eday: pd.Timestamp | None = ELECTION_DAY_2026):
    """House-effect-corrected, trend-adjusted block averages.

    Returns (frame keyed by component string, asof).
    """
    if polls is None:
        polls = load_2026()
    if asof is None:
        asof = polls["fieldwork_end"].max()
    recent = polls[(polls["fieldwork_end"] > asof - pd.Timedelta(days=LIST_WINDOW))
                   & (polls["fieldwork_end"] <= asof)
                   & (polls["pollster"] != "Unattributed")].copy()

    blocks = merge_blocks(recent["party_id"].unique())
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    recent["unit"] = recent["party_id"].map(lambda p: block_of[p.split("+")[0]])
    wide = recent.pivot_table(index="poll_id", columns="unit",
                              values="seats", aggfunc="sum").fillna(0)
    meta = recent[["poll_id", "pollster", "fieldwork_end", "sample_size"]]
    meta = meta.drop_duplicates("poll_id").set_index("poll_id")
    units = [u for u in range(len(blocks)) if u in wide.columns]
    wide = meta.join(wide)

    dev = deviations(wide, units)
    adj = wide.copy()
    if not dev.empty:
        h = eb_shrink(dev, units).pivot(
            index="pollster", columns="unit", values="house_effect")
        h = h.reindex(columns=units)
        adj[units] = wide[units] - h.reindex(wide["pollster"])[units].fillna(0).values
    adj[units] = trend_adjust(adj[units], meta["fieldwork_end"], asof)

    w = poll_weights(adj.reset_index()[["poll_id", "pollster",
                                        "fieldwork_end", "sample_size"]],
                     asof, eday=eday)
    live = adj.loc[adj.index.isin(w.index)]
    ww = w.reindex(live.index)
    avg = live[units].mul(ww, axis=0).sum() / ww.sum()

    pct = recent[recent["vote_pct"].notna()]
    pct_by_unit = (pct[pct["poll_id"].isin(w.index)]
                   .groupby("unit")["vote_pct"].mean() / 100.0)

    return pd.DataFrame({
        "components": ["+".join(sorted(blocks[u])) for u in avg.index],
        "avg_seats": avg.clip(lower=0).values,
        "polled_pct": pct_by_unit.reindex(avg.index).values,
    }), asof


def build_inputs(polls: pd.DataFrame | None = None,
                 asof: pd.Timestamp | None = None,
                 eday: pd.Timestamp | None = ELECTION_DAY_2026,
                 bloc_overrides: dict[str, str] | None = None,
                 debut: set[str] = DEBUT):
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    bloc_map.update(bloc_overrides or {})
    names = dict(zip(reg["party_id"], reg["name_en"]))
    avg, asof = corrected_average(polls, asof, eday)

    comps = [set(c.split("+")) for c in avg["components"]]
    avg["label"] = [short_name(c, names) for c in avg["components"]]
    avg["bloc"] = [
        (lambda bs: bs.pop() if len(bs) == 1 else "other")(
            {bloc_map.get(c, "other") for c in comp})
        for comp in comps
    ]
    fams = [[FAMILY_OF.get(c, "other") for c in comp] for comp in comps]
    avg["family"] = [max(set(f), key=f.count) for f in fams]
    avg["debut"] = [bool(comp & debut) for comp in comps]

    # Base vote shares: passers by seat share of the above-threshold pie,
    # sub-threshold lists by their polled percentages.
    below = avg["avg_seats"] < 0.5
    sub_share = avg.loc[below, "polled_pct"].fillna(SUB_THRESHOLD_DEFAULT)
    avg.loc[below, "share"] = sub_share
    passers_pie = max(1.0 - sub_share.sum() - 0.01, 0.5)  # ~1% micro-lists
    avg.loc[~below, "share"] = avg.loc[~below, "avg_seats"] / 120.0 * passers_pie
    return avg, asof


def dhondt(votes: np.ndarray, seats: int) -> np.ndarray:
    """Seats per faction by highest averages (Bader-Ofer core)."""
    alloc = np.zeros(len(votes), dtype=int)
    quot = votes.astype(float).copy()
    for _ in range(seats):
        i = int(np.argmax(quot))
        alloc[i] += 1
        quot[i] = votes[i] / (alloc[i] + 1)
    return alloc


def simulate_core(avg: pd.DataFrame, pairs: list[tuple[str, str]],
                  threshold: float = THRESHOLD, scale: float = 1.0,
                  bloc_swing_sd: float = BLOC_SWING_SD,
                  family_shock: dict | None = None,
                  n_sims: int = N_SIMS, seed: int = SEED) -> np.ndarray:
    family_shock = FAMILY_SHOCK if family_shock is None else family_shock
    rng = np.random.default_rng(seed)
    n_lists = len(avg)
    base = avg["share"].values

    swing = rng.standard_t(T_DF, n_sims) * bloc_swing_sd * scale / 120.0
    fam_shock = {
        f: (mu + rng.standard_t(T_DF, n_sims) * sd * scale) / 120.0
        for f, (mu, sd) in family_shock.items()
    }
    sd_list = (LIST_SD_BASE + LIST_SD_SLOPE * avg["avg_seats"].values) / 120.0
    sd_list = sd_list * np.where(avg["debut"].values, DEBUT_FACTOR, 1.0) * scale
    noise = rng.standard_normal((n_sims, n_lists)) * sd_list

    is_nb = (avg["bloc"] == "netanyahu_bloc").values
    shares = np.tile(base, (n_sims, 1))
    w_nb = np.where(is_nb, base, 0.0)
    w_op = np.where(~is_nb, base, 0.0)
    if w_nb.sum() > 0 and w_op.sum() > 0:
        shares += swing[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())
    for f, shock in fam_shock.items():
        in_f = (avg["family"] == f).values
        if not in_f.any() or in_f.all():
            continue
        w_f = np.where(in_f, base, 0.0)
        w_rest = np.where(~in_f, base, 0.0)
        shares += shock[:, None] * (w_f / w_f.sum() - w_rest / w_rest.sum())
    shares = np.clip(shares + noise, 0.0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    comp_of = {c: i for i, cs in enumerate(avg["components"]) for c in cs.split("+")}
    pair_idx = [(comp_of[a], comp_of[b]) for a, b in pairs
                if a in comp_of and b in comp_of
                and comp_of[a] != comp_of[b]]

    seats = np.zeros((n_sims, n_lists), dtype=int)
    for s in range(n_sims):
        sh = shares[s]
        passed = sh >= threshold
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        faction_votes, faction_members = [], []
        used = set()
        for a, b in pair_idx:
            if passed[a] and passed[b]:
                faction_votes.append(votes[a] + votes[b])
                faction_members.append([a, b])
                used |= {a, b}
        for i in np.nonzero(passed)[0]:
            if i not in used:
                faction_votes.append(votes[i])
                faction_members.append([int(i)])
        alloc = dhondt(np.array(faction_votes), 120)
        for members, k in zip(faction_members, alloc):
            if len(members) == 1:
                seats[s, members[0]] = k
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[s, a], seats[s, b] = int(inner[0]), int(inner[1])
    return seats


def main() -> None:
    avg, asof = build_inputs()
    days_out = max((ELECTION_DAY_2026 - asof).days, 0)
    scale = uncertainty_scale(days_out)
    seats = simulate_core(avg, SURPLUS_PAIRS, scale=scale)

    dist = pd.DataFrame({
        "list": avg["label"], "bloc": avg["bloc"].map(BLOC_LABEL),
        "avg_input": avg["avg_seats"].round(1),
        "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p50": np.percentile(seats, 50, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
    }).sort_values("mean", ascending=False)
    dist["asof"] = asof.date().isoformat()
    dist.to_csv(PROCESSED_DIR / "forecast_2026.csv", index=False)

    nb = seats[:, (avg["bloc"] == "netanyahu_bloc").values].sum(axis=1)
    anti = seats[:, (avg["bloc"] == "opposition_bloc").values].sum(axis=1)
    summary = pd.DataFrame([{
        "asof": asof.date().isoformat(), "n_sims": N_SIMS,
        "days_to_election": days_out, "uncertainty_scale": round(scale, 2),
        "p_netanyahu_bloc_61": (nb >= 61).mean().round(3),
        "p_anti_bloc_61": (anti >= 61).mean().round(3),
        "p_neither": ((nb < 61) & (anti < 61)).mean().round(3),
        "nb_mean": nb.mean().round(1), "nb_p05": int(np.percentile(nb, 5)),
        "nb_p95": int(np.percentile(nb, 95)),
    }])
    summary.to_csv(PROCESSED_DIR / "forecast_blocs.csv", index=False)

    print(f"Forecast as of {asof.date()} ({N_SIMS:,} simulations, "
          f"{days_out} days out, uncertainty x{scale:.2f})\n")
    print(dist.drop(columns="asof").to_string(index=False))
    s = summary.iloc[0]
    print(f"\nP(Netanyahu bloc >= 61) = {s['p_netanyahu_bloc_61']:.1%}")
    print(f"P(anti-Netanyahu bloc >= 61, without Arab parties) = "
          f"{s['p_anti_bloc_61']:.1%}")
    print(f"P(neither bloc reaches 61) = {s['p_neither']:.1%}")
    print(f"Netanyahu bloc: mean {s['nb_mean']}, 90% interval "
          f"[{s['nb_p05']}, {s['nb_p95']}]")

    plot(nb, s)
    print(f"\nwrote forecast_2026.csv, forecast_blocs.csv, "
          f"{FIG_DIR / 'forecast_2026.png'}")


def plot(nb: np.ndarray, s: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=200, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    lo, hi = int(nb.min()), int(nb.max())
    bins = np.arange(lo - 0.5, hi + 1.5)
    counts, edges = np.histogram(nb, bins=bins, density=True)
    centers = (edges[:-1] + edges[1:]) / 2
    maj = centers >= 60.5
    ax.bar(centers[~maj], counts[~maj], width=0.92, color=BLUE, alpha=0.45,
           linewidth=0)
    ax.bar(centers[maj], counts[maj], width=0.92, color=BLUE, alpha=0.95,
           linewidth=0)
    ax.set_xlim(lo - 2, max(hi, 66) + 2)
    ax.axvline(60.5, color=BASELINE, lw=1.2, ls=(0, (4, 3)))
    ax.text(60.8, ax.get_ylim()[1] * 0.95, "61 — majority",
            fontsize=8.5, color=MUTED, va="top")
    ax.text(0.985, 0.82,
            f"P(Netanyahu bloc ≥ 61)\n{s['p_netanyahu_bloc_61']:.0%}",
            transform=ax.transAxes, ha="right", fontsize=11, color=INK,
            fontweight="bold")
    ax.text(0.985, 0.64,
            f"mean {s['nb_mean']:.0f} seats · 90% interval "
            f"{s['nb_p05']}–{s['nb_p95']}",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=INK_2)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(axis="x", labelsize=8.5, colors=MUTED)
    ax.set_xlabel("Netanyahu-bloc seats across simulations", fontsize=9,
                  color=INK_2)
    ax.set_title("The only number that matters — simulated Netanyahu-bloc "
                 "seat distribution", fontsize=11, color=INK, loc="left",
                 pad=12)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "forecast_2026.png", facecolor=SURFACE)


if __name__ == "__main__":
    main()
