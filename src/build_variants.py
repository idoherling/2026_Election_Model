"""The 2026 forecast of every model variant, for the site's model explorer.

    python src/build_variants.py [--only ID[,ID]] [--vectors 50] [--work DIR]

Each available variant of src/model_variants.py goes through the same chain
as the official forecast, with its flags applied (model_variants.
variant_flags, restored afterwards):

  1. registration_scenarios.main(): bayes_model.project on the production
     posterior (data/processed/m3_idata.nc, read only) at the production
     seed, mixed over the registration events;
  2. official_forecast.main(): the official central count (Bader-Ofer on the
     mixture's median shares), the 90% intervals and pass probabilities;
  3. the formation tree (government_formation.simulate_formation, the loop
     of government_formation.main) on those seat draws, with FEWER
     behavioural parameter vectors than production for speed (--vectors,
     default 50 of production's 200; the first 50 of production's own
     parameter stream, so the official variant's formation is a subset of
     the published one). Every variant runs on the same vectors and seeds,
     so its difference from the official run is paired; groups_paired /
     pm_paired put it on the published scale (published official value +
     paired difference), which is what the site shows.

The official variant applies no flag at all: it is production as
committed, whatever the code's flags are.

Steps 1-2 run their own code with PROCESSED_DIR pointed at a per-variant
scratch directory (--work, default a temporary directory), so nothing in
data/processed is written except this script's output. The simple
benchmark ("simple" kind) runs simulate.build_inputs + simulate_core on the
polls fielded since filing day, then the same central count and formation.

The official variant must reproduce the published headline: its mixture
bloc probabilities and central seats equal data/processed/mixture_blocs.csv
and official_forecast.csv (same code, posterior and seed), and its formation
groups sit within Monte Carlo noise of government_groups.csv. The script
checks this and exits 1 when it fails.

Output: data/processed/model_variants.json
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "model_variants.json"
FORMATION_VECTORS = 50          # production: 200 (government_formation.main)
PRODUCTION_VECTORS = 200
FILING_DAY = pd.Timestamp("2026-09-09")   # the ballot is fixed from here (dossier s.31)
GROUPS = ["netanyahu", "change", "unity", "repeat", "netanyahu_in_office"]
# chain inputs read from PROCESSED_DIR by registration_scenarios / official_forecast
CHAIN_INPUTS = ["arab_scenarios.csv", "fit_summary.json", "bayes_forecast_2026.csv"]
# the simple pipeline's labels -> the production chain's list names
SIMPLE_RENAME = {"Together": "Bennett 2026 + Yesh Atid", "Joint List": "Balad + Hadash-Ta'al"}
# the simple pipeline's component ids for the signed pairs (its Joint List
# column is "joint_list"; simulate.SURPLUS_PAIRS names the Balad component)
SIMPLE_PAIR_IDS = {"balad": "joint_list"}
SIMPLE_COMPONENTS = {"joint_list": "balad+hadash_taal"}


class CheckFailed(RuntimeError):
    pass


# --- formation --------------------------------------------------------------

def formation_frame(draws: pd.DataFrame) -> pd.DataFrame:
    """government_formation.load_draws' column fill, for any seat draws."""
    import government_formation as gf
    d = draws.copy()
    for col in gf.NB_CORE + gf.CENTRE + [gf.JOINT_LIST, gf.RAAM, gf.AMCHA]:
        if col not in d.columns:
            d[col] = 0
    return d


