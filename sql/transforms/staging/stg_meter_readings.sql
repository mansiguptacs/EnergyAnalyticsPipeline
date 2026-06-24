-- sql/transforms/staging/stg_meter_readings.sql
-- 
-- Purpose: Clean, type-cast, quarantine invalid rows, and deduplicate raw meter readings
-- Source: raw.raw_meter_readings
-- Target: staging.stg_meter_readings
-- Grain: one row per (meter_id, reading_timestamp)

-- Step 1: Insert quarantined records (rows that fail type casting or constraints)
INSERT INTO dq.dq_quarantine (source_table, source_id, reason, raw_data)
SELECT 
    'raw.raw_meter_readings',
    id,
    CASE 
        WHEN reading_timestamp !~ '^\d{4}-\d{2}-\d{2}' 
            THEN 'invalid_timestamp: ' || COALESCE(reading_timestamp, 'null')
        WHEN consumption_kwh !~ '^-?\d+\.?\d*$' 
            THEN 'invalid_consumption_format: ' || COALESCE(consumption_kwh, 'null')
        WHEN consumption_kwh::DECIMAL < 0 
            THEN 'negative_consumption: ' || consumption_kwh
    END,
    jsonb_build_object(
        'meter_id', meter_id,
        'reading_timestamp', reading_timestamp,
        'consumption_kwh', consumption_kwh
    )
FROM raw.raw_meter_readings
WHERE _batch_id = %(batch_id)s
  AND (
    reading_timestamp !~ '^\d{4}-\d{2}-\d{2}'
    OR consumption_kwh !~ '^-?\d+\.?\d*$'
    OR consumption_kwh::DECIMAL < 0
  );

-- Step 2: Insert valid, deduplicated records into staging
INSERT INTO staging.stg_meter_readings (
    meter_id,
    reading_timestamp,
    consumption_kwh,
    reading_date,
    reading_hour,
    _raw_id,
    _batch_id
)
SELECT 
    meter_id,
    reading_timestamp::TIMESTAMP AS reading_timestamp,
    consumption_kwh::DECIMAL(12,4) AS consumption_kwh,
    reading_timestamp::TIMESTAMP::DATE AS reading_date,
    EXTRACT(HOUR FROM reading_timestamp::TIMESTAMP)::SMALLINT AS reading_hour,
    id AS _raw_id,
    _batch_id
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY meter_id, reading_timestamp 
            ORDER BY _loaded_at DESC
        ) AS rn
    FROM raw.raw_meter_readings
    WHERE _batch_id = %(batch_id)s
      AND reading_timestamp ~ '^\d{4}-\d{2}-\d{2}'
      AND consumption_kwh ~ '^-?\d+\.?\d*$'
      AND consumption_kwh::DECIMAL >= 0
) deduped
WHERE rn = 1
ON CONFLICT (meter_id, reading_timestamp) 
DO UPDATE SET
    consumption_kwh = EXCLUDED.consumption_kwh,
    _raw_id = EXCLUDED._raw_id,
    _batch_id = EXCLUDED._batch_id,
    _loaded_at = NOW();
