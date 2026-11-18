"""The post-election scorecard: the frozen forecast, and every model of the
site's "Choose a model" panel, graded against the official result with
proper scoring rules.

    python src/scorecard.py --freeze                    freeze the published forecast, write the page
    python src/scorecard.py --verify [FILE]             recompute a frozen file's sha256
    python src/scorecard.py --score --result R [--government G] [--pm NAME] [--frozen FILE]
    python src/scorecard.py --page                      rebuild the page from what is stored
    python src/scorecard.py --rehearse 2022             the whole path on 2022 (rehearsal page)

RUNBOOK
  final build   the last build before the poll blackout (fieldwork to D-4, 23 Oct;
                bayes_model.EVENT_BLACKOUT_DAYS). Commit the build, then
                  python src/scorecard.py --freeze
                  git add data/processed/frozen_forecast_<asof>.json output/site/scorecard.*
                and commit. A freeze made before the blackout is marked provisional; one
                made during it is final (no poll can be published after it). Publish
                the site with scorecard.html and scorecard.json beside it
                (pipeline.SUPPORTING_FILES): the page shows the sha256 before any result.
  28 Oct        python src/scorecard.py --score --result <R>, where R is
                  - the CEC's result as a CSV: list,votes,seats (list = ballot letters,
                    English or Hebrew name; the certified result is the authority), or
                  - election_night.py's final page data, output/site/election-night.json, or
                  - one of its snapshot directories, data/raw/election_night/<stamp>
                    (the seat law is applied to the count, election_night.allocate).
                Republish scorecard.html + scorecard.json.
  later         python src/scorecard.py --score --government netanyahu|change|unity|repeat
                  --pm "<name>"   once the government is sworn in (the stored result is
                reused); repeat election = --government repeat --pm "none (repeat election)".

WHAT IS FROZEN (data/processed/frozen_forecast_<asof>.json, committed)
  The published official forecast and every variant of data/processed/
  model_variants.json: per-list seat pmfs (integer counts over the draws:
  the official from mixture_draws.parquet, the published distribution;
  the variants from their build_variants runs), central counts, 90%
  intervals, bloc probabilities, formation groups and P(next PM); the
  scoring rules and the backtest expectations below; the git commit and
  the sha256 of every input file. The file's sha256 is taken over the
  canonical JSON of the payload (sorted keys, no spaces, UTF-8), so
  `--verify` or three lines of Python reproduce it.

THE SCORES (per model; the rules are frozen with the forecast)
  per list      log score log p(y) of the seat count y, CRPS
                sum_k (F(k) - 1{k >= y})^2 (seats; for integer forecasts this is
                the exact integral), mid-PIT F(y-1) + p(y)/2, threshold Brier
                (P(seats > 0) - passed)^2, 90%-interval coverage, absolute error
                of the central count.
                A seat count no draw reached is scored at half a draw (0.5 / n).
                Means are over the scored lists: lists the official forecast puts
                at 1% of the vote or more (the record's smallest graded list was
                1.15%) and any list that wins seats. The threshold Brier is also
                given over every list.
  blocs         Brier and log score of P(Netanyahu bloc >= 61) and P(change bloc
                >= 61) (the site's blocs, site/template.html BLOC). A published
                probability of 0.000 is scored at 0.0005 (half its rounding unit).
  formation     log score of the government group (netanyahu / change / unity /
                repeat) and of the next PM, manual inputs, the same floor.
  ranking       by the mean per-list log score, then the CRPS.
  expectation   each score beside what the eight-cycle record says such scores look
                like (data/processed/model_validation_bayes_lists.csv and
                model_validation_bayes.csv, the validate_bayes eve harness): the
                per-cycle values of the same score, 2009-2022, and where 2026 falls
                among them; each variant's own graded backtest row (median MAE,
                coverage, threshold Brier) beside its result. The record keeps
                only each projection's mean, median, 90% interval and P(pass),
                so its log scores, CRPS and PITs are computed on a rebuilt pmf
                (record_pmf), an approximation that is said so on the page.
                Beside it, what the model itself expected (self_expectation,
                frozen): each score's expectation under its own pmfs and, for
                the official model, the 5-95% range of a whole election's mean
                score over its joint draws. The 2026 forecast is wider than most
                past ones, so a calibrated 2026 model can land outside the
                record's range; the two references are read together.
  One election is one draw: twelve-odd correlated lists from a single
  election. A model that ranks first may simply have been lucky; the
  eight-cycle backtest remains the better guide to which model is better.

THE FINAL POLLS (poll_comparison; 2026 pages with a result)
  The official forecast's central counts beside every outlet's last poll
  before the blackout (fieldwork from 14 Oct) and their average: seats
  missed, the Netanyahu-bloc error, threshold calls and the vote-share error
  per list (src/postmortem_shares.py). Computed at page build, outside the
  frozen payload, so the fingerprint is unaffected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import NormalDist
from typing import Optional

import numpy as np
import pandas as pd

import election_night as en
from build_variants import seat_pmfs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output" / "site"
OUT_HTML = OUT_DIR / "scorecard.html"
PAGE_TEMPLATE = ROOT / "site" / "scorecard.html"
RECORD_LISTS = PROCESSED / "model_validation_bayes_lists.csv"
RECORD_BLOCS = PROCESSED / "model_validation_bayes.csv"
COUNTS = ROOT / "data" / "cec_final_counts.csv"

ELECTION_DAY = date(2026, 10, 27)
POLLS_CLOSE_IL = datetime(2026, 10, 27, 22, 0)        # Israel time
BLACKOUT_DAYS = 4                                      # = bayes_model.EVENT_BLACKOUT_DAYS
BLACKOUT_FROM = ELECTION_DAY - timedelta(days=BLACKOUT_DAYS)

SCORED_SHARE = 0.01        # lists scored in the means: official mean share >= 1% (or seats won)
FLOOR_DRAWS = 0.5          # a seat count no draw reached: half a draw
FLOOR_P = 0.0005           # a published probability of 0.000: half its rounding unit
GROUPS = ["netanyahu", "change", "unity", "repeat"]
BLOC_KEYS = ["nb", "anti"]
INPUTS = ["mixture_draws.parquet", "official_forecast.csv", "mixture_blocs.csv",
          "mixture_shares.csv", "government_groups.csv", "pm_probabilities.csv",
          "model_variants.json", "model_validation_bayes_lists.csv", "model_validation_bayes.csv"]
# (metric, which way is better) for the per-model summary
METRICS = [("log", "high"), ("crps", "low"), ("abs_err", "low"), ("coverage", None),
           ("brier", "low")]
RULES = {
    "scored_share": SCORED_SHARE, "floor_draws": FLOOR_DRAWS, "floor_p": FLOOR_P,
    "interval": 0.90, "rank_by": ["log", "crps"], "pit": "mid-PIT F(y-1) + p(y)/2",
    "crps": "sum over seat counts k of (F(k) - 1{k >= y})^2",
    "threshold_brier": "(P(seats > 0) - passed)^2",
    "blocs": {"nb": "Netanyahu bloc >= 61", "anti": "change bloc (without Ra'am) >= 61"},
    "groups": GROUPS,
    "record": "per-cycle values of the same scores on the eight-cycle eve record; log score, "
              "CRPS and PIT on pmfs rebuilt from the record's summaries (record_pmf)",
}
PM_HE = {"Netanyahu": "נתניהו", "Eisenkot": "אייזנקוט", "Bennett": "בנט", "Liberman": "ליברמן",
         "Lapid": "לפיד", "none (repeat election)": "אף אחד (בחירות חוזרות)",
         "Likud successor (unity)": "יורש בליכוד (ממשלת אחדות)",
         "rotation / Likud successor": "רוטציה / יורש בליכוד", "another leader": "מנהיג אחר"}
PM_EN = {"none (repeat election)": "No one (repeat election)",
         "Likud successor (unity)": "A Likud successor (unity government)",
         "rotation / Likud successor": "Rotation / Likud successor",
         "another leader": "Another leader"}


class ScorecardError(RuntimeError):
    pass


# --------------------------------------------------------------- proper scores
def pmf_probs(spec) -> tuple:
    """[lo, c_lo, c_lo+1, ...] (counts or probabilities) -> (lo, p), p summing to 1."""
    lo = int(spec[0])
    c = np.asarray(spec[1:], dtype=float)
    t = c.sum()
    if t <= 0:
        return 0, np.array([1.0])
    return lo, c / t


def point_mass(k: int = 0) -> list:
    return [int(k), 1]


def prob_at(lo: int, p: np.ndarray, y: int) -> float:
    i = int(y) - lo
    return float(p[i]) if 0 <= i < len(p) else 0.0


def cdf_at(lo: int, p: np.ndarray, y: int) -> float:
    """F(y) = P(X <= y)."""
    i = int(y) - lo
    if i < 0:
        return 0.0
    return float(p[: i + 1].sum()) if i < len(p) else 1.0


def log_score(lo: int, p: np.ndarray, y: int, floor: float) -> float:
    """log p(y); a seat count with no mass is scored at `floor`."""
    return math.log(max(prob_at(lo, p, y), floor))


def crps(lo: int, p: np.ndarray, y: int) -> float:
    """CRPS of an integer-valued forecast: the integral of (F(x) - 1{x >= y})^2,
    which for integer support and integer y is sum_k (F(k) - 1{k >= y})^2."""
    y = int(y)
    a, b = min(lo, y), max(lo + len(p) - 1, y)
    full = np.zeros(b - a + 1)
    full[lo - a: lo - a + len(p)] = p
    F = np.cumsum(full)                      # F(k) for k = a..b; 0 below a, 1 from b on
    H = (np.arange(a, b + 1) >= y).astype(float)
    return float(((F - H) ** 2).sum())


def pit(lo: int, p: np.ndarray, y: int) -> float:
    """Mid-PIT of a discrete forecast: F(y - 1) + p(y) / 2 (uniform on [0, 1]
    in expectation under a calibrated forecast)."""
    return cdf_at(lo, p, int(y) - 1) + 0.5 * prob_at(lo, p, y)


def brier(p: float, o: bool) -> float:
    return (float(p) - float(bool(o))) ** 2


def binary_log(p: float, o: bool, floor: float = FLOOR_P) -> float:
    q = float(p) if o else 1.0 - float(p)
    return math.log(max(q, floor))


# --------------------------------------------------------------- the eight-cycle record
def record_pmf(mean: float, median: float, p05: float, p95: float, p_pass: float,
               kmin: int = 4, kmax: int = 120) -> tuple:
    """An approximate seat pmf for one list of the record, which keeps only
    summaries of each projection. P(0) = 1 - P(pass); the passing mass is a
    discretised normal on kmin..kmax whose mean is the conditional mean
    (mean / P(pass)) and whose spread matches the 90% interval: both ends
    when the 5% point is above zero, the 95% point otherwise."""
    nd = NormalDist()
    p_pass = float(min(max(p_pass, 0.0), 1.0))
    p0 = 1.0 - p_pass
    if p_pass < 1e-9:
        return 0, np.array([1.0])
    mu = max(float(mean) / p_pass, float(kmin))
    sd = None
    q_hi = (0.95 - p0) / p_pass
    if p05 > 0 and p0 < 0.05:
        q_lo = (0.05 - p0) / p_pass
        span = nd.inv_cdf(min(q_hi, 0.999)) - nd.inv_cdf(max(q_lo, 0.001))
        if span > 0 and p95 > p05:
            sd = (p95 - p05) / span
    elif 0.55 < q_hi < 0.999:
        z = nd.inv_cdf(q_hi)
        if p95 > mu:
            sd = (p95 - mu) / z
    if not sd or not np.isfinite(sd):
        sd = max(1.0, 0.25 * mu)
    sd = max(sd, 0.6)
    k = np.arange(kmin, kmax + 1, dtype=float)
    cdf = np.array([NormalDist(mu, sd).cdf(x) for x in np.concatenate([k - 0.5, [kmax + 0.5]])])
    w = np.diff(cdf)
    w = w / w.sum() if w.sum() > 0 else np.eye(1, len(k), 0).ravel()
    p = np.zeros(kmax + 1)
    p[0] = p0
    p[kmin:] = p_pass * w
    return 0, p


def _cycle_kmin(cycle: str) -> int:
    from validate_model import CYCLE_THRESHOLD
    return 2 if CYCLE_THRESHOLD.get(str(cycle), 0.0325) < 0.03 else 4


def record_rows(lists_csv: Path = RECORD_LISTS, exclude=()) -> pd.DataFrame:
    """Per list and cycle of the record: the same scores as the scorecard."""
    h = pd.read_csv(lists_csv, dtype={"cycle": str})
    h = h[~h["cycle"].isin(set(exclude))]
    out = []
    for r in h.itertuples():
        lo, p = record_pmf(r.pred, r.pred_median, r.p05, r.p95, r.p_pass, _cycle_kmin(r.cycle))
        y = int(r.actual)
        out.append({"cycle": r.cycle, "list": r.components, "y": y,
                    "log": log_score(lo, p, y, FLOOR_DRAWS / 8000), "crps": crps(lo, p, y),
                    "pit": pit(lo, p, y), "abs_err": abs(float(r.pred_median) - y),
                    "covered": bool(r.p05 <= y <= r.p95), "brier": brier(r.p_pass, y > 0)})
    return pd.DataFrame(out)


def record_expectations(lists_csv: Path = RECORD_LISTS, blocs_csv: Path = RECORD_BLOCS,
                        exclude=()) -> dict:
    """What the eight-cycle record says each score looks like: its value in
    every past cycle (the range an ordinary election falls in), pooled."""
    rows = record_rows(lists_csv, exclude)
    cyc = {}
    for c, g in rows.groupby("cycle", sort=False):
        cyc[c] = {"log": round(float(g["log"].mean()), 4), "crps": round(float(g["crps"].mean()), 4),
                  "abs_err": round(float(g["abs_err"].mean()), 4),
                  "coverage": round(float(g["covered"].mean()), 4),
                  "brier": round(float(g["brier"].mean()), 4),
                  "pit_tails": round(float(((g["pit"] < 0.05) | (g["pit"] > 0.95)).mean()), 4),
                  "n": int(len(g))}
    pooled = {"log": round(float(rows["log"].mean()), 4), "crps": round(float(rows["crps"].mean()), 4),
              "abs_err": round(float(rows["abs_err"].mean()), 4),
              "coverage": round(float(rows["covered"].mean()), 4),
              "brier": round(float(rows["brier"].mean()), 4),
              "pit_tails": round(float(((rows["pit"] < 0.05) | (rows["pit"] > 0.95)).mean()), 4),
              "n": int(len(rows))}
    nb = {}
    b = pd.read_csv(blocs_csv, dtype={"cycle": str})
    b = b[~b["cycle"].isin(set(exclude))]
    for r in b.itertuples():
        o = bool(r.bloc_61_happened)
        nb[r.cycle] = {"p": float(r.p_bloc_61), "o": o, "brier": round(brier(r.p_bloc_61, o), 4),
                       "log": round(binary_log(r.p_bloc_61, o), 4)}
    nb_pooled = {"brier": round(float(np.mean([v["brier"] for v in nb.values()])), 4),
                 "log": round(float(np.mean([v["log"] for v in nb.values()])), 4)} if nb else {}
    return {"source": f"{_rel(lists_csv)}, {_rel(blocs_csv)} (validate_bayes eve harness)",
            "excluded": list(exclude), "cycles": cyc, "pooled": pooled,
            "nb_bloc": {"cycles": nb, "pooled": nb_pooled},
            "uniform_group_log": round(math.log(1 / len(GROUPS)), 4)}


def _list_tables(spec, central: int, ivl, floor: float) -> tuple:
    """Every score of one list as a function of its seat count y, over the
    support of its pmf: (lo, p, {score: array over y})."""
    lo, p = pmf_probs(spec)
    ys = np.arange(lo, lo + len(p))
    F = np.cumsum(p)
    H = (ys[None, :] >= ys[:, None]).astype(float)          # row y: 1{k >= y}
    pp = 1.0 - prob_at(lo, p, 0)
    return lo, p, {"log": np.log(np.maximum(p, floor)), "crps": ((F[None, :] - H) ** 2).sum(axis=1),
                   "abs_err": np.abs(central - ys).astype(float),
                   "coverage": ((ys >= ivl[0]) & (ys <= ivl[1])).astype(float),
                   "brier": (pp - (ys > 0)) ** 2}


def self_expectation(m: dict, scored: list, joint: Optional[pd.DataFrame] = None) -> dict:
    """What the model itself expects its scores to be if it is right: the
    mean over the scored lists of each score's expectation under the
    model's own pmf (exact from the marginals), and, given its joint seat
    draws, the 5-95% range of the per-election mean score (each draw scored
    as if it were the result). Bloc probabilities: E Brier = p(1 - p)."""
    floor = FLOOR_DRAWS / max(int(m.get("n_sims") or 0), 1)
    keys = [k for k, _ in METRICS]
    tabs = {}
    for k in scored:
        tabs[k] = _list_tables(m["pmf"].get(k, point_mass(0)), int(m["central"].get(k, 0)),
                               m["interval"].get(k, [0, 0]), floor)
    out = {s: {"mean": round(float(np.mean([(p * t[s]).sum() for _, p, t in tabs.values()])), 4)}
           for s in keys}
    if joint is not None and len(joint):
        per = {s: np.zeros(len(joint)) for s in keys}
        for k, (lo, p, t) in tabs.items():
            y = joint[k].to_numpy().astype(int) if k in joint.columns else np.zeros(len(joint), int)
            idx = np.clip(y - lo, 0, len(p) - 1)
            for s in keys:
                per[s] += t[s][idx]
        for s in keys:
            v = per[s] / len(tabs)
            out[s].update(p05=round(float(np.percentile(v, 5)), 4), p95=round(float(np.percentile(v, 95)), 4))
    for b in BLOC_KEYS:
        p = (m.get("blocs") or {}).get(b)
        if p is not None:
            p = float(p)
            out[f"{b}_brier"] = {"mean": round(p * (1 - p), 4)}
            out[f"{b}_log"] = {"mean": round(p * binary_log(p, True) + (1 - p) * binary_log(p, False), 4)}
    return out


def scored_lists(payload: dict, seats: Optional[dict] = None) -> list:
    """The lists the means run over: official mean share >= SCORED_SHARE,
    plus every list that won seats."""
    reg, seats = payload["lists"], seats or {}
    keys = list(reg) + [k for k in seats if k not in reg]
    return [k for k in keys if reg.get(k, {}).get("share", 0) >= payload["rules"]["scored_share"]
            or seats.get(k, 0) > 0]


def place(value: Optional[float], cycles: dict, key: str, better: Optional[str]) -> Optional[dict]:
    """Where a 2026 score falls among the record's per-cycle values."""
    vals = [float(v[key]) for v in cycles.values() if v.get(key) is not None]
    if value is None or not vals:
        return None
    out = {"min": round(min(vals), 4), "max": round(max(vals), 4),
           "mean": round(float(np.mean(vals)), 4), "n": len(vals),
           "inside": bool(min(vals) - 1e-9 <= value <= max(vals) + 1e-9)}
    if better == "high":
        out["beats"] = int(sum(value > v for v in vals))
    elif better == "low":
        out["beats"] = int(sum(value < v for v in vals))
    return out


