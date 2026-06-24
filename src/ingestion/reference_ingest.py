"""
Reference Data Ingestion Module

Loads customer, location, and meter CSV files into the raw PostgreSQL layer.
Uses transactional upsert (ON CONFLICT DO UPDATE) for idempotency.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class ReferenceIngestor:
    """
    Ingests reference dimension tables into raw schema.
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def ingest_customers(self, file_path: Path) -> dict[str, Any]:
        """Ingest customers.csv into raw.raw_customers."""
        if not file_path.exists():
            raise FileNotFoundError(f"Customers file not found: {file_path}")

        start_time = datetime.now(timezone.utc)
        rows_processed = 0

        conn = psycopg2.connect(self.connection_string)
        try:
            with conn:
                with conn.cursor() as cursor:
                    # Read CSV
                    batch = []
                    with open(file_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            signup_date = row.get("signup_date") or None
                            batch.append((
                                row.get("customer_id", "").strip(),
                                row.get("customer_name", "").strip(),
                                row.get("tariff_type", "").strip(),
                                signup_date,
                                row.get("status", "").strip(),
                            ))

                    if batch:
                        query = """
                            INSERT INTO raw.raw_customers (
                                customer_id, customer_name, tariff_type, signup_date, status
                            )
                            VALUES %s
                            ON CONFLICT (customer_id) 
                            DO UPDATE SET
                                customer_name = EXCLUDED.customer_name,
                                tariff_type = EXCLUDED.tariff_type,
                                signup_date = EXCLUDED.signup_date,
                                status = EXCLUDED.status,
                                _loaded_at = NOW()
                        """
                        execute_values(cursor, query, batch, page_size=1000)
                        rows_processed = len(batch)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Ingested {rows_processed} customers in {duration:.2f}s",
                extra={"pipeline": "ingest_reference", "file": file_path.name, "rows": rows_processed}
            )
            return {"status": "success", "file": file_path.name, "rows": rows_processed, "duration": duration}

        except Exception as e:
            logger.error(f"Failed to ingest customers: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def ingest_locations(self, file_path: Path) -> dict[str, Any]:
        """Ingest locations.csv into raw.raw_locations."""
        if not file_path.exists():
            raise FileNotFoundError(f"Locations file not found: {file_path}")

        start_time = datetime.now(timezone.utc)
        rows_processed = 0

        conn = psycopg2.connect(self.connection_string)
        try:
            with conn:
                with conn.cursor() as cursor:
                    batch = []
                    with open(file_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            lat = row.get("latitude")
                            lon = row.get("longitude")
                            batch.append((
                                row.get("location_id", "").strip(),
                                row.get("address", "").strip(),
                                row.get("city", "").strip(),
                                row.get("region", "").strip(),
                                row.get("country", "UK").strip(),
                                float(lat) if lat else None,
                                float(lon) if lon else None,
                                row.get("timezone", "Europe/London").strip(),
                            ))

                    if batch:
                        query = """
                            INSERT INTO raw.raw_locations (
                                location_id, address, city, region, country, latitude, longitude, timezone
                            )
                            VALUES %s
                            ON CONFLICT (location_id)
                            DO UPDATE SET
                                address = EXCLUDED.address,
                                city = EXCLUDED.city,
                                region = EXCLUDED.region,
                                country = EXCLUDED.country,
                                latitude = EXCLUDED.latitude,
                                longitude = EXCLUDED.longitude,
                                timezone = EXCLUDED.timezone,
                                _loaded_at = NOW()
                        """
                        execute_values(cursor, query, batch, page_size=1000)
                        rows_processed = len(batch)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Ingested {rows_processed} locations in {duration:.2f}s",
                extra={"pipeline": "ingest_reference", "file": file_path.name, "rows": rows_processed}
            )
            return {"status": "success", "file": file_path.name, "rows": rows_processed, "duration": duration}

        except Exception as e:
            logger.error(f"Failed to ingest locations: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def ingest_meters(self, file_path: Path) -> dict[str, Any]:
        """Ingest meters.csv into raw.raw_meters."""
        if not file_path.exists():
            raise FileNotFoundError(f"Meters file not found: {file_path}")

        start_time = datetime.now(timezone.utc)
        rows_processed = 0

        conn = psycopg2.connect(self.connection_string)
        try:
            with conn:
                with conn.cursor() as cursor:
                    batch = []
                    with open(file_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            install_date = row.get("install_date") or None
                            batch.append((
                                row.get("meter_id", "").strip(),
                                row.get("customer_id", "").strip(),
                                row.get("meter_type", "").strip(),
                                install_date,
                                row.get("location_id", "").strip(),
                                row.get("status", "").strip(),
                            ))

                    if batch:
                        query = """
                            INSERT INTO raw.raw_meters (
                                meter_id, customer_id, meter_type, install_date, location_id, status
                            )
                            VALUES %s
                            ON CONFLICT (meter_id)
                            DO UPDATE SET
                                customer_id = EXCLUDED.customer_id,
                                meter_type = EXCLUDED.meter_type,
                                install_date = EXCLUDED.install_date,
                                location_id = EXCLUDED.location_id,
                                status = EXCLUDED.status,
                                _loaded_at = NOW()
                        """
                        execute_values(cursor, query, batch, page_size=1000)
                        rows_processed = len(batch)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Ingested {rows_processed} meters in {duration:.2f}s",
                extra={"pipeline": "ingest_reference", "file": file_path.name, "rows": rows_processed}
            )
            return {"status": "success", "file": file_path.name, "rows": rows_processed, "duration": duration}

        except Exception as e:
            logger.error(f"Failed to ingest meters: {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def ingest_directory(self, source_dir: Path) -> dict[str, dict[str, Any]]:
        """Ingest all reference files in the given directory."""
        results = {}
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        cust_file = source_dir / "customers.csv"
        loc_file = source_dir / "locations.csv"
        mtr_file = source_dir / "meters.csv"

        if cust_file.exists():
            results["customers"] = self.ingest_customers(cust_file)
        if loc_file.exists():
            results["locations"] = self.ingest_locations(loc_file)
        if mtr_file.exists():
            results["meters"] = self.ingest_meters(mtr_file)

        return results


def main():
    import argparse
    from src.utils.logging_config import setup_logging

    setup_logging("ingest_reference", use_json=False)

    parser = argparse.ArgumentParser(description="Ingest reference master data into PostgreSQL")
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing customers.csv, locations.csv, meters.csv",
    )
    parser.add_argument(
        "--db-conn",
        type=str,
        default=None,
        help="PostgreSQL connection string (default: from env vars)",
    )

    args = parser.parse_args()

    if args.db_conn:
        conn_string = args.db_conn
    else:
        from src.utils.config import get_config
        conn_string = get_config().db.connection_string

    ingestor = ReferenceIngestor(conn_string)
    results = ingestor.ingest_directory(args.source_dir)

    print("\n" + "=" * 60)
    print("REFERENCE INGESTION SUMMARY")
    print("=" * 60)
    for name, r in results.items():
        print(f"  ✅ {name} ({r['file']}): {r['status']} ({r['rows']} rows)")
    print("=" * 60)


if __name__ == "__main__":
    main()
