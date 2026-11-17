"""Targeting layer, part 4: the field-budget planner.

Turns the per-station programme values written by targeting_model.py
(planner_units.pkl) into compact capacity tranches for the site, and
allocates a contact budget greedily, best value first. The site's planner
page runs the same allocation in JavaScript (site/targeting_app.js,
allocate()); this module is the reference implementation used for the
headline scenarios and the briefs.

Programmes:
    area   door canvassing of whole polling-station areas with positive value
    sup    turnout calls to identified change-bloc supporters (list-based)
    pers   persuasion calls to identified soft Netanyahu-bloc voters
    resc   rescue calls to identified Blue and White / Reservists voters

List programmes reach only identified voters, so their capacity scales with
the identified share (default targeting_model.LIST_IDENTIFIED).
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from targeting_model import LIST_IDENTIFIED, OUT

PROGS = ["area", "sup", "pers", "resc"]
MIN_AREA = 1000        # a door team goes only where it can complete 1,000 contacts
N_TRANCHES = 4


def load_units() -> dict:
    with open(OUT / "planner_units.pkl", "rb") as fh:
        return pickle.load(fh)


def tranches(units: dict, loc_ids, n: int = N_TRANCHES) -> dict:
    """Per objective and programme: rows [locality index, capacity, value per
    1,000 contacts], one row per capacity quartile of the locality's
    positive-value stations (best stations first). List-programme capacity is
    the full identified-at-100% pool; the planner scales it."""
    idx = {int(lid): k for k, lid in enumerate(loc_ids)}
    out = {}
    for obj, progs in units.items():
        out[obj] = {}
        for p in PROGS:
            locs, val, cap = progs[p]
            df = pd.DataFrame({"l": np.asarray(locs).astype(int), "v": val, "c": cap})
            df = df[(df.v > 0) & (df.c > 0) & df.l.isin(idx)]
            rows = []
            for lid, g in df.groupby("l"):
                g = g.sort_values("v", ascending=False)
                share = (g.c.cumsum() - g.c / 2) / g.c.sum()
                k = np.minimum((share.values * n).astype(int), n - 1)
                for _, gg in g.groupby(k):
                    rows.append([idx[lid], int(round(gg.c.sum())),
                                 round(float(np.average(gg.v, weights=gg.c)), 2)])
            out[obj][p] = rows
    return out


def allocate(tr: dict, budget: float, ident: float = LIST_IDENTIFIED, mult: float = 1.0,
             exclude=frozenset(), progs=PROGS, min_area: float = MIN_AREA) -> dict:
    """Greedy allocation of `budget` completed contacts across the tranches of
    one objective. Door teams (area) go only to localities with at least
    `min_area` contacts available and allocated; list programmes have no
    minimum. `mult` scales list programmes only. Returns totals and the
    per-locality allocation."""
    area_cap = {}
    for i, c, v in tr["area"]:
        area_cap[i] = area_cap.get(i, 0) + c
    units = []
    for p in progs:
        for i, c, v in tr[p]:
            if i in exclude:
                continue
            if p == "area" and area_cap.get(i, 0) < min_area:
                continue
            cc = c if p == "area" else c * ident
            if cc > 0:   # contact quality applies to calls and asks, not doors
                units.append((v * (1.0 if p == "area" else mult), cc, i, p))
    units.sort(key=lambda u: -u[0])
    dropped: set = set()
    for _ in range(5):
        left, alloc = float(budget), {}
        for v, c, i, p in units:
            if left <= 0:
                break
            if p == "area" and i in dropped:
                continue
            take = min(left, c)
            left -= take
            a = alloc.setdefault(i, {q: 0.0 for q in PROGS} | {"ve": 0.0})
            a[p] += take
            a["ve"] += take * v / 1000
        small = {i for i, a in alloc.items() if 0 < a["area"] < min_area} - dropped
        if not small:
            break
        dropped |= small
    ve = sum(a["ve"] for a in alloc.values())
    by_prog = {p: sum(a[p] for a in alloc.values()) for p in PROGS}
    return {"ve": ve, "used": budget - max(0.0, left), "contacts": by_prog,
            "localities": len(alloc), "alloc": alloc}