# --------------------------------------------------------------- freeze
def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      default=en._json_default).encode("utf-8")


def payload_sha256(payload: dict) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args) -> Optional[str]:
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except (ValueError, OSError):
        return str(p)


def _israel_now() -> datetime:
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)


def registry_2026() -> tuple:
    """Every list's names, ballot letters, bloc and colour as the main site has
    them (election_night.site_lexicon), with the official mean share."""
    lex = en.site_lexicon()
    sh = pd.read_csv(PROCESSED / "mixture_shares.csv")
    comp = dict(zip(sh["list"], sh["components"].astype(str)))
    share = dict(zip(sh["list"], sh["share_mean"].astype(float)))
    return lex, comp, share


def _entry(name: str, lex: dict, comp: dict, share: dict) -> dict:
    return {"en": lex["SHORT"].get(name, name), "he": lex["HE_PARTY"].get(name, name),
            "letter": lex["HEB"].get(name), "bloc": lex["BLOC"].get(name, "una"),
            "pvar": lex["PVAR"].get(name), "components": comp.get(name),
            "share": round(float(share.get(name, 0.0)), 5), "aliases": [name]}


def official_model(mv_off: dict) -> dict:
    """The published official forecast, from the published files; checked
    against build_variants' official run (same code, posterior and seed)."""
    draws = pd.read_parquet(PROCESSED / "mixture_draws.parquet")
    off = pd.read_csv(PROCESSED / "official_forecast.csv")
    mb = pd.read_csv(PROCESSED / "mixture_blocs.csv").iloc[0]
    gg = pd.read_csv(PROCESSED / "government_groups.csv").set_index("group")["probability"]
    pm = pd.read_csv(PROCESSED / "pm_probabilities.csv")
    m = {"id": "official", "name": mv_off["name"], "status": "official", "kind": mv_off["kind"],
         "n_sims": int(len(draws)), "pmf": seat_pmfs(draws),
         "central": {r.list: int(r.central_seats) for r in off.itertuples()},
         "interval": {r.list: [int(x) for x in str(r.interval_90).split("-")] for r in off.itertuples()},
         "blocs": {"nb": float(mb.p_nb_61), "anti": float(mb.p_anti_61),
                   "antiRaam": float(mb.p_anti_raam_61), "neither": float(mb.p_neither),
                   "nb_mean": float(mb.nb_mean), "nb_p05": int(mb.nb_p05), "nb_p95": int(mb.nb_p95)},
         "groups": {g: float(gg[g]) for g in GROUPS + ["netanyahu_in_office"] if g in gg.index},
         "pm": [[r.pm, float(r.probability)] for r in pm.itertuples()],
         "backtest": mv_off.get("backtest")}
    problems = []
    if mv_off.get("pmf") != m["pmf"]:
        problems.append("its seat pmfs differ from mixture_draws.parquet")
    for k in ("nb", "anti", "antiRaam", "neither"):
        if abs(float(mv_off["blocs"][k]) - m["blocs"][k]) > 1e-9:
            problems.append(f"blocs.{k} {mv_off['blocs'][k]} vs {m['blocs'][k]}")
    if {r["name"]: r["seats"] for r in mv_off["lists"]} != m["central"]:
        problems.append("its central seats differ from official_forecast.csv")
    if problems:
        raise ScorecardError("model_variants.json's official variant is not the published forecast ("
                             + "; ".join(problems) + "): run python src/build_variants.py")
    return m


