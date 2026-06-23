"""
Shared pytest fixtures for the Energy Analytics Pipeline test suite.

Fixtures:
  - tmp_csv_file: Creates a temporary CSV file with sample meter readings.
  - sample_readings: Returns a list of sample reading dicts.
  - sample_csv_dir: Creates a temp directory with multiple CSV files.
"""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def sample_readings() -> list[dict]:
    """Return a list of realistic sample meter reading dicts."""
    return [
        {
            "meter_id": "MTR-00001",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "1.2345",
            "unit": "kWh",
        },
        {
            "meter_id": "MTR-00001",
            "reading_timestamp": "2024-01-15 08:15:00",
            "consumption_kwh": "1.5678",
            "unit": "kWh",
        },
        {
            "meter_id": "MTR-00002",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "0.8901",
            "unit": "kWh",
        },
        {
            "meter_id": "MTR-00002",
            "reading_timestamp": "2024-01-15 08:15:00",
            "consumption_kwh": "0.9123",
            "unit": "kWh",
        },
        {
            "meter_id": "MTR-00003",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "3.4567",
            "unit": "kWh",
        },
    ]


@pytest.fixture
def sample_readings_with_bad_data() -> list[dict]:
    """Return readings that include intentional DQ issues."""
    return [
        # Good rows
        {
            "meter_id": "MTR-00001",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "1.2345",
            "unit": "kWh",
        },
        {
            "meter_id": "MTR-00001",
            "reading_timestamp": "2024-01-15 08:15:00",
            "consumption_kwh": "1.5678",
            "unit": "kWh",
        },
        # Bad: empty meter_id
        {
            "meter_id": "",
            "reading_timestamp": "2024-01-15 08:30:00",
            "consumption_kwh": "1.0000",
            "unit": "kWh",
        },
        # Bad: negative consumption
        {
            "meter_id": "MTR-00002",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "-5.0000",
            "unit": "kWh",
        },
        # Bad: non-numeric consumption
        {
            "meter_id": "MTR-00003",
            "reading_timestamp": "2024-01-15 08:00:00",
            "consumption_kwh": "N/A",
            "unit": "kWh",
        },
    ]


@pytest.fixture
def tmp_csv_file(tmp_path: Path, sample_readings: list[dict]) -> Path:
    """Create a temporary CSV file with sample readings."""
    filepath = tmp_path / f"readings_{uuid.uuid4().hex[:8]}.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_readings[0].keys())
        writer.writeheader()
        writer.writerows(sample_readings)
    return filepath


@pytest.fixture
def sample_csv_dir(tmp_path: Path, sample_readings: list[dict]) -> Path:
    """Create a temp directory with two CSV files."""
    csv_dir = tmp_path / "source"
    csv_dir.mkdir()

    for i in range(2):
        filepath = csv_dir / f"readings_2024-01-{15 + i:02d}.csv"
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=sample_readings[0].keys())
            writer.writeheader()
            writer.writerows(sample_readings)

    return csv_dir