def formation_summary(draws: pd.DataFrame, M: int = FORMATION_VECTORS) -> dict:
    """The parameter-vector loop of government_formation.main, M vectors:
    who leads (groups) and P(next PM), mean and 5-95% over the vectors.
    Reads the module's flags at call time (POST_DEADLOCK_STAGE,
    STAGE_RESOLUTION, BEHAVIOR, ...)."""
    import government_formation as gf
    draws = formation_frame(draws)
    stage, resolution = gf.POST_DEADLOCK_STAGE, gf.STAGE_RESOLUTION
    by_record = stage and resolution == "record"
    by_mix = stage and resolution == "mix"
    prng = np.random.default_rng(gf.SEED + 7)
    r_stage = gf.stage_draws(M, stage)
    s_stage = gf.resolution_draws(M, by_record)
    w_stage = [None] * M
    if by_mix:
        import validate_formation as vf
        w_stage, _ = vf.mix_posterior_2026(M)
    pm_names = gf.PM_NAMES[:-1] + [gf.PM_OTHER_UNITY, gf.PM_OTHER, "Netanyahu",
                                   "none (repeat election)"]
    gidx = np.array([["netanyahu", "change", "unity", "repeat"].index(gf.OUTCOME_GROUP[o])
                     for o in range(len(gf.OUTCOMES))])
    grp = np.zeros((M, len(GROUPS)))
    pmm = np.zeros((M, len(pm_names)))
    occ = np.zeros((M, len(gf.OUTCOMES)))
    for m in range(M):
        b = gf.draw_behavior(prng)
        pa = gf.draw_pm_alloc(prng)
        if r_stage[m] is not None:
            b["repeat_deadlock"] = r_stage[m]
        if s_stage[m] is not None:
            b["resolution_shares"] = s_stage[m]
        if w_stage[m] is not None:
            b["resolution_mix"] = w_stage[m]
        oc, pmv = gf.simulate_formation(draws, b, seed=gf.SEED + m, pm_alloc=pa)
        gi = gidx[oc]
        for g in range(4):
            grp[m, g] = (gi == g).mean()
        grp[m, 4] = ((gi == 0) | (gi == 3)).mean()
        cnt = pd.Series(pmv).value_counts(normalize=True)
        pmm[m] = [cnt.get(n, 0.0) for n in pm_names]
        oc_cnt = np.bincount(oc, minlength=len(gf.OUTCOMES)) / len(oc)
        occ[m] = oc_cnt[:len(gf.OUTCOMES)]

    def trio(col):
        return [round(float(col.mean()), 3), round(float(np.percentile(col, 5)), 3),
                round(float(np.percentile(col, 95)), 3)]
    groups = {g: trio(grp[:, i]) for i, g in enumerate(GROUPS)}
    # Monte Carlo standard error of each group mean over the vectors
    se = {g: round(float(grp[:, i].std(ddof=1) / np.sqrt(M)), 4) if M > 1 else 0.0
          for i, g in enumerate(GROUPS)}
    pm = sorted(([n, *trio(pmm[:, j])] for j, n in enumerate(pm_names)), key=lambda r: -r[1])
    pm = [r for r in pm if r[1] > 0.001]
    outcomes = [[o, round(float(occ[:, i].mean()), 3)] for i, o in enumerate(gf.OUTCOMES)]
    return {"groups": groups, "groups_se": se, "pm": pm, "outcomes": outcomes,
            "vectors": M, "n_draws": int(len(draws))}


# --- the production chain ----------------------------------------------------

@contextlib.contextmanager
def chain_output(work: Path):
    """registration_scenarios / official_forecast / government_formation
    read and write their PROCESSED_DIR; point it at `work` for the block.
    bayes_model.PROCESSED_DIR (prepare_data's inputs) is left alone: it is
    only read."""
    from model_variants import variant_flags
    with variant_flags({m: {"PROCESSED_DIR": work} for m in
                        ("registration_scenarios", "official_forecast", "government_formation")}):
        yield


