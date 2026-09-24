"""Step 1: read the raw CSV files.

Everything is read as text on purpose. If pandas guesses the types it turns
"00123" into 123 and drops anything it cannot parse - losing information
before we get to decide what to do with it.
"""

import logging
from pathlib import Path

import pandas as pd

from src.config import SOURCES

logger = logging.getLogger(__name__)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run: make data")
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    logger.info("Extracted %-10s %5d rows", path.stem, len(data))
    return data


def extract_all() -> dict[str, pd.DataFrame]:
    return {name: read_csv(path) for name, path in SOURCES.items()}
