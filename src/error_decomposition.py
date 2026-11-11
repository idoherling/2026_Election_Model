"""Sequential decomposition of historical final-poll errors, 2009-2022.

The projection layer applies election-day shocks in a fixed order (bloc
swing, family totals, party-anchored means, per-list residual). This module
calibrates ALL of them from the same sequential decomposition of the
eight-cycle record, so no component is counted twice:

  e0  raw signed error (final-poll average - actual), per cycle x list
  e1  = e0 minus the cycle's bloc swing, distributed proportionally
  e2  = e1 minus the cycle's Arab/haredi family totals (own family)
  e3  = e2 minus the party anchors:
          likud    - lists containing Likud (its record: polls understate it)
          leader   - the cycle's largest remaining list
      residual -> per-list shock scale (fit vs list size)

get_error_params(exclude_cycle=...) returns everything the projection needs,
leave-one-cycle-out for validation. Full-sample values are written to
data/processed/error_decomposition.csv by running this module directly.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

import record
from backtest import FINAL_WINDOW
from bias_audit import block_frame, window_polls
from scrape_polls import ELECTION_DAY, PROCESSED_DIR

# the graded cycles: 2009-2022, plus 2026 under RECORD_2026=1 (src/record.py)
ORDER = list(record.CYCLES)
NB_FAMILIES = {"right", "haredi"}


@lru_cache(maxsize=1)
def _frames():
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = record.results()
    frames = {}
    for cycle, res in results.groupby("cycle"):
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        f = block_frame(window_polls(polls, cycle, eday, FINAL_WINDOW, 0), res)
        f = f[(f["actual"] > 0) | (f["polled"] >= 0.5)].copy()
        f["error"] = f["polled"] - f["actual"]
        f["is_nb"] = f["family"].isin(NB_FAMILIES)
        f["has_likud"] = f["components"].str.split("+").map(
            lambda cs: "likud" in cs)
        frames[cycle] = f
    return frames


@lru_cache(maxsize=32)
def decompose(exclude_cycle: str | None = None, index_fix: bool = False):
    """Per-cycle component estimates plus pooled residual rows.

    index_fix (dossier s.48, found 15 Oct): the per-cycle frames are indexed
    by block number, so the pooled residual frame below has duplicate
    labels across cycles, and step 4's resid.loc[<leader label>] subtracts
    the seat-leader anchor (-1.74 seats) from every cycle's row carrying
    that label, not only the leader's. That inflates the residual line
    (full sample 1.83 + 0.044 x seats; 1.48 + 0.041 with the labels made
    unique). bloc_sd, the family terms and the anchors are unaffected.
    False = the shipped (collided) residual; production reads it."""
    rows_resid, bloc_totals = [], {}
    fam_totals = {"arab": {}, "haredi": {}}
    fam_e0 = {"arab": {}, "haredi": {}}     # raw (pre-swing) family totals
    likud_e2, leader_e2 = {}, {}

    for cycle, f0 in _frames().items():
        f = f0.copy()
        w = f["polled"].clip(lower=0.1)

        # 1. bloc swing: NB-side total error, removed proportionally both ways
        nb, rest = f["is_nb"], ~f["is_nb"]
        delta = float(f.loc[nb, "error"].sum())
        bloc_totals[cycle] = delta
        f["e1"] = f["error"] - np.where(
            nb, delta * w / w[nb].sum(), -delta * w / w[rest].sum())

        # 2. family totals (own family only)
        f["e2"] = f["e1"]
        for fam in ("arab", "haredi"):
            in_f = f["family"] == fam
            if not in_f.any():
                continue
            t = float(f.loc[in_f, "e1"].sum())
            fam_totals[fam][cycle] = t
            fam_e0[fam][cycle] = float(f.loc[in_f, "error"].sum())
            f.loc[in_f, "e2"] = f.loc[in_f, "e1"] - t * w[in_f] / w[in_f].sum()

        # 3. party anchors: Likud, then the largest remaining list
        f["e3"] = f["e2"]
        lk = f["has_likud"]
        if lk.any():
            likud_e2[cycle] = float(f.loc[lk, "e2"].mean())
        others = f[~lk]
        if len(others):
            lead = others["actual"].idxmax()
            leader_e2[cycle] = float(f.loc[lead, "e2"])
        rows_resid.append(f.assign(cycle=cycle))

    use = [c for c in ORDER if c != exclude_cycle]
    resid = pd.concat(rows_resid, ignore_index=index_fix)
    anchors = {
        "likud": float(np.mean([likud_e2[c] for c in use if c in likud_e2])),
        "leader": float(np.mean([leader_e2[c] for c in use if c in leader_e2])),
    }
    # 4. residual, after removing the anchors from their own rows
    resid = resid[resid["cycle"].isin(use)].copy()
    resid.loc[resid["has_likud"], "e3"] -= anchors["likud"]
    for c in use:
        f = resid[resid["cycle"] == c]
        others = f[~f["has_likud"]]
        if len(others):
            resid.loc[others["actual"].idxmax(), "e3"] -= anchors["leader"]

    small = resid[resid["actual"] <= 8]["e3"]
    big = resid[resid["actual"] > 8]["e3"]
    sd_small, sd_big = float(small.std(ddof=1)), float(big.std(ddof=1))
    mean_small = float(resid[resid["actual"] <= 8]["actual"].mean())
    mean_big = float(resid[resid["actual"] > 8]["actual"].mean())
    slope = max((sd_big - sd_small) / max(mean_big - mean_small, 1.0), 0.0)
    base = max(sd_small - slope * mean_small, 0.4)

    return {
        "bloc_sd": float(np.std([bloc_totals[c] for c in use], ddof=1)),
        "family": {
            fam: (float(np.mean([d[c] for c in use if c in d])),
                  float(np.std([d[c] for c in use if c in d], ddof=1)))
            for fam, d in fam_totals.items()
        },
        # 2026-10-13 (dossier s.43, arab_turnout_regime): RAW family totals
        # (e0, before the bloc swing is removed). The projection's bloc
        # swing has mean zero, so the NB mean that e1 strips out is applied
        # nowhere; e0 is the additive control the Arab turnout mechanism is
        # graded against. Not used by production defaults.
        "family_e0": {
            fam: (float(np.mean([d[c] for c in use if c in d])),
                  float(np.std([d[c] for c in use if c in d], ddof=1)))
            for fam, d in fam_e0.items()
        },
        "anchors": anchors,
        "resid_base": float(base), "resid_slope": float(slope),
    }


# ---------------------------------------------------------------------------
# Residual on VOTE SHARES (dossier s.48, arm B). decompose() measures every
# error in seats, so a list that died at the threshold enters the residual
# as a +4..6-seat miss (Meretz 2022: polled 4.4 seats, 0 won, on a 0.3 pp
# vote miss). The projection applies the residual in vote-share space and
# then applies the threshold again, so the death is counted twice. Here the
# same sequential decomposition runs on vote-share errors of the lists that
# RAN, in u = 120 x share (the units the projection's sd_list x 120 is in).
# ---------------------------------------------------------------------------
VOTE_ZERO_IMPUTE = 0.5     # a 0-seat poll row with no printed % = half the threshold
VOTE_MIN_MEASURED = 0.5    # share of a list's final-window polls that must measure it


@lru_cache(maxsize=1)
def _vote_frames():
    """Per cycle x block, in u = 120 x vote share: final-window polled share
    (the model's seat->share map: seats/120 x (1 - wasted - 0.01); 0-seat
    rows at their printed %, else VOTE_ZERO_IMPUTE x threshold) and actual
    share (lists that won seats: seats x (1 - W - 0.01), W = the failed
    lists' CEC share; lists that ran and failed: their CEC vote share,
    data/ran_vote_shares.csv). Kept: lists that ran, measured in at least
    VOTE_MIN_MEASURED of their polls, that won seats or polled >= 0.5 u."""
    from backtest import merge_blocks
    from bias_audit import family_of_block
    from validate_model import CYCLE_THRESHOLD
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = record.results(dtype={"cycle": str})
    ran = record.ran_vote_shares(dtype={"cycle": str})
    frames = {}
    for cycle, res in results.groupby("cycle"):
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        thr = CYCLE_THRESHOLD.get(cycle, 0.0325)
        w = window_polls(polls, cycle, eday, FINAL_WINDOW, 0).copy()
        failed = ran[(ran["cycle"] == cycle) & (ran["seats"] == 0)]
        W = float(failed["vote_pct"].sum()) / 100.0
        wasted = (w[w["seats"] == 0].assign(x=w["vote_pct"].fillna(0) / 100)
                  .groupby("poll_id")["x"].sum())
        w["wasted"] = w["poll_id"].map(wasted).fillna(0.0)
        meas = (w["seats"] > 0) | w["vote_pct"].notna()
        sh = np.where(w["seats"] > 0, w["seats"] / 120.0 * (1.0 - w["wasted"] - 0.01),
                      w["vote_pct"] / 100.0)
        w["u"] = np.where(meas, sh, VOTE_ZERO_IMPUTE * thr) * 120.0
        w["meas"] = meas
        blocks = merge_blocks(list(w["party_id"].unique()) + list(res["party_id"])
                              + list(failed["party_id"]))
        block_of = {c: i for i, b in enumerate(blocks) for c in b}
        w["block"] = w["party_id"].map(lambda p: block_of[p.split("+")[0]])
        per_poll = w.groupby(["block", "poll_id"]).agg(u=("u", "sum"), meas=("meas", "any"))
        polled = per_poll.groupby("block")["u"].mean()
        frac = per_poll.groupby("block")["meas"].mean()
        act_u, act_seats, ran_b = {}, {}, {}
        for r in res.itertuples():
            b = block_of[r.party_id.split("+")[0]]
            act_seats[b] = act_seats.get(b, 0) + int(r.seats)
            if r.seats > 0:
                act_u[b] = act_u.get(b, 0.0) + r.seats * (1.0 - W - 0.01)
                ran_b[b] = True
        for r in failed.itertuples():
            b = block_of[r.party_id.split("+")[0]]
            act_u[b] = act_u.get(b, 0.0) + 120.0 * r.vote_pct / 100.0
            act_seats.setdefault(b, 0)
            ran_b[b] = True
        idx = sorted(set(polled.index) | set(act_u))
        f = pd.DataFrame({
            "polled": polled.reindex(idx).fillna(0.0).values,
            "actual_u": [act_u.get(b, 0.0) for b in idx],
            "actual": [act_seats.get(b, 0) for b in idx],
            "measured": frac.reindex(idx).fillna(0.0).values,
            "ran": [ran_b.get(b, False) for b in idx],
            "family": [family_of_block(blocks[b]) for b in idx],
            "components": ["+".join(sorted(blocks[b])) for b in idx],
        })
        f = f[f["ran"] & (f["measured"] >= VOTE_MIN_MEASURED)
              & ((f["actual"] > 0) | (f["polled"] >= 0.5))].copy()
        f["error"] = f["polled"] - f["actual_u"]
        f["is_nb"] = f["family"].isin(NB_FAMILIES)
        f["has_likud"] = f["components"].str.split("+").map(lambda cs: "likud" in cs)
        frames[cycle] = f.reset_index(drop=True)
    return frames


def _resid_record(frames, use, size_col):
    """decompose()'s steps 1-4 on any frame set: bloc swing and own-family
    totals removed proportionally, LOO anchors removed; returns the residual
    rows of the cycles in `use` and the fitted (base, slope) sd line, with
    `size_col` as the size the slope multiplies."""
    rows, likud_e2, leader_e2 = [], {}, {}
    for cycle, f0 in frames.items():
        f = f0.copy()
        w = f["polled"].clip(lower=0.1)
        nb, rest = f["is_nb"], ~f["is_nb"]
        delta = float(f.loc[nb, "error"].sum())
        f["e1"] = f["error"] - np.where(
            nb, delta * w / w[nb].sum(), -delta * w / w[rest].sum())
        f["e2"] = f["e1"]
        for fam in ("arab", "haredi"):
            in_f = f["family"] == fam
            if not in_f.any():
                continue
            t = float(f.loc[in_f, "e1"].sum())
            f.loc[in_f, "e2"] = f.loc[in_f, "e1"] - t * w[in_f] / w[in_f].sum()
        f["e3"] = f["e2"]
        lk = f["has_likud"]
        if lk.any():
            likud_e2[cycle] = float(f.loc[lk, "e2"].mean())
        others = f[~lk]
        if len(others):
            leader_e2[cycle] = float(f.loc[others["actual"].idxmax(), "e2"])
        rows.append(f.assign(cycle=cycle))
    anchors = {"likud": float(np.mean([likud_e2[c] for c in use if c in likud_e2])),
               "leader": float(np.mean([leader_e2[c] for c in use if c in leader_e2]))}
    resid = pd.concat(rows, ignore_index=True)
    resid = resid[resid["cycle"].isin(use)].copy()
    resid.loc[resid["has_likud"], "e3"] -= anchors["likud"]
    for c in use:
        f = resid[resid["cycle"] == c]
        others = f[~f["has_likud"]]
        if len(others):
            resid.loc[others["actual"].idxmax(), "e3"] -= anchors["leader"]
    small, big = resid[resid["actual"] <= 8], resid[resid["actual"] > 8]
    sd_small, sd_big = float(small["e3"].std(ddof=1)), float(big["e3"].std(ddof=1))
    m_small, m_big = float(small[size_col].mean()), float(big[size_col].mean())
    slope = max((sd_big - sd_small) / max(m_big - m_small, 1.0), 0.0)
    base = max(sd_small - slope * m_small, 0.4)
    return resid, base, slope


def tail_df(resid: pd.DataFrame, base: float, slope: float, size_col: str) -> dict:
    """Arm D (dossier s.48): Student-t df by the method of moments from the
    excess kurtosis G2 (bias-corrected) of the residuals standardised by
    their fitted sd line: df = 4 + 6 / G2, clipped to [4.5, 30]; G2 <= 0.2
    gives 30 (effectively normal)."""
    from scipy.stats import kurtosis
    z = resid["e3"] / (base + slope * resid[size_col])
    g2 = float(kurtosis(z, fisher=True, bias=False))
    df = 30.0 if g2 <= 0.2 else float(np.clip(4.0 + 6.0 / g2, 4.5, 30.0))
    return {"g2": g2, "df": df, "n": int(len(z))}


@lru_cache(maxsize=16)
def decompose_vote(exclude_cycle: str | None = None) -> dict:
    """Arm B: the residual sd line (u = 120 x share per seat-equivalent)
    re-estimated on vote-share errors of the lists that ran, leave-one-
    cycle-out; plus the arm-D tail df of that record."""
    use = [c for c in ORDER if c != exclude_cycle]
    resid, base, slope = _resid_record(_vote_frames(), use, "actual_u")
    return {"resid_base": float(base), "resid_slope": float(slope),
            "n": int(len(resid)), "tail": tail_df(resid, base, slope, "actual_u")}


@lru_cache(maxsize=16)
def seat_tail(exclude_cycle: str | None = None) -> dict:
    """Arm D on the shipped (seat-error) record: the same df estimator on
    decompose()'s residual rows (reproduces decompose()'s base/slope)."""
    use = [c for c in ORDER if c != exclude_cycle]
    resid, base, slope = _resid_record(_frames(), use, "actual")
    return tail_df(resid, base, slope, "actual")


def main() -> None:
    p = decompose()
    print(f"Full-sample error decomposition ({len(ORDER)} cycles):")
    print(f"  bloc swing sd:      {p['bloc_sd']:.2f} seats")
    for fam, (m, s) in p["family"].items():
        print(f"  {fam:7} family:     mean {m:+.2f}, sd {s:.2f}")
    print(f"  Likud anchor:       {p['anchors']['likud']:+.2f} seats "
          f"(polls' systematic miss on Likud, after bloc removal)")
    print(f"  seat-leader anchor: {p['anchors']['leader']:+.2f} seats")
    print(f"  residual sd:        {p['resid_base']:.2f} + "
          f"{p['resid_slope']:.3f} x seats")
    flat = {"bloc_sd": p["bloc_sd"], "anchor_likud": p["anchors"]["likud"],
            "anchor_leader": p["anchors"]["leader"],
            "resid_base": p["resid_base"], "resid_slope": p["resid_slope"]}
    for fam, (m, s) in p["family"].items():
        flat[f"family_{fam}_mean"], flat[f"family_{fam}_sd"] = m, s
    record.TABLE_DIR.mkdir(parents=True, exist_ok=True)   # record9/ under RECORD_2026
    pd.Series(flat).round(3).to_csv(
        record.table("error_decomposition.csv"))
    print("\nwrote error_decomposition.csv")

    print("\nLeave-one-out anchors (stability check):")
    for c in ORDER:
        q = decompose(exclude_cycle=c)
        print(f"  without {c}: likud {q['anchors']['likud']:+.2f}, "
              f"leader {q['anchors']['leader']:+.2f}, "
              f"bloc sd {q['bloc_sd']:.2f}")


if __name__ == "__main__":
    main()