def _stage_inputs(work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    nc = PROCESSED / "m3_idata.nc"
    if not nc.exists():
        raise CheckFailed("no production posterior data/processed/m3_idata.nc (not in git)")
    link = work / "m3_idata.nc"
    if not link.exists():
        try:
            link.symlink_to(nc)
        except OSError:
            shutil.copy2(nc, link)
    for f in CHAIN_INPUTS:
        if (PROCESSED / f).exists():
            shutil.copy2(PROCESSED / f, work / f)


def run_bayes(flags: dict, work: Path, M: int, log) -> dict:
    """registration mixture -> official central count -> formation, with
    `flags` applied, every chain output in `work`."""
    import government_formation as gf
    import official_forecast as of
    import registration_scenarios as rs
    from model_variants import variant_flags
    _stage_inputs(work)
    buf = io.StringIO()
    with variant_flags(flags), chain_output(work):
        with contextlib.redirect_stdout(buf):
            rs.main()
            of.main()
            draws = gf.load_draws()
        form = formation_summary(draws, M)
    log.write(buf.getvalue())
    mb = pd.read_csv(work / "mixture_blocs.csv").iloc[0]
    off = pd.read_csv(work / "official_forecast.csv")
    mix = pd.read_csv(work / "bayes_forecast_mixture.csv")
    mean = dict(zip(mix["list"], mix["mean"]))
    lists = []
    for r in off.itertuples():
        lo, hi = (int(x) for x in str(r.interval_90).split("-"))
        lists.append({"name": r.list, "seats": int(r.central_seats), "lo": lo, "hi": hi,
                      "p_pass": round(float(r.p_pass), 3),
                      "mean": round(float(mean.get(r.list, r.central_seats)), 1)})
    blocs = {"nb": round(float(mb.p_nb_61), 3), "anti": round(float(mb.p_anti_61), 3),
             "antiRaam": round(float(mb.p_anti_raam_61), 3),
             "neither": round(float(mb.p_neither), 3), "nb_mean": round(float(mb.nb_mean), 1),
             "nb_p05": int(mb.nb_p05), "nb_p95": int(mb.nb_p95)}
    return {"blocs": blocs, "lists": lists, "asof": str(off["asof"].iloc[0]),
            "n_sims": int(len(draws)), **form}


def run_simple(M: int, log) -> dict:
    """The weighted-average benchmark (simulate.build_inputs + simulate_core,
    the calls simulate.main makes) on the polls fielded since filing day,
    then the official central count on its median shares and the
    formation tree. Nothing is written."""
    import official_forecast as of
    import simulate as sim
    from polling_average import ELECTION_DAY_2026, load_2026
    polls = load_2026()
    polls = polls[polls["fieldwork_end"] >= FILING_DAY]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        avg, asof = sim.build_inputs(polls=polls)
        days_out = max((ELECTION_DAY_2026 - asof).days, 0)
        scale = sim.uncertainty_scale(days_out)
        pairs = [(SIMPLE_PAIR_IDS.get(a, a), SIMPLE_PAIR_IDS.get(b, b)) for a, b in sim.SURPLUS_PAIRS]
        seats = sim.simulate_core(avg, pairs, scale=scale)
    log.write(buf.getvalue())
    shares = sim.simulate_core.last_shares
    names = [SIMPLE_RENAME.get(x, x) for x in avg["label"]]
    # allocate_central resolves simulate.SURPLUS_PAIRS by component id: the
    # simple pipeline's single Joint List column is the Balad + Hadash-Ta'al list
    comps = [SIMPLE_COMPONENTS.get(c, c) for c in avg["components"]]
    sh = pd.DataFrame({"list": names, "components": comps,
                       "share_median": np.median(shares, axis=0)})
    central = of.allocate_central(sh)
    assert sum(central.values()) == 120, sum(central.values())
    blocs_of = avg["bloc"].values
    nb = seats[:, blocs_of == "netanyahu_bloc"].sum(axis=1)
    anti = seats[:, blocs_of == "opposition_bloc"].sum(axis=1)
    raam = seats[:, [i for i, n in enumerate(names) if n == "Ra'am"]].sum(axis=1)
    anti_raam = anti + raam
    blocs = {"nb": round(float((nb >= 61).mean()), 3), "anti": round(float((anti >= 61).mean()), 3),
             "antiRaam": round(float((anti_raam >= 61).mean()), 3),
             "neither": round(float(((nb < 61) & (anti_raam < 61)).mean()), 3),
             "nb_mean": round(float(nb.mean()), 1), "nb_p05": int(np.percentile(nb, 5)),
             "nb_p95": int(np.percentile(nb, 95))}
    lists = [{"name": n, "seats": int(central.get(n, 0)),
              "lo": int(np.percentile(seats[:, i], 5)), "hi": int(np.percentile(seats[:, i], 95)),
              "p_pass": round(float((seats[:, i] >= 4).mean()), 3),
              "mean": round(float(seats[:, i].mean()), 1)}
             for i, n in enumerate(names)]
    lists.sort(key=lambda r: (-r["seats"], -r["p_pass"]))
    form = formation_summary(pd.DataFrame(seats, columns=names), M)
    return {"blocs": blocs, "lists": lists, "asof": asof.date().isoformat(),
            "n_sims": int(len(seats)), "polls_from": FILING_DAY.date().isoformat(),
            "uncertainty_scale": round(scale, 2), **form}


# --- the reproduction check ---------------------------------------------------

def check_official(res: dict) -> dict:
    """The official variant against the published files. Mixture and central
    count: identical (same code, posterior, seed); formation groups: within
    3 Monte Carlo standard errors (M of production's 200 vectors) or 0.01."""
    mb = pd.read_csv(PROCESSED / "mixture_blocs.csv").iloc[0]
    off = pd.read_csv(PROCESSED / "official_forecast.csv")
    gg = pd.read_csv(PROCESSED / "government_groups.csv").set_index("group")["probability"]
    out = {"blocs": {}, "groups": {}, "central_seats": {}, "ok": True, "problems": []}
    pub = {"nb": mb.p_nb_61, "anti": mb.p_anti_61, "antiRaam": mb.p_anti_raam_61,
           "neither": mb.p_neither, "nb_mean": mb.nb_mean}
    for k, v in pub.items():
        d = round(float(res["blocs"][k]) - float(v), 4)
        # a bloc probability over 8,000 draws: 3 binomial standard errors
        tol = 0.05 if k == "nb_mean" else 3 * np.sqrt(max(v * (1 - v), 1e-4) / res["n_sims"])
        out["blocs"][k] = {"published": float(v), "variant": res["blocs"][k], "delta": d,
                           "tol": round(float(tol), 4)}
        if abs(d) > tol:
            out["ok"] = False
            out["problems"].append(f"blocs.{k} {res['blocs'][k]} vs published {v}")
    cs = dict(zip(off["list"], off["central_seats"]))
    mine = {r["name"]: r["seats"] for r in res["lists"]}
    diff = {n: (int(cs[n]), mine.get(n)) for n in cs if int(cs[n]) != mine.get(n)}
    out["central_seats"] = {"identical": not diff, "differences": diff}
    if diff:
        out["ok"] = False
        out["problems"].append(f"central seats differ: {diff}")
    for g in GROUPS:
        if g not in gg.index:
            continue
        d = round(res["groups"][g][0] - float(gg[g]), 4)
        tol = max(3 * res["groups_se"][g], 0.01)
        out["groups"][g] = {"published": float(gg[g]), "variant": res["groups"][g][0],
                            "delta": d, "tol": round(float(tol), 4)}
        if abs(d) > tol:
            out["ok"] = False
            out["problems"].append(f"groups.{g} {res['groups'][g][0]} vs published {gg[g]}")
    return out


def paired(rows: list) -> None:
    """Formation numbers on the published scale. Every variant's formation
    run uses the same first M parameter vectors and the same seeds, so its
    difference from the official run on those vectors is measured with
    common random numbers. groups_paired / pm_paired = the published
    official value (all 200 vectors) + that paired difference: the official
    variant shows exactly the published numbers, and each variant's level
    carries the paired difference's (small) noise instead of the 50-vector
    subset's. The raw M-vector numbers stay in groups / pm."""
    off = next((r for r in rows if r["id"] == "official"), None)
    if off is None:
        return
    gg = pd.read_csv(PROCESSED / "government_groups.csv").set_index("group")["probability"]
    pmp = pd.read_csv(PROCESSED / "pm_probabilities.csv").set_index("pm")["probability"]
    o_g = {g: off["groups"][g][0] for g in GROUPS}
    o_pm = {r[0]: r[1] for r in off["pm"]}
    for r in rows:
        r["groups_paired"] = {g: round(float(np.clip(gg.get(g, o_g[g]) + r["groups"][g][0] - o_g[g],
                                                     0, 1)), 3)
                              for g in GROUPS}
        v_pm = {x[0]: x[1] for x in r["pm"]}
        names = list(dict.fromkeys(list(pmp.index) + list(v_pm) + list(o_pm)))
        pm = [[n, round(float(np.clip(pmp.get(n, o_pm.get(n, 0.0)) + v_pm.get(n, 0.0)
                                      - o_pm.get(n, 0.0), 0, 1)), 3)] for n in names]
        r["pm_paired"] = sorted([x for x in pm if x[1] > 0.001], key=lambda x: -x[1])


# --- assembly -----------------------------------------------------------------

def _flags_text(flags: dict) -> dict:
    return {f"{m}.{a}": (v if isinstance(v, (int, float, str, bool)) or v is None else "(set)")
            for m, attrs in (flags or {}).items() for a, v in attrs.items()}


def validate_texts(variants) -> list[str]:
    """Every citation id resolves in the registry; every decision-log link
    names a dossier section that exists."""
    import re
    from model_variants import cited_ids, dl_sections
    reg = json.loads((ROOT / "data" / "forecast_sources.json").read_text(encoding="utf-8"))
    ids = {s["id"] for s in reg} | {a for s in reg for a in s.get("aliases", [])}
    dossier = (ROOT / "docs" / "priors_dossier.md").read_text(encoding="utf-8")
    secs = {int(n) for n in re.findall(r"^## (\d+)\.", dossier, flags=re.M)}
    bad = []
    for v in variants:
        miss = sorted(cited_ids(v) - ids)
        if miss:
            bad.append(f"{v.id}: unresolved citation ids {miss}")
        gone = sorted(dl_sections(v) - secs)
        if gone:
            bad.append(f"{v.id}: decision-log sections not in the dossier {gone}")
    return bad


def build(only=None, M: int = FORMATION_VECTORS, work: Path | None = None, log=None) -> dict:
    import model_variants as mv
    log = log or io.StringIO()
    chosen = [v for v in mv.VARIANTS if not only or v.id in only]
    tmp = None
    if work is None:
        tmp = tempfile.TemporaryDirectory(prefix="variants_")
        work = Path(tmp.name)
    rows, skipped, check = [], [], None
    try:
        for v in chosen:
            ok, why = mv.available(v)
            if not ok:
                skipped.append({"id": v.id, "reason": why})
                print(f"[skip] {v.id}: {why}")
                continue
            t0 = time.time()
            flags = v.resolved_flags()
            if v.kind == "simple":
                res = run_simple(M, log)
            else:
                res = run_bayes(flags, work / v.id, M, log)
            print(f"[ ok ] {v.id} ({time.time() - t0:.0f}s): P(NB>=61) {res['blocs']['nb']:.3f} | "
                  f"change {res['blocs']['anti']:.3f} | with Ra'am {res['blocs']['antiRaam']:.3f} | "
                  f"neither {res['blocs']['neither']:.3f} | groups "
                  + " ".join(f"{g} {res['groups'][g][0]:.3f}" for g in GROUPS[:4]))
            if v.id == "official":
                check = check_official(res)
            rows.append({
                "id": v.id, "kind": v.kind, "status": v.status,
                "name": {"en": v.name_en, "he": v.name_he},
                "desc": {"en": v.desc_en, "he": v.desc_he},
                "verdict": {"en": v.verdict_en, "he": v.verdict_he},
                "sections": list(v.sections), "flags": _flags_text(flags),
                "backtest": v.backtest, "backtest_src": v.backtest_src,
                **res,
            })
    finally:
        if tmp is not None:
            tmp.cleanup()
    paired(rows)
    return {"basis": mv.BASIS, "default": "official",
            "settings": {"formation_vectors": M, "production_vectors": PRODUCTION_VECTORS,
                         "note": (f"formation groups and PM use {M} behavioural parameter vectors "
                                  f"(production {PRODUCTION_VECTORS}): the first {M} of "
                                  "production's parameter stream, the same for every variant. "
                                  "groups_paired / pm_paired = the published official value + "
                                  "the variant's paired difference from the official on those "
                                  "vectors (the official variant = the published numbers)")},
            "check": check, "variants": rows, "skipped": skipped}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="comma-separated variant ids (default: every available one)")
    ap.add_argument("--vectors", type=int, default=FORMATION_VECTORS,
                    help=f"behavioural parameter vectors in the formation tree (production "
                         f"{PRODUCTION_VECTORS})")
    ap.add_argument("--work", type=Path, help="scratch directory for the chain outputs "
                                              "(default: a temporary directory)")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    import model_variants as mv
    # placeholders cite the dossier section their own work will add: checked
    # once they are available
    bad = validate_texts([v for v in mv.VARIANTS if mv.available(v)[0]])
    if bad:
        print("variant texts:\n  " + "\n  ".join(bad))
        return 1
    only = set(a.only.split(",")) if a.only else None
    out = build(only, a.vectors, a.work)
    chk = out["check"]
    if chk is not None:
        print("official vs published: " + ("OK" if chk["ok"] else "FAILED"))
        for k, d in chk["blocs"].items():
            print(f"  {k:9s} variant {d['variant']}  published {d['published']}  delta {d['delta']:+.4f}"
                  f"  (tol {d['tol']})")
        for k, d in chk["groups"].items():
            print(f"  {k:20s} variant {d['variant']}  published {d['published']}  "
                  f"delta {d['delta']:+.4f}  (tol {d['tol']})")
        print(f"  central seats identical: {chk['central_seats']['identical']}")
        if not chk["ok"]:
            print("the official variant does not reproduce the published headline: "
                  + "; ".join(chk["problems"]))
            return 1
    elif not only or "official" in only:
        print("the official variant did not run")
        return 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {a.out.relative_to(ROOT) if a.out.is_relative_to(ROOT) else a.out} "
          f"({len(out['variants'])} variants; skipped: "
          f"{', '.join(s['id'] for s in out['skipped']) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
