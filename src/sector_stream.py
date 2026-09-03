"""Sector polls as a second observation stream.

Sector-specialist firms (Afkar, StatNet) poll a sector as a universe of its
own: "the Joint List has 38% of Arab voters". Mainstream national panels
under-reach exactly these sectors, which is where the error decomposition
finds the largest structured misses. A sector share converts to a national
vote share through two measured quantities from the kalpi layer:

    national_share = share_of_sector x W_sector / conc_list

    W_sector   the sector's weight in the national vote = eligible (locality
               count / locality concentration) x turnout / total voters
    conc_list  the fraction of the list's national vote that comes from the
               sector (kalpi poststrat); only lists drawing at least
               MIN_CONC of their vote from the sector convert cleanly

The converted observation enters the state-space fit as a poll by the
sector firm, with a noise multiplier for the conversion's own uncertainty
(turnout and concentration are estimates). Turnout is the measured
locality value by default; SECTOR_TURNOUT can be dialled for scenarios.

Inputs:  data/sector_polls.csv, data/processed/kalpi_sectors.csv,
         data/processed/kalpi_poststrat_2026.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

LOCALITY_CONC = {"arab": 0.78}      # share of the sector's votes cast in its own localities
SECTOR_TURNOUT = {"arab": None}     # None -> measured locality turnout (0.538 in 2022)
MIN_CONC = 0.5
NOISE_MULT = 1.6                    # conversion uncertainty on top of sampling noise
COMPOSITE = {"Balad + Hadash-Ta'al": "balad+hadash_taal",
             "Bennett 2026 + Yesh Atid": "together"}


def sector_observations(name_to_id: dict) -> pd.DataFrame:
    """Rows: poll_id, pollster, fieldwork_end, party_id, share, n, noise_mult."""
    path = ROOT / "data" / "sector_polls.csv"
    if not path.exists():
        return pd.DataFrame()
    sp = pd.read_csv(path, parse_dates=["fieldwork_end"])
    loc = pd.read_csv(PROCESSED / "kalpi_sectors.csv")
    ps = pd.read_csv(PROCESSED / "kalpi_poststrat_2026.csv")
    ps["party_id"] = ps["list"].map(lambda l: COMPOSITE.get(l, name_to_id.get(l, l)))
    total_voters = float(loc["voters"].sum())
    rows = []
    for sector, g in sp.groupby("sector"):
        sec = loc[loc["sector"] == sector]
        elig_sector = float(sec["eligible"].sum()) / LOCALITY_CONC.get(sector, 1.0)
        turnout = SECTOR_TURNOUT.get(sector) or float(sec["voters"].sum() / sec["eligible"].sum())
        W = elig_sector * turnout / total_voters
        conc = dict(zip(ps[ps["sector"] == sector]["party_id"],
                        ps[ps["sector"] == sector]["share_of_list"]))
        for r in g.itertuples():
            c = conc.get(r.party_id)
            if c is None or c < MIN_CONC:
                continue
            rows.append({
                "poll_id": f"sector_{r.pollster}_{r.fieldwork_end.date().isoformat()}".replace(" ", ""),
                "pollster": f"{r.pollster} (sector)", "fieldwork_end": r.fieldwork_end,
                "party_id": r.party_id, "share": r.share_of_sector * W / c,
                "n": r.n, "noise_mult": NOISE_MULT, "W": W, "conc": c,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from normalize import load_party_registry
    reg = load_party_registry()
    obs = sector_observations(dict(zip(reg["name_en"], reg["party_id"])))
    print(obs.to_string(index=False))
