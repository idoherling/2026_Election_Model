"""Canonicalization of pollster names and party labels.

Every raw label that enters the database passes through here. Unknown labels
raise rather than pass silently — a new alias is a deliberate one-line edit,
never an accident.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Canonical pollster name -> known variants as they appear in published tables.
# Extend as the scraper hits new spellings; keys are the only names allowed
# in processed data.
POLLSTER_ALIASES: dict[str, list[str]] = {
    "Lazar": ["Lazar Research", "Panels/Lazar", "Maariv/Lazar"],
    "Midgam": ["Midgam Institute", "Migdam", "Midgam R&C", "Midgam Research",
               "Meno Geva", "Mano Geva"],
    "Midgam Project": [],
    "Midgam Project & StatNet": ["Midgam Project & Stat Net"],
    "Kantar": ["Kantar Institute", "Kan/Kantar"],
    "Maagar Mochot": ["Ma'agar Mochot", "Maagar Mohot", "Maagar",
                      "Makor Rishon Maagar Mochot"],
    "Direct Polls": ["DirectPolls", "Direct Polls Institute"],
    "Filber": ["Next Data/Filber", "Filber Institute"],
    "Tatika": ["Taktika", "Yossi Tatika"],
    "StatNet": ["Statnet", "Stat-Net"],
    "Camil Fuchs": ["Camile Fuchs"],
    "Panels Politics": ["Panels", "Panel Politics", "PanelPolitics",
                        "Panel Polls", "Maariv Panels", "Panels Politics, Mako"],
    "Smith Consulting": ["Smith", "Smith Poll", "Jerusalem Post /Smith Poll",
                         "Smith Research", "Rafi Smith"],
    "Timor Group": [],
    "TrendZone": [],
    "Viterbi Center": [],
    # Firms of the 2015-2022 era
    "Dialog": ["Old Dialog", "Dialogue"],
    "Geocartography": ["Geocartographia"],
    "Teleseker": ["TNS-Teleseker", "TNS Teleseker"],
    "TNS": [],
    "Shvakim Panorama": [],
    "Miskar": [],
    "Sarid": ["Machon Sarid"],
    "Number 10 Strategies": [],
    # Firms of the 2009-2015 era
    "Dahaf": [],
    "New Wave": ["The New Wave", "Gal Hadash (New Wave)", "Gal Hadash"],
    "TRI": [],
    "202 Strategies": [],
}

# Midgam Project variants predate the "/" convention, so alias them here too.
POLLSTER_ALIASES["Midgam Project"] += [
    "Panel Project HaMidgam",
    "Panel HaMidgam Project",
    "Midgam & iPanel",
    "Panel HaMidgam",
]
POLLSTER_ALIASES["Midgam Project & StatNet"] += [
    "Panel Project HaMidgam & Statnet",
    "Midgam Panel + Statnet",
]

_pollster_lookup = {
    alias.casefold(): canonical
    for canonical, aliases in POLLSTER_ALIASES.items()
    for alias in [canonical, *aliases]
}


def canonical_pollster(raw: str) -> str:
    key = raw.strip().casefold()
    if key not in _pollster_lookup:
        raise KeyError(
            f"Unknown pollster label {raw!r} — add it to POLLSTER_ALIASES"
        )
    return _pollster_lookup[key]


def load_party_registry() -> pd.DataFrame:
    registry = pd.read_csv(DATA_DIR / "party_registry.csv")
    registry["alias_list"] = registry["aliases"].fillna("").str.split("|")
    return registry


def party_lookup() -> dict[str, str]:
    """Map every known party label (casefolded) to its party_id."""
    registry = load_party_registry()
    lookup: dict[str, str] = {}
    for row in registry.itertuples():
        for label in [row.name_en, row.name_he, *row.alias_list]:
            if label:
                lookup[label.strip().casefold()] = row.party_id
    return lookup
