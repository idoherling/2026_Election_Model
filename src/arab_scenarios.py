"""Arab-sector scenario polls: scrape and project list-configuration risk.

The 2026 polling page carries an "Arab voters" table of scenario polls —
the same surveys run under alternative Arab-list configurations (a
hypothetical Segalovitz list in/out; the Joint List's components merged or
split, with Balad's standalone share shown in percent). These don't add
observations for the CURRENT configuration (their baseline rows duplicate
the main tables), but they are exactly the empirical inputs for the
registration-deadline question: how do the blocs move if the Arab lists
reconfigure?

Also scraped: the StatNet/KAP-TAU attitude series on Arab participation in
government (context for the formation model's Ra'am assumptions).

Implementation: three projections from the fitted posterior —
  current          the registered status quo (baseline forecast)
  balad_splits     Balad leaves the Joint List and runs alone at its
                   scenario-polled share; the Joint List loses it
  segalovitz       a new centre-aligned list enters at its scenario-polled
                   share, carved proportionally from the centre bloc
                   (assumption: it is a Jewish-Arab centre list)

Outputs:
    data/processed/arab_scenarios.csv        scraped scenario polls
    data/processed/arab_attitudes.csv        participation-attitude series
    data/processed/config_scenarios.csv      bloc outcomes per configuration
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd
import lxml.html

from scrape_polls import (
    PROCESSED_DIR, RAW_DIR, clean_text, expand_grid, column_labels,
    parse_date, explicit_year,
)
from simulate import THRESHOLD, dhondt

warnings.filterwarnings("ignore")

SEED = 20261027
N_PROJ = 8000
PCT = re.compile(r"\((\d+(?:\.\d+)?)\)")


def scrape_arab_tables():
    doc = lxml.html.fromstring((RAW_DIR / "2026_main.html").read_text())
    heading, out_polls, out_att = None, [], []
    for el in doc.iter():
        if el.tag in ("h2", "h3", "h4"):
            heading = clean_text(el.text_content())
        elif el.tag == "table" and "wikitable" in (el.get("class") or ""):
            if heading == "Arab voters":
                out_polls = parse_scenarios(el)
            elif heading and "Inclusion of Arab parties" in heading:
                out_att = parse_attitudes(el)
    return pd.DataFrame(out_polls), pd.DataFrame(out_att)


def parse_scenarios(table_el):
    grid = expand_grid(table_el)
    labels, bs = column_labels(grid)
    col = {l: i for i, l in enumerate(labels)}
    party_cols = [i for i, l in enumerate(labels)
                  if l and l not in ("Fieldwork date", "Polling firm",
                                     "Publisher", "Sample size")]
    rows = []
    for r in range(bs, len(grid)):
        row = grid[r]
        date_cell = row[col["Fieldwork date"]]
        firm_cell = row[col["Polling firm"]]
        if date_cell is None or firm_cell is None or not firm_cell.text:
            continue
        dt = parse_date(date_cell.text, 2026)
        if dt is None:
            continue
        seg = row[col.get("Segalovitz")] if "Segalovitz" in col else None
        has_seg = bool(seg and seg.text and "N/a" not in seg.text
                       and seg.text not in ("–", "—", ""))
        seen = set()
        for c in party_cols:
            cell = row[c]
            if cell is None or cell.origin in seen:
                continue
            seen.add(cell.origin)
            covered = [labels[cc] for cc in party_cols
                       if row[cc] is not None and row[cc].origin == cell.origin]
            txt = cell.text
            if not txt or txt in ("–", "—") or "N/a" in txt:
                continue
            pct = PCT.search(txt)
            seats = None
            if pct is None:
                try:
                    seats = int(float(txt))
                except ValueError:
                    continue
            rows.append({
                "fieldwork_end": dt.date(), "pollster": firm_cell.text,
                "scenario": "with_segalovitz" if has_seg else "baseline",
                "list": "+".join(sorted(covered)),
                "seats": seats,
                "below_pct": float(pct.group(1)) if pct else None,
            })
    return rows


def parse_attitudes(table_el):
    grid = expand_grid(table_el)
    labels, bs = column_labels(grid)
    rows = []
    for r in range(bs, len(grid)):
        row = grid[r]
        vals = [c.text if c else "" for c in row]
        if len(vals) < len(labels):
            continue
        rec = dict(zip(labels, vals))
        if rec.get("Polling firm"):
            rows.append(rec)
    return rows


def scenario_params(scen: pd.DataFrame):
    """Empirical inputs from the scenario polls."""
    seg = scen[(scen["scenario"] == "with_segalovitz")
               & (scen["list"] == "Segalovitz") & scen["seats"].notna()]
    balad_alone = scen[scen["list"].str.fullmatch("Balad")
                       & scen["below_pct"].notna()]
    return {
        "segalovitz_seats_mean": float(seg["seats"].mean()) if len(seg) else 4.0,
        "n_segalovitz_polls": int(len(seg)),
        "balad_alone_pct": (float(balad_alone["below_pct"].mean())
                            if len(balad_alone) else 1.8),
        "n_balad_split_polls": int(len(balad_alone)),
    }


def project_configs(params):
    """Bloc outcomes under each Arab-list configuration, from the posterior."""
    import arviz as az
    from bayes_model import (
        prepare_data, fit, project, SEED as BSEED,
    )
    from scrape_polls import PROCESSED_DIR as P

    nc = P / "m3_idata.nc"
    data = prepare_data()
    if nc.exists():
        idata = az.from_netcdf(nc)
    else:
        _, idata = fit(data, draws=600, tune=600)
        az.to_netcdf(idata, nc)

    results = []
    for config in ("current", "balad_splits", "segalovitz"):
        rng = np.random.default_rng(SEED)
        seats, labels, blocs = project(data, idata, rng,
                                       config=config, config_params=params)
        blocs = np.array(blocs)
        nb = seats[:, blocs == "netanyahu_bloc"].sum(axis=1)
        anti = seats[:, blocs == "opposition_bloc"].sum(axis=1)
        jl = [i for i, l in enumerate(labels) if "Hadash" in l]
        results.append({
            "config": config,
            "p_nb_61": round(float((nb >= 61).mean()), 3),
            "p_anti_61": round(float((anti >= 61).mean()), 3),
            "p_neither": round(float(((nb < 61) & (anti < 61)).mean()), 3),
            "nb_mean": round(float(nb.mean()), 1),
            "p_joint_list_passes": (round(float((seats[:, jl[0]] >= 4).mean()), 3)
                                    if jl else None),
        })
    return pd.DataFrame(results)


def main() -> None:
    scen, att = scrape_arab_tables()
    scen.to_csv(PROCESSED_DIR / "arab_scenarios.csv", index=False)
    att.to_csv(PROCESSED_DIR / "arab_attitudes.csv", index=False)
    print(f"scraped {len(scen)} scenario rows, {len(att)} attitude rows")

    params = scenario_params(scen)
    print("scenario parameters:", params)

    table = project_configs(params)
    table.to_csv(PROCESSED_DIR / "config_scenarios.csv", index=False)
    print("\nBloc outcomes by Arab-list configuration:")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
