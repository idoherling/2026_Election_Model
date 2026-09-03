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

from bayes_model import SEED, T_DF, WITHDRAWN_WEEKS, fit, prepare_data
from error_decomposition import decompose
from bias_audit import FAMILY_OF
from normalize import load_party_registry
from scrape_polls import ELECTION_DAY, PROCESSED_DIR
from simulate import THRESHOLD, dhondt
from validate_model import (
    CYCLE_THRESHOLD, ORDER, PAST_PAIRS, VAL_BLOC_OVERRIDES,
)

warnings.filterwarnings("ignore")

N_PROJ = 4000
WIDTH_GRID = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1]
ABLATIONS = [("full", {}), ("no_resid", {"resid": False}), ("no_swing", {"swing": False}),
             ("no_family", {"family": False}), ("no_anchors", {"anchors": False}),
             ("no_gevalt", {"gevalt": False}), ("no_loyal", {"loyal": False}),
             ("latent_only", {k: False for k in ["resid", "swing", "family", "anchors", "gevalt", "loyal"]}),
             ("no_likud_anchor", {"anchor_likud": False}), ("no_leader_anchor", {"anchor_leader": False}),
             ("half_anchors", {"anchor_scale": 0.5})]

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


ALL_LAYERS = {"resid": True, "swing": True, "family": True, "anchors": True,
              "gevalt": True, "loyal": True,
              "anchor_likud": True, "anchor_leader": True, "anchor_scale": 1.0,
              "shock_scale": 1.0}


def project_cycle(data, idata, eday, threshold, pairs, params,
                  bloc_overrides, rng, resid_scale=1.0, layers=None,
                  weeks_override=None):
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

    gone = data["last_obs_day"] < -7 * WITHDRAWN_WEEKS
    if gone.any():
        shares[:, np.nonzero(gone)[0]] = 0.0
        shares /= shares.sum(axis=1, keepdims=True)
    base0 = shares.mean(axis=0)
    sd_list = (params["resid_base"]
               + params["resid_slope"] * base0 * 120) / 120.0 * resid_scale
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
    shares /= shares.sum(axis=1, keepdims=True)

    comp_of = {c: i for i, cs in enumerate(data["components"])
               for c in cs.split("+")}
    pair_idx = [(comp_of[a], comp_of[b]) for a, b in pairs
                if a in comp_of and b in comp_of and comp_of[a] != comp_of[b]]

    seats = np.zeros((N_PROJ, shares.shape[1]), dtype=int)
    for i in range(N_PROJ):
        sh = shares[i]
        passed = sh >= threshold
        if not passed.any():
            continue
        votes = np.where(passed, sh, 0.0)
        fvotes, fmembers, used = [], [], set()
        for a, b in pair_idx:
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
        for tag, flags in ABLATIONS:
            sa, _, ba, _ = project_cycle(
                data, idata, eday, CYCLE_THRESHOLD.get(cycle, THRESHOLD),
                PAST_PAIRS[cycle], params, VAL_BLOC_OVERRIDES.get(cycle),
                np.random.default_rng(SEED + 11), layers=flags)
            act_a = (ba >= 0.005) | (actual > 0)
            lo_a, hi_a = np.percentile(sa, 5, axis=0), np.percentile(sa, 95, axis=0)
            ppa = (sa >= 1).mean(axis=0)
            abl_rows.append({"cycle": cycle, "ablation": tag,
                             "seat_mae": float(np.abs(sa.mean(axis=0) - actual)[act_a].mean()),
                             "seat_mae_median": float(np.abs(np.median(sa, axis=0) - actual)[act_a].mean()),
                             "coverage_90": float(((actual >= lo_a) & (actual <= hi_a))[act_a].mean()),
                             "threshold_brier": float(np.mean((ppa[act_a] - (actual[act_a] > 0)) ** 2))})

        # Interval-width calibration curve (audit improvement #2): the same
        # posterior re-projected under a grid of residual-width factors.
        for w in WIDTH_GRID:
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
