"""Database connection helpers."""

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL

logger = logging.getLogger(__name__)

# pool_pre_ping checks the connection is alive before reusing it,
# which matters when the Docker container restarted in between.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def check_connection() -> bool:
    """Return False instead of crashing when PostgreSQL is unreachable."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as error:
        logger.error("Cannot reach PostgreSQL: %s", error)
        return False


def run_sql_file(path: Path) -> None:
    """Run a whole .sql file in one transaction."""
    with engine.begin() as connection:
        connection.execute(text(path.read_text(encoding="utf-8")))
    logger.info("Ran %s", path.name)


def query(sql: str) -> pd.DataFrame:
    """Run a SELECT and return the result as a DataFrame."""
    with engine.connect() as connection:
        return pd.read_sql_query(text(sql), connection)
