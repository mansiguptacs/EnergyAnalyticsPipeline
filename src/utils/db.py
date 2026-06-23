"""
Database connection utilities for the Energy Analytics Pipeline.

Provides a context-managed connection helper and a SQL file executor.

Design decisions:
- Context manager pattern ensures connections are always closed
- Separate get_connection() for cases needing manual control
- execute_sql_file() for running schema/transform SQL files
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg2
from psycopg2.extensions import connection as PgConnection

from src.utils.config import DatabaseConfig, get_config

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(config: DatabaseConfig | None = None) -> Generator[PgConnection, None, None]:
    """
    Context-managed database connection.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    Args:
        config: Optional DatabaseConfig. Uses default from env if not provided.

    Yields:
        psycopg2 connection object (auto-committed on success, rolled back on error).
    """
    if config is None:
        config = get_config().db

    conn = psycopg2.connect(**config.connection_dict)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_raw_connection(config: DatabaseConfig | None = None) -> PgConnection:
    """
    Get a raw connection without context management.
    Caller is responsible for closing.

    Use this when you need to pass the connection to external code
    that manages its own lifecycle (e.g., data quality framework).
    """
    if config is None:
        config = get_config().db
    return psycopg2.connect(**config.connection_dict)


def execute_sql_file(
    sql_path: Path | str,
    config: DatabaseConfig | None = None,
    params: dict | None = None,
) -> None:
    """
    Execute a SQL file against the database.

    Args:
        sql_path: Path to the .sql file.
        config: Optional DatabaseConfig.
        params: Optional dict of named parameters for %(name)s substitution.
    """
    sql_path = Path(sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql = sql_path.read_text()
    logger.info(f"Executing SQL file: {sql_path.name}")

    with get_connection(config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or {})

    logger.info(f"SQL file executed successfully: {sql_path.name}")


def test_connection(config: DatabaseConfig | None = None) -> bool:
    """Test database connectivity. Returns True if successful."""
    try:
        with get_connection(config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
