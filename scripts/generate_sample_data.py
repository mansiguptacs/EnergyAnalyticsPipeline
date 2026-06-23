#!/usr/bin/env python3
"""
Sample Data Generator for the Energy Analytics Pipeline.

Generates realistic energy consumption data for development and testing:
  - Customers, meters, locations (reference data)
  - Meter readings (30 days, 15-min intervals, ~100 meters)
  - Weather data (hourly, matching the reading period)

The data models realistic patterns:
  - Higher consumption during business hours and cold weather
  - Weekend vs weekday differences
  - Random noise to simulate real-world variability
  - Some intentionally bad rows (nulls, negatives) for DQ testing

Usage:
    python scripts/generate_sample_data.py [--output-dir ./data/sample] [--days 30] [--meters 100]
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CITIES = [
    ("LOC-001", "London",       "Greater London",   "UK", 51.5074, -0.1278),
    ("LOC-002", "Manchester",   "Greater Manchester","UK", 53.4808, -2.2426),
    ("LOC-003", "Birmingham",   "West Midlands",    "UK", 52.4862, -1.8904),
    ("LOC-004", "Leeds",        "West Yorkshire",   "UK", 53.8008, -1.5491),
    ("LOC-005", "Bristol",      "Bristol",          "UK", 51.4545, -2.5879),
]

TARIFF_TYPES = ["residential", "commercial", "industrial"]
METER_TYPES  = ["smart", "smart", "smart", "analog"]  # weighted: 75% smart
CUSTOMER_STATUSES = ["active", "active", "active", "active", "inactive"]  # 80% active

# Consumption profiles (kWh per 15-min interval, base values)
CONSUMPTION_PROFILES = {
    "residential": {"base": 0.3, "peak_multiplier": 1.8, "weekend_multiplier": 1.2},
    "commercial":  {"base": 1.2, "peak_multiplier": 2.5, "weekend_multiplier": 0.3},
    "industrial":  {"base": 3.0, "peak_multiplier": 1.5, "weekend_multiplier": 0.5},
}


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_customers(num_customers: int) -> list[dict]:
    """Generate customer reference data."""
    customers = []
    for i in range(1, num_customers + 1):
        tariff = random.choice(TARIFF_TYPES)
        customers.append({
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"Customer {i}",
            "tariff_type": tariff,
            "signup_date": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "status": random.choice(CUSTOMER_STATUSES),
        })
    return customers


def generate_locations() -> list[dict]:
    """Generate location reference data."""
    locations = []
    for loc_id, city, region, country, lat, lon in CITIES:
        locations.append({
            "location_id": loc_id,
            "address": f"{random.randint(1, 200)} {random.choice(['High', 'King', 'Queen', 'Park', 'Station'])} Street",
            "city": city,
            "region": region,
            "country": country,
            "latitude": str(round(lat + random.uniform(-0.05, 0.05), 7)),
            "longitude": str(round(lon + random.uniform(-0.05, 0.05), 7)),
            "timezone": "Europe/London",
        })
    return locations


def generate_meters(customers: list[dict], locations: list[dict]) -> list[dict]:
    """Generate meter reference data — one meter per customer."""
    meters = []
    for i, customer in enumerate(customers):
        location = random.choice(locations)
        meters.append({
            "meter_id": f"MTR-{i + 1:05d}",
            "customer_id": customer["customer_id"],
            "meter_type": random.choice(METER_TYPES),
            "install_date": customer["signup_date"],
            "location_id": location["location_id"],
            "status": "active" if customer["status"] == "active" else "decommissioned",
        })
    return meters


def generate_meter_readings(
    meters: list[dict],
    start_date: datetime,
    num_days: int,
    bad_data_rate: float = 0.005,
) -> list[dict]:
    """
    Generate meter readings with realistic consumption patterns.

    Args:
        meters: List of meter dicts (from generate_meters).
        start_date: First day of readings.
        num_days: Number of days to generate.
        bad_data_rate: Fraction of rows with intentional data quality issues.

    Returns:
        List of reading dicts.
    """
    readings = []
    active_meters = [m for m in meters if m["status"] == "active"]

    # Pre-compute the customer tariff lookup
    customer_tariffs = {m["meter_id"]: random.choice(TARIFF_TYPES) for m in active_meters}

    for day_offset in range(num_days):
        current_date = start_date + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5

        for meter in active_meters:
            meter_id = meter["meter_id"]
            tariff = customer_tariffs[meter_id]
            profile = CONSUMPTION_PROFILES[tariff]

            # Generate 96 readings (one per 15-min interval)
            for interval in range(96):
                hour = interval // 4
                minute = (interval % 4) * 15
                ts = current_date.replace(hour=hour, minute=minute, second=0)

                # Base consumption
                base = profile["base"]

                # Time-of-day pattern
                if 7 <= hour <= 9:      # morning peak
                    base *= profile["peak_multiplier"] * 0.8
                elif 17 <= hour <= 20:  # evening peak
                    base *= profile["peak_multiplier"]
                elif 0 <= hour <= 5:    # overnight low
                    base *= 0.3
                elif 10 <= hour <= 16:  # daytime moderate
                    base *= 1.2 if tariff == "commercial" else 0.7

                # Weekend adjustment
                if is_weekend:
                    base *= profile["weekend_multiplier"]

                # Random noise (±30%)
                consumption = max(0, base * random.uniform(0.7, 1.3))
                consumption = round(consumption, 4)

                # Inject intentional bad data for DQ testing
                row = {
                    "meter_id": meter_id,
                    "reading_timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "consumption_kwh": str(consumption),
                    "unit": "kWh",
                }

                if random.random() < bad_data_rate:
                    defect = random.choice(["null_meter", "null_ts", "negative", "non_numeric", "extreme"])
                    if defect == "null_meter":
                        row["meter_id"] = ""
                    elif defect == "null_ts":
                        row["reading_timestamp"] = ""
                    elif defect == "negative":
                        row["consumption_kwh"] = str(-abs(consumption))
                    elif defect == "non_numeric":
                        row["consumption_kwh"] = "N/A"
                    elif defect == "extreme":
                        row["consumption_kwh"] = str(round(consumption * 100, 4))

                readings.append(row)

    return readings


def generate_weather(locations: list[dict], start_date: datetime, num_days: int) -> list[dict]:
    """Generate hourly weather data for each location."""
    weather = []
    for day_offset in range(num_days):
        current_date = start_date + timedelta(days=day_offset)

        # Daily base temperature (seasonal pattern)
        day_of_year = current_date.timetuple().tm_yday
        # UK-ish temperatures: winter ~5°C, summer ~20°C
        seasonal_temp = 12.5 + 7.5 * (1 - abs(day_of_year - 182) / 182)

        for location in locations:
            for hour in range(24):
                ts = current_date.replace(hour=hour, minute=0, second=0)

                # Diurnal temperature cycle
                hour_adjustment = -3 + 6 * (1 - abs(hour - 14) / 14)
                temp = seasonal_temp + hour_adjustment + random.uniform(-2, 2)

                weather.append({
                    "location_id": location["location_id"],
                    "observation_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "temperature_c": str(round(temp, 1)),
                    "humidity_pct": str(round(random.uniform(40, 95), 1)),
                    "wind_speed_ms": str(round(random.uniform(0, 15), 1)),
                    "cloud_cover_pct": str(round(random.uniform(0, 100), 1)),
                    "precipitation_mm": str(round(max(0, random.gauss(0.2, 0.5)), 2)),
                })

    return weather


# ---------------------------------------------------------------------------
# File Writers
# ---------------------------------------------------------------------------

def write_csv(data: list[dict], filepath: Path) -> int:
    """Write a list of dicts to a CSV file. Returns row count."""
    if not data:
        return 0

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    return len(data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate sample data for the Energy Analytics Pipeline")
    parser.add_argument("--output-dir", type=Path, default=Path("data/sample"), help="Output directory")
    parser.add_argument("--days", type=int, default=30, help="Number of days of readings to generate")
    parser.add_argument("--meters", type=int, default=50, help="Number of meters (≈ customers)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2024, 1, 1)

    logger.info("=" * 60)
    logger.info("ENERGY ANALYTICS PIPELINE — Sample Data Generator")
    logger.info("=" * 60)
    logger.info(f"  Output:  {output_dir.absolute()}")
    logger.info(f"  Period:  {start_date.date()} → {(start_date + timedelta(days=args.days - 1)).date()}")
    logger.info(f"  Meters:  {args.meters}")
    logger.info(f"  Seed:    {args.seed}")
    logger.info("")

    # 1. Reference data
    logger.info("Generating customers...")
    customers = generate_customers(args.meters)
    count = write_csv(customers, output_dir / "customers.csv")
    logger.info(f"  ✅ customers.csv — {count} rows")

    logger.info("Generating locations...")
    locations = generate_locations()
    count = write_csv(locations, output_dir / "locations.csv")
    logger.info(f"  ✅ locations.csv — {count} rows")

    logger.info("Generating meters...")
    meters_data = generate_meters(customers, locations)
    count = write_csv(meters_data, output_dir / "meters.csv")
    logger.info(f"  ✅ meters.csv — {count} rows")

    # 2. Meter readings (split into daily files for realistic ingestion)
    logger.info("Generating meter readings...")
    all_readings = generate_meter_readings(meters_data, start_date, args.days)

    # Group by date and write daily files
    readings_by_date: dict[str, list] = {}
    for r in all_readings:
        date_str = r["reading_timestamp"][:10] if r["reading_timestamp"] else "unknown"
        readings_by_date.setdefault(date_str, []).append(r)

    readings_dir = output_dir / "meter_readings"
    readings_dir.mkdir(parents=True, exist_ok=True)

    total_reading_rows = 0
    for date_str, day_readings in sorted(readings_by_date.items()):
        filename = f"readings_{date_str}.csv"
        count = write_csv(day_readings, readings_dir / filename)
        total_reading_rows += count

    logger.info(f"  ✅ meter_readings/ — {total_reading_rows} rows across {len(readings_by_date)} daily files")

    # 3. Weather data
    logger.info("Generating weather data...")
    weather = generate_weather(locations, start_date, args.days)
    count = write_csv(weather, output_dir / "weather.csv")
    logger.info(f"  ✅ weather.csv — {count} rows")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info(f"  Total files: {len(readings_by_date) + 4}")
    logger.info(f"  Total rows:  {len(customers) + len(locations) + len(meters_data) + total_reading_rows + len(weather):,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
