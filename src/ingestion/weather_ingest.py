"""
Weather Data Ingestion Module

Loads weather observation CSV files into the raw PostgreSQL layer.
Uses batch inserts for performance and supports idempotency checks.
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


class WeatherIngestor:
    """
    Ingests weather CSV files into raw.raw_weather_data.
    """

    BATCH_SIZE = 10_000

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def ingest_file(self, file_path: Path) -> dict[str, Any]:
        """
        Ingest a single CSV file into raw.raw_weather_data.
        Idempotent: skips file if already loaded.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        batch_id = uuid.uuid4()
        start_time = datetime.now(timezone.utc)
        rows_read = 0
        rows_inserted = 0
        source_key = str(file_path.name)

        logger.info(
            "Starting weather ingestion",
            extra={"file": source_key, "batch_id": str(batch_id), "pipeline": "ingest_weather"}
        )

        conn = psycopg2.connect(self.connection_string)
        try:
            with conn:
                with conn.cursor() as cursor:
                    # Idempotency check
                    cursor.execute(
                        "SELECT COUNT(*) FROM raw.raw_weather_data WHERE _source_file = %s",
                        (source_key,)
                    )
                    existing = cursor.fetchone()[0]
                    if existing > 0:
                        logger.warning(
                            f"Weather file already ingested ({existing} rows). Skipping.",
                            extra={"file": source_key, "pipeline": "ingest_weather"}
                        )
                        return {
                            "status": "skipped",
                            "reason": "already_ingested",
                            "file": source_key,
                            "existing_rows": existing,
                        }

                    # Read and insert
                    batch = []
                    with open(file_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            rows_read += 1
                            batch.append((
                                row.get("location_id", "").strip(),
                                row.get("observation_time", "").strip(),
                                row.get("temperature_c", "").strip(),
                                row.get("humidity_pct", "").strip(),
                                row.get("wind_speed_ms", "").strip(),
                                row.get("cloud_cover_pct", "").strip(),
                                row.get("precipitation_mm", "").strip(),
                                source_key,
                                str(batch_id)
                            ))

                            if len(batch) >= self.BATCH_SIZE:
                                rows_inserted += self._insert_batch(cursor, batch)
                                batch = []

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
                f"Weather ingestion complete: {rows_inserted} rows in {duration:.1f}s",
                extra={
                    "file": source_key,
                    "batch_id": str(batch_id),
                    "rows_processed": rows_inserted,
                    "pipeline": "ingest_weather"
                }
            )
            return result

        except Exception as e:
            logger.error(
                f"Weather ingestion failed: {e}",
                extra={"file": source_key, "pipeline": "ingest_weather"},
                exc_info=True
            )
            conn.rollback()
            raise
        finally:
            conn.close()

    def _insert_batch(self, cursor, batch: list[tuple]) -> int:
        query = """
            INSERT INTO raw.raw_weather_data (
                location_id, observation_time, temperature_c, humidity_pct,
                wind_speed_ms, cloud_cover_pct, precipitation_mm, _source_file, _batch_id
            )
            VALUES %s
        """
        execute_values(cursor, query, batch, page_size=self.BATCH_SIZE)
        return len(batch)

    def ingest_directory(self, directory: Path, pattern: str = "weather*.csv") -> list[dict[str, Any]]:
        """Ingest all matching CSV files from a directory."""
        if not directory.exists():
            raise FileNotFoundError(f"Source directory not found: {directory}")

        files = sorted(directory.glob(pattern))
        logger.info(
            f"Found {len(files)} weather files matching '{pattern}' in {directory}",
            extra={"pipeline": "ingest_weather"}
        )

        results = []
        for file_path in files:
            result = self.ingest_file(file_path)
            results.append(result)

        return results


def main():
    import argparse
    from src.utils.logging_config import setup_logging

    setup_logging("ingest_weather", use_json=False)

    parser = argparse.ArgumentParser(description="Ingest weather CSV files into PostgreSQL")
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing weather CSV files",
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
        default="weather.csv",
        help="File glob pattern (default: weather.csv)",
    )

    args = parser.parse_args()

    if args.db_conn:
        conn_string = args.db_conn
    else:
        from src.utils.config import get_config
        conn_string = get_config().db.connection_string

    ingestor = WeatherIngestor(conn_string)
    results = ingestor.ingest_directory(args.source_dir, args.pattern)

    print("\n" + "=" * 60)
    print("WEATHER INGESTION SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "⏭️"
        print(f"  {status_icon}  {r['file']}: {r['status']} ({r.get('rows_inserted', 0)} rows)")
    print("=" * 60)


if __name__ == "__main__":
    main()
