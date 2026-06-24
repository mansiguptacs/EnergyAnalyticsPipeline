"""
Ingestion Pipeline DAG

Orchestrates loading customer, location, and meter reference data, 
along with daily smart meter readings and weather observations, 
into the raw schema tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


def get_db_uri() -> str:
    """Retrieve the URI for the target database using PostgresHook."""
    hook = PostgresHook(postgres_conn_id="energy_postgres")
    return hook.get_uri()


def run_reference_ingestion(**context) -> dict:
    """Ingest reference datasets (customers, locations, meters) if available."""
    from src.ingestion.reference_ingest import ReferenceIngestor

    conn_string = get_db_uri()
    ingestor = ReferenceIngestor(conn_string)
    source_dir = Path("/opt/airflow/data/sample")

    results = ingestor.ingest_directory(source_dir)
    return results


def run_meter_ingestion(**context) -> dict:
    """Ingest daily meter readings for the specific DAG run date."""
    from src.ingestion.meter_readings_ingest import MeterReadingsIngestor

    conn_string = get_db_uri()
    ingestor = MeterReadingsIngestor(conn_string)

    # Use Airflow execution date (ds) formatted as YYYY-MM-DD
    execution_date_str = context["ds"]
    file_path = Path(f"/opt/airflow/data/sample/meter_readings/readings_{execution_date_str}.csv")

    if not file_path.exists():
        raise AirflowSkipException(f"Meter readings file not found for date: {execution_date_str}")

    result = ingestor.ingest_file(file_path)

    # Push the generated batch_id to XCom so the transformation DAG can read it
    if result.get("status") == "success":
        context["ti"].xcom_push(key="batch_id", value=result["batch_id"])

    return result


def run_weather_ingestion(**context) -> dict:
    """Ingest daily weather observations."""
    from src.ingestion.weather_ingest import WeatherIngestor

    conn_string = get_db_uri()
    ingestor = WeatherIngestor(conn_string)

    execution_date_str = context["ds"]
    
    # Try daily weather file first, then fall back to full weather file for local simulation
    daily_file = Path(f"/opt/airflow/data/sample/weather_{execution_date_str}.csv")
    fallback_file = Path("/opt/airflow/data/sample/weather.csv")
    file_path = daily_file if daily_file.exists() else fallback_file

    if not file_path.exists():
        raise AirflowSkipException(f"Weather data file not found: {file_path}")

    result = ingestor.ingest_file(file_path)

    if result.get("status") == "success":
        context["ti"].xcom_push(key="weather_batch_id", value=result["batch_id"])

    return result


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "ingest_pipeline",
    default_args=default_args,
    description="Ingest reference data, daily meter readings, and weather metrics into raw schema",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=True,
    max_active_runs=1,
) as dag:

    ingest_ref = PythonOperator(
        task_id="ingest_reference_data",
        python_callable=run_reference_ingestion,
    )

    ingest_meter = PythonOperator(
        task_id="ingest_meter_readings",
        python_callable=run_meter_ingestion,
    )

    ingest_weather = PythonOperator(
        task_id="ingest_weather_data",
        python_callable=run_weather_ingestion,
    )

    ingest_ref >> [ingest_meter, ingest_weather]
