"""Retro-validation of the Bayesian model on the eight graded cycles.

Same protocol as validate_model.py graded the simple pipeline with: for each
past election, the state-space model is refit using only that cycle's polls
as of the day before the vote, projected through that cycle's threshold and
(approximate) surplus pairs with LEAVE-ONE-CYCLE-OUT industry shocks, and
graded on 90% interval coverage, threshold Brier, seat MAE, and the stated
bloc-majority probability. Ends with the head-to-head against the simple
pipeline's model_validation.csv.

The projection code deliberately mirrors bayes_model.project() in
validation-parameterized form rather than sharing it — the production path
stays untouched by validation needs.

Outputs:
    data/processed/model_validation_bayes.csv
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

import bayes_model as bm
from bayes_model import SEED, T_DF, WITHDRAWN_WEEKS, fit, prepare_data
from error_decomposition import decompose
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
import simulate as _sim
from simulate import THRESHOLD, dhondt
from validate_model import (
    CYCLE_THRESHOLD, ORDER, PAST_PAIRS, VAL_BLOC_OVERRIDES,
)

warnings.filterwarnings("ignore")

N_PROJ = 4000
WIDTH_GRID = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1]
ABLATIONS = [
    ("shipped", {}),
    ("no_resid", {"resid": False}), ("no_swing", {"swing": False}),
    ("no_family", {"family": False}), ("no_gevalt", {"gevalt": False}),
    ("no_loyal", {"loyal": False}),
    ("no_trail", {"gevalt_cond": False}), ("trail_full", {"trail_scale": 1.0}),
    ("no_nstrad", {"new_straddler": False}),
    ("anchors_on", {"anchors": True}),
    ("pair_fix", {"pair_fix": True}), ("pair_alias", {"pair_alias": True}),
    # candidate gone14 (2026-10-10, dossier s.41): withdrawn-list rule at 14
    # days inside the final four weeks; gone_zero keeps dropped lists at
    # zero through the residual shock (the stats/build skeptic fix).
    ("gone14", {"gone_days": 14}), ("gone10", {"gone_days": 10}),
    ("gone_zero", {"gone_zero": True}),
    ("gone14_zero", {"gone_days": 14, "gone_zero": True}),
    # candidate trail_geometry (2026-10-10, dossier s.41). PRIMARY,
    # pre-registered: trail_sat = same draw, same gate, same half strength,
    # sourced from the bloc's own non-haredi satellites (the gevalt
    # coupling's rule mask). The rest are sensitivity runs, not choices.
    ("trail_sat", {"trail_source": "sat"}),
    ("trail_sat_era", {"trail_source": "era"}),
    ("trail_draw_sat", {"trail_source": "sat", "trail_mode": "draw"}),
    ("trail_draw_sat_full", {"trail_source": "sat", "trail_mode": "draw", "trail_scale": 1.0}),
    ("trail_ramp_sat", {"trail_source": "sat", "trail_mode": "ramp", "trail_hi": 2.0}),
    # 2026-10-13 combine: the ship set together
    ("combined", {"pair_fix": True, "gone_days": 14, "gone_zero": True, "trail_source": "sat"}),
    ("latent_only", {k: False for k in ["resid", "swing", "family", "gevalt", "loyal",
                                        "gevalt_cond", "new_straddler"]}),
]
# Quick runs (candidate testing): HARNESS_ABLATIONS=shipped,my_layer limits the
# ablation list by name; HARNESS_SKIP_WIDTH=1 skips the width grid.
import os as _os
if _os.environ.get("HARNESS_ABLATIONS"):
    _keep = set(_os.environ["HARNESS_ABLATIONS"].split(","))
    ABLATIONS = [a for a in ABLATIONS if a[0] in _keep]

# Era-specific alliance identities: which composite each historical id was.
# Applied component-wise before block-building, so pre-merger component
# polls and post-merger joint polls share one entity — the same treatment
# 2026 gets (Together = Bennett + Yesh Atid), without which past windows
# carry phantom lists that poll early, vanish, and get graded as misses.
DECOMP = {
    "2015": {"joint_list": "balad+hadash_taal+raam_taal",
             "zionist_union": "hatnuah+labor"},
    "2019a": {"hosen_telem": "hosen+telem",
              "blue_white": "hosen+telem+yesh_atid",
              "urwp": "jewish_home+national_union",
              "raam_balad": "balad+raam"},
    "2019s": {"hosen_telem": "hosen+telem",
              "blue_white": "hosen+telem+yesh_atid",
              "urwp": "jewish_home+national_union",
              "dem_union": "idp+meretz",
              "labor_gesher": "gesher+labor",
              "raam_balad": "balad+raam"},
    "2020": {"blue_white": "hosen+telem+yesh_atid",
             "dem_union": "idp+meretz",
             "labor_gesher": "gesher+labor",
             "labor_gesher_meretz": "gesher+labor+meretz",
             "yesh_atid_telem": "telem+yesh_atid"},
    "2021": {"labor_meretz": "labor+meretz",
             "otzma_noam": "noam+otzma"},
    "2022": {"otzma_noam": "noam+otzma"},
}


def apply_decomp(polls: pd.DataFrame, cycle: str) -> pd.DataFrame:
    mapping = DECOMP.get(cycle)
    if not mapping:
        return polls
    polls = polls.copy()
    polls["party_id"] = polls["party_id"].map(
        lambda pid: "+".join(sorted({
            part for c in pid.split("+")
            for part in mapping.get(c, c).split("+")})))
    return polls


# Defaults MIRROR PRODUCTION (bayes_model): anchors retired, the
# trailing-Likud conditional at half strength sourced from the bloc's
# satellites, new-straddler desertion on, the surplus-pair resolver fix,
# the 14-day withdrawn-list rule with dropped lists held at zero
# (2026-10-13 ship set, dossier s.41).
# An ablation turns one layer off (or an alternative on) relative to this.
ALL_LAYERS = {"resid": True, "swing": True, "family": True, "anchors": False,
              "gevalt": True, "loyal": True,
              "anchor_likud": True, "anchor_leader": True, "anchor_scale": 1.0,
              "shock_scale": 1.0,
              # accuracy round four #4: Likud's poll beat conditional on
              # TRAILING (or tying) the largest non-bloc list at the
              # projection date - the successor to the retired fixed anchor
              "gevalt_cond": True, "trail_scale": 0.5,
              # accuracy round four #1: first-cycle lists projected at the
              # threshold band lose votes to strategic desertion (measured on
              # the D-56/D-21 straddler record: 2 of 11 passed, drift -1.6 pp)
              "new_straddler": True,
              # dossier s.40: surplus-pair resolver fix (simulate.
              # PAIR_RESOLVER_FIX); pair_alias also resolves DECOMP-renamed
              # PAST_PAIRS ids
              "pair_fix": True, "pair_alias": False,
              # candidate gone14 (OFF): unpolled-days cutoff that replaces
              # 7 x WITHDRAWN_WEEKS when the projection date is within
              # gone_gate days of the election; gone_zero holds dropped
              # lists at zero (no residual shock resurrects them).
              "gone_days": 14, "gone_gate": 28, "gone_zero": True,
              # candidate trail_geometry (defaults = shipped geometry):
              # source 'field' | 'sat' (NB non-haredi non-Likud rule mask,
              # the gevalt coupling's) | 'era' (hand list, sensitivity only);
              # gate 'mean' (0.5-seat cliff on the mean projection) | 'draw'
              # (same test per pre-shock latent draw) | 'ramp' (weight falls
              # linearly from margin 0.5 to trail_hi seats)
              "trail_source": "sat", "trail_mode": "mean", "trail_hi": 2.0}
# Hand-picked right-flank ids per era (sensitivity run only: its case was
# argued from outcomes - it drops Yisrael Beytenu from the 2015 pool).
GEVALT_ERA_IDS = {"jewish_home", "national_union", "otzma", "yachad_yishai",
                  "zehut", "new_right", "urwp", "yamina", "rzp", "noam",
                  "amcha_yisrael"}
NSTRAD_BAND = (-0.75, 1.5)   # pp around the threshold (projected share)


def new_lists_for_cycle(polls: pd.DataFrame, cycle: str) -> set:
    """Component ids first polled in this cycle (no polls in any earlier one)."""
    seen = set()
    for cyc in ORDER:
        if cyc == cycle:
            break
        seen |= set(polls[polls["cycle"] == cyc]["party_id"].str.split("+").explode())
    now = set(polls[polls["cycle"] == cycle]["party_id"].str.split("+").explode())
    return {c for c in now if c not in seen}


def new_straddler_params(exclude_cycle: str | None = None) -> dict:
    """LOO mean/sd of the realised drift (result - projected share, pp) of
    FIRST-CYCLE lists projected within NSTRAD_BAND at D-56/D-21, from
    model_validation_threshold.csv (validate_threshold.py)."""
    try:
        d = pd.read_csv(PROCESSED_DIR / "model_validation_threshold.csv")
    except FileNotFoundError:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    if "new" not in d.columns:
        return {"mu": 0.0, "sd": 0.0, "n": 0}
    d = d[d["new"] & (d["cycle"].astype(str) != str(exclude_cycle))]
    if len(d) < 3:
        return {"mu": 0.0, "sd": 0.0, "n": int(len(d))}
    return {"mu": float(d["drift"].mean()), "sd": float(d["drift"].std(ddof=1)), "n": int(len(d))}
TRAIL_MARGIN = 0.5   # seats: "trailing or tied" = Likud <= leader + margin


def trailing_likud_params(polls: pd.DataFrame, results: pd.DataFrame,
                          exclude_cycle: str | None = None) -> dict:
    """Leave-one-cycle-out measurement of Likud's final-week poll miss in
    cycles where it trailed (or tied) the largest non-Netanyahu-bloc list
    in the final week. Returns {"mu", "sd", "n", "cycles"}."""
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    misses = {}
    for cyc in ORDER:
        if cyc == exclude_cycle:
            continue
        eday = pd.Timestamp(ELECTION_DAY[cyc])
        p = polls[(polls["cycle"] == cyc) & (polls["fieldwork_end"] < eday)
                  & (polls["fieldwork_end"] >= eday - pd.Timedelta(days=7))]
        r = results[results["cycle"] == cyc]
        if p.empty or r.empty:
            continue
        bm_c = dict(bloc_map, **VAL_BLOC_OVERRIDES.get(cyc, {}))
        avg = p.groupby("party_id")["seats"].mean()
        lk = [pid for pid in avg.index if "likud" in pid.split("+")]
        if not lk:
            continue
        lk = lk[0]
        others = [pid for pid in avg.index
                  if pid != lk and bm_c.get(pid.split("+")[0], "other") != "netanyahu_bloc"]
        if not others:
            continue
        leader = avg[others].max()
        if avg[lk] <= leader + TRAIL_MARGIN:
            act = r[r["party_id"] == lk]["seats"]
            if len(act):
                misses[cyc] = float(act.iloc[0]) - float(avg[lk])
    vals = np.array(list(misses.values()))
    if len(vals) == 0:
        return {"mu": 0.0, "sd": 0.0, "n": 0, "cycles": {}}
    return {"mu": float(vals.mean()), "sd": float(vals.std(ddof=1)) if len(vals) > 1 else 3.0,
            "n": int(len(vals)), "cycles": misses}


def allocate_vector(v, threshold, pair_idx):
    """Threshold + surplus pairs + d'Hondt (Bader-Ofer) on one share vector."""
    v = np.asarray(v, float) / np.sum(v)
    out = np.zeros(len(v), dtype=int)
    passed = v >= threshold
    if not passed.any():
        return out
    fvotes, fmembers, used = [], [], set()
    for a, b in pair_idx:
        if passed[a] and passed[b]:
            fvotes.append(v[a] + v[b]); fmembers.append([a, b]); used |= {a, b}
    for j in np.nonzero(passed)[0]:
        if j not in used:
            fvotes.append(v[j]); fmembers.append([int(j)])
    alloc = dhondt(np.array(fvotes), 120)
    for members, k in zip(fmembers, alloc):
        if len(members) == 1:
            out[members[0]] = k
        else:
            a, b = members
            inner = dhondt(np.array([v[a], v[b]]), int(k))
            out[a], out[b] = int(inner[0]), int(inner[1])
    return out


