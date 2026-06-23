-- ==============================================================================
-- 006: Create Indexes
-- ==============================================================================
-- Indexes are aligned with the most common query patterns in each layer.
-- Each index has a comment explaining which query pattern it supports.
-- ==============================================================================

-- === RAW LAYER =============================================================

-- Idempotency check: "has this file already been loaded?"
CREATE INDEX IF NOT EXISTS idx_raw_readings_source_file
    ON raw.raw_meter_readings(_source_file);

-- Batch-based processing: "get all rows from a specific pipeline run"
CREATE INDEX IF NOT EXISTS idx_raw_readings_batch
    ON raw.raw_meter_readings(_batch_id);

-- DQ checks: "get rows loaded today"
CREATE INDEX IF NOT EXISTS idx_raw_readings_loaded_date
    ON raw.raw_meter_readings((_loaded_at::DATE));


-- === STAGING LAYER =========================================================

-- Date-based batch transforms: "process all readings for a specific date"
CREATE INDEX IF NOT EXISTS idx_stg_readings_date
    ON staging.stg_meter_readings(reading_date);

-- Common query pattern: "get all readings for a specific meter on a date range"
CREATE INDEX IF NOT EXISTS idx_stg_readings_meter_date
    ON staging.stg_meter_readings(meter_id, reading_date);

-- Batch tracking
CREATE INDEX IF NOT EXISTS idx_stg_readings_batch
    ON staging.stg_meter_readings(_batch_id);


-- === ANALYTICS LAYER =======================================================

-- Date-range queries (most common dashboard filter)
CREATE INDEX IF NOT EXISTS idx_fact_consumption_date
    ON analytics.fact_consumption(date_key);

-- Customer analysis dashboards
CREATE INDEX IF NOT EXISTS idx_fact_consumption_customer
    ON analytics.fact_consumption(customer_key);

-- Location/regional analysis
CREATE INDEX IF NOT EXISTS idx_fact_consumption_location
    ON analytics.fact_consumption(location_key);

-- Time-series per meter
CREATE INDEX IF NOT EXISTS idx_fact_consumption_meter_date
    ON analytics.fact_consumption(meter_key, date_key);

-- Covering index: daily summary dashboard (avoids heap access for aggregations)
CREATE INDEX IF NOT EXISTS idx_fact_consumption_daily_summary
    ON analytics.fact_consumption(date_key, customer_key)
    INCLUDE (consumption_kwh, cost_usd, is_peak_hour);


-- === DATA QUALITY ==========================================================

CREATE INDEX IF NOT EXISTS idx_dq_results_date
    ON dq.dq_check_results(execution_date);

CREATE INDEX IF NOT EXISTS idx_dq_results_table
    ON dq.dq_check_results(table_name);

CREATE INDEX IF NOT EXISTS idx_dq_quarantine_table
    ON dq.dq_quarantine(source_table);

-- Partial index: find unresolved quarantine items quickly
CREATE INDEX IF NOT EXISTS idx_dq_quarantine_unresolved
    ON dq.dq_quarantine(resolved) WHERE NOT resolved;

CREATE INDEX IF NOT EXISTS idx_dq_metrics_pipeline_date
    ON dq.dq_pipeline_metrics(pipeline_name, execution_date);
