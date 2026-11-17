"""Marginal value of one vote, by list: the exchange rate of the targeting layer.

Israel elects 120 seats in one national district, so a vote has the same
value wherever it is cast - but NOT the same value whichever list it goes
to. A vote for a list sitting on the 3.25% threshold, a vote that tips a
surplus pair's last seat, and a vote that takes a seat from the Netanyahu
bloc all move the outcome by different amounts. This module measures, for
each list L, how much one additional vote for L changes each campaign
objective, by perturbing the forecast's own election-day share draws:

    MV_L(obj) = [obj(S + d e_L) - obj(S - d e_L)] / (2 d V)

S is the 8,000 x lists matrix of projected vote shares from the
registration-mixture projection (the same draws behind the published
forecast; reproduced bit-for-bit here and checked against
mixture_draws.parquet). Adding d to list L and renormalising is the
arithmetic of NEW voters for L (mobilisation); moving a voter from A to B
is worth MV_B - MV_A (persuasion). Seats are recomputed through the full
seat law (threshold, surplus pairs, Bader-Ofer) and government outcomes
through government_formation.simulate_formation with common random
numbers, so the differences are low-noise.

Objectives:
    change_govt      P(change-led government): change alone, + unaligned/
                     Amcha, + a haredi party, + Ra'am, or the Joint-List-
                     backed centre minority (formation model)
    change61         P(change lists alone >= 61)
    change_raam61    P(change lists + Ra'am >= 61)
    block_nb         P(Netanyahu bloc < 61)
    change_seats     E[change-list seats]

Outputs:
    data/processed/targeting/share_draws.parquet
    data/processed/targeting/marginal_values.csv   (per 10,000 votes)
    data/processed/targeting/marginal_meta.json
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR
from simulate import THRESHOLD, dhondt

warnings.filterwarnings("ignore")

OUT = PROCESSED_DIR / "targeting"
SEED = 20261027                 # registration_scenarios.SEED
VALID_VOTES_2026 = 4_823_026    # Kolot Nodedim K26 estimate (data/raw/transfer/kn26)
DELTA = 0.0020                  # +-0.20% of the vote (~9,600 votes) per side
M_BEHAVIOR = 60                 # formation parameter vectors (CRN across arms)

CHANGE = ["Yashar", "Bennett 2026 + Yesh Atid", "The Democrats",
          "Yisrael Beytenu"]
# Registry bloc "netanyahu_bloc" (as in mixture_blocs.csv's p_nb_61).
NB = ["Likud", "Shas", "United Torah Judaism", "Otzma Yehudit",
      "Religious Zionist Party", "Amcha Yisrael", "Noam",
      "The Haredi Public"]
CHANGE_GOVT = {2, 3, 4, 5, 8}
# Surplus-vote agreements, signed or expected by the 16 Oct deadline (dossier
# s.38), by list label. The forecast's own pair list resolves components by
# name and drops two of these (Together - Yisrael Beytenu, because no
# component is called "together"; Joint List - Ra'am, which lands on the
# empty "Balad (alone)" component), so the atlas sets them explicitly.
PAIR_LABELS = [("Likud", "Religious Zionist Party"),
               ("Bennett 2026 + Yesh Atid", "Yisrael Beytenu"),
               ("Yashar", "The Democrats"),
               ("Shas", "United Torah Judaism"),
               ("Otzma Yehudit", "Amcha Yisrael"),
               ("Balad + Hadash-Ta'al", "Ra'am")]


def label_pairs(labels: list) -> list:
    return [(labels.index(a), labels.index(b)) for a, b in PAIR_LABELS
            if a in labels and b in labels]


def share_draws() -> tuple[np.ndarray, list, list]:
    """Reproduce the registration-mixture projection and keep its shares."""
    import arviz as az
    from bayes_model import prepare_data, project

    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "share_draws.parquet"
    meta_p = OUT / "share_draws_meta.json"
    if cache.exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text())
        return (pd.read_parquet(cache).values, meta["labels"],
                [tuple(p) for p in meta["pairs"]])

    # Same scenario parameters as registration_scenarios.main().
    params = {}
    try:
        scen = pd.read_csv(PROCESSED_DIR / "arab_scenarios.csv")
        balad = scen[scen["list"].str.fullmatch("Balad")
                     & scen["below_pct"].notna()]["below_pct"].mean()
        joint = scen[(scen["list"] == "Ra'am+Segalovitz")
                     & scen["seats"].notna()]
        base = scen[(scen["scenario"] == "baseline")
                    & (scen["list"] == "Ra'am") & scen["seats"].notna()]
        base_map = base.groupby(["pollster", "fieldwork_end"])["seats"].mean()
        boosts = [r.seats - base_map[(r.pollster, r.fieldwork_end)]
                  for r in joint.itertuples()
                  if (r.pollster, r.fieldwork_end) in base_map.index]
        params = {"balad_alone_pct": float(balad),
                  "segalovitz_boost_seats": (float(np.mean(boosts))
                                             if boosts else 1.3)}
    except FileNotFoundError:
        pass

    data = prepare_data()
    idata = az.from_netcdf(PROCESSED_DIR / "m3_idata.nc")
    rng = np.random.default_rng(SEED)
    seats, labels, _ = project(data, idata, rng, config="mixture",
                               config_params=params)
    shares = project.last_shares
    pairs = project.last_pairs

    published = pd.read_parquet(PROCESSED_DIR / "mixture_draws.parquet")
    same = (published[list(labels)].values == seats).mean()
    print(f"reproduction check vs mixture_draws.parquet: {same:.4f} of cells equal")
    if same < 0.999:
        raise RuntimeError("share draws do not reproduce the published seats")

    pd.DataFrame(shares, columns=labels).to_parquet(cache)
    meta_p.write_text(json.dumps({"labels": list(labels),
                                  "pairs": [list(map(int, p)) for p in pairs],
                                  "asof": data["asof"].date().isoformat()}))
    return shares, list(labels), pairs


def allocate(shares: np.ndarray, pairs: list) -> np.ndarray:
    """The seat law on a matrix of share draws (threshold, pairs, Bader-Ofer)."""
    n, k = shares.shape
    seats = np.zeros((n, k), dtype=int)
    for i in range(n):
        sh = shares[i]
        passed = sh >= THRESHOLD
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers, used = [], [], set()
        for a, b in pairs:
            if passed[a] and passed[b]:
                fvotes.append(votes[a] + votes[b])
                fmembers.append([a, b])
                used |= {a, b}
        for j in np.nonzero(passed)[0]:
            if j not in used:
                fvotes.append(votes[j])
                fmembers.append([int(j)])
        alloc = dhondt(np.array(fvotes), 120)
        for members, kk in zip(fmembers, alloc):
            if len(members) == 1:
                seats[i, members[0]] = kk
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(kk))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats


def behavior_vectors(m: int = M_BEHAVIOR) -> list:
    """The first m formation parameter vectors exactly as government_formation.main() draws them:
    the same behaviour and PM-allocation stream, plus the post-deadlock stage (P(repeat | deadlock)
    and, when the forecast ships them, the record's resolution shares or mix weights). Without the
    stage, deadlocks never resolve into unity, defector or change governments and the change-led
    baseline falls well below the published one."""
    import government_formation as gf
    prng = np.random.default_rng(gf.SEED + 7)
    M_PROD = 200                      # government_formation.main(): same generators, first m vectors
    stage = getattr(gf, "POST_DEADLOCK_STAGE", False)
    res = getattr(gf, "STAGE_RESOLUTION", "gates")
    r_stage = gf.stage_draws(M_PROD, stage) if hasattr(gf, "stage_draws") else [None] * M_PROD
    s_stage = (gf.resolution_draws(M_PROD, stage and res == "record") if hasattr(gf, "resolution_draws")
               else [None] * M_PROD)
    w_stage = [None] * M_PROD
    if stage and res == "mix":
        import validate_formation as vf
        w_stage, _ = vf.mix_posterior_2026(M_PROD)
    out = []
    for k in range(m):
        b, pa = gf.draw_behavior(prng), gf.draw_pm_alloc(prng)
        if r_stage[k] is not None:
            b["repeat_deadlock"] = r_stage[k]
        if s_stage[k] is not None:
            b["resolution_shares"] = s_stage[k]
        if w_stage[k] is not None:
            b["resolution_mix"] = w_stage[k]
        out.append((b, pa))
    return out


def objectives(seats: np.ndarray, labels: list, behaviors: list) -> dict:
    from government_formation import (simulate_formation, SEED as GSEED,
                                      NB_CORE, CENTRE, JOINT_LIST, RAAM,
                                      AMCHA)

    d = pd.DataFrame(seats, columns=labels)
    for col in NB_CORE + CENTRE + [JOINT_LIST, RAAM, AMCHA]:
        if col not in d:     # as government_formation.load_draws does
            d[col] = 0
    ch = d[[c for c in CHANGE if c in d]].sum(axis=1).values
    nb = d[[c for c in NB if c in d]].sum(axis=1).values
    raam = d["Ra'am"].values if "Ra'am" in d else 0
    out = {"change61": float((ch >= 61).mean()),
           "change_raam61": float((ch + raam >= 61).mean()),
           "block_nb": float((nb < 61).mean()),
           "change_seats": float(ch.mean())}
    # The formation model: same behavior vectors and seeds in every arm.
    for col in ["Amcha Yisrael", "Balad + Hadash-Ta'al", "Ra'am"]:
        if col not in d:
            d[col] = 0
    p = []
    for m, (b, pa) in enumerate(behaviors):
        oc, _ = simulate_formation(d, b, seed=GSEED + m, pm_alloc=pa)
        p.append(np.isin(oc, list(CHANGE_GOVT)).mean())
    out["change_govt"] = float(np.mean(p))
    return out


def main() -> None:
    shares, labels, pairs = share_draws()
    n, k = shares.shape
    fixed = label_pairs(list(labels))
    print(f"share draws: {n} x {k}; forecast pairs {pairs} -> atlas pairs {fixed}")
    pairs = fixed
    behaviors = behavior_vectors()

    base_seats = allocate(shares, pairs)
    base = objectives(base_seats, labels, behaviors)
    print("baseline:", {k_: round(v, 4) for k_, v in base.items()})

    rows = []
    per_votes = 10_000 / VALID_VOTES_2026     # share units per 10k votes
    for j, lab in enumerate(labels):
        if shares[:, j].max() <= 0:
            continue
        arms = {}
        for sign in (+1, -1):
            s = shares.copy()
            s[:, j] = np.clip(s[:, j] + sign * DELTA, 0, None)
            s /= s.sum(axis=1, keepdims=True)
            arms[sign] = objectives(allocate(s, pairs), labels, behaviors)
        row = {"list": lab,
               "share_mean": round(float(shares[:, j].mean()), 5),
               "p_pass": round(float((shares[:, j] >= THRESHOLD).mean()), 3)}
        for obj in base:
            mv = (arms[+1][obj] - arms[-1][obj]) / (2 * DELTA) * per_votes
            row[obj] = mv
        rows.append(row)
        print(f"  {lab:32s} " + " ".join(
            f"{o}={row[o]:+.5f}" for o in base))

    mv = pd.DataFrame(rows)
    mv.to_csv(OUT / "marginal_values.csv", index=False)
    (OUT / "marginal_meta.json").write_text(json.dumps({
        "baseline": base, "delta_share": DELTA,
        "valid_votes_2026": VALID_VOTES_2026, "n_draws": int(n),
        "m_behavior": M_BEHAVIOR,
        "pairs": [[labels[a], labels[b]] for a, b in pairs],
        "units": "change in objective per 10,000 additional votes for the list "
                 "(probabilities as fractions; change_seats in seats)"},
        indent=1))
    print(f"wrote {OUT / 'marginal_values.csv'}")


if __name__ == "__main__":
    main()