def project_cycle(data, idata, eday, threshold, pairs, params,
                  bloc_overrides, rng, resid_scale=None, layers=None,
                  weeks_override=None):
    if resid_scale is None:
        resid_scale = bm.RESID_SCALE          # production width
    L = dict(ALL_LAYERS, **(layers or {}))
    swing_sd, shocks = params["bloc_sd"], params["family"]
    reg = load_party_registry()
    bloc_map = dict(zip(reg["party_id"], reg["bloc"]))
    bloc_map.update(bloc_overrides or {})

    post = idata.posterior
    z_last = post["z"].values[:, :, -1, :].reshape(-1, post["z"].shape[-1])
    tau = post["tau"].values.reshape(-1, post["tau"].shape[-1])
    take = rng.choice(len(z_last), N_PROJ, replace=True)
    z_last, tau = z_last[take], tau[take]
    weeks = max((eday - data["asof"]).days, 0) / 7.0
    if weeks_override is not None:
        weeks = float(weeks_override)
    z_e = z_last + np.sqrt(weeks) * tau * rng.standard_normal(z_last.shape)
    z_f = np.concatenate([z_e, np.zeros((N_PROJ, 1))], axis=1)
    shares = np.exp(z_f - z_f.max(axis=1, keepdims=True))
    shares /= shares.sum(axis=1, keepdims=True)

    # days_ahead from the real dates, never weeks_override (calendar weeks)
    days_ahead = max((eday - data["asof"]).days, 0)
    gone_days = 7 * WITHDRAWN_WEEKS
    if L["gone_days"] is not None and days_ahead <= L["gone_gate"]:
        gone_days = L["gone_days"]
    gone = data["last_obs_day"] < -gone_days
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)
    shares_pre = shares.copy()    # latent draws before any shock (draw gate)
    base0 = shares.mean(axis=0)
    sd_list = (params["resid_base"]
               + params["resid_slope"] * base0 * 120) / 120.0 * resid_scale
    if L["gone_zero"]:
        sd_list = np.where(gone, 0.0, sd_list)
    if L["resid"]:
        shares = np.clip(
            shares + rng.standard_normal(shares.shape) * sd_list, 0, None)
        shares /= shares.sum(axis=1, keepdims=True)

    comps = [set(c.split("+")) for c in data["components"]]
    blocs = np.array([
        (lambda bs: bs.pop() if len(bs) == 1 else "other")(
            {bloc_map.get(c, "other") for c in cp}) for cp in comps])
    fams = np.array([max([FAMILY_OF.get(c, "other") for c in cp],
                         key=[FAMILY_OF.get(c, "other") for c in cp].count)
                     for cp in comps])

    base = shares.mean(axis=0)
    is_nb = blocs == "netanyahu_bloc"
    if L["swing"] and is_nb.any() and (~is_nb).any():
        sw = rng.standard_t(T_DF, N_PROJ) * swing_sd * L["shock_scale"] / 120.0
        w_nb, w_op = np.where(is_nb, base, 0), np.where(~is_nb, base, 0)
        shares = shares + sw[:, None] * (w_nb / w_nb.sum() - w_op / w_op.sum())
    # Family shocks with the kalpi-measured haredi<->arab correlation,
    # mirrored from bayes_model (shared chi-square mixer -> correlated t).
    from bayes_model import KALPI_FAMILY_RHO, GEVALT_SD
    fam_names = [f for f in shocks if (fams == f).any() and not (fams == f).all()]
    rho = KALPI_FAMILY_RHO if len(fam_names) == 2 else 0.0
    cov = np.array([[1.0, rho], [rho, 1.0]]) if rho else np.eye(max(len(fam_names), 1))
    zf = rng.multivariate_normal(np.zeros(len(fam_names)), cov[:len(fam_names), :len(fam_names)],
                                 size=N_PROJ) if fam_names else np.zeros((N_PROJ, 0))
    mixer = np.sqrt(rng.chisquare(T_DF, N_PROJ) / T_DF)
    for k, f in enumerate(fam_names):
        if not L["family"]:
            break
        mu_f, sd_f = shocks[f]
        in_f = fams == f
        sk = (-mu_f + (zf[:, k] / mixer) * sd_f * L["shock_scale"]) / 120.0
        w_f, w_r = np.where(in_f, base, 0), np.where(~in_f, base, 0)
        shares = shares + sk[:, None] * (w_f / w_f.sum() - w_r / w_r.sum())
    # Gevalt coupling, mirrored: zero-sum Likud <-> its bloc's non-haredi
    # satellites (the era's right-flank lists), sd GEVALT_SD seats.
    lk = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    sat = np.array([(blocs[i] == "netanyahu_bloc") and (fams[i] != "haredi") and i != lk
                    for i in range(len(comps))])
    if L["gevalt"] and lk is not None and sat.any():
        g = rng.standard_normal(N_PROJ) * GEVALT_SD / 120.0
        w_s = np.where(sat, base, 0)
        shares[:, lk] += g
        shares = shares - g[:, None] * (w_s / w_s.sum())

    # Party anchors (error-space means, negated to shift simulated truth).
    likud_col = next((i for i, cp in enumerate(comps) if "likud" in cp), None)
    non_likud = [i for i in range(len(comps)) if i != likud_col]
    leader_col = non_likud[int(np.argmax(base[non_likud]))] if non_likud else None
    for col, mu, on in ((likud_col, params["anchors"]["likud"], L["anchor_likud"]),
                        (leader_col, params["anchors"]["leader"], L["anchor_leader"])):
        if col is None or not L["anchors"] or not on:
            continue
        mu = mu * L["anchor_scale"]
        onehot = np.zeros(len(comps))
        onehot[col] = 1.0
        w_r = np.where(onehot == 0, base, 0)
        shares = shares + (-mu / 120.0) * (onehot - w_r / w_r.sum())

    # New-straddler desertion (accuracy round four #1): first-cycle lists
    # whose projected share sits in the threshold band get the LOO-measured
    # mean drift (negative) with its sd, zero-sum against the field.
    if L["new_straddler"] and params.get("nstrad", {}).get("n", 0) >= 3 and "new_lists" in params:
        ns = params["nstrad"]
        for i, cp in enumerate(comps):
            if not (cp <= params["new_lists"]):
                continue
            rel = base[i] * 100 - threshold * 100
            if NSTRAD_BAND[0] <= rel <= NSTRAD_BAND[1]:
                g = rng.normal(ns["mu"], ns["sd"], N_PROJ) / 100.0
                onehot = np.zeros(len(comps)); onehot[i] = 1.0
                w_r = np.where(onehot == 0, base, 0)
                shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]
        shares = np.clip(shares, 0, None)

    # Trailing-Likud conditional (accuracy round four #4): if Likud's
    # projected standing at the projection date trails or ties the largest
    # non-bloc list, add the LOO-measured miss of trailing years (mean mu,
    # sd over those years), zero-sum against the rest of the field.
    project_cycle.last_trail = {"frac": 0.0, "overflow": None}
    if L["gevalt_cond"] and likud_col is not None and "trail" in params:
        tp = params["trail"]
        non_nb = [i for i in range(len(comps)) if blocs[i] != "netanyahu_bloc" and i != likud_col]
        if non_nb and tp["n"] > 0:
            margin = (base[likud_col] - base[non_nb].max()) * 120.0
            if L["trail_mode"] == "draw":
                m_d = (shares_pre[:, likud_col] - shares_pre[:, non_nb].max(axis=1)) * 120.0
                gate = (m_d <= TRAIL_MARGIN).astype(float)
            elif L["trail_mode"] == "ramp":
                gate = np.full(N_PROJ, float(np.clip(
                    (L["trail_hi"] - margin) / (L["trail_hi"] - TRAIL_MARGIN), 0.0, 1.0)))
            else:
                gate = np.full(N_PROJ, float(margin <= TRAIL_MARGIN))
            project_cycle.last_trail["frac"] = float(gate.mean())
            if gate.any():
                g = rng.normal(tp["mu"], tp["sd"], N_PROJ) * L["trail_scale"] / 120.0 * gate
                if L["trail_source"] == "sat":
                    src = sat
                elif L["trail_source"] == "era":
                    src = np.array([bool(cp & GEVALT_ERA_IDS) for cp in comps])
                else:
                    src = np.zeros(len(comps), bool)
                if src.any():
                    shares, ov = bm.trail_transfer(shares, g, likud_col, src, base)
                    project_cycle.last_trail["overflow"] = ov
                else:   # shipped geometry: zero-sum against the whole field
                    onehot = np.zeros(len(comps)); onehot[likud_col] = 1.0
                    w_r = np.where(onehot == 0, base, 0)
                    shares = shares + g[:, None] * (onehot - w_r / w_r.sum())[None, :]

    # Loyal-electorate calibration, mirrored from bayes_model.LOYAL_SD:
    # standalone captive-base lists are shrunk to their measured total sd.
    from bayes_model import LOYAL_SD
    for pid, tgt in (LOYAL_SD.items() if L["loyal"] else []):
        want = set(pid.split("+"))
        col = next((i for i, cs in enumerate(comps) if cs == want), None)
        if col is None:
            continue
        v = shares[:, col]
        act = v.std() * 120.0
        if act > tgt:
            shares[:, col] = v.mean() + (v - v.mean()) * (tgt / act)
    shares = np.clip(shares, 0, None)
    if L["gone_zero"] and gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
    shares /= shares.sum(axis=1, keepdims=True)

    # Surplus pairs through the shared resolver (dossier s.40). pair_fix:
    # first occurrence wins + a list is never pooled twice in a draw (the
    # production fix; a provable no-op here). pair_alias additionally
    # resolves PAST_PAIRS ids that DECOMP renamed (urwp, blue_white,
    # labor_gesher, ...) - the harness analogue of 'together'.
    pair_idx, comp_of, _ = _sim.resolve_pairs(
        pairs, data["components"],
        aliases=params.get("pair_alias") if L["pair_alias"] else None,
        fixed=L["pair_fix"] or L["pair_alias"])
    # production's central estimator: the seat law applied once to the
    # renormalised median share vector (official_forecast.allocate_central)
    project_cycle.last_central = allocate_vector(np.median(shares, axis=0), threshold, pair_idx)
    fixed_pairs = L["pair_fix"] or L["pair_alias"]

    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        sh = shares[i]
        passed = sh >= threshold
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers = _sim.form_factions(pair_idx, passed, votes,
                                              fixed=fixed_pairs)
        alloc = dhondt(np.array(fvotes), 120)
        for members, k in zip(fmembers, alloc):
            if len(members) == 1:
                seats[i, members[0]] = k
            else:
                a, b = members
                inner = dhondt(np.array([votes[a], votes[b]]), int(k))
                seats[i, a], seats[i, b] = int(inner[0]), int(inner[1])
    return seats, blocs, base, comp_of


