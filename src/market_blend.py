"""Prediction-market blend (dossier s.71).

Polymarket trades the seat counts of the large lists, the threshold fate of
three small ones, the largest party and two bloc questions. This module
reweights the model's joint seat draws (mixture_draws.parquet) so that, for
every traded question, the weighted draws reproduce a linear pool of the
model's own probability and the market's:

    target_k = w * market_k + (1 - w) * model_k

w follows the money traded on the question (MARKET_WEIGHT_TIERS). The
weights are the minimum-relative-entropy solution (iterative proportional
fitting, damped), so the draws move as little as the targets require and
every draw stays a coherent 120-seat outcome: blocs, the official count and
the formation tree read the blended draws exactly as they read the model's.
The draws are then resampled (systematic, seeded) to equal weight.

No backtest exists: Israeli seat-count markets did not trade in earlier
cycles, so the weights are a stated judgment (s.71), not a graded layer.
Kalshi lists the same questions with a few hundred dollars of volume and is
left out; the prime-minister and hung-parliament markets price coalition
behaviour, not seats, and are reported beside the blend, not fitted.

    python src/market_blend.py --fetch          # pull prices (data/raw/markets/<utc>)
    python src/market_blend.py --report         # model vs market vs blend, no write
    python src/market_blend.py --apply          # rewrite the mixture draws in place
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR

RAW_DIR = PROCESSED_DIR.parent / "raw" / "markets"
GAMMA = "https://gamma-api.polymarket.com/events?slug={}"
SEED = 20261027
# Linear-pool weight on the market, by the event's total traded volume (USD).
MARKET_WEIGHT_TIERS = [(250_000, 0.50), (20_000, 0.25), (0, 0.15)]
# A bracket's price is the bid/ask midpoint when the spread is at most this
# wide, else the last trade; the brackets of an event are then normalised.
MAX_SPREAD = 0.10
DAMPING = 0.5
ITERS = 400

# (slug, kind, list column or None, extra)
QUESTIONS = [
    ("israel-election-likud-of-seats", "seats", "Likud", None),
    ("israel-election-yashar-of-seats", "seats", "Yashar", None),
    ("israel-election-together-of-seats", "seats", "Bennett 2026 + Yesh Atid", None),
    ("israel-election-shas-of-seats", "seats", "Shas", None),
    ("israel-election-otzma-of-seats", "seats", "Otzma Yehudit", None),
    ("israel-election-yisrael-beiteinu-of-seats", "seats", "Yisrael Beytenu", None),
    ("israel-election-reservistsnew-economic-party-vote-share", "pass", "Reservists – Economic Party", None),
    ("israel-election-religious-zionist-party-zehut-vote-share", "pass", "Religious Zionist Party", None),
    ("israel-election-united-arab-list-raam-vote-share", "pass", "Ra'am", None),
    ("israeli-legislative-election-winner", "largest", None, ("Yashar", "Likud")),
    ("israel-election-which-bloc-wins-more-seats", "bloc_more", None, None),
    ("israel-election-any-coalition-wins-a-majority", "any61", None, None),
]
# Reported, not fitted (coalition behaviour, not seats).
COMPARE_ONLY = ["israeli-election-results-in-a-hung-parliament",
                "who-will-be-the-next-prime-minister-of-israel-after-the-next-election"]
# The markets' bloc definitions (resolution text): Amcha counts with the
# Netanyahu bloc, the opposition is the four Zionist lists.
NB_COLS = ["Likud", "Otzma Yehudit", "Religious Zionist Party", "Amcha Yisrael",
           "United Torah Judaism", "Shas"]
OPP_COLS = ["The Democrats", "Yashar", "Bennett 2026 + Yesh Atid", "Yisrael Beytenu"]
THRESHOLD_PCT = 3.25


def fetch(out: Path | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out or RAW_DIR / stamp
    out.mkdir(parents=True, exist_ok=True)
    for slug in [q[0] for q in QUESTIONS] + COMPARE_ONLY:
        with urllib.request.urlopen(GAMMA.format(slug), timeout=30) as r:
            (out / f"{slug}.json").write_bytes(r.read())
    (out / "pulled_at.txt").write_text(stamp)
    return out


def latest_raw() -> Path:
    dirs = sorted(p for p in RAW_DIR.glob("*") if p.is_dir())
    if not dirs:
        raise FileNotFoundError("no market snapshot: run with --fetch")
    return dirs[-1]


def _price(m: dict) -> float:
    try:
        last = float(json.loads(m.get("outcomePrices") or "[]")[0])
    except (ValueError, IndexError):
        last = np.nan
    bid, ask = m.get("bestBid"), m.get("bestAsk")
    if bid is not None and ask is not None and float(ask) - float(bid) <= MAX_SPREAD:
        return (float(bid) + float(ask)) / 2.0
    return last


def _seat_range(label: str) -> tuple:
    s = label.replace(" ", "")
    if m := re.fullmatch(r"<(\d+)", s):
        return (0, int(m.group(1)) - 1)
    if m := re.fullmatch(r"(\d+)-(\d+)", s):
        return (int(m.group(1)), int(m.group(2)))
    if m := re.fullmatch(r"(\d+)\+", s):
        return (int(m.group(1)), 10 ** 6)
    raise ValueError(f"seat bracket {label!r}")


def _below_threshold(label: str) -> bool:
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", label)]
    return label.strip().startswith("<") and nums[0] <= THRESHOLD_PCT or (
        len(nums) == 2 and nums[1] <= THRESHOLD_PCT)


def market_question(raw: Path, slug: str, kind: str, extra) -> dict:
    ev = json.loads((raw / f"{slug}.json").read_text())[0]
    vol = float(ev.get("volume") or 0)
    mk = [m for m in ev.get("markets", []) if not m.get("closed")]
    if kind == "seats":
        cats = [(m.get("groupItemTitle"), _seat_range(m.get("groupItemTitle")), _price(m)) for m in mk]
        p = np.array([c[2] for c in cats]); p = p / p.sum()
        return {"labels": [c[0] for c in cats], "ranges": [c[1] for c in cats], "p": p, "vol": vol}
    if kind == "pass":
        below = sum(_price(m) for m in mk if _below_threshold(m.get("groupItemTitle")))
        tot = sum(_price(m) for m in mk)
        return {"labels": ["fails", "passes"], "p": np.array([below, tot - below]) / tot, "vol": vol}
    if kind == "largest":
        pr = {m.get("groupItemTitle"): _price(m) for m in mk}
        pr = {k: v for k, v in pr.items() if np.isfinite(v)}   # unpriced contracts out
        named = [pr.get(n, 0.0) for n in extra]
        rest = max(sum(pr.values()) - sum(named), 0.0)
        p = np.array(named + [rest]); p = p / p.sum()
        return {"labels": list(extra) + ["another list"], "p": p, "vol": vol}
    # binary: outcomePrices[0] is "Bibi" (bloc_more) or "Yes" (any61)
    y = _price(mk[0])
    return {"labels": ["no", "yes"] if kind == "any61" else ["Opp.", "Bibi"],
            "p": np.array([1 - y, y]), "vol": vol}


def indicators(draws: pd.DataFrame, kind: str, col, q: dict) -> np.ndarray:
    """n_draws x n_categories membership (rows sum to 1; ties split)."""
    n = len(draws)
    if kind == "seats":
        x = draws[col].values
        return np.stack([((x >= lo) & (x <= hi)).astype(float) for lo, hi in q["ranges"]], axis=1)
    if kind == "pass":
        x = draws[col].values > 0
        return np.stack([~x, x], axis=1).astype(float)
    if kind == "largest":
        seats = draws.values.astype(float)
        mx = seats.max(axis=1, keepdims=True)
        top = seats == mx
        share = top / top.sum(axis=1, keepdims=True)
        cols = list(draws.columns)
        named = [share[:, cols.index(n)] for n in q["labels"][:-1]]
        return np.stack(named + [1 - np.sum(named, axis=0)], axis=1)
    nb = draws[NB_COLS].sum(axis=1).values
    op = draws[OPP_COLS].sum(axis=1).values
    if kind == "bloc_more":
        bibi = (nb > op) + 0.5 * (nb == op)
        return np.stack([1 - bibi, bibi], axis=1).astype(float)
    if kind == "any61":
        y = ((nb >= 61) | (op >= 61)).astype(float)
        return np.stack([1 - y, y], axis=1)
    raise ValueError(kind)


def weight_for(vol: float) -> float:
    return next(w for v0, w in MARKET_WEIGHT_TIERS if vol >= v0)


def rake(mats: list, targets: list, iters: int = ITERS, damping: float = DAMPING) -> np.ndarray:
    """Minimum-relative-entropy weights matching every target (damped IPF)."""
    n = mats[0].shape[0]
    w = np.full(n, 1.0 / n)
    for _ in range(iters):
        for M, t in zip(mats, targets):
            cur = w @ M
            ratio = np.where(cur > 0, t / np.where(cur > 0, cur, 1), 1.0)
            w = w * (M @ (ratio ** damping))
            w /= w.sum()
    return w


def blend(draws: pd.DataFrame, raw: Path) -> tuple[np.ndarray, list]:
    mats, targets, rows = [], [], []
    for slug, kind, col, extra in QUESTIONS:
        q = market_question(raw, slug, kind, extra)
        M = indicators(draws, kind, col, q)
        model = M.mean(axis=0)
        w_mk = weight_for(q["vol"])
        t = w_mk * q["p"] + (1 - w_mk) * model
        mats.append(M); targets.append(t)
        rows.append({"slug": slug, "kind": kind, "labels": q["labels"], "volume": q["vol"],
                     "weight": w_mk, "market": q["p"], "model": model, "target": t})
    w = rake(mats, targets)
    for r, M in zip(rows, mats):
        r["blend"] = w @ M
    return w, rows


def resample(draws: pd.DataFrame, w: np.ndarray, seed: int = SEED) -> pd.DataFrame:
    """Systematic resampling to equal weight (same number of draws)."""
    n = len(w)
    u = (np.random.default_rng(seed).random() + np.arange(n)) / n
    idx = np.minimum(np.searchsorted(np.cumsum(w), u), n - 1)
    return draws.iloc[idx].reset_index(drop=True)


def ess(w: np.ndarray) -> float:
    return float(1.0 / np.sum(w ** 2))


def bloc_summary(draws: pd.DataFrame, blocs: dict) -> dict:
    """mixture_blocs.csv on (blended) draws: the registration_scenarios
    definitions (anti = the opposition lists; + Ra'am as a whole)."""
    cols = list(draws.columns)
    nb = draws[[c for c in cols if blocs.get(c) == "netanyahu_bloc"]].sum(axis=1).values
    anti = draws[[c for c in cols if blocs.get(c) == "opposition_bloc"]].sum(axis=1).values
    raam = draws["Ra'am"].values if "Ra'am" in cols else 0
    anti_raam = anti + raam
    return {"p_nb_61": round(float((nb >= 61).mean()), 3),
            "p_anti_61": round(float((anti >= 61).mean()), 3),
            "p_anti_raam_61": round(float((anti_raam >= 61).mean()), 3),
            "p_neither": round(float(((nb < 61) & (anti_raam < 61)).mean()), 3),
            "nb_mean": round(float(nb.mean()), 1),
            "nb_p05": int(np.percentile(nb, 5)), "nb_p95": int(np.percentile(nb, 95))}


def list_blocs(processed: Path = PROCESSED_DIR) -> dict:
    """Mixture-draw column -> registry bloc id, via bayes_forecast_2026.csv."""
    f = pd.read_csv(processed / "bayes_forecast_2026.csv")
    ids = {"Netanyahu bloc": "netanyahu_bloc", "Anti-Netanyahu bloc": "opposition_bloc",
           "Arab parties": "arab", "Unaligned": "unaligned"}
    return {r.list: ids.get(r.bloc, "unknown") for r in f.itertuples()}


def apply(processed: Path = PROCESSED_DIR, raw: Path | None = None) -> dict:
    """Rewrite the mixture outputs in `processed` from the market-blended
    draws: mixture_draws / mixture_share_draws (resampled together, so each
    seat vector keeps its own shares), bayes_forecast_mixture.csv,
    mixture_shares.csv (the official count's median shares) and
    mixture_blocs.csv. The model's draws are kept as *_model.parquet."""
    raw = raw or latest_raw()
    src = processed / "mixture_draws.parquet"
    ssrc = processed / "mixture_share_draws.parquet"
    model = pd.read_parquet(src)
    shares = pd.read_parquet(ssrc)
    model.to_parquet(processed / "mixture_draws_model.parquet")
    shares.to_parquet(processed / "mixture_share_draws_model.parquet")
    w, rows = blend(model, raw)
    n = len(w)
    u = (np.random.default_rng(SEED).random() + np.arange(n)) / n
    idx = np.minimum(np.searchsorted(np.cumsum(w), u), n - 1)
    blended = model.iloc[idx].reset_index(drop=True)
    bshares = shares.iloc[idx].reset_index(drop=True)
    blended.to_parquet(src)
    bshares.to_parquet(ssrc)
    # bayes_forecast_mixture.csv and mixture_shares.csv as registration_scenarios writes them
    pd.DataFrame({"list": blended.columns,
                  "mean": blended.mean(axis=0).round(1).values,
                  "p05": np.percentile(blended, 5, axis=0).astype(int),
                  "p95": np.percentile(blended, 95, axis=0).astype(int),
                  "p_pass": (blended >= 4).mean(axis=0).round(3).values}
                 ).sort_values("mean", ascending=False).to_csv(
        processed / "bayes_forecast_mixture.csv", index=False)
    old = pd.read_csv(processed / "mixture_shares.csv")
    comps = dict(zip(old["list"], old["components"]))
    pd.DataFrame({"list": bshares.columns,
                  "components": [comps.get(c, "") for c in bshares.columns],
                  "share_mean": np.round(bshares.mean(axis=0).values, 5),
                  "share_median": np.round(np.median(bshares.values, axis=0), 5)}).to_csv(
        processed / "mixture_shares.csv", index=False)
    summ = bloc_summary(blended, list_blocs(processed))
    pd.DataFrame([summ]).to_csv(processed / "mixture_blocs.csv", index=False)
    report = {"snapshot": raw.name, "ess": round(ess(w), 1), "n": len(w),
              "weights": MARKET_WEIGHT_TIERS, "blocs": summ,
              "questions": [{k: (v.round(4).tolist() if isinstance(v, np.ndarray) else v)
                             for k, v in r.items()} for r in rows]}
    (processed / "market_blend.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if a.fetch:
        print("snapshot:", fetch())
    if a.report or a.apply:
        raw = latest_raw()
        draws = pd.read_parquet(PROCESSED_DIR / "mixture_draws.parquet")
        w, rows = blend(draws, raw)
        print(f"snapshot {raw.name}; effective sample {ess(w):.0f} of {len(w)}")
        for r in rows:
            print(f"\n{r['slug']} (${r['volume']:,.0f}, w {r['weight']})")
            for i, lab in enumerate(r["labels"]):
                print(f"  {str(lab):14s} model {r['model'][i]:.3f}  market {r['market'][i]:.3f}  "
                      f"target {r['target'][i]:.3f}  blend {r['blend'][i]:.3f}")
        if a.apply:
            print(json.dumps(apply()["blocs"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
