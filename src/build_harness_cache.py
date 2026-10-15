"""Fit missing harness posteriors into a cache (research refits, restatements).

    BAYES_CLR=1 HARNESS_CACHE_DIR=harness_cache_clr \
        python src/build_harness_cache.py 2021_eve 2020_D21 ...

Each job is <cycle>_eve or <cycle>_D<h>. The data windows and draw counts
are exactly those of validate_bayes.main (eve: asof = election day - 1,
600/600) and validate_horizon.main (D-h: asof = election day - h, 400/400,
skipped below 8 polls), built through the same harness_frame /
harness_prepare (so HARNESS_FIDELITY=1 builds ballot-fidelity windows), and
written by load_or_fit with the cache signature (components, observation
count, latent). A job whose file exists is signature-checked and skipped. A
latent other than the shared cache's may never write into
data/processed/harness_cache (validate_bayes.harness_cache_dir).
(round three, 2026-10-15, dossier s.46)
"""
from __future__ import annotations

import sys
import time
import warnings

import pandas as pd

from scrape_polls import ELECTION_DAY, PROCESSED_DIR
from validate_bayes import (harness_cache_dir, harness_frame, harness_prepare,
                            load_or_fit)

warnings.filterwarnings("ignore")


def main(jobs: list[str]) -> None:
    import os
    import bayes_model as bm
    if os.environ.get("FIT_SEED"):
        # research only: re-run a fit whose chains did not mix (r-hat) with
        # another NUTS seed; the job log records it
        bm.SEED = int(os.environ["FIT_SEED"])
        print(f"NUTS seed overridden: {bm.SEED}", flush=True)
    polls = pd.read_csv(PROCESSED_DIR / "polls.csv", parse_dates=["fieldwork_end"])
    cache = harness_cache_dir(write=True)
    cache.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        cycle, kind = job.split("_")
        nc = cache / f"{job}.nc"
        eday = pd.Timestamp(ELECTION_DAY[cycle])
        if kind == "eve":
            asof, draws = eday - pd.Timedelta(days=1), 600
        else:
            asof, draws = eday - pd.Timedelta(days=int(kind[1:])), 400
        cyc = harness_frame(polls, cycle, eday, asof)
        data = harness_prepare(cyc, asof)
        if kind != "eve" and data["n_polls"] < 8:
            print(f"[{job}] only {data['n_polls']} polls, skipped", flush=True)
            continue
        existed = nc.exists()
        t0 = time.time()
        idata = load_or_fit(nc, data, draws, draws)   # checks an existing file
        if existed:
            print(f"[{job}] exists (signature ok), skipped", flush=True)
            continue
        div = int(idata.sample_stats["diverging"].sum())
        print(f"[{job}] {len(data['latent_blocks'])} lists, {data['n_polls']} polls: "
              f"fit {time.time() - t0:.0f} s, {div} divergences -> {nc}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