def variant_model(v: dict) -> dict:
    if "pmf" not in v:
        raise ScorecardError(f"model_variants.json variant {v['id']} has no seat pmfs: "
                             "run python src/build_variants.py")
    pm = v.get("pm_paired") or [[r[0], r[1]] for r in v["pm"]]
    groups = v.get("groups_paired") or {g: x[0] for g, x in v["groups"].items()}
    return {"id": v["id"], "name": v["name"], "status": v["status"], "kind": v["kind"],
            "n_sims": int(v["n_sims"]), "pmf": v["pmf"],
            "central": {r["name"]: int(r["seats"]) for r in v["lists"]},
            "interval": {r["name"]: [int(r["lo"]), int(r["hi"])] for r in v["lists"]},
            "blocs": dict(v["blocs"]), "groups": {g: float(p) for g, p in groups.items()},
            "pm": [[n, float(p)] for n, p in pm], "backtest": v.get("backtest")}


def build_frozen_2026(now_il: Optional[datetime] = None) -> dict:
    mvp = PROCESSED / "model_variants.json"
    if not mvp.exists():
        raise ScorecardError("no data/processed/model_variants.json: run python src/build_variants.py")
    mv = json.loads(mvp.read_text(encoding="utf-8"))
    rows = {v["id"]: v for v in mv["variants"]}
    if "official" not in rows:
        raise ScorecardError("model_variants.json has no official variant")
    models = [official_model(rows["official"])]
    models += [variant_model(v) for v in mv["variants"] if v["id"] != "official"]
    lex, comp, share = registry_2026()
    names = list(dict.fromkeys(n for m in models for n in m["pmf"]))
    off = models[0]
    names.sort(key=lambda n: (-off["central"].get(n, 0), -share.get(n, 0.0)))
    now_il = now_il or _israel_now()
    asof = str(pd.read_csv(PROCESSED / "official_forecast.csv")["asof"].iloc[0])
    paths = [PROCESSED / f for f in INPUTS]
    dirty = _git("status", "--porcelain", "--", *[str(p) for p in paths])
    payload = {
        "version": 1, "cycle": "2026", "election_day": ELECTION_DAY.isoformat(), "asof": asof,
        "frozen_utc": en.utc_iso(), "frozen_israel": now_il.strftime("%Y-%m-%d %H:%M"),
        "blackout_from": BLACKOUT_FROM.isoformat(),
        "final": bool(BLACKOUT_FROM <= now_il.date() and now_il < POLLS_CLOSE_IL),
        "lists": {n: _entry(n, lex, comp, share) for n in names},
        "raam": "Ra'am", "models": models, "rules": RULES,
        "record": record_expectations(),
        "provenance": {"git_head": _git("rev-parse", "HEAD"),
                       "inputs_dirty": [ln for ln in (dirty or "").splitlines() if ln.strip()],
                       "inputs": {_rel(p): file_sha256(p) for p in paths if p.exists()},
                       "code": "src/scorecard.py --freeze"},
    }
    scored = scored_lists(payload)
    joint = pd.read_parquet(PROCESSED / "mixture_draws.parquet")
    for m in models:
        m["expect_self"] = self_expectation(m, scored, joint if m["id"] == "official" else None)
    return payload