def main() -> None:
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv",
                        parse_dates=["fieldwork_end"])
    results = pd.read_csv(PROCESSED_DIR / "results.csv")
    rng = np.random.default_rng(SEED)

    rows, covered_all, list_rows, width_rows, abl_rows = [], [], [], [], []
    for cycle in ORDER:
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        asof = eday - pd.Timedelta(days=1)
        cyc = polls[(polls["cycle"] == cycle) & polls["sums_ok"]]
        cyc = apply_decomp(cyc, cycle)
        try:
            data = prepare_data(cyc, asof, modern_remaps=(cycle == "2026"))
            print(f"[{cycle}] {data['n_polls']} polls, "
                  f"{len(data['latent_blocks'])} lists, "
                  f"{data['n_weeks']} weeks — fitting...")
            import arviz as az
            cache = PROCESSED_DIR / "harness_cache"; cache.mkdir(exist_ok=True)
            nc = cache / f"{cycle}_eve.nc"
            if nc.exists():
                idata = az.from_netcdf(nc)
            else:
                _, idata = fit(data, draws=600, tune=600)
                az.to_netcdf(idata, nc)
            div = int(idata.sample_stats["diverging"].sum())
            params = decompose(exclude_cycle=cycle)
            params["trail"] = trailing_likud_params(polls, results, exclude_cycle=cycle)
            params["new_lists"] = new_lists_for_cycle(polls, cycle)
            params["nstrad"] = new_straddler_params(exclude_cycle=cycle)
            params["pair_alias"] = DECOMP.get(cycle, {})
            print(f"[{cycle}] trailing-Likud LOO: mu {params['trail']['mu']:+.2f} sd {params['trail']['sd']:.2f} n {params['trail']['n']}")
            seats, blocs, base, comp_of = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params,
                VAL_BLOC_OVERRIDES.get(cycle), rng)
        except Exception as e:
            print(f"[{cycle}] FAILED: {e}")
            continue

        res = apply_decomp(results[results["cycle"] == cycle], cycle)
        actual = np.zeros(seats.shape[1])
        unmatched = 0
        for r in res.itertuples():
            hit = {comp_of[c] for c in r.party_id.split("+") if c in comp_of}
            if len(hit) == 1:
                actual[hit.pop()] += r.seats
            else:
                unmatched += r.seats

        # Layer ablation (accuracy round 3, #1): which projection layers
        # help or hurt point accuracy on the graded record.
        # *_fixed columns grade every ablation on the SHIPPED config's list
        # mask, so a layer that moves a list across the 0.5% scoring cutoff
        # (e.g. holding dropped lists at zero) is not graded on a different
        # denominator (harness_compare --fixed).
        fixed = None
        for tag, flags in ABLATIONS:
            sa, _, ba, _ = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                np.random.default_rng(SEED + 11 + int(_os.environ.get("HARNESS_SEED_OFFSET", 0))),
                layers=flags)
            act_a = (ba >= 0.005) | (actual > 0)
            if tag == "shipped":
                fixed = act_a
            lo_a, hi_a = np.percentile(sa, 5, axis=0), np.percentile(sa, 95, axis=0)
            ppa = (sa >= 1).mean(axis=0)
            row = {"cycle": cycle, "ablation": tag}
            for sfx, m in (("", act_a), ("_fixed", fixed if fixed is not None else act_a)):
                row.update({"seat_mae" + sfx: float(np.abs(sa.mean(axis=0) - actual)[m].mean()),
                            "seat_mae_median" + sfx: float(np.abs(np.median(sa, axis=0) - actual)[m].mean()),
                            "coverage_90" + sfx: float(((actual >= lo_a) & (actual <= hi_a))[m].mean()),
                            "threshold_brier" + sfx: float(np.mean((ppa[m] - (actual[m] > 0)) ** 2))})
            abl_rows.append(row)

        # Interval-width calibration curve (audit improvement #2): the same
        # posterior re-projected under a grid of residual-width factors.
        for w in ([] if _os.environ.get("HARNESS_SKIP_WIDTH") else WIDTH_GRID):
            sw, _, bw, _ = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                np.random.default_rng(SEED + 7), resid_scale=w)
            act_w = (bw >= 0.005) | (actual > 0)
            lo_w, hi_w = np.percentile(sw, 5, axis=0), np.percentile(sw, 95, axis=0)
            pp = (sw >= 1).mean(axis=0)
            a = 0.10   # interval score (Gneiting-Raftery): width + miss penalties
            isc = (hi_w - lo_w) + (2/a) * np.maximum(lo_w - actual, 0) + (2/a) * np.maximum(actual - hi_w, 0)
            width_rows.append({"cycle": cycle, "width": w,
                               "coverage_90": float(((actual >= lo_w) & (actual <= hi_w))[act_w].mean()),
                               "seat_mae": float(np.abs(sw.mean(axis=0) - actual)[act_w].mean()),
                               "threshold_brier": float(np.mean((pp[act_w] - (actual[act_w] > 0)) ** 2)),
                               "interval_score": float(isc[act_w].mean())})

        pred_mean = seats.mean(axis=0)
        p05 = np.percentile(seats, 5, axis=0)
        p95 = np.percentile(seats, 95, axis=0)
        active = (base >= 0.005) | (actual > 0)
        cov = ((actual >= p05) & (actual <= p95))[active]
        p_pass = (seats >= 1).mean(axis=0)
        brier = float(np.mean((p_pass[active] - (actual[active] > 0)) ** 2))
        mae = float(np.abs(pred_mean - actual)[active].mean())
        nb_mask = blocs == "netanyahu_bloc"
        nb_sim = seats[:, nb_mask].sum(axis=1)
        nb_actual = int(actual[nb_mask].sum())
        for i in np.nonzero(active)[0]:
            list_rows.append({"cycle": cycle,
                              "components": data["components"][i]
                              if i < len(data["components"]) else "micro",
                              "pred": float(pred_mean[i]),
                              "actual": int(actual[i])})
        rows.append({
            "cycle": cycle, "n_lists": int(active.sum()),
            "coverage_90": round(float(cov.mean()), 2),
            "threshold_brier": round(brier, 3),
            "seat_mae": round(mae, 2),
            "p_bloc_61": round(float((nb_sim >= 61).mean()), 3),
            "bloc_actual": nb_actual,
            "bloc_61_happened": nb_actual >= 61,
            "divergences": div, "unmatched_actual_seats": unmatched,
        })
        covered_all.append(cov)
        print(f"[{cycle}] coverage {rows[-1]['coverage_90']:.0%} | "
              f"MAE {rows[-1]['seat_mae']} | brier "
              f"{rows[-1]['threshold_brier']} | P(bloc61) "
              f"{rows[-1]['p_bloc_61']:.1%} (actual {nb_actual})")

    out = pd.DataFrame(rows).set_index("cycle")
    out.to_csv(PROCESSED_DIR / "model_validation_bayes.csv")
    pd.DataFrame(list_rows).to_csv(
        PROCESSED_DIR / "model_validation_bayes_lists.csv", index=False)
    pooled = np.concatenate(covered_all)
    p61, hap = out["p_bloc_61"], out["bloc_61_happened"].astype(float)
    print("\n== BAYESIAN MODEL, eight-cycle grade ==")
    print(out.to_string())
    print(f"\npooled 90% coverage: {pooled.mean():.1%} "
          f"({int(pooled.sum())}/{len(pooled)})")
    print(f"bloc Brier {((p61 - hap) ** 2).mean():.3f} "
          f"(mean stated {p61.mean():.1%}, realized {hap.mean():.1%})")
    print(f"pooled seat MAE {out['seat_mae'].mean():.2f}")

    try:
        simple = pd.read_csv(PROCESSED_DIR / "model_validation.csv",
                             index_col=0)
        both = pd.DataFrame({
            "mae_bayes": out["seat_mae"], "mae_simple": simple["seat_mae"],
            "cov_bayes": out["coverage_90"], "cov_simple": simple["coverage_90"],
            "brier_bayes": out["threshold_brier"],
            "brier_simple": simple["threshold_brier"],
        })
        print("\n== HEAD-TO-HEAD vs simple pipeline ==")
        print(both.to_string())
        print(f"\npooled MAE: bayes {both['mae_bayes'].mean():.2f} vs "
              f"simple {both['mae_simple'].mean():.2f} | "
              f"threshold Brier: bayes {both['brier_bayes'].mean():.3f} vs "
              f"simple {both['brier_simple'].mean():.3f}")
    except FileNotFoundError:
        pass
    if abl_rows:
        adf = pd.DataFrame(abl_rows)
        adf.to_csv(PROCESSED_DIR / "model_validation_ablation.csv", index=False)
        print("\nLayer ablation (pooled over cycles):")
        print(adf.groupby("ablation").agg(mae=("seat_mae", "mean"), mae_med=("seat_mae_median", "mean"),
                                          coverage=("coverage_90", "mean"), brier=("threshold_brier", "mean"))
              .loc[[t for t, _ in ABLATIONS]].round(3).to_string())
    if width_rows:
        wdf = pd.DataFrame(width_rows)
        wdf.to_csv(PROCESSED_DIR / "model_validation_width.csv", index=False)
        pooled = wdf.groupby("width").agg(coverage=("coverage_90", "mean"), mae=("seat_mae", "mean"),
                                          brier=("threshold_brier", "mean"), iscore=("interval_score", "mean"))
        print("\nInterval-width calibration (pooled over cycles):")
        print(pooled.round(3).to_string())
        loo = []
        for cyc in wdf["cycle"].unique():
            other = wdf[wdf["cycle"] != cyc].groupby("width")["interval_score"].mean()
            loo.append((cyc, float(other.idxmin())))
        print("LOO width choices:", loo)
        print(f"pooled choice (min interval score): {pooled['iscore'].idxmin()}")
    print("\nwrote model_validation_bayes.csv")


if __name__ == "__main__":
    main()
