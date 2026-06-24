"""
Transformation Pipeline DAG

Orchestrates the running of SQL transformations to clean raw data into staging tables,
update dimension tables (including SCD Type 2 logic for customers), 
and populate the central fact table.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.trigger_rule import TriggerRule


def get_db_hook() -> PostgresHook:
    return PostgresHook(postgres_conn_id="energy_postgres")


def run_stg_meter_transform(**context) -> str:
    """Run staging transform for meter readings, resolving batch_id from raw load."""
    hook = get_db_hook()
    execution_date_str = context["ds"]
    source_file = f"readings_{execution_date_str}.csv"

    # Query raw database to find the batch UUID for the file ingested for this date
    res = hook.get_first(
        "SELECT _batch_id FROM raw.raw_meter_readings WHERE _source_file = %s LIMIT 1",
        parameters=(source_file,),
    )
    if not res:
        raise AirflowSkipException(f"No raw readings found for source file: {source_file}")

    batch_id = str(res[0])
    sql_path = Path("/opt/airflow/sql/transforms/staging/stg_meter_readings.sql")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    hook.run(sql, autocommit=True, parameters={"batch_id": batch_id})
    return batch_id


def run_stg_weather_transform(**context) -> str:
    """Run staging transform for weather data, resolving batch_id from raw load."""
    hook = get_db_hook()
    execution_date_str = context["ds"]
    
    # Try daily file first, then fall back to full weather file
    daily_file = f"weather_{execution_date_str}.csv"
    fallback_file = "weather.csv"

    res = hook.get_first(
        "SELECT _batch_id FROM raw.raw_weather_data WHERE _source_file = %s LIMIT 1",
        parameters=(daily_file,),
    )
    if not res:
        res = hook.get_first(
            "SELECT _batch_id FROM raw.raw_weather_data WHERE _source_file = %s LIMIT 1",
            parameters=(fallback_file,),
        )

    if not res:
        raise AirflowSkipException("No raw weather data batch found. Skipping transform.")

    batch_id = str(res[0])
    sql_path = Path("/opt/airflow/sql/transforms/staging/stg_weather_data.sql")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    hook.run(sql, autocommit=True, parameters={"batch_id": batch_id})
    return batch_id


def run_stg_telemetry_transform(**context) -> str:
    """Run staging transform for telemetry (skipped if no raw data is loaded)."""
    hook = get_db_hook()
    execution_date_str = context["ds"]
    source_file = f"telemetry_{execution_date_str}.json"

    res = hook.get_first(
        "SELECT _batch_id FROM raw.raw_equipment_telemetry WHERE _source_file = %s LIMIT 1",
        parameters=(source_file,),
    )
    if not res:
        raise AirflowSkipException(f"No raw telemetry found for source file: {source_file}")

    batch_id = str(res[0])
    sql_path = Path("/opt/airflow/sql/transforms/staging/stg_equipment_telemetry.sql")
    
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    hook.run(sql, autocommit=True, parameters={"batch_id": batch_id})
    return batch_id


def run_dim_transform(sql_file_name: str, **context) -> None:
    """Execute a static SQL transform file without parameters (used for dimensions)."""
    hook = get_db_hook()
    sql_path = Path("/opt/airflow/sql/transforms/analytics") / sql_file_name

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    hook.run(sql, autocommit=True)


def run_fact_consumption_transform(**context) -> None:
    """Build fact_consumption using the readings batch_id for this run."""
    hook = get_db_hook()
    execution_date_str = context["ds"]
    source_file = f"readings_{execution_date_str}.csv"

    # Fact table inserts correspond to the readings batch loaded for this execution day
    res = hook.get_first(
        "SELECT _batch_id FROM raw.raw_meter_readings WHERE _source_file = %s LIMIT 1",
        parameters=(source_file,),
    )
    if not res:
        raise AirflowSkipException(f"No meter readings batch resolved for {source_file}")

    batch_id = str(res[0])
    sql_path = Path("/opt/airflow/sql/transforms/analytics/fact_consumption.sql")

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    hook.run(sql, autocommit=True, parameters={"batch_id": batch_id})


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "transform_pipeline",
    default_args=default_args,
    description="Run staging, dimension, and fact table SQL transformations",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=True,
    max_active_runs=1,
) as dag:

    # --- Staging Layer Tasks ---
    stg_meter = PythonOperator(
        task_id="transform_stg_meter_readings",
        python_callable=run_stg_meter_transform,
    )

    stg_weather = PythonOperator(
        task_id="transform_stg_weather_data",
        python_callable=run_stg_weather_transform,
    )

    stg_telemetry = PythonOperator(
        task_id="transform_stg_equipment_telemetry",
        python_callable=run_stg_telemetry_transform,
    )

    # --- Dimension Layer Tasks ---
    dim_customer = PythonOperator(
        task_id="transform_dim_customer",
        python_callable=run_dim_transform,
        op_kwargs={"sql_file_name": "dim_customer.sql"},
    )

    dim_location = PythonOperator(
        task_id="transform_dim_location",
        python_callable=run_dim_transform,
        op_kwargs={"sql_file_name": "dim_location.sql"},
    )

    dim_meter = PythonOperator(
        task_id="transform_dim_meter",
        python_callable=run_dim_transform,
        op_kwargs={"sql_file_name": "dim_meter.sql"},
    )

    # --- Fact Layer Tasks ---
    fact_consumption = PythonOperator(
        task_id="transform_fact_consumption",
        python_callable=run_fact_consumption_transform,
        trigger_rule=TriggerRule.NONE_FAILED,
    )

    # Define dependencies
    # Dimensions: Customer and location can run in parallel, meter depends on both
    [dim_customer, dim_location] >> dim_meter
    
    # Fact table: Depends on clean meter readings and resolving meter keys
    [stg_meter, dim_meter] >> fact_consumption
    
    # Weather is optional (left joined), but fact must wait for it if it runs.
    # Runs successfully even if weather skips due to trigger_rule=NONE_FAILED.
    stg_weather >> fact_consumption