def frozen_path(payload: dict) -> Path:
    return PROCESSED / f"frozen_forecast_{payload['asof']}.json"


def write_frozen(payload: dict, path: Optional[Path] = None) -> tuple:
    path = Path(path or frozen_path(payload))
    sha = payload_sha256(payload)
    doc = {"sha256": sha,
           "hash": "sha256 of the UTF-8 JSON of payload with sorted keys and separators (',', ':')",
           "payload": payload}
    en._atomic_write(path, json.dumps(doc, ensure_ascii=False, indent=1, default=en._json_default)
                     + "\n")
    return path, sha


def verify_doc(doc: dict) -> bool:
    return payload_sha256(doc["payload"]) == doc.get("sha256")


def load_frozen(path: Optional[Path] = None) -> tuple:
    """The named frozen file, else the latest: final freezes first, then the
    latest asof, then the latest freeze."""
    if path is None:
        docs = []
        for p in sorted(PROCESSED.glob("frozen_forecast_*.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            pl = d["payload"]
            docs.append(((bool(pl.get("final")), pl["asof"], pl["frozen_utc"]), p, d))
        if not docs:
            return None, None
        _, path, doc = max(docs, key=lambda t: t[0])
        return doc, path
    return json.loads(Path(path).read_text(encoding="utf-8")), Path(path)


# --------------------------------------------------------------- the result
def alias_table(reg: dict) -> dict:
    t = {}
    for key, e in reg.items():
        comps = (e.get("components") or "")
        for a in [key, e.get("en"), e.get("he"), e.get("letter"), comps, *comps.split("+"),
                  *e.get("aliases", [])]:
            if a:
                t.setdefault(en._norm(a), key)
    return t


def resolve(label, table: dict) -> Optional[str]:
    if label is None or (isinstance(label, float) and math.isnan(label)):
        return None
    return table.get(en._norm(str(label)))


def read_result(path, payload: dict) -> dict:
    """The official result: a CSV (list,votes,seats), election_night.py's page
    data (election-night.json, its final count) or one of its snapshot
    directories. Returns {seats: {list: n}, votes: {list: n}, rows, source}."""
    path = Path(path)
    reg = payload["lists"]
    table = alias_table(reg)
    rows, note, meta = [], "", {}
    if path.is_dir():
        if payload["cycle"] != "2026":
            raise ScorecardError("a snapshot directory is a 2026 election-night count")
        count = en.load_snapshot(path)
        if count is None:
            raise ScorecardError(f"{path}: no usable file in the snapshot")
        cyc = en.cycle_2026()
        pairs, _ = cyc.letter_pairs()
        alloc = en.allocate(count.votes, pairs)
        for l, v in count.votes.items():
            if l != en.REST:
                rows.append({"label": l, "votes": int(v), "seats": int(alloc.seats.get(l, 0))})
        kind = "snapshot"
        note = f"{count.level} count fetched {count.fetched_utc}, {count.valid:,} valid votes"
    elif path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("mode") == "waiting" or not d.get("lists"):
            raise ScorecardError(f"{path}: the election-night page has no count yet")
        for r in d["lists"]:
            if r.get("seats_raw") is None:
                continue
            rows.append({"label": r.get("letter") or r.get("name"), "votes": r.get("votes"),
                         "seats": int(r["seats_raw"])})
        kind = "election_night"
        pr = d.get("progress") or {}
        note = (f"{(d.get('source') or {}).get('level')} count fetched {d.get('fetched_utc')}, "
                f"{pr.get('valid')} valid votes")
        if not pr.get("envelope_valid"):
            note += "; WARNING: no double envelopes counted yet (not the final count)"
    else:
        df = pd.read_csv(path, dtype=str, comment="#", skipinitialspace=True)
        cols = {en._norm(c): c for c in df.columns}
        lc = next((cols[k] for k in ("list", "letters", "party", "name", "רשימה") if k in cols), None)
        sc = next((cols[k] for k in ("seats", "מנדטים") if k in cols), None)
        vc = next((cols[k] for k in ("votes", "קולות") if k in cols), None)
        if lc is None or sc is None:
            raise ScorecardError(f"{path}: need 'list' and 'seats' columns, got {list(df.columns)}")
        for r in df.itertuples(index=False):
            lab = getattr(r, lc)
            if pd.isna(lab) or str(lab).strip() == "":
                continue
            s = en._to_int(getattr(r, sc))
            v = en._to_int(getattr(r, vc)) if vc else None
            rows.append({"label": str(lab).strip(), "votes": v, "seats": int(s or 0)})
        kind = "csv"
        # "# key: value" header lines carry the page's source line (source_url,
        # as_of_utc, certified yes|no); other comment lines are ignored
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"#\s*(source_url|as_of_utc|certified)\s*:\s*(\S+)", ln)
            if m:
                meta[m.group(1)] = m.group(2)
    seats, votes, unmatched = {}, {}, []
    for r in rows:
        if en._norm(r["label"]) in en.REST_ALIASES:
            r["key"] = None
            continue
        k = resolve(r["label"], table)
        r["key"] = k
        if k is None:
            if r["seats"] > 0:
                raise ScorecardError(f"result row {r['label']!r} won {r['seats']} seats but matches "
                                     f"no forecast list (use ballot letters or the site's names)")
            unmatched.append(r["label"])
            continue
        seats[k] = seats.get(k, 0) + int(r["seats"])
        if r["votes"] is not None:
            votes[k] = votes.get(k, 0) + int(r["votes"])
    total = sum(seats.values())
    if total != 120:
        raise ScorecardError(f"the result's seats sum to {total}, not 120")
    off = payload["models"][0]
    missing = [k for k in reg if k not in seats and off["central"].get(k, 0) > 0]
    if missing:
        print("WARNING lists the official forecast gave seats are not in the result (scored as 0): "
              + ", ".join(missing))
    valid = sum(int(r["votes"]) for r in rows if r.get("votes") is not None) or None
    return {"seats": seats, "votes": votes, "valid": valid, "unmatched": unmatched,
            "source": {"kind": kind, "path": _rel(path), "note": note,
                       "url": meta.get("source_url"), "as_of_utc": meta.get("as_of_utc"),
                       "certified": meta.get("certified", "").lower() == "yes"}}


# --------------------------------------------------------------- scoring
def bloc_seats(payload: dict, seats: dict) -> dict:
    reg = payload["lists"]
    nb = sum(s for k, s in seats.items() if reg.get(k, {}).get("bloc") == "nb")
    anti = sum(s for k, s in seats.items() if reg.get(k, {}).get("bloc") == "anti")
    return {"nb": nb, "anti": anti, "antiRaam": anti + seats.get(payload.get("raam"), 0)}


def _match(name: Optional[str], options) -> Optional[str]:
    if not name:
        return None
    for o in options:
        if en._norm(o) == en._norm(name):
            return o
    return name


def score_model(m: dict, payload: dict, seats: dict, scored: list, every: list,
                blocs_actual: dict, government: Optional[str], pm: Optional[str]) -> dict:
    floor = FLOOR_DRAWS / max(int(m.get("n_sims") or 0), 1)
    lists = {}
    for k in every:
        lo, p = pmf_probs(m["pmf"].get(k, point_mass(0)))
        y = int(seats.get(k, 0))
        ivl = m["interval"].get(k, [0, 0])
        central = int(m["central"].get(k, 0))
        p_pass = 1.0 - prob_at(lo, p, 0)
        lists[k] = {"y": y, "central": central, "lo": int(ivl[0]), "hi": int(ivl[1]),
                    "p_pass": round(p_pass, 4), "log": round(log_score(lo, p, y, floor), 4),
                    "crps": round(crps(lo, p, y), 4), "pit": round(pit(lo, p, y), 4),
                    "brier": round(brier(p_pass, y > 0), 4), "abs_err": abs(central - y),
                    "covered": bool(ivl[0] <= y <= ivl[1]), "scored": k in scored}
    S = [lists[k] for k in scored]
    summary = {"log": float(np.mean([r["log"] for r in S])), "crps": float(np.mean([r["crps"] for r in S])),
               "abs_err": float(np.mean([r["abs_err"] for r in S])),
               "coverage": float(np.mean([r["covered"] for r in S])),
               "brier": float(np.mean([r["brier"] for r in S])),
               "brier_all": float(np.mean([lists[k]["brier"] for k in every])),
               "pit_tails": int(sum((r["pit"] < 0.05) or (r["pit"] > 0.95) for r in S)),
               "n": len(S), "n_all": len(every)}
    summary = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in summary.items()}
    blocs = {}
    for b in BLOC_KEYS:
        p = (m.get("blocs") or {}).get(b)
        o = blocs_actual[b] >= 61
        blocs[b] = None if p is None else {"p": p, "o": o, "brier": round(brier(p, o), 4),
                                           "log": round(binary_log(p, o), 4)}
    form = None
    if government and m.get("groups"):
        p = float(m["groups"].get(government, 0.0))
        form = {"group": government, "p": p, "log": round(math.log(max(p, FLOOR_P)), 4)}
    pms = None
    if pm and m.get("pm"):
        d = {n: float(q) for n, q in m["pm"]}
        name = _match(pm, d)
        p = d.get(name, 0.0)
        pms = {"name": name, "p": p, "log": round(math.log(max(p, FLOOR_P)), 4)}
    return {"id": m["id"], "summary": summary, "blocs": blocs, "formation": form, "pm": pms,
            "lists": lists}


