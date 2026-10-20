import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import data as D  # noqa: E402


@pytest.fixture(scope="session")
def loaded():
    """Everything loaded and validated from data/raw/CTU_Routes_Structured.xlsx (once per test run)."""
    return D.load_all()


@pytest.fixture(scope="session")
def routes(loaded):
    return loaded["routes"]
