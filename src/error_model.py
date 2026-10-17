"""Hierarchical Bayesian model of final-poll error (dossier s.61).

The projection's election-day error stack (bloc swing, haredi family shock,
per-list residual) has been a set of moment estimates from eight cycles,
plugged in as fixed values (error_decomposition.decompose). This module
replaces them with ONE joint model of the vote-share error record, in the
spirit of Shirani-Mehr, Rothschild, Goel & Gelman (2018, JASA) and
Heidemanns, Gelman & Morris (2020), fitted in PyMC:

  e_{c,l} = beta_c s_{c,l} + phi^h_c f^h_{c,l} + phi^a_c f^a_{c,l}
            + kappa_c g_{c,l} + eps_{c,l}

  e        final-poll error of list l in cycle c, polled - actual, in
           u = 120 x vote share (error_decomposition._vote_frames: the lists
           that RAN, reused unchanged)
  s        bloc loading exactly as the projection applies the swing:
           w / W_NB on the Netanyahu bloc, -w / W_rest elsewhere (w = polled
           share clipped at 0.1, as decompose()); zero-sum. The bloc is the
           harness's (registry + VAL_BLOC_OVERRIDES on the DECOMP-expanded
           components), i.e. the bloc the projection moves and P(NB>=61)
           counts.
  beta_c   ~ N(mu_beta, sigma_beta)       the election-level bloc error
  f^h, f^a family loadings as the projection applies family shocks:
           w / W_family on the family, -w / W_others elsewhere (zero-sum)
  phi^h_c  ~ N(mu_h, sigma_h)              haredi family effect
  phi^a_c  ~ N(mu_a, sigma_a)              Arab family effect: a NUISANCE.
           It is estimated so the Arab lists' correlated error does not leak
           into beta (they load on the non-NB side) or into the residual
           scale; it is NOT drawn at projection, where the graded turnout
           term (s.43) carries the Arab family.
  g        w / W_all: a common proportional error (the modelled lists are
           over-polled together by the unmodelled micro-lists' share, about
           +1.4 u per cycle). The projection renormalises shares, so it is
           invisible there; kappa_c ~ N(mu_k, sigma_k) is a nuisance.
  eps      ~ Student-t(nu, 0, sigma_l),
           log sigma_l = a + b log(size_l / 8) + gamma new_l
           size = polled u floored at 0.5 (the record's smallest); new = a
           first-cycle list (first_cycle_mask).

Units: u (shares x 120), the space in which the projection adds every
shock; the size dependence is modelled by b instead of being imposed by a
logit transform (see s.61.1).

At projection each simulation takes one joint posterior draw of the
hyperparameters and draws a NEW election's beta, phi^h and eps from the
posterior predictive (bayes_model.ERROR_MODEL "hierarchical";
validate_bayes layer error_model). Leave-one-cycle-out: the harness grades
cycle c with the fit that leaves c out (8 fits + the full-sample fit used
by production), cached as netcdf under data/processed/error_model/.

    python src/error_model.py fit        # 9 fits (cached) + sampler gates
    python src/error_model.py prior      # prior predictive checks
    python src/error_model.py summary    # posterior summaries, predictive sds
    python src/error_model.py ppc        # coverage of each cycle's errors
    python src/error_model.py loo        # LOO-PSIS vs nested variants
"""
from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

from scrape_polls import PROCESSED_DIR

ERROR_MODEL_DIR = PROCESSED_DIR / "error_model"
SPEC_VERSION = "s61-v1"
ORDER = ["2009", "2013", "2015", "2019a", "2019s", "2020", "2021", "2022"]
SIZE_REF = 8.0      # u: `a` is the log residual scale of an 8-seat list
SIZE_FLOOR = 0.5    # u: the record's smallest polled size; projection floors here
PRIORS = {
    "mu_beta": ("normal", 0.0, 3.0), "sigma_beta": ("halfnormal", 5.0),
    "mu_h": ("normal", 0.0, 3.0), "sigma_h": ("halfnormal", 3.0),
    "mu_a": ("normal", 0.0, 3.0), "sigma_a": ("halfnormal", 3.0),
    "mu_k": ("normal", 0.0, 3.0), "sigma_k": ("halfnormal", 3.0),
    "a": ("normal", 0.0, 1.0), "b": ("normal", 0.5, 0.5), "gamma": ("normal", 0.0, 0.5),
    "nu_minus_2": ("gamma", 2.0, 0.1),
}
SAMPLER = {"draws": 1000, "tune": 1500, "chains": 4, "target_accept": 0.95,
           "random_seed": 20261027}
