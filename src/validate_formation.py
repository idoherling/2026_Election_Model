"""Grade the SHIPPED formation tree on the Israeli record, 1977-2022.

Rebuilt 2026-10-15 (dossier s.49). Everything behavioural is IMPORTED from
government_formation: BEHAVIOR and BEHAVIOR_NEFF (drawn per parameter
vector exactly as main() draws them), PM_ALLOC, COND, and simulate_formation
itself. The only things this module adds are the historical seat maps and
which 2026 ROLE each historical list plays. The previous version kept its
own, older parameter set (haredi 0.30, Ra'am joins 0.55, unity 0.15, a
hard-coded 0.33 pledge-break) while its header said they matched.

Seventeen Knessets, 1977-2022 (ParlGov seats and first non-caretaker
cabinets, cross-checked with the IDI election pages, 1977-2006; CEC results
in results.csv, 2009-2022). The eight 1949-1973 elections are left out: in
the dominant-party era the religious parties were Mapai's partners and the
two-bloc roles do not exist (all eight formed a government).

Roles (era-adapted, decided from pre-election positions, not from outcomes):
  Likud                    the right's main list
  Religious Zionist Party  every other right-wing list (NRP, Tehiya, Tzomet,
                           Moledet, National Union, Jewish Home, Yamina in
                           the 2019-20 bloc, YB before 2019, Kulanu 2019a)
  Shas, UTJ                Shas; Agudat Yisrael / Degel / UTJ
  Yashar                   the change side's largest list
  The Democrats            the other change lists
  Yisrael Beytenu          Liberman's list once in the change camp (2020-22),
                           so his vetoes bite only there
  Kingmaker 1, 2           lists that declared for neither PM candidate, or
                           made joining conditional (Dash 1977, Ometz 1984,
                           YBA and the Third Way 1996, Centre and YBA 1999,
                           Gil 2006, Kulanu and YB 2015, YB 2019a/s, Yamina
                           2021); each gets the tree's generic kingmaker
                           split (bw_right / bw_centre) with its own draw
  Ra'am                    the Ra'am lineage (ADP 1988-92, UAL from 1996;
                           its MKs inside a joint Arab list)
  Balad + Hadash-Ta'al     every other Arab or Arab-Jewish list
  (dropped)                Kach 1984, boycotted by every list
The gates' COND covariates are centred on the 2026 draws (the shipped
centring), so each historical parliament is judged by the shipped gate
functions, not re-centred on itself.

Cycles where the Netanyahu-role bloc alone held 61 (1977, 1981, 1988, 2003,
2009, 2013, 2022) score P = 1 under ANY tree with bloc-first precedence:
they are reported but cannot discriminate. 1996 and 1999 elected the PM
directly; they are scored at weight 0.5 in a secondary score only. The
primary score is the mean log P(realized class) over the eight informative
parliamentary-era cycles (1984, 1992, 2006, 2015, 2019a, 2019s, 2020, 2021).

Four trees are scored on the same behavioural draws (common random numbers):
  production    the pre-s49 tree: hand-set likud_sans_bibi 0.18 (NEFF 20),
                no post-deadlock stage (PRE_S49 below)
  unity_record  the record-based unity prior alone, Beta(0.5, 3.5), no stage
  stage_only    the post-deadlock stage on the pre-s49 unity prior
  candidate     what s.49 ships: the stage plus the record-based unity prior
Both record-fitted pieces are scored leave-one-out. For a deadlock cycle,
the stage's Beta posterior is fitted without that cycle's outcome. For the
two scored cycles that are themselves unity governments (1984, 2020), the
unity prior becomes Jeffreys on 0 of 2, Beta(0.5, 2.5) (1988 is a certain
cycle and is not scored).

Outputs:
  data/processed/formation_validation.csv          per-cycle scores
  data/processed/formation_validation_classes.csv  9-class forecasts
  data/processed/formation_calibration.csv         calibration tables
  data/processed/formation_deadlock_record.csv     the record behind the
                                                   stage, its posteriors and
                                                   the position check
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats

import government_formation as gf
from government_formation import (OUTCOMES, SEED, STAGE_SEED_OFFSET,
                                  DEADLOCK_RECORD, CONVENTIONAL_DEADLOCKS,
                                  deadlock_posterior, draw_behavior,
                                  draw_pm_alloc, simulate_formation)
from scrape_polls import PROCESSED_DIR

warnings.filterwarnings("ignore")

N = 2000            # rows per cycle (one seat map; the variation is behavioural)
M = 200             # parameter vectors, as in government_formation.main()
KINGMAKERS = {"Kingmaker 1": ("bw_right", "bw_centre"),
              "Kingmaker 2": ("bw_right", "bw_centre")}
COLS = (gf.NB_CORE + gf.CENTRE + [gf.JOINT_LIST, gf.RAAM, gf.AMCHA]
        + list(KINGMAKERS))

# The pre-s49 production values (hand-set unity prior), kept so the change
# can be scored against what shipped before it: {key: (mean, NEFF)}.
PRE_S49 = {"likud_sans_bibi": (0.18, 20)}
# what that tree gave P(repeat | deadlock) on the 2026 draws (government_
# deadlock.csv, stage off, pre-s49 values), for the record table
PRE_S49_REPEAT_GIVEN_D = 0.596
# the unity governments in the unity prior's record (none dropped a leader)
UNITY_GOVERNMENTS = ("1984", "1988", "2020")
VARIANTS = {"production": dict(pre=True, stage=False),
            "unity_record": dict(pre=False, stage=False),
            "stage_only": dict(pre=True, stage=True),
            "candidate": dict(pre=False, stage=True)}


def unity_prior(pre: bool, cycle: str):
    """(mean, NEFF) of the unity gate's Beta prior: the pre-s49 hand value,
    or the shipped record prior, refitted leave-one-out (Jeffreys on 0 of
    2) when the scored cycle is itself one of the unity governments."""
    if pre:
        return PRE_S49["likud_sans_bibi"]
    if cycle in UNITY_GOVERNMENTS:
        n_left = len(UNITY_GOVERNMENTS) - 1
        return 0.5 / (n_left + 1), n_left + 1
    return (gf.BEHAVIOR["likud_sans_bibi"],
            gf.BEHAVIOR_NEFF["likud_sans_bibi"])

# 2026-role seat maps. realized = index into OUTCOMES:
# 0 NB alone, 1 NB + unaligned / Amcha, 2 change alone, 3 change +
# unaligned, 4 change + haredi, 5 JL-backed minority, 6 unity, 7 repeat,
# 8 change + Ra'am, 9 NB + a change-bloc defector (split from 1 on 16 Oct,
# s.52: 2020 is the pledge-break path; 1996 and 2015 were closed by
# kingmakers).
L, R, S, U = "Likud", "Religious Zionist Party", "Shas", "United Torah Judaism"
Y, D, YB = "Yashar", "The Democrats", "Yisrael Beytenu"
K1, K2, RA, JL, AM = ("Kingmaker 1", "Kingmaker 2", gf.RAAM, gf.JOINT_LIST,
                      gf.AMCHA)
HISTORY = {
    "1977": dict(regime="parliamentary", realized=0, seats={
        L: 45, R: 12, U: 5, Y: 32, D: 4, K1: 15, K2: 1, JL: 6},
        note="Likud 43 + Shlomzion 2 (merged after the vote); NRP 12; Agudah "
             "4 + PAI 1; Alignment 32; Sheli 2, Ratz 1, ILP 1; Dash 15 and "
             "Flatto-Sharon 1 kingmakers; Hadash 5, UAL-77 1. Begin I."),
    "1981": dict(regime="parliamentary", realized=0, seats={
        L: 48, R: 12, U: 4, Y: 47, D: 3, K1: 2, JL: 4},
        note="NRP 6, Tehiya 3, Tami 3; Agudah 4; Shinui 2, Ratz 1; Telem 2 "
             "kingmaker. Begin II."),
    "1984": dict(regime="parliamentary", realized=6, alt={1, 6}, seats={
        L: 41, R: 12, S: 4, U: 2, Y: 44, D: 9, K1: 1, JL: 6},
        note="Tehiya 5, NRP 4, Morasha 2, Tami 1; Shinui 3, Ratz 3, Yahad 3; "
             "Ometz 1 kingmaker; Hadash 4, PLP 2; Kach 1 dropped. Unity with "
             "rotation inside Peres's first (extended) mandate."),
    "1988": dict(regime="parliamentary", realized=0, seats={
        L: 40, R: 12, S: 6, U: 7, Y: 39, D: 10, JL: 5, RA: 1},
        note="Right-religious bloc 65; Shamir chose unity anyway (Shamir PM)."),
    "1992": dict(regime="parliamentary", realized=4, seats={
        L: 32, R: 17, S: 6, U: 4, Y: 44, D: 12, JL: 3, RA: 2},
        note="Tzomet 8, NRP 6, Moledet 3; Meretz 12; Hadash 3, ADP 2. Rabin: "
             "Labor-Meretz + Shas (62), Hadash/ADP outside (atlas D10-F23)."),
    "1996": dict(regime="direct", realized=1, seats={
        L: 32, R: 11, S: 10, U: 4, Y: 34, D: 9, K1: 7, K2: 4, JL: 5, RA: 4},
        note="PM elected directly (Netanyahu). Likud-Gesher-Tzomet 32; NRP "
             "9, Moledet 2; YBA 7 and Third Way 4 kingmakers; both joined."),
    "1999": dict(regime="direct", realized=4, seats={
        L: 19, R: 13, S: 17, U: 5, Y: 26, D: 18, K1: 6, K2: 6, JL: 5, RA: 5},
        note="PM elected directly (Barak). NRP 5, NU 4, YB 4; Meretz 10, "
             "Shinui 6, One Nation 2; Centre 6 and YBA 6 kingmakers. Barak + "
             "Shas, UTJ, NRP, Centre, YBA, Meretz."),
    "2003": dict(regime="parliamentary", realized=0, seats={
        L: 40, R: 13, S: 11, U: 5, Y: 19, D: 24, JL: 6, RA: 2},
        note="Likud 38 + YBA 2 (merged); NU 7, NRP 6; Shinui 15, Meretz 6, "
             "One Nation 3. Sharon + Shinui, NRP, NU."),
    "2006": dict(regime="parliamentary", realized=4, seats={
        L: 12, R: 20, S: 12, U: 6, Y: 29, D: 24, K1: 7, JL: 6, RA: 4},
        note="YB 11, NU-NRP 9; Kadima 29; Labor 19, Meretz 5; Gil 7 "
             "kingmaker. Olmert: Kadima-Labor-Gil + Shas (atlas D10-F28)."),
    "2009": dict(regime="parliamentary", realized=0, seats={
        L: 27, R: 22, S: 11, U: 5, Y: 28, D: 16, JL: 7, RA: 4},
        note="YB 15, NU 4, JH 3; Kadima largest, Netanyahu tasked with 65 "
             "recommendations (atlas D10-F17)."),
    "2013": dict(regime="parliamentary", realized=0, seats={
        L: 31, R: 12, S: 11, U: 7, Y: 19, D: 29, JL: 7, RA: 4},
        note="Likud-Beytenu 31, JH 12: the bloc exactly 61; Netanyahu + YA, "
             "JH, Hatnuah."),
    "2015": dict(regime="parliamentary", realized=1, seats={
        L: 30, R: 8, S: 7, U: 6, Y: 24, D: 16, K1: 10, K2: 6, JL: 10, RA: 3},
        note="JH 8; Zionist Union 24; YA 11, Meretz 5; Kulanu 10 and YB 6 "
             "kingmakers; Joint List 13 (UAL 3). Netanyahu + Kulanu (61)."),
    "2019a": dict(regime="parliamentary", realized=7, seats={
        L: 35, R: 9, S: 8, U: 8, Y: 35, D: 10, K1: 5, JL: 8, RA: 2},
        note="URWP 5, Kulanu 4 (declared for Netanyahu); YB 5 kingmaker "
             "(conditional on the draft law); Ra'am-Balad 4 split 2/2. "
             "Dissolved before a government formed (atlas D10-F25)."),
    "2019s": dict(regime="parliamentary", realized=7, seats={
        L: 32, R: 7, S: 9, U: 7, Y: 33, D: 11, K1: 8, JL: 10, RA: 3},
        note="Yamina 7 (signed the 55 bloc); YB 8 kingmaker; Joint List 13 "
             "(UAL 3). Window lapsed (atlas D10-F22)."),
    "2020": dict(regime="parliamentary", realized=9, seats={
        L: 36, R: 6, S: 9, U: 7, Y: 33, D: 7, YB: 7, JL: 11, RA: 4},
        note="Yamina 6; LGM 7; YB with Gantz; Joint List 15 (UAL 4). Gantz's "
             "faction joins Netanyahu (atlas D10-F25)."),
    "2021": dict(regime="parliamentary", realized=8, seats={
        L: 30, R: 6, S: 9, U: 7, Y: 17, D: 27, YB: 7, K1: 7, JL: 6, RA: 4},
        note="RZP 6; YA 17; B&W 8, Labor 7, Meretz 6, New Hope 6; Yamina 7 "
             "kingmaker. Change + Yamina + Ra'am (atlas D10-F26)."),
    "2022": dict(regime="parliamentary", realized=0, seats={
        L: 32, R: 14, S: 11, U: 7, Y: 24, D: 16, YB: 6, JL: 5, RA: 5},
        note="RZP 14; National Unity 12, Labor 4; bloc 64."),
}
# Role sensitivity: the two lists that recommended Netanyahu but made
# joining conditional on a policy demand (YB 2015, YB 2019a) take Amcha's
# role (amcha_right / AMCHA_JOIN_EISENKOT) instead of the generic split.
AMCHA_ROLE = {"2015": K2, "2019a": K1}

SOURCES = (
    "Seats and cabinets 1977-2006: ParlGov development version "
    "(view_election, view_cabinet; Israel), cross-checked with the IDI "
    "election pages (atlas D10-F23, F24 verified; COA-F11 recomputed). "
    "2009-2022: CEC results (data/processed/results.csv). Outcomes: IDI "
    "election pages and atlas D10-F17, F22, F25, F26, F28.")


def frame(seats: dict) -> pd.DataFrame:
    row = {c: 0 for c in COLS}
    row.update(seats)
    assert sum(row.values()) <= 120
    return pd.DataFrame([row] * N)


def centres_2026() -> dict:
    """The shipped centring constants: COND covariate means over the 2026
    draws at the central BEHAVIOR."""
    simulate_formation(gf.load_draws(), dict(gf.BEHAVIOR))
    return dict(simulate_formation.last_centres)


def forecast(df, centres, r_draws=None, unity=None):
    """Mean 9-class forecast over M parameter vectors (main()'s scheme), and
    the mean share of draws that are deadlocks. unity = (mean, NEFF): the
    unity gate's value is drawn from its own generator, so every variant
    shares the other parameters' draws (common random numbers)."""
    prng = np.random.default_rng(SEED + 7)
    urng = np.random.default_rng(SEED + 31)
    probs = np.zeros(len(OUTCOMES))
    dl = 0.0
    for m in range(M):
        b = draw_behavior(prng)
        pa = draw_pm_alloc(prng)
        if unity is not None:
            p, n = unity
            b["likud_sans_bibi"] = float(urng.beta(p * n, (1 - p) * n))
        if r_draws is not None:
            b["repeat_deadlock"] = r_draws[m]
        oc, _ = simulate_formation(df, b, seed=SEED + m, pm_alloc=pa,
                                   centres=centres, unaligned=KINGMAKERS)
        probs += np.bincount(oc, minlength=len(OUTCOMES)) / len(oc)
        dl += simulate_formation.last_deadlock["p_deadlock"]
    return probs / M, dl / M


def stage_r(a_b):
    a, b = a_b
    return np.random.default_rng(SEED + STAGE_SEED_OFFSET).beta(a, b, size=M)


def run(centres, role_variant=None, variants=VARIANTS):
    """Every variant's forecast for every cycle."""
    rows, classes = [], []
    record = {r[0] for r in DEADLOCK_RECORD if r[2] == "parliamentary"}
    for cyc, h in HISTORY.items():
        seats = dict(h["seats"])
        if role_variant == "amcha" and cyc in AMCHA_ROLE:
            col = AMCHA_ROLE[cyc]
            seats[AM] = seats.pop(col)
        df = frame(seats)
        a_b = deadlock_posterior(exclude=(cyc,) if cyc in record else ())
        nb_core = sum(seats.get(c, 0) for c in gf.NB_CORE)
        certain = nb_core >= 61
        weight = 0.0 if certain else (1.0 if h["regime"] == "parliamentary"
                                      else 0.5)
        k = h["realized"]
        row = {"cycle": cyc, "regime": h["regime"], "certain": certain,
               "weight": weight, "realized": OUTCOMES[k], "nb_core": nb_core,
               "change_lists": sum(seats.get(c, 0) for c in gf.CENTRE),
               "kingmakers": seats.get(K1, 0) + seats.get(K2, 0),
               "raam": seats.get(RA, 0), "stage_beta": f"{a_b[0]:g},{a_b[1]:g}",
               "realized_set_alt": (",".join(str(i) for i in sorted(h["alt"]))
                                    if "alt" in h else "")}
        for v, spec in variants.items():
            p, dl = forecast(df, centres,
                             stage_r(a_b) if spec["stage"] else None,
                             unity_prior(spec["pre"], cyc))
            row["p_deadlock_draws"] = round(dl, 3)
            row[f"p_realized_{v}"] = p[k]
            row[f"p_repeat_{v}"] = p[7]
            row[f"top_{v}"] = OUTCOMES[int(np.argmax(p))]
            row[f"p_alt_{v}"] = (sum(p[i] for i in h["alt"]) if "alt" in h
                                 else np.nan)
            for i, o in enumerate(OUTCOMES):
                classes.append({"cycle": cyc, "tree": v, "class": o,
                                "probability": round(float(p[i]), 4),
                                "realized": int(i == k), "weight": weight})
        row["note"] = h["note"]
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(classes)


def log_(p):
    # Monte Carlo zero -> half a count of N*M (reported, never silent)
    return np.log(np.maximum(p, 0.5 / (N * M)))


def scores(df: pd.DataFrame, a="production", b="candidate", col="realized",
           weights="primary") -> dict:
    """Mean log P(realized) of trees a and b, and the bootstrap SE of b - a
    over the scored cycles."""
    w = (np.where(df.weight == 1.0, 1.0, 0.0) if weights == "primary"
         else df.weight.values)
    la, lb = log_(df[f"p_{col}_{a}"].values), log_(df[f"p_{col}_{b}"].values)
    out = {"tree_a": a, "tree_b": b, "n_cycles": float(w.sum()),
           "log_a": float((w * la).sum() / w.sum()),
           "log_b": float((w * lb).sum() / w.sum()),
           "uniform_9": float(np.log(1 / 9))}
    idx = np.flatnonzero(w > 0)
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(10_000):
        s = rng.choice(idx, size=len(idx), replace=True)
        diffs.append(((w[s] * (lb[s] - la[s])).sum()) / w[s].sum())
    out["diff"] = out["log_b"] - out["log_a"]
    out["diff_se"] = float(np.std(diffs))
    out["p_diff_le_0"] = float(np.mean(np.array(diffs) <= 0))
    return out


def binary_repeat(df: pd.DataFrame, trees) -> dict:
    """Repeat vs government: log and Brier, (i) over the ten non-certain
    cycles and (ii) over all 17 (certain cycles cost no tree anything);
    1996/1999 at weight 0.5 in both."""
    y = (df.realized == "Repeat election").values.astype(float)
    out = {}
    for lab, keep in (("noncertain", df.weight.values > 0),
                      ("all17", np.ones(len(df), bool))):
        w = np.where(df.regime == "parliamentary", 1.0, 0.5) * keep
        for t in trees:
            p = df[f"p_repeat_{t}"].values
            ll = y * log_(p) + (1 - y) * log_(1 - p)
            out[f"{lab}_log_{t}"] = float((w * ll).sum() / w.sum())
            out[f"{lab}_brier_{t}"] = float((w * (p - y) ** 2).sum()
                                            / w.sum())
    return out


def calibration(classes: pd.DataFrame, trees) -> pd.DataFrame:
    edges = [0, 0.05, 0.15, 0.30, 0.50, 0.70, 1.0001]
    out = []
    inf = classes[(classes.weight == 1.0) & classes.tree.isin(trees)]
    for tree, g in inf.groupby("tree"):
        b = pd.cut(g.probability, edges, right=False)
        for iv, gg in g.groupby(b, observed=True):
            out.append({"table": "9-class, informative cycles", "tree": tree,
                        "bin": f"[{iv.left:.2f}, {min(iv.right, 1):.2f})",
                        "n_forecasts": len(gg),
                        "mean_forecast": round(gg.probability.mean(), 3),
                        "realized_freq": round(gg.realized.mean(), 3),
                        "n_realized": int(gg.realized.sum())})
    return pd.DataFrame(out)


def position_check() -> pd.DataFrame:
    """Does P(repeat | deadlock) depend on the place in an election run?
    Logistic logit p = a + b (position - 1) on the seven parliamentary
    deadlocks; priors a ~ N(0, 1.5), b ~ N(0, 1); grid posterior."""
    rec = [r for r in DEADLOCK_RECORD if r[2] == "parliamentary"]
    pos = np.array([r[1] for r in rec], float) - 1
    y = np.array([r[3] for r in rec], float)
    A, B = np.meshgrid(np.linspace(-6, 6, 601), np.linspace(-5, 5, 501))
    lp = stats.norm.logpdf(A, 0, 1.5) + stats.norm.logpdf(B, 0, 1.0)
    for x_, y_ in zip(pos, y):
        eta = A + B * x_
        lp += y_ * -np.log1p(np.exp(-eta)) + (1 - y_) * -np.log1p(np.exp(eta))
    w = np.exp(lp - lp.max())
    w /= w.sum()
    rows = []
    for k in (1, 2, 3, 4):
        pk = 1 / (1 + np.exp(-(A + B * (k - 1))))
        rows.append({"quantity": f"logistic P(repeat | deadlock, position {k})",
                     "value": round(float((w * pk).sum()), 3)})
    rows.append({"quantity": "logistic slope b: posterior mean",
                 "value": round(float((w * B).sum()), 3)})
    rows.append({"quantity": "logistic slope b: P(b < 0)",
                 "value": round(float(w[B < 0].sum()), 3)})
    for lab, keep in (("position 1 only", lambda r: r[1] == 1),
                      ("positions 2-4", lambda r: r[1] >= 2),
                      ("positions 3-4", lambda r: r[1] >= 3)):
        sub = [r for r in rec if keep(r)]
        k = sum(r[3] for r in sub)
        a, b = 0.5 + k, 0.5 + len(sub) - k
        rows.append({"quantity": f"Beta {lab}: {k} of {len(sub)}",
                     "value": round(a / (a + b), 3)})
    return pd.DataFrame(rows)


def record_table() -> pd.DataFrame:
    rows = []
    for c, pos, reg, rep, how in DEADLOCK_RECORD:
        rows.append({"cycle": c, "position": pos, "regime": reg,
                     "repeat": rep, "how_it_ended": how})
    t = pd.DataFrame(rows)
    P, Dr, Mt = "parliamentary", "direct", "midterm"
    variants = [
        ("stage record (post-election, parliamentary, matched event)", {}),
        ("+ 1999 (direct election)", dict(regimes=(P, Dr))),
        ("+ Oct 2008 (Livni, mid-term)", dict(regimes=(P, Mt),
                                              exclude=("1995m",))),
        ("+ Nov 1995 and Oct 2008 (mid-term)", dict(regimes=(P, Mt))),
        ("bloc era 2019-21 only", dict(cycles=("2019a", "2019s", "2020",
                                               "2021"))),
        ("conventional five (desk/verifier; drops 1992, 2006)",
         dict(cycles=CONVENTIONAL_DEADLOCKS)),
        ("conventional five + Oct 2008", dict(
            regimes=(P, Mt), cycles=CONVENTIONAL_DEADLOCKS + ("2008m",))),
    ]
    post = []
    for lab, kw in variants:
        a, b = deadlock_posterior(**kw)
        d = stats.beta(a, b)
        post.append({"cycle": "POSTERIOR", "position": np.nan,
                     "regime": lab, "repeat": np.nan,
                     "how_it_ended": f"Beta({a:g}, {b:g}): mean "
                     f"{a / (a + b):.3f}, 90% [{d.ppf(.05):.3f}, "
                     f"{d.ppf(.95):.3f}], P(r >= {PRE_S49_REPEAT_GIVEN_D}, "
                     f"pre-s49 production) {d.sf(PRE_S49_REPEAT_GIVEN_D):.3f}"})
    return pd.concat([t, pd.DataFrame(post)], ignore_index=True)


def main() -> None:
    C = centres_2026()
    print("2026 centring constants:", {k: round(v, 3) for k, v in C.items()})
    trees = list(VARIANTS)
    per, classes = run(C)
    per_r = per.copy()
    for t in trees:
        for c in ("p_realized", "p_repeat", "p_alt"):
            per_r[f"{c}_{t}"] = per_r[f"{c}_{t}"].round(4)
        per_r[f"log_{t}"] = log_(per[f"p_realized_{t}"]).round(3)
    per_r.to_csv(PROCESSED_DIR / "formation_validation.csv", index=False)
    classes.to_csv(PROCESSED_DIR / "formation_validation_classes.csv",
                   index=False)
    show = (["cycle", "regime", "weight", "realized", "p_deadlock_draws"]
            + [f"p_realized_{t}" for t in trees]
            + ["p_repeat_production", "p_repeat_candidate", "top_production"])
    print("\nP(realized class) by tree; P(repeat), pre-s49 production vs the "
          "s.49 candidate (leave-one-out):\n")
    print(per_r[show].to_string(index=False))

    summ = []
    for b in ("unity_record", "stage_only", "candidate"):
        summ.append(dict(score=f"primary: {b} vs production",
                         **scores(per, b=b)))
    summ.append(dict(score="+ 1996, 1999 at weight 0.5",
                     **scores(per, weights="all")))
    alt = per.assign(**{f"p_realized_{t}": per[f"p_alt_{t}"].fillna(
        per[f"p_realized_{t}"]) for t in trees})
    summ.append(dict(score="1984 scored as {1, 6} (grand coalition)",
                     **scores(alt)))
    sub = {k: VARIANTS[k] for k in ("production", "candidate")}
    per_a, _ = run(C, role_variant="amcha", variants=sub)
    summ.append(dict(score="YB 2015/2019a in Amcha's role", **scores(per_a)))
    summ = pd.DataFrame(summ)
    print("\nMean log P(realized class), 8 informative cycles unless noted "
          "(uniform over 9 = -2.197):\n")
    print(summ.round(3).to_string(index=False))

    br = binary_repeat(per, trees)
    print("\nRepeat vs government (1996/1999 at 0.5):")
    for t in trees:
        print(f"  {t:13s} non-certain: log {br[f'noncertain_log_{t}']:.3f} "
              f"Brier {br[f'noncertain_brier_{t}']:.3f} | all 17: log "
              f"{br[f'all17_log_{t}']:.3f} Brier {br[f'all17_brier_{t}']:.3f}")
    inf = per[per.weight == 1.0]
    for t in trees:
        top = (inf[f"top_{t}"] == inf["realized"]).sum()
        print(f"{t}: realized class is the top class in {top} of {len(inf)} "
              "informative cycles")

    cal = calibration(classes, ["production", "candidate"])
    rep = per[["cycle", "regime", "realized"]
              + [f"p_repeat_{t}" for t in trees]].copy()
    rep["table"] = "P(repeat) by cycle"
    summ_out = summ.assign(table="mean log score").round(4)
    br_out = pd.DataFrame([dict(table="repeat vs government (binary)",
                                **{k: round(v, 4) for k, v in br.items()})])
    pd.concat([cal, rep.round(4), summ_out, br_out], ignore_index=True).to_csv(
        PROCESSED_DIR / "formation_calibration.csv", index=False)
    print("\nCalibration, 9-class forecasts on the informative cycles:\n")
    print(cal.to_string(index=False))

    rec = record_table()
    pc = position_check()
    pd.concat([rec, pc.rename(columns={"quantity": "regime",
                                       "value": "how_it_ended"})
               .assign(cycle="POSITION")], ignore_index=True).to_csv(
        PROCESSED_DIR / "formation_deadlock_record.csv", index=False)
    print("\nThe record behind the stage:\n")
    print(rec.to_string(index=False))
    print("\nPosition in an election run:\n")
    print(pc.to_string(index=False))
    print("\n" + SOURCES)


if __name__ == "__main__":
    main()