def score_frozen(payload: dict, seats: dict, government: Optional[str] = None,
                 pm: Optional[str] = None) -> dict:
    if government is not None and government not in GROUPS:
        raise ScorecardError(f"--government must be one of {GROUPS}")
    reg = payload["lists"]
    blocs_actual = bloc_seats(payload, seats)
    scored = scored_lists(payload, seats)
    every = list(reg) + [k for k in seats if k not in reg and seats[k] > 0]
    rec = payload.get("record") or {}
    models = [score_model(m, payload, seats, scored, every, blocs_actual, government, pm)
              for m in payload["models"]]
    order = sorted(range(len(models)), key=lambda i: (-models[i]["summary"]["log"],
                                                      models[i]["summary"]["crps"]))
    for r, i in enumerate(order, 1):
        models[i]["rank"] = r
    for key, better in METRICS:
        if better is None:
            continue
        vals = [m["summary"][key] for m in models]
        for m in models:
            v = m["summary"][key]
            m.setdefault("ranks", {})[key] = 1 + sum((x > v) if better == "high" else (x < v)
                                                     for x in vals)
    for m in models:
        m["expect"] = {key: place(m["summary"][key], rec.get("cycles", {}), key, better)
                       for key, better in METRICS}
        nbr = (rec.get("nb_bloc") or {}).get("cycles", {})
        if m["blocs"].get("nb"):
            m["expect"]["nb_brier"] = place(m["blocs"]["nb"]["brier"], nbr, "brier", "low")
            m["expect"]["nb_log"] = place(m["blocs"]["nb"]["log"], nbr, "log", "high")
        # the model's own expectation (frozen): inside its 90% range of election scores?
        own = next(x for x in payload["models"] if x["id"] == m["id"]).get("expect_self") or {}
        vals = {**m["summary"], **{f"{b}_{s}": (m["blocs"].get(b) or {}).get(s)
                                   for b in BLOC_KEYS for s in ("brier", "log")}}
        m["expect_self"] = {}
        for key, e in own.items():
            v = vals.get(key)
            m["expect_self"][key] = dict(e, inside=(None if v is None or "p05" not in e
                                                    else bool(e["p05"] - 1e-9 <= v <= e["p95"] + 1e-9)))
    return {"scored": scored, "every": every, "blocs_actual": blocs_actual,
            "government": government, "pm": pm, "ranking": [models[i]["id"] for i in order],
            "models": models}