RETRY = {"tune": 3000, "target_accept": 0.99}     # one retry when a gate fails
GATES = {"divergences": 0, "rhat_max": 1.01, "ess_min": 400}
VARIANTS = ("full", "no_slope", "gaussian", "no_new")
# Lineage facts the DECOMP maps do not carry, used ONLY for the first-cycle
# covariate (never for blocs): Yamina (Sept 2019) = New Right + URWP; the
# Joint List (Sept 2019) = Hadash-Ta'al + Balad + Ra'am reunited; RZP
# (2021) = Tkuma (National Union) + Otzma + Noam; The Democrats (2026) =
# Labor + Meretz (registry note). The record's earlier mergers (Zionist
# Union, Democratic Union, Labor-Gesher-Meretz) are expanded by DECOMP.
LINEAGE = {"2019s": {"yamina": "jewish_home+national_union+new_right",
                     "joint_list": "balad+hadash_taal+raam"},
           "2021": {"rzp": "national_union+noam+otzma"},
           "2026": {"democrats": "labor+meretz"}}
HYPER = ("mu_beta", "sigma_beta", "mu_h", "sigma_h", "a", "b", "gamma", "nu")


# ---------------------------------------------------------------------------
# identities: DECOMP expansion, bloc, family, first-cycle status
# ---------------------------------------------------------------------------
def _decomp(cycle: str, lineage: bool = False) -> dict:
    """The harness's identity map for the cycle (DECOMP + ballot-fidelity
    DECOMP_FIDELITY, the shipped harness), plus LINEAGE when asked."""
    from validate_bayes import DECOMP, DECOMP_FIDELITY
    m = dict(DECOMP.get(cycle, {}))
    m.update(DECOMP_FIDELITY.get(cycle, {}))
    if lineage:
        m.update(LINEAGE.get(cycle, {}))
    return m


def expand(components, cycle: str, lineage: bool = False) -> set:
    m = _decomp(cycle, lineage)
    comps = components.split("+") if isinstance(components, str) else components
    return {p for c in comps for p in m.get(c, c).split("+")}


@lru_cache(maxsize=16)
def ballot_ids_before(cycle: str) -> frozenset:
    """Component ids on any earlier ballot (results.csv: lists that won
    seats; data/ran_vote_shares.csv: lists that ran and failed), raw and
    DECOMP/LINEAGE-expanded. 2009 has no earlier cycle in the record: every
    list it polled had run in 2006 under the same or a predecessor name, so
    nothing in 2009 is first-cycle (empty-set sentinel handled by the caller)."""
    res = pd.read_csv(PROCESSED_DIR / "results.csv", dtype={"cycle": str})
    ran = pd.read_csv(PROCESSED_DIR.parent / "ran_vote_shares.csv", dtype={"cycle": str})
    allc = ORDER + ["2026"]
    upto = allc[:allc.index(cycle)] if cycle in allc else ORDER
    ids = set()
    for c in upto:
        for pid in list(res[res["cycle"] == c]["party_id"]) + list(ran[ran["cycle"] == c]["party_id"]):
            ids |= set(pid.split("+")) | expand(pid, c, lineage=True)
    return frozenset(ids)


def first_cycle_mask(components, cycle: str) -> np.ndarray:
    """True for a list none of whose (lineage-expanded) components was on
    an earlier ballot. The same rule for the record, the harness windows and
    production 2026."""
    cycle = str(cycle)
    if cycle == ORDER[0]:
        return np.zeros(len(components), bool)
    old = ballot_ids_before(cycle)
    return np.array([not (expand(c, cycle, lineage=True) & old) for c in components], bool)


