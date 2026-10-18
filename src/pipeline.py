"""The production build as one command.

    python src/pipeline.py [--refresh] [--refit | --project-only] [--publish-check]

Steps, in order. Each is logged with its command, output and timing to
logs/pipeline_<timestamp>.log; the run stops at the first failure, says
which step failed and why, and exits non-zero.

  1. refresh  (--refresh) move data/raw/2026_main.html aside (to
              data/raw/previous/) so scrape_polls.py downloads the 2026
              archive page again, then scrape_polls.py, then scrape_cec.py
              (downloads the PDFs of new index rows and re-parses every
              filing). New filings the gov.il index does not list yet are
              found with `python src/scrape_cec.py --discover`, by hand.
  2. model    --refit         bayes_model.py: 14-day holdouts, the NUTS fit,
                              the refit gates (s.46), the posterior save and
                              the "current" projection
              --project-only  BAYES_PROJECT_ONLY=1 bayes_model.py: the saved
                              posterior (m3_idata.nc) re-projected, no refit
              (neither)       skipped; the chain below re-projects the saved
                              posterior through the registration mixture
  3. chain    registration_scenarios -> government_formation ->
              official_forecast -> kalpi_model
  4. site     build_sources -> build_decision_log -> build_history (every
              committed build read back from git) -> build_variants (every
              model variant of src/model_variants.py through the same chain,
              for the "Choose a model" explorer; --skip build_variants keeps
              the last file, which build_site drops if it no longer matches
              the official forecast) -> build_site
  5. checks   src/site_checks.py on output/site/index.html (always): the
              script parses, EN/HE chapter counts match, every citation
              resolves, מנדטים not מושבים, no "Others", every cited finding
              verified or corrected. --publish-check adds the pytest suite
              and writes the publish copy to output/publish/
              (knesset-model-site.html = index.html without the doctype and
              <html> lines, which the artifact host adds, + decision-log.html)
  and prints the headline.

This mirrors the hand-run scripts of 14-17 Oct (refit_16late.sh, chain14.sh,
publish_checkpoint.sh), with one difference: every step's exit code and
outputs are checked (those scripts piped through `tail`/`head`, which hid
failures - build_sources.py has been failing unseen since v45).

--skip NAME skips one named step (repeatable), for a build that must go out
around a known failure; the log records it.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
RAW = DATA / "raw"
SITE = ROOT / "output" / "site"
PUBLISH = ROOT / "output" / "publish"
LOGS = ROOT / "logs"

CHAIN = ["registration_scenarios", "government_formation", "official_forecast", "kalpi_model"]
SITE_STEPS = ["build_sources", "build_decision_log", "build_history", "build_variants", "build_site"]
# files each step must (re)write; a step that exits 0 without them fails
OUTPUTS = {
    "scrape_polls": [PROCESSED / "polls.csv", PROCESSED / "results.csv"],
    "scrape_cec": [PROCESSED / "cec_filings.csv", PROCESSED / "cec_party_pcts.csv"],
    "bayes_model": [PROCESSED / "bayes_forecast_2026.csv", PROCESSED / "bayes_forecast_blocs.csv",
                    PROCESSED / "bayes_draws.parquet"],
    "registration_scenarios": [PROCESSED / "bayes_forecast_mixture.csv", PROCESSED / "mixture_shares.csv",
                               PROCESSED / "mixture_draws.parquet", PROCESSED / "mixture_blocs.csv",
                               PROCESSED / "registration_effects.csv"],
    "government_formation": [PROCESSED / "government_formation.csv", PROCESSED / "government_groups.csv",
                             PROCESSED / "government_membership.csv", PROCESSED / "government_by_nb.csv",
                             PROCESSED / "pm_probabilities.csv", PROCESSED / "government_deadlock.csv"],
    "official_forecast": [PROCESSED / "official_forecast.csv"],
    "kalpi_model": [PROCESSED / "kalpi_sectors.csv", PROCESSED / "kalpi_poststrat_2026.csv"],
    "build_sources": [DATA / "forecast_sources.json", DATA / "forecast_findings.json"],
    "build_decision_log": [SITE / "decision-log.html"],
    "build_history": [PROCESSED / "forecast_history.csv"],
    "build_variants": [PROCESSED / "model_variants.json"],
    "build_site": [SITE / "index.html", SITE / "site_data.json"],
}
TAIL = 12          # output lines echoed to the console per step


class StepFailed(RuntimeError):
    pass


def _rel(path: Path) -> str:
    """A path relative to the repository root where it lies inside it."""
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


class Pipeline:
    def __init__(self, log_path: Path, verbose: bool = False, skip=()):
        self.log_path = log_path
        self.verbose = verbose
        self.skip = set(skip)
        self.timings: list[tuple[str, float, str]] = []
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(log_path, "a", encoding="utf-8")

    def log(self, msg: str, console: bool = True) -> None:
        stamp = time.strftime("%H:%M:%S")
        self._fh.write(f"[{stamp}] {msg}\n")
        self._fh.flush()
        if console:
            print(msg, flush=True)

    def close(self) -> None:
        self._fh.close()

    def run(self, name: str, script: str, args=(), env=None) -> None:
        """Run src/<script> as a step; stream its output into the log."""
        if name in self.skip:
            self.log(f"[skip] {name} (--skip)")
            self.timings.append((name, 0.0, "skipped"))
            return
        cmd = [sys.executable, "-u", str(SRC / script), *args]
        full_env = dict(os.environ)
        full_env["PYTHONPATH"] = str(SRC) + (os.pathsep + full_env["PYTHONPATH"]
                                             if full_env.get("PYTHONPATH") else "")
        full_env.setdefault("MPLBACKEND", "Agg")          # headless: figures are saved, not shown
        full_env.setdefault("PYTHONIOENCODING", "utf-8")  # Hebrew output, whatever the locale
        full_env.update(env or {})
        extra = " ".join(f"{k}={v}" for k, v in (env or {}).items())
        self.log(f"[run ] {name}: {extra + ' ' if extra else ''}{_rel(SRC / script)}"
                 + (" " + " ".join(args) if args else ""))
        t0 = time.time()
        tail: deque = deque(maxlen=60)
        proc = subprocess.Popen(cmd, cwd=ROOT, env=full_env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                errors="replace", bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            self._fh.write(f"    {line}\n")
            tail.append(line)
            if self.verbose:
                print(f"    {line}", flush=True)
        self._fh.flush()
        rc = proc.wait()
        dt = time.time() - t0
        if rc != 0:
            self.timings.append((name, dt, f"FAILED (exit {rc})"))
            raise StepFailed(f"{name} exited with code {rc} after {dt:.1f}s; last output:\n"
                             + "\n".join(f"    {ln}" for ln in list(tail)[-30:]))
        stale = [p for p in OUTPUTS.get(name, []) if not p.exists() or p.stat().st_mtime < t0 - 1]
        if stale:
            self.timings.append((name, dt, "FAILED (outputs not written)"))
            raise StepFailed(f"{name} exited 0 but did not write: "
                             + ", ".join(_rel(p) for p in stale))
        if not self.verbose:
            shown = [ln for ln in tail if ln.strip() and "warn" not in ln.lower()][-TAIL:]
            for ln in shown:
                print(f"    {ln}")
        self.timings.append((name, dt, "ok"))
        self.log(f"[ ok ] {name} ({dt:.1f}s)")

    def timed(self, name: str, fn) -> None:
        """An in-process step (no subprocess)."""
        if name in self.skip:
            self.log(f"[skip] {name} (--skip)")
            self.timings.append((name, 0.0, "skipped"))
            return
        self.log(f"[run ] {name}")
        t0 = time.time()
        try:
            fn()
        except StepFailed:
            self.timings.append((name, time.time() - t0, "FAILED"))
            raise
        dt = time.time() - t0
        self.timings.append((name, dt, "ok"))
        self.log(f"[ ok ] {name} ({dt:.1f}s)")


# --- steps -----------------------------------------------------------------

def step_refresh(p: Pipeline, stamp: str) -> None:
    page = RAW / "2026_main.html"
    aside = None
    if page.exists() and "scrape_polls" not in p.skip:
        aside = RAW / "previous" / f"2026_main_{stamp}.html"
        aside.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(page), str(aside))
        p.log(f"       moved data/raw/2026_main.html aside -> {_rel(aside)}")
    try:
        p.run("scrape_polls", "scrape_polls.py")
    except StepFailed:
        if aside is not None and not page.exists():
            shutil.copy2(aside, page)
            p.log("       restored the previous 2026 archive page")
        raise
    p.run("scrape_cec", "scrape_cec.py")


def _fit_summary() -> dict:
    fs = PROCESSED / "fit_summary.json"
    try:
        return json.loads(fs.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def step_model(p: Pipeline, refit: bool) -> None:
    nc = PROCESSED / "m3_idata.nc"
    if refit:
        before = nc.stat().st_mtime if nc.exists() else 0.0
        p.run("bayes_model", "bayes_model.py")
        if "bayes_model" in p.skip:
            return
        if not nc.exists() or nc.stat().st_mtime <= before:
            raise StepFailed("bayes_model finished but data/processed/m3_idata.nc was not replaced")
        fs = _fit_summary()
        p.log(f"       fit: asof {fs.get('asof')}, {fs.get('n_polls')} polls, latent {fs.get('latent')}, "
              f"{fs.get('divergences')} divergences, max r-hat {fs.get('rhat_max')}, "
              f"min ESS {fs.get('ess_min')}, holdout {fs.get('holdout_median_err')}")
        if fs.get("refit_gates") not in (None, "passed"):
            p.log(f"       WARNING refit gates: {fs.get('refit_gates')} (the build ships the latent "
                  f"recorded above; dossier s.46)")
    else:
        if not nc.exists():
            raise StepFailed("--project-only needs the saved posterior data/processed/m3_idata.nc "
                             "(not in git); run with --refit")
        p.run("bayes_model", "bayes_model.py", env={"BAYES_PROJECT_ONLY": "1"})


def step_checks(p: Pipeline) -> None:
    sys.path.insert(0, str(SRC))
    import site_checks
    results = site_checks.run_all()
    bad = {k: v for k, v in results.items() if v}
    for k, v in results.items():
        p.log(f"       {'ok  ' if not v else 'FAIL'} {k}" + ("" if not v else ": " + " | ".join(v)))
    if bad:
        raise StepFailed("site checks failed: " + "; ".join(f"{k}: {v[0]}" for k, v in bad.items()))
    p.log("       checks OK: " + site_checks.summary(results))


def step_tests(p: Pipeline) -> None:
    """The fast suite (tests/, pytest.ini), run as a module of this
    interpreter."""
    name = "tests"
    if name in p.skip:
        p.log(f"[skip] {name} (--skip)")
        p.timings.append((name, 0.0, "skipped"))
        return
    try:
        import pytest  # noqa: F401
    except ImportError:
        raise StepFailed("--publish-check runs the test suite, but pytest is not installed "
                         "in this interpreter: pip install -r requirements.txt")
    p.log(f"[run ] {name}: python -m pytest -q")
    t0 = time.time()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("MPLBACKEND", "Agg")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                       cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip().splitlines()
    for ln in out:
        p._fh.write(f"    {ln}\n")
    dt = time.time() - t0
    if r.returncode != 0:
        p.timings.append((name, dt, f"FAILED (exit {r.returncode})"))
        raise StepFailed("test suite failed:\n" + "\n".join(f"    {ln}" for ln in out[-25:]))
    p.timings.append((name, dt, "ok"))
    p.log(f"[ ok ] {name} ({dt:.1f}s): {out[-1] if out else ''}")


# Files the page links to or fetches; publish them with the page.
SUPPORTING_FILES = ("decision-log.html", "annex-data.json",
                    "election-night.html", "election-night.json")


def write_publish_copy(p: Pipeline) -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    head = '<!doctype html>\n<html lang="en">\n'
    if html.startswith(head):
        html = html[len(head):]
    PUBLISH.mkdir(parents=True, exist_ok=True)
    (PUBLISH / "knesset-model-site.html").write_text(html, encoding="utf-8")
    # supporting files published next to the page (the artifact's files map)
    extra = [n for n in SUPPORTING_FILES if (SITE / n).exists()]
    for n in extra:
        shutil.copy2(SITE / n, PUBLISH / n)
    p.log(f"       publish copy: {_rel(PUBLISH / 'knesset-model-site.html')} "
          f"(+ supporting files {', '.join(extra)})")


def headline() -> str:
    import pandas as pd
    lines = []
    fs = _fit_summary()
    try:
        mix = pd.read_csv(PROCESSED / "mixture_blocs.csv").iloc[0]
        off = pd.read_csv(PROCESSED / "official_forecast.csv")
    except FileNotFoundError as e:
        return f"(no headline: {e})"
    asof = off["asof"].iloc[0] if "asof" in off.columns else fs.get("asof")
    lines.append(f"HEADLINE  forecast as of {asof}  (fit {fs.get('asof')}, {fs.get('n_polls')} polls, "
                 f"latent {fs.get('latent')}, refit gates {fs.get('refit_gates')})")
    lines.append(f"  P(Netanyahu bloc >= 61)  {mix['p_nb_61']:.1%}")
    lines.append(f"  P(change bloc >= 61)     {mix['p_anti_61']:.1%}   with Ra'am {mix['p_anti_raam_61']:.1%}")
    lines.append(f"  P(neither)               {mix['p_neither']:.1%}")
    lines.append(f"  Netanyahu-bloc seats     mean {mix['nb_mean']}, 90% interval {int(mix['nb_p05'])}-{int(mix['nb_p95'])}")
    try:
        g = pd.read_csv(PROCESSED / "government_groups.csv").set_index("group")["probability"]
        lines.append("  Government led by        "
                     + " | ".join(f"{k} {g[k]:.1%}" for k in ("netanyahu", "change", "unity", "repeat") if k in g))
    except FileNotFoundError:
        pass
    top = off[off["central_seats"] > 0].sort_values("central_seats", ascending=False)
    lines.append("  Central seats            "
                 + ", ".join(f"{r.list} {int(r.central_seats)}" for r in top.itertuples()))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the forecast build end to end.")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download the 2026 archive page, re-scrape polls and CEC filings")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--refit", action="store_true", help="refit the Bayesian model (MCMC)")
    mode.add_argument("--project-only", action="store_true",
                      help="re-project the saved posterior (BAYES_PROJECT_ONLY=1)")
    ap.add_argument("--publish-check", action="store_true",
                    help="also run the test suite and write the publish copy to output/publish/")
    ap.add_argument("--skip", action="append", default=[], metavar="STEP",
                    help="skip a named step (e.g. kalpi_model); repeatable")
    ap.add_argument("-v", "--verbose", action="store_true", help="echo every output line")
    argv = sys.argv[1:] if argv is None else list(argv)
    args = ap.parse_args(argv)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    p = Pipeline(LOGS / f"pipeline_{stamp}.log", verbose=args.verbose, skip=args.skip)
    p.log(f"pipeline {' '.join(argv) or '(no flags)'} | {sys.executable} | {ROOT}")
    if args.skip:
        p.log(f"WARNING skipping: {', '.join(args.skip)}")
    if args.refresh and not args.refit:
        p.log("WARNING --refresh without --refit: the projection uses a posterior fitted "
              "before the new data")
    t_start = time.time()
    try:
        if args.refresh:
            step_refresh(p, stamp)
        if args.refit or args.project_only:
            step_model(p, refit=args.refit)
        if "registration_scenarios" not in p.skip and not (PROCESSED / "m3_idata.nc").exists():
            # registration_scenarios would quietly fit a posterior of its own
            raise StepFailed("no saved posterior data/processed/m3_idata.nc (not in git): "
                             "run with --refit, or copy the posterior in")
        for s in CHAIN:
            p.run(s, f"{s}.py")
        for s in SITE_STEPS:
            p.run(s, f"{s}.py")
        p.timed("checks", lambda: step_checks(p))
        if args.publish_check:
            step_tests(p)
            p.timed("publish_copy", lambda: write_publish_copy(p))
    except StepFailed as e:
        p.log(f"\nPIPELINE FAILED: {e}")
        p.log(f"log: {_rel(p.log_path)}")
        p.close()
        return 1
    except KeyboardInterrupt:
        p.log("\nPIPELINE INTERRUPTED")
        p.close()
        return 130
    total = time.time() - t_start
    p.log("\nsteps: " + "; ".join(f"{n} {dt:.1f}s{'' if st == 'ok' else ' ' + st}"
                                    for n, dt, st in p.timings))
    p.log(f"total {total / 60:.1f} min | log: {_rel(p.log_path)}\n")
    p.log(headline())
    p.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