# --------------------------------------------------------------- the final polls
def poll_comparison(payload: dict, seats: dict) -> Optional[dict]:
    """The frozen official forecast beside every outlet's last poll before the
    blackout, against the result (2026 only; the page's "final polls"
    section). Polls publish seat tables, so the model enters with its
    published central counts. Per forecast, over the scored lists: seats
    missed (the sum of |forecast - result|), the signed Netanyahu-bloc error,
    threshold calls (lists put on the wrong side of the threshold) and the
    vote-share error per list (postmortem_shares, dossier s.74). The polls
    are build_insights.final_polls (fieldwork from postmortem_shares.SINCE,
    each outlet's last); a reference row averages their seat tables.
    Returns None when an input is missing."""
    if payload.get("cycle") != "2026":
        return None
    import build_insights as bi
    import postmortem_shares as ps
    try:
        fin = bi.final_polls(bi._polls())
        share = ps.table(with_average=True)
    except (OSError, KeyError, ValueError) as e:
        print(f"WARNING no final-poll comparison on the page: {e}")
        return None
    reg, off = payload["lists"], payload["models"][0]
    keys = scored_lists(payload, seats)
    col = {name: pid for pid, name in bi.PID.items()}
    if any(k not in col for k in keys):
        print("WARNING no final-poll comparison on the page: no poll column for "
              + ", ".join(k for k in keys if k not in col))
        return None
    y = {k: int(seats.get(k, 0)) for k in keys}
    nb = [k for k in keys if reg[k]["bloc"] == "nb"]
    mae = {r.outlet: (round(float(r.mae), 2), r.basis) for r in share.itertuples()}

    def grade(v: dict, exact: bool = True) -> dict:
        e = [v[k] - y[k] for k in keys]
        g = {"err": sum(abs(x) for x in e), "nb": sum(v[k] - y[k] for k in nb)}
        if exact:
            g["thr"] = int(sum((v[k] > 0) != (y[k] > 0) for k in keys))
        else:
            g = {k: round(float(x), 1) for k, x in g.items()}
            g["thr"] = None
        return g

    def row(rid, kind, outlet, firm, when, n, v, label):
        m = mae.get(label)
        return {"id": rid, "kind": kind, "outlet": outlet, "firm": firm, "date": when, "n": n,
                "seats": v, **grade(v, kind != "average"),
                "share_mae": m[0] if m else None, "share_basis": m[1] if m else None}

    rows = []
    for _, r in fin.iterrows():
        v = {k: int(r[col[k]]) if col[k] in fin.columns else 0 for k in keys}
        rows.append(row(f"{r.publisher}|{r.pollster}", "panel" if r.pollster in bi.PANELS else "poll",
                        r.publisher, r.pollster, r.fieldwork_end.strftime("%Y-%m-%d"),
                        None if pd.isna(r.sample_size) else int(r.sample_size), v,
                        f"{r.publisher} ({r.pollster})"))
    polls = list(rows)
    rows.append(row("model", "model", None, None, payload["asof"], None,
                    {k: int(off["central"].get(k, 0)) for k in keys}, "MODEL (frozen forecast)"))
    rows.sort(key=lambda r: (r["err"], abs(r["nb"])))
    avg = {k: round(float(np.mean([r["seats"][k] for r in polls])), 1) for k in keys}
    return {"since": ps.SINCE, "n_polls": len(polls), "lists": sorted(keys, key=lambda k: -y[k]),
            "result": y, "rows": rows,
            "average": row("average", "average", None, None, None, None, avg, "AVERAGE (final polls)"),
            "source": "data/processed/polls.csv; data/processed/postmortem_cec_filings.csv, "
                      "postmortem_cec_party_pcts.csv (src/postmortem_shares.py)"}


