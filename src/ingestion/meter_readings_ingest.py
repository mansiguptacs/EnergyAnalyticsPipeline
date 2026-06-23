"""
Meter Readings Ingestion Module

Loads energy consumption CSV files into the raw PostgreSQL layer.

Design decisions:
  - Batch inserts using execute_values (10x faster than row-by-row INSERT)
  - All values stored as strings in raw (no type coercion at ingestion)
  - Each file gets a unique batch_id for lineage tracking
  - Idempotent: checks _source_file to avoid re-loading the same file
  - Transaction-safe: entire file load is atomic (commit or rollback)

Usage:
    # As a module
    from src.ingestion.meter_readings_ingest import MeterReadingsIngestor
    ingestor = MeterReadingsIngestor(conn_string)
    result = ingestor.ingest_file(Path("readings_2024-01-15.csv"))

    # From command line
    python -m src.ingestion.meter_readings_ingest \\
        --source-dir /data/source \\
        --db-conn "postgresql://user:pass@host:5432/db"
"""

from __future__ import annotations

import csv
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class MeterReadingsIngestor:
    """
    Ingests meter reading CSV files into raw.raw_meter_readings.

    Each CSV file is expected to have columns:
        meter_id, reading_timestamp, consumption_kwh [, unit]

    Attributes:
        BATCH_SIZE: Number of rows per INSERT batch (tuned for performance).
    """

    BATCH_SIZE = 10_000

    def __init__(self, connection_string: str):
        """
        Args:
            connection_string: psycopg2 connection URI, e.g.
                "postgresql://user:pass@host:5432/dbname"
        """
        self.connection_string = connection_string

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_file(self, file_path: Path) -> dict[str, Any]:
        """
        Ingest a single CSV file into raw.raw_meter_readings.

        The operation is idempotent — if the file has already been loaded
        (checked via _source_file), it is skipped.

        Args:
            file_path: Path to the CSV file.

        Returns:
            Dict with ingestion metrics:
                status, file, batch_id, rows_read, rows_inserted, duration_seconds

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: On database errors (after rollback).
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        batch_id = uuid.uuid4()
        start_time = datetime.now(timezone.utc)
        rows_read = 0
        rows_inserted = 0
        source_key = str(file_path.name)  # Use filename, not full path, for portability

        logger.info(
            "Starting ingestion",
            extra={"file": source_key, "batch_id": str(batch_id), "pipeline": "ingest_meter"},
        )

        conn = psycopg2.connect(self.connection_string)
        try:
            with conn:
                with conn.cursor() as cursor:
                    # ----- Idempotency check -----
                    cursor.execute(
                        "SELECT COUNT(*) FROM raw.raw_meter_readings WHERE _source_file = %s",
                        (source_key,),
                    )
                    existing = cursor.fetchone()[0]
                    if existing > 0:
                        logger.warning(
                            f"File already ingested ({existing} rows). Skipping.",
                            extra={"file": source_key, "pipeline": "ingest_meter"},
                        )
                        return {
                            "status": "skipped",
                            "reason": "already_ingested",
                            "file": source_key,
                            "existing_rows": existing,
                        }

                    # ----- Read CSV and batch insert -----
                    batch: list[tuple] = []
                    with open(file_path, "r", newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            rows_read += 1
                            batch.append(
                                (
                                    row.get("meter_id", "").strip(),
                                    row.get("reading_timestamp", "").strip(),
                                    row.get("consumption_kwh", "").strip(),
                                    row.get("unit", "kWh").strip(),
                                    source_key,
                                    str(batch_id),
                                )
                            )

                            if len(batch) >= self.BATCH_SIZE:
                                rows_inserted += self._insert_batch(cursor, batch)
                                batch = []

                    # Insert remaining rows
                    if batch:
                        rows_inserted += self._insert_batch(cursor, batch)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            result = {
                "status": "success",
                "file": source_key,
                "batch_id": str(batch_id),
                "rows_read": rows_read,
                "rows_inserted": rows_inserted,
                "duration_seconds": round(duration, 2),
            }

            logger.info(
                f"Ingestion complete: {rows_inserted} rows in {duration:.1f}s",
                extra={
                    "file": source_key,
                    "batch_id": str(batch_id),
                    "rows_processed": rows_inserted,
                    "pipeline": "ingest_meter",
                },
            )
            return result

        except Exception as e:
            logger.error(
                f"Ingestion failed: {e}",
                extra={"file": source_key, "pipeline": "ingest_meter"},
                exc_info=True,
            )
            conn.rollback()
            raise

        finally:
            conn.close()

    def ingest_directory(self, directory: Path, pattern: str = "*.csv") -> list[dict[str, Any]]:
        """
        Ingest all matching CSV files from a directory.

        Files are processed in sorted order for deterministic behavior.

        Args:
            directory: Path to the source directory.
            pattern: Glob pattern for file matching (default: "*.csv").

        Returns:
            List of result dicts, one per file.
        """
        if not directory.exists():
            raise FileNotFoundError(f"Source directory not found: {directory}")

        files = sorted(directory.glob(pattern))
        logger.info(
            f"Found {len(files)} files matching '{pattern}' in {directory}",
            extra={"pipeline": "ingest_meter"},
        )

        results = []
        for file_path in files:
            result = self.ingest_file(file_path)
            results.append(result)

        # Summary
        success = sum(1 for r in results if r["status"] == "success")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        total_rows = sum(r.get("rows_inserted", 0) for r in results)
        logger.info(
            f"Directory ingestion complete: {success} loaded, {skipped} skipped, {total_rows} total rows",
            extra={"pipeline": "ingest_meter", "rows_processed": total_rows},
        )

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _insert_batch(self, cursor, batch: list[tuple]) -> int:
        """Insert a batch of rows using execute_values for performance."""
        query = """
            INSERT INTO raw.raw_meter_readings
                (meter_id, reading_timestamp, consumption_kwh, unit, _source_file, _batch_id)
            VALUES %s
        """
        execute_values(cursor, query, batch, page_size=self.BATCH_SIZE)
        return len(batch)


# ==============================================================================
# CLI entry point
# ==============================================================================

def main():
    """Command-line interface for the meter readings ingestor."""
    import argparse

    from src.utils.logging_config import setup_logging

    setup_logging("ingest_meter", use_json=False)

    parser = argparse.ArgumentParser(description="Ingest meter reading CSV files into PostgreSQL")
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing CSV files to ingest",
    )
    parser.add_argument(
        "--db-conn",
        type=str,
        default=None,
        help="PostgreSQL connection string (default: from env vars)",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.csv",
        help="File glob pattern (default: *.csv)",
    )

    args = parser.parse_args()

    # Build connection string
    if args.db_conn:
        conn_string = args.db_conn
    else:
        from src.utils.config import get_config

        conn_string = get_config().db.connection_string

    ingestor = MeterReadingsIngestor(conn_string)
    results = ingestor.ingest_directory(args.source_dir, args.pattern)

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "⏭️"
        print(f"  {status_icon}  {r['file']}: {r['status']} ({r.get('rows_inserted', 0)} rows)")
    print("=" * 60)


if __name__ == "__main__":
    main()
