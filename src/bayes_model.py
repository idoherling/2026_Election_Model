"""Full Bayesian forecast: latent-trend state-space model over the poll data.

The model (Jackman/Linzer lineage, adapted to Israel):

  latent   z_w  (weeks x lists-1, additive-log-ratio space)
           z_w = z_{w-1} + tau_b * eps_w          random-walk trend,
                                                  innovation ESTIMATED
  house    delta_{f,b} ~ N(gamma_{g(f),b}, sigma_f)   firm effects nested in
           gamma_{g,b} ~ N(0, sigma_g)                correlation groups
  obs      y_{p,b} ~ StudentT(4, softmax(z_{w(p)})_b + delta_{f(p),b}, s_b)
                                                  fat-tailed, noise ESTIMATED

This replaces the weighted average, trendline adjustment, house-effect
shrinkage, and the days-remaining scale in one joint posterior: forecast
uncertainty is the random walk run forward to election day. What polls can
NEVER identify — how wrong the whole industry is together — enters at
projection with the backtest-calibrated industry shocks (bloc swing, Arab
and haredi family errors), exactly as in the simple model.

Micro-lists that no pollster carries as a column (Zehut, Noam, NEP, and any
polled-at-zero list) join at projection from historical priors, so the
forecast covers the entire registered party space.

Ra'am is modeled separately from the Joint List throughout; the few polls
that merged them into one composite are excluded.

Workflow: prior predictive sanity -> NUTS -> convergence diagnostics ->
posterior predictive coverage -> 14-day holdout check -> projection through
threshold + Bader-Ofer -> comparison against the simple model.

Outputs:
    data/processed/bayes_forecast_2026.csv    per-list seat distribution
    data/processed/bayes_forecast_blocs.csv   bloc probabilities
    data/processed/bayes_draws.parquet        election-day seat draws
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from backtest import merge_blocks, short_name
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from polling_average import ELECTION_DAY_2026, load_2026
from scrape_polls import PROCESSED_DIR
from simulate import BLOC_LABEL, SURPLUS_PAIRS, THRESHOLD, dhondt

warnings.filterwarnings("ignore")

WINDOW_DAYS = 240
HOLDOUT_DAYS = 14
# Non-uniform latent grid: weekly bins through the campaign, finer bins in
# the final stretch — Israeli campaigns break late, and the harness showed a
# weekly latent smooths away final-week movement the simple average catches.
FINE_DAYS = 28
FINE_STEP = 2


def time_grid():
    """Bin edges in days-relative-to-asof, and per-step dt in week units."""
    edges = list(range(-WINDOW_DAYS, -FINE_DAYS, 7)) \
        + list(range(-FINE_DAYS, 1, FINE_STEP))
    if edges[-1] != 0:
        edges.append(0)
    edges = np.array(edges, dtype=float)
    mids = (edges[:-1] + edges[1:]) / 2.0
    dt_weeks = np.diff(mids) / 7.0
    return edges, dt_weeks
N_PROJ = 8_000          # posterior projection draws
# Forward event-risk multiplier on the bloc swing (Aug 30 macro sweep):
# two incumbent-controlled escalation dials (Lebanon, Turkey/Syria), a
# sanctions "D-Day", trial resumption Sept 8, ~30% undecided among
# first-time voters, and an unprecedented count of threshold-straddling
# lists. Forward-looking judgment, NOT applied in the historical harness
# (validate_bayes has its own projection where election-eve scale is 1).
EVENT_RISK = 1.2
SEED = 20261027
T_DF = 5

# All election-day shocks come from the sequential decomposition of the
# eight-cycle error record (error_decomposition.py), so no component is
# double-counted. Means are in ERROR space (polled - actual): the projection
# applies the NEGATED mean, since simulated truth = polled - error.
from error_decomposition import decompose as _decompose

_P = _decompose()
BLOC_SWING_SD = _P["bloc_sd"]
FAMILY_SHOCK = _P["family"]        # {family: (error mean, sd)} in seats
ANCHORS = _P["anchors"]            # {"likud": .., "leader": ..} error means
LIST_SHOCK_BASE = _P["resid_base"]
LIST_SHOCK_SLOPE = _P["resid_slope"]
# A list with no polls in its final weeks has left the race by election day.
WITHDRAWN_WEEKS = 5

# Prior-only micro-lists: (share mean, share sd) from their electoral history.
MICRO_PRIORS = {
    "zehut": (0.012, 0.007),   # 2.74% in Apr 2019, dormant since
    "noam": (0.007, 0.004),    # never cleared 1% alone
    "nep": (0.008, 0.005),     # ~1% in 2021
}


def prepare_data(polls: pd.DataFrame | None = None,
                 asof: pd.Timestamp | None = None,
                 modern_remaps: bool = True):
    """Build the model's data dict; parameterized so the validation harness
    can rebuild any past cycle's window (modern_remaps encodes 2026-only
    list identities — in earlier eras Ra'am really was inside the Joint
    List, so those rules must not apply)."""
    if polls is None:
        polls = load_2026()
    polls = polls[polls["pollster"] != "Unattributed"].copy()
    if modern_remaps:
        # Ra'am separate from the Joint List: joint_list == hadash_taal+balad,
        # and polls merging raam into a wider Arab composite are dropped.
        polls.loc[polls["party_id"] == "joint_list", "party_id"] = "balad+hadash_taal"
        # Together IS Yesh Atid + Bennett 2026: one entity across the merger,
        # so pre-merger component polls and post-merger joint polls share a
        # block.
        polls.loc[polls["party_id"] == "together", "party_id"] = "bennett_2026+yesh_atid"
        bad = polls[polls["party_id"].str.contains(r"raam.*\+|\+.*raam")]["poll_id"]
        polls = polls[~polls["poll_id"].isin(set(bad))]

    if asof is None:
        asof = polls["fieldwork_end"].max()
    win = polls[(polls["fieldwork_end"] > asof - pd.Timedelta(days=WINDOW_DAYS))
                & (polls["fieldwork_end"] <= asof)].copy()

    blocks = merge_blocks(win["party_id"].unique())
    block_of = {c: i for i, b in enumerate(blocks) for c in b}
    win["block"] = win["party_id"].map(lambda p: block_of[p.split("+")[0]])

    obs = implied_share_obs(win)
    if modern_remaps:
        obs = _merge_cec(obs, block_of, asof)

    edges, dt_weeks = time_grid()
    obs["obs_day"] = (obs["fieldwork_end"] - asof).dt.days
    obs["week"] = np.clip(np.digitize(obs["obs_day"], edges) - 1,
                          0, len(edges) - 2)
    firms = sorted(obs["pollster"].unique())
    firm_ix = {f: i for i, f in enumerate(firms)}
    try:
        meta = pd.read_csv(PROCESSED_DIR.parent / "pollster_meta.csv")
        gmap = dict(zip(meta["pollster"], meta["correlation_group"]))
    except FileNotFoundError:
        gmap = {}
    groups = sorted({gmap.get(f, f) for f in firms})
    group_ix = {g: i for i, g in enumerate(groups)}
    firm_group = np.array([group_ix[gmap.get(f, f)] for f in firms])

    # Latent lists: blocks with real data; the rest become micro-lists.
    counts = obs.groupby("block")["share"].count()
    latent_blocks = sorted(counts[counts >= 5].index)
    lb_ix = {b: i for i, b in enumerate(latent_blocks)}
    obs = obs[obs["block"].isin(latent_blocks)]

    try:
        fil = pd.read_csv(PROCESSED_DIR / "cec_filings.csv",
                          dtype={"ref": str})
        umap = dict(zip("cec" + fil["ref"], fil["undecided_pct"] / 100.0))
        uvals = obs["poll_id"].map(umap)
        u_c = (uvals - uvals.mean()).fillna(0.0).values
    except FileNotFoundError:
        u_c = np.zeros(len(obs))

    last_obs_day = obs.groupby("block")["obs_day"].max()
    data = {
        "asof": asof,
        "blocks": blocks,
        "latent_blocks": latent_blocks,
        "last_obs_day": last_obs_day.reindex(latent_blocks).values,
        "obs_day": obs["obs_day"].values.astype(int),
        "u_c": u_c,
        "dt_weeks": dt_weeks,
        "components": ["+".join(sorted(blocks[b])) for b in latent_blocks],
        "y": obs["share"].values,
        "week": obs["week"].values.astype(int),
        "block_i": obs["block"].map(lb_ix).values.astype(int),
        "firm_i": obs["pollster"].map(firm_ix).values.astype(int),
        "firm_group": firm_group,
        "n_weeks": len(edges) - 1,
        "firms": firms,
        "groups": groups,
        "n_polls": obs["poll_id"].nunique(),
    }
    return data


def implied_share_obs(win: pd.DataFrame) -> pd.DataFrame:
    """Implied vote share per poll x block: seat rows share the
    above-threshold pie, "(x.y%)" rows are direct shares; component rows of
    a joint list contribute the SUM."""
    win = win.copy()
    wasted = (win[win["seats"] == 0].assign(w=win["vote_pct"].fillna(0) / 100)
              .groupby("poll_id")["w"].sum())
    win["wasted"] = win["poll_id"].map(wasted).fillna(0.0)
    seat_share = win["seats"] / 120.0 * (1.0 - win["wasted"] - 0.01)
    pct_share = win["vote_pct"] / 100.0
    win["share"] = np.where(win["seats"] > 0, seat_share, pct_share)
    return (win[win["share"].notna()]
            .groupby(["poll_id", "block"], as_index=False)
            .agg(share=("share", "sum"), pollster=("pollster", "first"),
                 fieldwork_end=("fieldwork_end", "first")))


def _merge_cec(obs: pd.DataFrame, block_of: dict, asof) -> pd.DataFrame:
    """Swap in CEC-filed RAW percentages where available.

    Filings (scrape_cec.py) carry each list's raw support share, including
    sub-threshold lists — strictly better observations than inverting
    published seat tables. Only filings whose parsed distribution sums to
    90-105% are trusted; each one displaces the matching seat-derived poll
    (same pollster within 3 days) to avoid double counting. Unmatched
    filings (polls absent from the public tables) enter as new polls.
    """
    try:
        pcts = pd.read_csv(PROCESSED_DIR / "cec_party_pcts.csv",
                           parse_dates=["fieldwork_end"], dtype={"ref": str})
    except FileNotFoundError:
        return obs
    sums = pcts.groupby("ref")["raw_pct"].sum()
    good = set(sums[(sums >= 90) & (sums <= 105)].index)
    pcts = pcts[pcts["ref"].isin(good)
                & (pcts["fieldwork_end"] <= asof)].copy()
    if pcts.empty:
        return obs

    remap = {"together": "bennett_2026"}
    rows, displaced = [], set()
    for ref, g in pcts.groupby("ref"):
        pollster = g["pollster"].iloc[0]
        fw = g["fieldwork_end"].iloc[0]
        near = obs[(obs["pollster"] == pollster)
                   & ((obs["fieldwork_end"] - fw).dt.days.abs() <= 3)]
        displaced |= set(near["poll_id"])
        for r in g.itertuples():
            comp = remap.get(r.party_id, r.party_id).split("+")[0]
            if comp not in block_of:
                continue
            rows.append({"poll_id": f"cec{ref}", "block": block_of[comp],
                         "share": r.raw_pct / 100.0, "pollster": pollster,
                         "fieldwork_end": fw})
    cec_obs = pd.DataFrame(rows).groupby(
        ["poll_id", "block"], as_index=False).agg(
        share=("share", "sum"), pollster=("pollster", "first"),
        fieldwork_end=("fieldwork_end", "first"))
    kept = obs[~obs["poll_id"].isin(displaced)]
    print(f"CEC filings merged: {cec_obs['poll_id'].nunique()} filings "
          f"({len(cec_obs)} obs) displacing {len(displaced)} table-derived "
          f"polls")
    return pd.concat([kept, cec_obs], ignore_index=True)


def fit(data, draws=800, tune=800, holdout_mask=None):
    import pymc as pm
    import pytensor.tensor as pt

    B = len(data["latent_blocks"])
    W = data["n_weeks"]
    F = len(data["firms"])
    G = len(data["groups"])
    keep = slice(None) if holdout_mask is None else ~holdout_mask
    y, wk = data["y"][keep], data["week"][keep]
    bi, fi = data["block_i"][keep], data["firm_i"][keep]
    u_c = np.asarray(data.get("u_c", np.zeros(len(data["y"]))))[keep]

    # Empirical ALR start point for faster convergence.
    first = pd.DataFrame({"b": data["block_i"], "y": data["y"],
                          "w": data["week"]})
    early = first[first["w"] <= 8].groupby("b")["y"].mean()
    early = early.reindex(range(B)).fillna(0.01).clip(lower=0.004)
    mu0 = np.log(early.values[:-1] / early.values[-1])

    with pm.Model() as model:
        z0 = pm.Normal("z0", mu=mu0, sigma=0.5, shape=B - 1)
        tau = pm.HalfNormal("tau", 0.06, shape=B - 1)
        steps = pm.Normal("steps", 0, 1, shape=(W - 1, B - 1))
        z = pm.Deterministic(
            "z", pt.concatenate(
                [z0[None, :],
                 z0[None, :] + pt.cumsum(
                     steps * tau
                     * np.sqrt(data["dt_weeks"])[:, None], axis=0)],
                axis=0))
        shares = pm.Deterministic(
            "shares", pt.special.softmax(
                pt.concatenate([z, pt.zeros((W, 1))], axis=1), axis=1))

        sigma_g = pm.HalfNormal("sigma_g", 0.015)
        sigma_f = pm.HalfNormal("sigma_f", 0.008)
        gamma = pm.Normal("gamma", 0, sigma_g, shape=(G, B))
        delta = pm.Normal("delta", gamma[data["firm_group"]], sigma_f,
                          shape=(F, B))
        delta_c = pm.Deterministic("delta_c", delta - delta.mean(axis=0))

        s_obs = pm.HalfNormal("s_obs", 0.012, shape=B)
        # Firm reliability: per-firm noise multipliers with priors from the
        # results-graded accuracy scorecard — the information a within-cycle
        # likelihood cannot see. A firm with a poor final-poll record enters
        # with a wider prior noise; the 2026 data can still update it.
        from polling_average import QUALITY_ALIAS, quality_map
        q = np.array([quality_map().get(QUALITY_ALIAS.get(f, f), 1.0)
                      for f in data["firms"]])
        lam = pm.LogNormal("lam", mu=np.log(1.0 / q ** 2), sigma=0.25,
                           shape=F)
        # Undecided-share effect on informativeness: a filing-reported
        # undecided share above the field average widens that poll's noise
        # by an ESTIMATED factor (beta_u -> 0 if undecideds don't matter).
        beta_u = pm.HalfNormal("beta_u", 3.0)
        mu = shares[wk, bi] + delta_c[fi, bi]
        pm.StudentT("y", nu=4, mu=mu,
                    sigma=(s_obs[bi] + 0.002) * lam[fi]
                    * pt.exp(beta_u * u_c), observed=y)

        idata = pm.sample(draws=draws, tune=tune, chains=4, cores=4,
                          target_accept=0.92, random_seed=SEED,
                          progressbar=False,
                          compute_convergence_checks=False)
    return model, idata


def diagnostics(idata):
    import arviz as az
    div = int(idata.sample_stats["diverging"].sum())
    summ = az.summary(idata, var_names=["tau", "sigma_g", "sigma_f", "s_obs"],
                      kind="diagnostics")
    rhat = float(summ["r_hat"].max())
    ess = float(summ["ess_bulk"].min())
    print(f"diagnostics: {div} divergences | max r_hat {rhat:.3f} | "
          f"min bulk ESS {ess:.0f}")
    return div, rhat, ess


def posterior_predictive_check(data, idata):
    post = idata.posterior
    shares = post["shares"].values.reshape(-1, *post["shares"].shape[2:])
    delta = post["delta_c"].values.reshape(-1, *post["delta_c"].shape[2:])
    s_obs = post["s_obs"].values.reshape(-1, post["s_obs"].shape[-1])
    idx = np.random.default_rng(0).choice(len(shares), 500, replace=False)
    mu = shares[idx][:, data["week"], data["block_i"]] \
        + delta[idx][:, data["firm_i"], data["block_i"]]
    sd = s_obs[idx][:, data["block_i"]] + 0.002
    lo = np.percentile(mu - 1.96 * sd, 2.5, axis=0)
    hi = np.percentile(mu + 1.96 * sd, 97.5, axis=0)
    cover = ((data["y"] >= lo) & (data["y"] <= hi)).mean()
    print(f"posterior predictive: {cover:.1%} of poll observations inside "
          f"95% predictive band")


def project(data, idata, rng, config="current", config_params=None):
    """Election-day seat draws: RW forward + industry shocks + micro-lists.

    config reshapes the list structure before shocks and threshold:
      "balad_splits"  Balad leaves the Joint List at its scenario-polled
                      standalone share; "segalovitz" adds a new
                      centre-aligned list at its scenario-polled size
                      (parameters from arab_scenarios.py).
    """
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    names = dict(zip(reg["party_id"], reg["name_en"]))

    post = idata.posterior
    z_last = post["z"].values[:, :, -1, :].reshape(-1, post["z"].shape[-1])
    tau = post["tau"].values.reshape(-1, post["tau"].shape[-1])
    n_post = len(z_last)
    take = rng.choice(n_post, N_PROJ, replace=True)
    z_last, tau = z_last[take], tau[take]

    weeks_ahead = max((ELECTION_DAY_2026 - data["asof"]).days, 0) / 7.0
    z_e = z_last + np.sqrt(weeks_ahead) * tau * rng.standard_normal(z_last.shape)
    z_full = np.concatenate([z_e, np.zeros((N_PROJ, 1))], axis=1)
    shares = np.exp(z_full - z_full.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)

    # Lists with no polls in their final weeks have left the race.
    gone = data["last_obs_day"] < -7 * WITHDRAWN_WEEKS
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)

    # Per-list election-day shock: residual final-poll error beyond
    # bloc/family components, calibrated on the backtest.
    base0 = shares.mean(axis=0)
    sd_list = (LIST_SHOCK_BASE + LIST_SHOCK_SLOPE * base0 * 120) / 120.0
    shares = np.clip(
        shares + rng.standard_normal(shares.shape) * sd_list, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    labels = [short_name(c, names) for c in data["components"]]
    comps = [set(c.split("+")) for c in data["components"]]

    # Micro-lists from priors, carved out of the modeled pie.
    micro_names, micro_draws = [], []
    for pid, (m, s) in MICRO_PRIORS.items():
        micro_names.append(names.get(pid, pid))
        comps.append({pid})
        micro_draws.append(np.clip(rng.normal(m, s, N_PROJ), 0, None))
    micro = np.column_stack(micro_draws)
    shares = np.concatenate([shares * (1 - micro.sum(axis=1, keepdims=True)),
                             micro], axis=1)
    labels += micro_names

    blocs = []
    for comp in comps:
        bs = {bloc_map.get(c, "other") for c in comp}
        blocs.append(bs.pop() if len(bs) == 1 else "other")
    blocs = np.array(blocs)
    fams = np.array([max([FAMILY_OF.get(c, "other") for c in comp],
                         key=[FAMILY_OF.get(c, "other") for c in comp].count)
                     for comp in comps])

    # Configuration scenarios (registration-deadline what-ifs).
    cp = config_params or {}
    if config == "mixture":
        from registration_scenarios import apply_registration_events
        shares, comps, labels, blocs, fams, events = \
            apply_registration_events(shares, comps, labels, blocs, fams,
                                      rng, cp)
        project.last_events = events
    elif config == "balad_splits":
        jl = next((i for i, c in enumerate(comps) if "hadash_taal" in c), None)
        if jl is not None:
            split = cp.get("balad_alone_pct", 1.8) / 100.0
            take = np.minimum(shares[:, jl], split)
            shares = np.concatenate([shares, take[:, None]], axis=1)
            shares[:, jl] = shares[:, jl] - take
            comps.append({"balad"})
            labels.append("Balad (alone)")
            blocs = np.append(blocs, "other")
            fams = np.append(fams, "arab")
    elif config == "segalovitz":
        # Segalovitz joins Ra'am's slate: Ra'am gains crossover votes carved
        # from the centre bloc (no new list).
        boost = cp.get("segalovitz_boost_seats", 1.3) / 120.0
        raam = next((i for i, c in enumerate(comps) if "raam" in c), None)
        centre = blocs == "opposition_bloc"
        w = np.where(centre, shares.mean(axis=0), 0.0)
        if raam is not None:
            shares = shares - boost * (w / w.sum())
            shares[:, raam] = shares[:, raam] + boost
    elif config == "arab_turnout":
        # Differential-turnout dial: scale Arab-family shares by a factor
        # calibrated on the 2021->2022 turnout swing (44.6% -> 53.2% moved
        # the Arab lists' national share by ~+24%; +/-12% spans the range).
        fct = cp.get("factor", 1.0)
        in_a = fams == "arab"
        shares[:, in_a] = shares[:, in_a] * fct
    if config != "current":
        shares = np.clip(shares, 0, None)
        shares /= shares.sum(axis=1, keepdims=True)

    # Industry shocks (unidentifiable from polls).
    base = shares.mean(axis=0)
    is_nb = blocs == "netanyahu_bloc"
    swing = rng.standard_t(T_DF, N_PROJ) * BLOC_SWING_SD * EVENT_RISK / 120.0
    w_nb, w_op = np.where(is_nb, base, 0), np.where(~is_nb, base, 0)
    shares = shares + swing[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())
    for f, (mu_f, sd_f) in FAMILY_SHOCK.items():
        in_f = fams == f
        if not in_f.any():
            continue
        shock = (-mu_f + rng.standard_t(T_DF, N_PROJ) * sd_f) / 120.0
        w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
        shares = shares + shock[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())

    # Party anchors: deterministic truth-shifts for Likud and the poll
    # leader (their variance already lives in the residual shock).
    likud_col = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    non_likud = [i for i in range(len(comps)) if i != likud_col]
    leader_col = non_likud[int(np.argmax(base[non_likud]))] if non_likud else None
    for col, mu in ((likud_col, ANCHORS["likud"]),
                    (leader_col, ANCHORS["leader"])):
        if col is None:
            continue
        onehot = np.zeros(len(comps))
        onehot[col] = 1.0
        w_r = np.where(onehot == 0, base, 0)
        shares = shares + (-mu / 120.0) * (onehot - w_r / w_r.sum())
    shares = np.clip(shares, 0, None)
    shares /= shares.sum(axis=1, keepdims=True)

    comp_of = {c: i for i, cs in enumerate(comps) for c in cs}
    pairs = [(comp_of[a], comp_of[b]) for a, b in SURPLUS_PAIRS
             if a in comp_of and b in comp_of and comp_of[a] != comp_of[b]]

    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
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
        for members, k in zip(fmembers, alloc):
            if len(members) == 1:
                seats[i, members[0]] = k
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats, labels, blocs


def main() -> None:
    rng = np.random.default_rng(SEED)
    data = prepare_data()
    print(f"data: {data['n_polls']} polls, {len(data['y'])} observations, "
          f"{len(data['latent_blocks'])} lists, {data['n_weeks']} weeks, "
          f"{len(data['firms'])} firms in {len(data['groups'])} groups")

    # Holdout: refit without the last 14 days, predict them.
    cut = data["asof"] - pd.Timedelta(days=HOLDOUT_DAYS)
    holdout = data["obs_day"] > -HOLDOUT_DAYS
    if holdout.sum() >= 10:
        _, idata_h = fit(data, draws=500, tune=600, holdout_mask=holdout)
        post = idata_h.posterior
        sh = post["shares"].values.reshape(-1, *post["shares"].shape[2:])
        wk_last = min(int(data["week"][~holdout].max()),
                      sh.shape[1] - 1)
        pred = sh[:, wk_last, :]  # frozen at last fitted week
        y_h = data["y"][holdout]
        b_h = data["block_i"][holdout]
        err = np.abs(np.median(pred, axis=0)[b_h] - y_h) * 120
        print(f"holdout ({int(holdout.sum())} obs, last {HOLDOUT_DAYS}d): "
              f"median |error| {np.median(err):.2f} seats "
              f"(no-update prediction)")

    model, idata = fit(data)
    diagnostics(idata)
    if "beta_u" in idata.posterior:
        bu = idata.posterior["beta_u"].values.ravel()
        print(f"undecided coefficient beta_u: mean {bu.mean():.2f}, "
              f"90% CI [{np.percentile(bu, 5):.2f}, "
              f"{np.percentile(bu, 95):.2f}]  "
              f"(x{np.exp(bu.mean() * 0.05):.2f} noise per +5pp undecided)")
    posterior_predictive_check(data, idata)

    seats, labels, blocs = project(data, idata, rng)
    is_max = seats == seats.max(axis=1, keepdims=True)
    p_largest = (is_max / is_max.sum(axis=1, keepdims=True)).mean(axis=0)

    dist = pd.DataFrame({
        "list": labels,
        "bloc": [BLOC_LABEL.get(b, b) for b in blocs],
        "mean": seats.mean(axis=0).round(1),
        "p05": np.percentile(seats, 5, axis=0).astype(int),
        "p50": np.percentile(seats, 50, axis=0).astype(int),
        "p95": np.percentile(seats, 95, axis=0).astype(int),
        "p_pass": (seats >= 4).mean(axis=0).round(3),
        "p_largest": p_largest.round(3),
    }).sort_values("mean", ascending=False)
    dist["asof"] = data["asof"].date().isoformat()
    dist.to_csv(PROCESSED_DIR / "bayes_forecast_2026.csv", index=False)
    pd.DataFrame(seats, columns=labels).to_parquet(
        PROCESSED_DIR / "bayes_draws.parquet")

    nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
    anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
    summary = pd.DataFrame([{
        "asof": data["asof"].date().isoformat(), "n_proj": N_PROJ,
        "p_netanyahu_bloc_61": (nb >= 61).mean().round(3),
        "p_anti_bloc_61": (anti >= 61).mean().round(3),
        "p_neither": ((nb < 61) & (anti < 61)).mean().round(3),
        "nb_mean": nb.mean().round(1),
        "nb_p05": int(np.percentile(nb, 5)),
        "nb_p95": int(np.percentile(nb, 95)),
    }])
    summary.to_csv(PROCESSED_DIR / "bayes_forecast_blocs.csv", index=False)

    print(f"\nBayesian forecast as of {data['asof'].date()}:\n")
    print(dist.drop(columns="asof").to_string(index=False))
    s = summary.iloc[0]
    print(f"\nP(Netanyahu bloc >= 61) = {s['p_netanyahu_bloc_61']:.1%}   "
          f"P(anti bloc >= 61) = {s['p_anti_bloc_61']:.1%}   "
          f"P(neither) = {s['p_neither']:.1%}")
    print(f"Netanyahu bloc mean {s['nb_mean']}, 90% interval "
          f"[{s['nb_p05']}, {s['nb_p95']}]")
    print("\nwrote bayes_forecast_2026.csv, bayes_forecast_blocs.csv, "
          "bayes_draws.parquet")


if __name__ == "__main__":
    main()