# --------------------------------------------------------------- page
def labels() -> dict:
    return {"pm_he": PM_HE, "pm_en": PM_EN}


def page_payload(doc: dict, path: Optional[Path], result: Optional[dict], scores: Optional[dict],
                 mode: str) -> dict:
    polls = poll_comparison(doc["payload"], result["seats"]) if result and scores else None
    return {"version": 1, "mode": mode, "generated_utc": en.utc_iso(),
            "frozen": {"file": _rel(path) if path else None, "sha256": doc["sha256"],
                       "verified": verify_doc(doc), "payload": doc["payload"]},
            "result": result, "scores": scores, "polls": polls, "labels": labels()}


def render(payload: dict) -> str:
    lex = en.site_lexicon()
    tpl = PAGE_TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=en._json_default)
    blob = blob.replace("</", "<\\/")
    for k, v in (("__EN_TOKENS__", lex["tokens"]), ("__EN_FONTS__", lex["fonts"]),
                 ("__EN_ICON__", lex["icon"])):
        tpl = tpl.replace(k, v)
    assert "__SC_DATA__" in tpl, "page template placeholder missing"
    return tpl.replace("__SC_DATA__", blob)


def write_page(payload: dict, html_path: Path = OUT_HTML) -> tuple:
    json_path = html_path.with_suffix(".json")
    en._atomic_write(json_path, json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                                           default=en._json_default))
    en._atomic_write(html_path, render(payload))
    return html_path, json_path


def stored(json_path: Path = OUT_HTML.with_suffix(".json")) -> dict:
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------- 2022 rehearsal
def frozen_2022() -> dict:
    """A synthetic freeze of 2022 built from the harness's 2022 eve projection
    (the record's per-list summaries, rebuilt as pmfs over 8,000 draws; the
    record's P(Netanyahu bloc >= 61)). The expectations leave 2022 out."""
    h = pd.read_csv(RECORD_LISTS, dtype={"cycle": str})
    h = h[h["cycle"] == "2022"]
    c = pd.read_csv(COUNTS, dtype={"cycle": str})
    c = c[(c["cycle"] == "2022") & c["party_id"].notna()]
    by_pid = {r.party_id: r for r in c.itertuples()}
    n = 8000
    reg, pmf, central, interval = {}, {}, {}, {}
    for r in h.sort_values("pred", ascending=False).itertuples():
        pid = r.components
        cr = by_pid.get(pid)
        name = cr.list_name if cr is not None else pid
        reg[pid] = {"en": en.EN_2022.get(pid, name), "he": en.HE_2022.get(pid, name),
                    "letter": str(cr.ballot).strip() if cr is not None else None,
                    "bloc": en.BLOC_2022.get(pid, "una"), "pvar": en.PVAR_2022.get(pid),
                    "components": pid, "share": round(float(r.share_base), 5), "aliases": [name]}
        lo, p = record_pmf(r.pred, r.pred_median, r.p05, r.p95, r.p_pass, _cycle_kmin("2022"))
        cnt = np.zeros(len(p), dtype=np.int64)
        cnt[0] = int(round(p[0] * n))
        rest = p[1:] / p[1:].sum() * (n - cnt[0]) if p[1:].sum() > 0 else np.zeros(len(p) - 1)
        fl = np.floor(rest).astype(np.int64)
        fl[np.argsort(-(rest - fl))[: int(n - cnt[0] - fl.sum())]] += 1
        cnt[1:] = fl
        nz = np.nonzero(cnt)[0]
        pmf[pid] = [int(nz[0])] + [int(x) for x in cnt[nz[0]: nz[-1] + 1]]
        central[pid] = int(round(r.pred_median))
        interval[pid] = [int(math.ceil(r.p05 - 1e-9)), int(math.floor(r.p95 + 1e-9))]
    b = pd.read_csv(RECORD_BLOCS, dtype={"cycle": str})
    p61 = float(b.loc[b["cycle"] == "2022", "p_bloc_61"].iloc[0])
    model = {"id": "official", "name": {"en": "The model's 2022 eve forecast (leave-one-cycle-out harness)",
                                        "he": "תחזית המודל לערב הבחירות 2022 (מבחן השמטה)"},
             "status": "official", "kind": "bayes", "n_sims": n, "pmf": pmf, "central": central,
             "interval": interval, "blocs": {"nb": p61}, "groups": None, "pm": None,
             "backtest": None}
    payload = {"version": 1, "cycle": "2022", "election_day": "2022-11-01", "asof": "2022-10-31",
               "frozen_utc": en.utc_iso(), "frozen_israel": None, "blackout_from": "2022-10-28",
               "final": True, "rehearsal": True, "lists": reg, "raam": "raam", "models": [model],
               "rules": RULES, "record": record_expectations(exclude=("2022",)),
               "provenance": {"git_head": _git("rev-parse", "HEAD"), "inputs_dirty": [],
                              "inputs": {_rel(RECORD_LISTS): file_sha256(RECORD_LISTS),
                                         _rel(RECORD_BLOCS): file_sha256(RECORD_BLOCS)},
                              "code": "src/scorecard.py --rehearse 2022"}}
    model["expect_self"] = self_expectation(model, scored_lists(payload))
    return payload


def result_2022_csv(path: Path) -> Path:
    """The official 2022 result (data/cec_final_counts.csv) as a result CSV."""
    c = pd.read_csv(COUNTS, dtype={"cycle": str})
    c = c[c["cycle"] == "2022"]
    pd.DataFrame({"list": c["ballot"].str.strip(), "votes": c["votes"].astype(int),
                  "seats": c["seats_official"].astype(int)}).to_csv(path, index=False)
    return path


