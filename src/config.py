"""Paths and database settings.

Anything machine-specific (password, port) comes from .env, never from code.
That is why .env is gitignored and only .env.example is committed.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"

SOURCES = {
    "customers": RAW_DIR / "customers.csv",
    "products": RAW_DIR / "products.csv",
    "orders": RAW_DIR / "orders.csv",
}

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'sales')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'sales')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}"
    f":{os.getenv('POSTGRES_PORT', '5433')}"
    f"/{os.getenv('POSTGRES_DB', 'sales')}"
)


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Third-party libraries are noisy at INFO level
    for library in ("matplotlib", "PIL"):
        logging.getLogger(library).setLevel(logging.WARNING)
