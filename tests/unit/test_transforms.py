"""
Unit tests for transform DAG tasks.

These tests mock the PostgresHook to verify that the transform callables:
  - Query the database to resolve batch_id correctly
  - Call hook.run with the correct SQL content and parameters
  - Raise AirflowSkipException when raw data is missing
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from airflow.exceptions import AirflowSkipException

from dags.transform_dag import (
    run_dim_transform,
    run_fact_consumption_transform,
    run_stg_meter_transform,
    run_stg_weather_transform,
)


@pytest.fixture
def mock_postgres_hook():
    with patch("dags.transform_dag.get_db_hook") as mock_get_hook:
        mock_hook = MagicMock()
        mock_get_hook.return_value = mock_hook
        yield mock_hook


class TestStagingTransforms:
    """Tests for staging layer transformation tasks in Airflow."""

    def test_run_stg_meter_transform_success(self, mock_postgres_hook):
        """Should resolve batch_id from raw readings and run SQL transform."""
        mock_postgres_hook.get_first.return_value = ("resolved-uuid-1234",)
        
        context = {"ds": "2024-01-15"}
        
        with patch("builtins.open", mock_open(read_data="SELECT 1 FROM %(batch_id)s")):
            batch_id = run_stg_meter_transform(**context)

        assert batch_id == "resolved-uuid-1234"
        mock_postgres_hook.get_first.assert_called_once_with(
            "SELECT _batch_id FROM raw.raw_meter_readings WHERE _source_file = %s LIMIT 1",
            parameters=("readings_2024-01-15.csv",)
        )
        mock_postgres_hook.run.assert_called_once()

    def test_run_stg_meter_transform_skips_when_no_data(self, mock_postgres_hook):
        """Should raise AirflowSkipException if no raw data exists for date."""
        mock_postgres_hook.get_first.return_value = None
        
        context = {"ds": "2024-01-15"}
        
        with pytest.raises(AirflowSkipException, match="No raw readings found"):
            run_stg_meter_transform(**context)

        mock_postgres_hook.get_first.assert_called_once()
        mock_postgres_hook.run.assert_not_called()

    def test_run_stg_weather_transform_fallback_success(self, mock_postgres_hook):
        """Should query daily weather first, then fallback to weather.csv."""
        # Query 1 (daily weather file) -> returns None
        # Query 2 (fallback weather file) -> returns batch_id
        mock_postgres_hook.get_first.side_effect = [None, ("weather-uuid-abc",)]
        
        context = {"ds": "2024-01-15"}
        
        with patch("builtins.open", mock_open(read_data="SELECT 1 FROM %(batch_id)s")):
            batch_id = run_stg_weather_transform(**context)

        assert batch_id == "weather-uuid-abc"
        assert mock_postgres_hook.get_first.call_count == 2
        mock_postgres_hook.run.assert_called_once()


class TestDimensionTransforms:
    """Tests for dimension loading tasks in Airflow."""

    def test_run_dim_transform_success(self, mock_postgres_hook):
        """Should read dimension SQL file and run it without parameters."""
        context = {}
        
        with patch("builtins.open", mock_open(read_data="SELECT 1")):
            run_dim_transform("dim_customer.sql", **context)

        mock_postgres_hook.run.assert_called_once()
        # Verify it ran without batch_id parameters
        args, kwargs = mock_postgres_hook.run.call_args
        assert "parameters" not in kwargs or kwargs["parameters"] is None


class TestFactTransforms:
    """Tests for fact table loading tasks in Airflow."""

    def test_run_fact_consumption_transform_success(self, mock_postgres_hook):
        """Should resolve batch_id from raw readings and run SQL transform."""
        mock_postgres_hook.get_first.return_value = ("resolved-uuid-1234",)
        
        context = {"ds": "2024-01-15"}
        
        with patch("builtins.open", mock_open(read_data="SELECT 1 FROM %(batch_id)s")):
            run_fact_consumption_transform(**context)

        mock_postgres_hook.get_first.assert_called_once_with(
            "SELECT _batch_id FROM raw.raw_meter_readings WHERE _source_file = %s LIMIT 1",
            parameters=("readings_2024-01-15.csv",)
        )
        mock_postgres_hook.run.assert_called_once()

    def test_run_fact_consumption_transform_skips(self, mock_postgres_hook):
        """Should raise AirflowSkipException if no readings batch is found."""
        mock_postgres_hook.get_first.return_value = None
        
        context = {"ds": "2024-01-15"}
        
        with pytest.raises(AirflowSkipException, match="No meter readings batch resolved"):
            run_fact_consumption_transform(**context)

        mock_postgres_hook.run.assert_not_called()