def rehearse(year: str = "2022", out: Optional[Path] = None) -> dict:
    import tempfile
    if year != "2022":
        raise ScorecardError("--rehearse supports 2022")
    payload = frozen_2022()
    doc = {"sha256": payload_sha256(payload), "payload": payload}
    with tempfile.TemporaryDirectory() as td:
        res = read_result(result_2022_csv(Path(td) / "result_2022.csv"), payload)
    res["source"]["path"] = "data/cec_final_counts.csv (cycle 2022)"
    scores = score_frozen(payload, res["seats"], government="netanyahu", pm="Netanyahu")
    page = page_payload(doc, None, res, scores, "rehearsal")
    write_page(page, Path(out) if out else OUT_DIR / "scorecard-rehearsal.html")
    return page


# --------------------------------------------------------------- CLI
def _print_scores(scores: dict, payload: dict) -> None:
    names = {m["id"]: m["name"]["en"] for m in payload["models"]}
    ba = scores["blocs_actual"]
    print(f"result: Netanyahu bloc {ba['nb']}, change bloc {ba['anti']} (+Ra'am {ba['antiRaam']}); "
          f"{len(scores['scored'])} lists scored")
    print(f"{'rank':>4}  {'model':34s} {'log':>8} {'CRPS':>7} {'|err|':>6} {'cov90':>6} "
          f"{'Brier':>7} {'NB61 Br':>8} {'chg61 Br':>8}")
    for mid in scores["ranking"]:
        m = next(x for x in scores["models"] if x["id"] == mid)
        s, b = m["summary"], m["blocs"]
        fb = lambda k: f"{b[k]['brier']:.3f}" if b.get(k) else "  –"
        print(f"{m['rank']:>4}  {names[mid][:34]:34s} {s['log']:8.3f} {s['crps']:7.3f} "
              f"{s['abs_err']:6.2f} {s['coverage']:6.2f} {s['brier']:7.4f} {fb('nb'):>8} {fb('anti'):>8}")
    rec = payload.get("record", {}).get("cycles", {})
    off = next(x for x in scores["models"] if x["id"] == "official")
    for key, _ in METRICS:
        e, o = off["expect"].get(key), off.get("expect_self", {}).get(key) or {}
        if e:
            own = (f"; own 90% range {o['p05']:.3f} to {o['p95']:.3f} "
                   f"({'inside' if o['inside'] else 'OUTSIDE'})" if "p05" in o else
                   (f"; own expectation {o['mean']:.3f}" if o else ""))
            print(f"  official {key:9s} {off['summary'][key]:.3f}  record {e['min']:.3f} to "
                  f"{e['max']:.3f} over {e['n']} cycles ({'inside' if e['inside'] else 'OUTSIDE'}){own}")
    if not rec:
        print("  (no record)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freeze", action="store_true", help="freeze the published forecast")
    ap.add_argument("--force", action="store_true", help="freeze even after the polls close")
    ap.add_argument("--verify", nargs="?", const="", metavar="FILE", help="check a frozen file's sha256")
    ap.add_argument("--score", action="store_true", help="grade the frozen forecast")
    ap.add_argument("--result", help="result CSV (list,votes,seats), election-night.json or a snapshot dir")
    ap.add_argument("--government", choices=GROUPS, help="the government group, once known")
    ap.add_argument("--pm", help="the next prime minister, once known")
    ap.add_argument("--frozen", help="the frozen file (default: the latest)")
    ap.add_argument("--page", action="store_true", help="rebuild the page from what is stored")
    ap.add_argument("--rehearse", metavar="YEAR", help="the whole path on a past election (2022)")
    a = ap.parse_args(argv)
    try:
        if a.rehearse:
            page = rehearse(a.rehearse)
            _print_scores(page["scores"], page["frozen"]["payload"])
            print(f"wrote {_rel(OUT_DIR / 'scorecard-rehearsal.html')} (+ .json)")
            return 0
        if a.freeze:
            now = _israel_now()
            if now >= POLLS_CLOSE_IL and not a.force:
                raise ScorecardError("the polls have closed: a freeze now is not a pre-registration "
                                     "(--force to write one anyway)")
            payload = build_frozen_2026(now)
            path, sha = write_frozen(payload)
            write_page(page_payload(json.loads(path.read_text(encoding="utf-8")), path, None, None, "pre"))
            print(f"froze the forecast as of {payload['asof']}: {_rel(path)}\n  sha256 {sha}\n"
                  f"  {len(payload['models'])} models, git {payload['provenance']['git_head']}")
            if payload["provenance"]["inputs_dirty"]:
                print("WARNING uncommitted forecast files (commit the build, then freeze again): "
                      + "; ".join(payload["provenance"]["inputs_dirty"]))
            if not payload["final"]:
                print(f"NOTE provisional: frozen before the blackout ({payload['blackout_from']}); "
                      "freeze again after the final pre-blackout build")
            print(f"wrote {_rel(OUT_HTML)} (+ .json)")
            return 0
        if a.verify is not None:
            doc, path = load_frozen(Path(a.verify) if a.verify else None)
            if doc is None:
                raise ScorecardError("no frozen forecast in data/processed")
            ok = verify_doc(doc)
            print(f"{_rel(path)}: sha256 {doc['sha256']} {'OK' if ok else 'MISMATCH'} "
                  f"(recomputed {payload_sha256(doc['payload'])})")
            return 0 if ok else 1
        if a.score or a.page:
            doc, path = load_frozen(Path(a.frozen) if a.frozen else None)
            if doc is None:
                raise ScorecardError("no frozen forecast: run --freeze first")
            if not verify_doc(doc):
                raise ScorecardError(f"{_rel(path)}: the sha256 does not match its payload")
            prev = stored()
            same = (prev.get("frozen") or {}).get("sha256") == doc["sha256"]
            result = prev.get("result") if same else None
            if a.score:
                if a.result:
                    result = read_result(a.result, doc["payload"])
                if result is None:
                    raise ScorecardError("--score needs --result (no stored result for this freeze)")
                ins = (prev.get("scores") or {}) if same else {}
                gov = a.government or ins.get("government")
                pm = a.pm or ins.get("pm")
                scores = score_frozen(doc["payload"], result["seats"], gov, pm)
                write_page(page_payload(doc, path, result, scores, "scored"))
                _print_scores(scores, doc["payload"])
            else:
                scores = (prev.get("scores") if same else None)
                write_page(page_payload(doc, path, result, scores, "scored" if scores else "pre"))
            print(f"wrote {_rel(OUT_HTML)} (+ .json) from {_rel(path)}")
            return 0
    except ScorecardError as e:
        print(f"scorecard: {e}")
        return 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