def bloc_of(components, cycle: str) -> str:
    """The harness's bloc: registry + VAL_BLOC_OVERRIDES on the DECOMP-
    expanded components, 'other' when they disagree (project_cycle)."""
    from normalize import load_party_registry
    from validate_model import VAL_BLOC_OVERRIDES
    reg = load_party_registry()
    bmap = dict(zip(reg["party_id"], reg["bloc"]))
    bmap.update(VAL_BLOC_OVERRIDES.get(cycle) or {})
    bs = {bmap.get(c, "other") for c in expand(components, cycle)}
    return bs.pop() if len(bs) == 1 else "other"


def family_of(components, cycle: str) -> str:
    from bias_audit import FAMILY_OF
    fs = [FAMILY_OF.get(c, "other") for c in expand(components, cycle)]
    return max(fs, key=fs.count)


def zero_sum(w: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """The projection's zero-sum allocation of a unit total: +w/W on the
    mask, -w/W on the rest (0 when either side is empty)."""
    w, mask = np.asarray(w, float), np.asarray(mask, bool)
    if not mask.any() or mask.all():
        return np.zeros(len(w))
    return np.where(mask, w / w[mask].sum(), -w / w[~mask].sum())


# ---------------------------------------------------------------------------
# the record
# ---------------------------------------------------------------------------
@lru_cache(maxsize=16)
def record(exclude_cycle: str | None = None) -> pd.DataFrame:
    """decompose_vote's record (lists that ran, u = 120 x share) with the
    model's loadings and covariates; the graded cycle left out."""
    from error_decomposition import _vote_frames
    rows = []
    for cycle, f in _vote_frames().items():
        cycle = str(cycle)
        if cycle == exclude_cycle:
            continue
        g = f.copy().reset_index(drop=True)
        g["cycle"] = cycle
        g["bloc"] = [bloc_of(c, cycle) for c in g["components"]]
        g["nb"] = g["bloc"] == "netanyahu_bloc"
        g["fam"] = [family_of(c, cycle) for c in g["components"]]
        w = g["polled"].clip(lower=0.1).values
        g["l_bloc"] = zero_sum(w, g["nb"].values)
        g["l_haredi"] = zero_sum(w, (g["fam"] == "haredi").values)
        g["l_arab"] = zero_sum(w, (g["fam"] == "arab").values)
        g["l_common"] = w / w.sum()
        g["size"] = g["polled"].clip(lower=SIZE_FLOOR)
        g["new"] = first_cycle_mask(list(g["components"]), cycle)
        rows.append(g)
    cols = ["cycle", "components", "bloc", "nb", "fam", "polled", "actual_u", "actual",
            "error", "l_bloc", "l_haredi", "l_arab", "l_common", "size", "new"]
    return pd.concat(rows, ignore_index=True)[cols]


def _key(rec: pd.DataFrame, variant: str) -> str:
    blob = json.dumps({"spec": SPEC_VERSION, "priors": PRIORS, "sampler": SAMPLER,
                       "variant": variant,
                       "rec": rec.round(6).astype(str).values.tolist()}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------
def _prior(pm, name, dims=None):
    kind, *p = PRIORS[name]
    if kind == "normal":
        return pm.Normal(name, p[0], p[1], dims=dims)
    if kind == "halfnormal":
        return pm.HalfNormal(name, p[0], dims=dims)
    if kind == "gamma":
        return pm.Gamma(name, alpha=p[0], beta=p[1], dims=dims)
    raise ValueError(kind)


def build_model(rec: pd.DataFrame, variant: str = "full"):
    """The PyMC model on a record (non-centred cycle effects). variant:
    'full' | 'no_slope' (b = 0) | 'gaussian' (eps Normal) | 'no_new' (gamma = 0)."""
    import pymc as pm
    if variant not in VARIANTS:
        raise ValueError(f"variant {variant!r}")
    ci, cycles = pd.factorize(rec["cycle"])
    coords = {"cycle": list(cycles), "obs": np.arange(len(rec))}
    ls = np.log(rec["size"].values / SIZE_REF)
    new = rec["new"].values.astype(float)
    with pm.Model(coords=coords) as m:
        eff = {}
        for k in ("beta", "h", "a", "k"):
            mu = _prior(pm, f"mu_{k}" if k != "beta" else "mu_beta")
            sd = _prior(pm, f"sigma_{k}" if k != "beta" else "sigma_beta")
            z = pm.Normal(f"z_{k}", 0.0, 1.0, dims="cycle")
            nm = {"beta": "beta", "h": "phi_h", "a": "phi_a", "k": "kappa"}[k]
            eff[k] = pm.Deterministic(nm, mu + sd * z, dims="cycle")
        a = _prior(pm, "a")
        b = 0.0 if variant == "no_slope" else _prior(pm, "b")
        gamma = 0.0 if variant == "no_new" else _prior(pm, "gamma")
        sigma = pm.math.exp(a + b * ls + gamma * new)
        mu_e = (eff["beta"][ci] * rec["l_bloc"].values + eff["h"][ci] * rec["l_haredi"].values
                + eff["a"][ci] * rec["l_arab"].values + eff["k"][ci] * rec["l_common"].values)
        if variant == "gaussian":
            pm.Normal("e", mu=mu_e, sigma=sigma, observed=rec["error"].values, dims="obs")
        else:
            nu = pm.Deterministic("nu", _prior(pm, "nu_minus_2") + 2.0)
            pm.StudentT("e", nu=nu, mu=mu_e, sigma=sigma, observed=rec["error"].values, dims="obs")
    return m


def diagnostics(idata) -> dict:
    import arviz as az
    post = idata.posterior
    keep = [v for v in post.data_vars if not v.startswith("z_")]   # z_* are the raw non-centred draws
    rhat = az.rhat(post[keep])
    ess = az.ess(post[keep], method="bulk")
    return {"divergences": int(idata.sample_stats["diverging"].sum()),
            "rhat_max": float(max(float(rhat[v].max()) for v in rhat.data_vars)),
            "ess_min": float(min(float(ess[v].min()) for v in ess.data_vars))}


def gate_failures(diag: dict) -> list:
    bad = []
    if diag["divergences"] > GATES["divergences"]:
        bad.append(f"{diag['divergences']} divergences")
    if diag["rhat_max"] > GATES["rhat_max"]:
        bad.append(f"r-hat {diag['rhat_max']:.3f}")
    if diag["ess_min"] < GATES["ess_min"]:
        bad.append(f"ESS {diag['ess_min']:.0f}")
    return bad


def sample(rec: pd.DataFrame, variant: str = "full", draws=None, tune=None, chains=None,
           target_accept=None, random_seed=None, cores=None, log_likelihood=True):
    import pymc as pm
    s = dict(SAMPLER)
    for k, v in (("draws", draws), ("tune", tune), ("chains", chains),
                 ("target_accept", target_accept), ("random_seed", random_seed)):
        if v is not None:
            s[k] = v
    with build_model(rec, variant):
        return pm.sample(draws=s["draws"], tune=s["tune"], chains=s["chains"],
                         cores=cores or s["chains"], target_accept=s["target_accept"],
                         random_seed=s["random_seed"], progressbar=False,
                         idata_kwargs={"log_likelihood": log_likelihood})


def fit(exclude_cycle: str | None = None, variant: str = "full", refit: bool = False,
        verbose: bool = True):
    """The cached posterior of the model on the record without
    `exclude_cycle` (None = all eight cycles, production). A fit that fails
    a gate is retried once (RETRY); its attrs carry the gate result."""
    import arviz as az
    rec = record(exclude_cycle)
    key = _key(rec, variant)
    path = ERROR_MODEL_DIR / f"{variant}_{exclude_cycle or 'all'}_{key}.nc"
    if path.exists() and not refit:
        return az.from_netcdf(path)
    idata = sample(rec, variant)
    diag, retried = diagnostics(idata), False
    if gate_failures(diag):
        idata = sample(rec, variant, **RETRY)
        diag, retried = diagnostics(idata), True
    idata.posterior.attrs.update({"spec": SPEC_VERSION, "key": key, "variant": variant,
                                  "exclude_cycle": exclude_cycle or "", "n_obs": int(len(rec)),
                                  "retried": int(retried), "gates": json.dumps(diag),
                                  "gate_failures": "; ".join(gate_failures(diag))})
    ERROR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".nc.tmp")
    az.to_netcdf(idata, tmp)
    tmp.replace(path)
    if verbose:
        print(f"[error_model {variant} -{exclude_cycle or 'none'}] n {len(rec)} {diag}"
              f"{' (retried)' if retried else ''} -> {path.name}")
    return idata


@lru_cache(maxsize=32)
def hyper(exclude_cycle: str | None = None, variant: str = "full") -> dict:
    """Flat joint posterior draws of the hyperparameters the projection
    needs (HYPER), aligned by draw."""
    post = fit(exclude_cycle, variant, verbose=False).posterior
    out = {}
    for k in HYPER:
        if k in post:
            out[k] = post[k].values.reshape(-1).astype(float)
    n = len(out["mu_beta"])
    out.setdefault("b", np.zeros(n))
    out.setdefault("gamma", np.zeros(n))
    out.setdefault("nu", np.full(n, np.inf))
    return out


# ---------------------------------------------------------------------------
# posterior predictive of a NEW election (the projection's draws)
# ---------------------------------------------------------------------------
def draw_index(hy: dict, n: int, rng) -> np.ndarray:
    """One joint posterior draw per simulation (with replacement)."""
    return rng.integers(len(hy["a"]), size=n)


def resid_scale(hy: dict, idx, size_u, new) -> np.ndarray:
    """(n, k) Student-t scale sigma_l per simulation (row) and list (col)."""
    ls = np.log(np.clip(np.asarray(size_u, float), SIZE_FLOOR, None) / SIZE_REF)
    new = np.asarray(new, float)
    return np.exp(hy["a"][idx][:, None] + hy["b"][idx][:, None] * ls[None, :]
                  + hy["gamma"][idx][:, None] * new[None, :])


def resid_draws(hy: dict, idx, size_u, new, rng) -> np.ndarray:
    """New-election residual errors eps (u), one row per simulation."""
    sc = resid_scale(hy, idx, size_u, new)
    nu = hy["nu"][idx]
    if np.isinf(nu).all():
        return sc * rng.standard_normal(sc.shape)
    return sc * rng.standard_t(nu[:, None], size=sc.shape)


def bloc_draws(hy: dict, idx, z) -> np.ndarray:
    """New-election bloc error beta (u, polled - actual) given N(0,1) z."""
    return hy["mu_beta"][idx] + hy["sigma_beta"][idx] * z


def haredi_draws(hy: dict, idx, z) -> np.ndarray:
    return hy["mu_h"][idx] + hy["sigma_h"][idx] * z


def predictive_summary(hy: dict, sizes=(4.0, 25.0), n: int = 400_000, seed: int = 1) -> dict:
    """Posterior-predictive sds of a new election's bloc error, haredi
    family effect and residual at the given sizes (established and
    first-cycle), by simulation; plus 90% half-widths / 1.645 (robust sd)."""
    rng = np.random.default_rng(seed)
    idx = draw_index(hy, n, rng)
    out = {}
    for nm, f in (("bloc", bloc_draws), ("haredi", haredi_draws)):
        x = f(hy, idx, rng.standard_normal(n))
        out[nm] = {"mean": float(x.mean()), "sd": float(x.std()),
                   "sd90": float((np.percentile(x, 95) - np.percentile(x, 5)) / 2 / 1.645)}
    for s in sizes:
        for nw in (0, 1):
            e = resid_draws(hy, idx, np.array([s]), np.array([nw]), rng)[:, 0]
            out[f"resid_{s:g}{'_new' if nw else ''}"] = {
                "sd": float(e.std()),
                "sd90": float((np.percentile(e, 95) - np.percentile(e, 5)) / 2 / 1.645)}
    return out


# ---------------------------------------------------------------------------
# harness / production entry points
# ---------------------------------------------------------------------------
def harness_params(cycle: str) -> dict:
    """What validate_bayes.project_cycle's hierarchical branch reads for a
    window of `cycle`: the leave-`cycle`-out hyperparameter draws."""
    return {"hyper": hyper(str(cycle)), "cycle": str(cycle)}


def production_hyper() -> dict:
    return hyper(None)


# ---------------------------------------------------------------------------
# diagnostics run from the CLI (s.61)
# ---------------------------------------------------------------------------
def prior_predictive(n: int = 2000, seed: int = 61) -> dict:
    """Prior predictive checks on the full record's design (no outcome
    used): simulated bloc-total sd across cycles, |e| quantiles by size,
    and the share of implausible errors (|e| > 20 u)."""
    import pymc as pm
    rec = record(None)
    with build_model(rec, "full"):
        pp = pm.sample_prior_predictive(n, random_seed=seed)
    e = pp.prior_predictive["e"].values.reshape(n, -1)
    beta = pp.prior["beta"].values.reshape(n, -1)
    sig_b = pp.prior["sigma_beta"].values.reshape(-1)
    nu = pp.prior["nu"].values.reshape(-1)
    sz = rec["size"].values
    groups = {"<4 u": sz < 4, "4-12 u": (sz >= 4) & (sz <= 12), ">12 u": sz > 12}
    out = {"bloc_sd_across_cycles": np.percentile(beta.std(axis=1, ddof=1), [5, 50, 95]).tolist(),
           "sigma_beta": np.percentile(sig_b, [5, 50, 95]).tolist(),
           "nu": np.percentile(nu, [5, 50, 95]).tolist(),
           "share_abs_gt_20u": float((np.abs(e) > 20).mean()),
           "share_abs_gt_10u": float((np.abs(e) > 10).mean())}
    for g, m in groups.items():
        out[f"abs_e {g}"] = np.percentile(np.abs(e[:, m]), [50, 90, 99]).tolist()
        out[f"abs_e {g} observed"] = np.percentile(np.abs(rec["error"].values[m]), [50, 90, 99]).tolist()
    nbtot = rec.assign(x=rec["error"] * rec["nb"]).groupby("cycle")["x"].sum()
    out["observed_nb_total_sd"] = float(nbtot.std(ddof=1))
    return out


def posterior_summary(exclude_cycle=None, variant="full") -> pd.DataFrame:
    import arviz as az
    post = fit(exclude_cycle, variant, verbose=False).posterior
    keep = [v for v in ["mu_beta", "sigma_beta", "mu_h", "sigma_h", "mu_a", "sigma_a",
                        "mu_k", "sigma_k", "a", "b", "gamma", "nu", "beta", "phi_h"] if v in post]
    return az.summary(post[keep], hdi_prob=0.9, round_to=3)


def _new_cycle_predictive(hy_post, rows: pd.DataFrame, n: int, rng) -> np.ndarray:
    """Replicated errors of a NEW cycle with `rows`' design (LOO check)."""
    idx = rng.integers(len(hy_post["mu_beta"]), size=n)
    z = rng.standard_normal((n, 4))
    beta = hy_post["mu_beta"][idx] + hy_post["sigma_beta"][idx] * z[:, 0]
    ph = hy_post["mu_h"][idx] + hy_post["sigma_h"][idx] * z[:, 1]
    pa = hy_post["mu_a"][idx] + hy_post["sigma_a"][idx] * z[:, 2]
    kp = hy_post["mu_k"][idx] + hy_post["sigma_k"][idx] * z[:, 3]
    mu = (beta[:, None] * rows["l_bloc"].values + ph[:, None] * rows["l_haredi"].values
          + pa[:, None] * rows["l_arab"].values + kp[:, None] * rows["l_common"].values)
    return mu + resid_draws(hy_post, idx, rows["size"].values, rows["new"].values, rng)


def ppc(n: int = 4000, seed: int = 62) -> pd.DataFrame:
    """Per cycle: 90% coverage of its observed errors by (i) the in-sample
    posterior predictive (the full fit, the cycle's own effects) and (ii)
    the leave-the-cycle-out NEW-election predictive; and the PIT of the
    cycle's NB-side total error under (ii)."""
    rng = np.random.default_rng(seed)
    full = fit(None, verbose=False).posterior
    rec = record(None)
    ci = {c: i for i, c in enumerate(pd.factorize(rec["cycle"])[1])}
    flat = {k: full[k].values.reshape(-1, *full[k].shape[2:]) for k in
            ("beta", "phi_h", "phi_a", "kappa", "a", "b", "gamma", "nu")}
    rows = []
    for c in ORDER:
        r = rec[rec["cycle"] == c]
        j = rng.integers(flat["a"].shape[0], size=n)
        k = ci[c]
        mu = (flat["beta"][j, k][:, None] * r["l_bloc"].values
              + flat["phi_h"][j, k][:, None] * r["l_haredi"].values
              + flat["phi_a"][j, k][:, None] * r["l_arab"].values
              + flat["kappa"][j, k][:, None] * r["l_common"].values)
        rep = mu + resid_draws(flat, j, r["size"].values, r["new"].values, rng)
        lo, hi = np.percentile(rep, 5, axis=0), np.percentile(rep, 95, axis=0)
        cov_in = float(((r["error"].values >= lo) & (r["error"].values <= hi)).mean())
        po = fit(c, verbose=False).posterior
        hp = {k2: po[k2].values.reshape(-1) for k2 in ("mu_beta", "sigma_beta", "mu_h", "sigma_h",
                                                       "mu_a", "sigma_a", "mu_k", "sigma_k",
                                                       "a", "b", "gamma", "nu")}
        rep2 = _new_cycle_predictive(hp, r, n, rng)
        lo2, hi2 = np.percentile(rep2, 5, axis=0), np.percentile(rep2, 95, axis=0)
        cov_loo = float(((r["error"].values >= lo2) & (r["error"].values <= hi2)).mean())
        nbt = rep2[:, r["nb"].values].sum(axis=1)
        obs_nb = float(r.loc[r["nb"], "error"].sum())
        rows.append({"cycle": c, "n": len(r), "cov90_in_sample": cov_in, "cov90_loo_new": cov_loo,
                     "nb_total_err": obs_nb, "nb_total_pit_loo": float((nbt < obs_nb).mean()),
                     "max_abs_z_loo": float(np.max(np.abs((r["error"].values - np.median(rep2, axis=0))
                                                          / ((hi2 - lo2) / 3.29))))})
    return pd.DataFrame(rows)


def loo_compare(variants=VARIANTS) -> pd.DataFrame:
    """LOO-PSIS (pointwise) of the error model against its nested variants
    on the full record (arviz.loo / arviz.compare)."""
    import arviz as az
    ids = {v: fit(None, v, verbose=False) for v in variants}
    cmp = az.compare(ids, ic="loo")
    khat = {v: float((az.loo(i, pointwise=True).pareto_k > 0.7).sum()) for v, i in ids.items()}
    cmp["n_khat_gt_0.7"] = [khat[v] for v in cmp.index]
    return cmp


def _cli(argv) -> None:
    cmd = argv[1] if len(argv) > 1 else "fit"
    pd.set_option("display.width", 200)
    if cmd == "fit":
        rows = []
        for ex in [None] + ORDER:
            idata = fit(ex)
            at = idata.posterior.attrs
            rows.append({"exclude": ex or "none", "n_obs": at.get("n_obs"), **json.loads(at["gates"]),
                         "retried": at.get("retried"), "fails": at.get("gate_failures") or "-"})
        for v in VARIANTS[1:]:
            idata = fit(None, v)
            at = idata.posterior.attrs
            rows.append({"exclude": f"none ({v})", "n_obs": at.get("n_obs"), **json.loads(at["gates"]),
                         "retried": at.get("retried"), "fails": at.get("gate_failures") or "-"})
        print(pd.DataFrame(rows).to_string(index=False))
    elif cmd == "prior":
        for k, v in prior_predictive().items():
            print(f"  {k}: {np.round(v, 3).tolist() if isinstance(v, list) else round(v, 4)}")
    elif cmd == "summary":
        print(posterior_summary().to_string())
        for ex in [None] + ORDER:
            ps = predictive_summary(hyper(ex))
            print(ex or "all", json.dumps({k: {kk: round(vv, 3) for kk, vv in v.items()}
                                           for k, v in ps.items()}))
    elif cmd == "ppc":
        print(ppc().round(3).to_string(index=False))
    elif cmd == "loo":
        print(loo_compare().round(3).to_string())
    elif cmd == "record":
        print(record(None).round(3).to_string())
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    _cli(sys.argv)
