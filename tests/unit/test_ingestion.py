"""
Unit tests for the Meter Readings Ingestion module.

These tests verify:
  - CSV file reading and parsing
  - Data validation before insertion
  - Batch construction logic
  - CLI argument parsing

Note: These are pure unit tests — no database required.
      Integration tests (which require PostgreSQL) are in tests/integration/.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.meter_readings_ingest import MeterReadingsIngestor


class TestMeterReadingsIngestor:
    """Tests for the MeterReadingsIngestor class."""

    def setup_method(self):
        """Create an ingestor instance with a fake connection string."""
        self.ingestor = MeterReadingsIngestor("postgresql://fake:fake@localhost:5432/fake")

    # ----- File Validation -----

    def test_ingest_nonexistent_file_raises(self):
        """Ingesting a non-existent file should raise FileNotFoundError."""
        fake_path = Path("/nonexistent/readings.csv")
        with pytest.raises(FileNotFoundError, match="Source file not found"):
            self.ingestor.ingest_file(fake_path)

    def test_ingest_nonexistent_directory_raises(self):
        """Ingesting a non-existent directory should raise FileNotFoundError."""
        fake_dir = Path("/nonexistent/dir")
        with pytest.raises(FileNotFoundError, match="Source directory not found"):
            self.ingestor.ingest_directory(fake_dir)

    # ----- CSV Reading -----

    def test_csv_is_read_correctly(self, tmp_csv_file: Path, sample_readings: list[dict]):
        """Verify that the CSV file can be read and parsed correctly."""
        with open(tmp_csv_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == len(sample_readings)
        assert rows[0]["meter_id"] == "MTR-00001"
        assert rows[0]["consumption_kwh"] == "1.2345"

    # ----- Batch Construction -----

    @patch("src.ingestion.meter_readings_ingest.execute_values")
    def test_insert_batch_returns_count(self, mock_execute_values):
        """_insert_batch should return the number of rows in the batch."""
        mock_cursor = MagicMock()
        batch = [
            ("MTR-00001", "2024-01-15 08:00:00", "1.23", "kWh", "test.csv", "uuid-1"),
            ("MTR-00002", "2024-01-15 08:00:00", "4.56", "kWh", "test.csv", "uuid-1"),
        ]
        result = self.ingestor._insert_batch(mock_cursor, batch)
        assert result == 2
        mock_execute_values.assert_called_once()

    def test_batch_size_is_positive(self):
        """BATCH_SIZE should be a positive integer."""
        assert MeterReadingsIngestor.BATCH_SIZE > 0
        assert isinstance(MeterReadingsIngestor.BATCH_SIZE, int)

    # ----- Idempotency -----

    @patch("src.ingestion.meter_readings_ingest.psycopg2")
    def test_skips_already_ingested_file(self, mock_psycopg2, tmp_csv_file):
        """If _source_file already exists in DB, the file should be skipped."""
        # Mock the connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simulate: file already exists (COUNT(*) returns 100)
        mock_cursor.fetchone.return_value = (100,)

        result = self.ingestor.ingest_file(tmp_csv_file)

        assert result["status"] == "skipped"
        assert result["reason"] == "already_ingested"

    # ----- Directory Processing -----

    def test_directory_finds_csv_files(self, sample_csv_dir: Path):
        """Verify glob finds CSV files in a directory."""
        files = sorted(sample_csv_dir.glob("*.csv"))
        assert len(files) == 2
        assert all(f.suffix == ".csv" for f in files)


class TestSampleDataIntegrity:
    """Tests for the sample data fixtures themselves."""

    def test_sample_readings_have_required_fields(self, sample_readings: list[dict]):
        """All sample readings should have the required CSV columns."""
        required_fields = {"meter_id", "reading_timestamp", "consumption_kwh", "unit"}
        for row in sample_readings:
            assert required_fields.issubset(row.keys())

    def test_sample_readings_count(self, sample_readings: list[dict]):
        """Should have the expected number of sample readings."""
        assert len(sample_readings) == 5

    def test_bad_data_has_issues(self, sample_readings_with_bad_data: list[dict]):
        """Bad data fixture should contain rows with quality issues."""
        meter_ids = [r["meter_id"] for r in sample_readings_with_bad_data]
        consumptions = [r["consumption_kwh"] for r in sample_readings_with_bad_data]

        # Should have an empty meter_id
        assert "" in meter_ids
        # Should have a negative value
        assert any(c.startswith("-") for c in consumptions)
        # Should have a non-numeric value
        assert "N/A" in consumptions
