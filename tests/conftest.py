"""Shared setup for the fast test suite (no MCMC, no network).

Run from the repository root:

    PYTHONPATH=src python -m pytest          # pytest.ini also adds src/

Fixtures:
    root          the repository root (data, output, docs are read from here)
    cec_fixtures  tests/fixtures/cec: four CEC filing PDFs (4202 Midgam,
                  4207 Lazar, 4211 Direct Polls, 4212 Next Data) copied from
                  data/raw/cec_pdfs, which git does not track
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")   # government_formation imports pyplot

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def cec_fixtures() -> Path:
    return FIXTURES / "cec"
