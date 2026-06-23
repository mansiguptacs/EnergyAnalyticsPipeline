-- ==============================================================================
-- 005: Create Data Quality Tables
-- ==============================================================================

-- ---------------------------------------------------------------------------
-- DQ Check Results — stores the outcome of every data quality check
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dq.dq_check_results (
    id                  BIGSERIAL       PRIMARY KEY,
    check_name          VARCHAR(100)    NOT NULL,
    table_name          VARCHAR(200)    NOT NULL,
    execution_date      DATE            NOT NULL,
    passed              BOOLEAN         NOT NULL,
    failed_count        INTEGER         NOT NULL DEFAULT 0,
    total_count         INTEGER         DEFAULT 0,
    severity            VARCHAR(20)     NOT NULL,
    details             TEXT,
    execution_time_ms   INTEGER,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE dq.dq_check_results IS 'Audit log of every data quality check execution and its result.';

-- ---------------------------------------------------------------------------
-- DQ Quarantine — holds rows that failed validation
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dq.dq_quarantine (
    id                  BIGSERIAL       PRIMARY KEY,
    source_table        VARCHAR(200)    NOT NULL,
    source_id           BIGINT,
    reason              VARCHAR(500)    NOT NULL,
    raw_data            JSONB,
    quarantined_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    resolved            BOOLEAN         NOT NULL DEFAULT FALSE,
    resolved_at         TIMESTAMP,
    resolution_note     TEXT
);

COMMENT ON TABLE dq.dq_quarantine IS 'Quarantined rows that failed data quality checks. Can be resolved manually.';

-- ---------------------------------------------------------------------------
-- DQ Pipeline Metrics — tracks pipeline-level metrics per run
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dq.dq_pipeline_metrics (
    id                  BIGSERIAL       PRIMARY KEY,
    pipeline_name       VARCHAR(100)    NOT NULL,
    execution_date      DATE            NOT NULL,
    metric_name         VARCHAR(100)    NOT NULL,
    metric_value        DECIMAL(15, 4),
    details             TEXT,
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE dq.dq_pipeline_metrics IS 'Operational metrics for each pipeline run (rows ingested, duration, etc.).';
