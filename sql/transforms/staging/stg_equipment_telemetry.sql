-- sql/transforms/staging/stg_equipment_telemetry.sql
-- 
-- Purpose: Clean, type-cast, quarantine invalid rows, and deduplicate raw equipment telemetry
-- Source: raw.raw_equipment_telemetry
-- Target: staging.stg_equipment_telemetry
-- Grain: one row per (equipment_id, sensor_type, reading_timestamp)

-- Step 1: Insert quarantined records (rows that fail type casting)
INSERT INTO dq.dq_quarantine (source_table, source_id, reason, raw_data)
SELECT 
    'raw.raw_equipment_telemetry',
    id,
    CASE 
        WHEN reading_timestamp !~ '^\d{4}-\d{2}-\d{2}' 
            THEN 'invalid_timestamp: ' || COALESCE(reading_timestamp, 'null')
        WHEN sensor_value IS NOT NULL AND sensor_value !~ '^-?\d+\.?\d*$' 
            THEN 'invalid_sensor_value_format: ' || COALESCE(sensor_value, 'null')
    END,
    jsonb_build_object(
        'equipment_id', equipment_id,
        'sensor_type', sensor_type,
        'reading_timestamp', reading_timestamp,
        'sensor_value', sensor_value
    )
FROM raw.raw_equipment_telemetry
WHERE _batch_id = %(batch_id)s
  AND (
    reading_timestamp !~ '^\d{4}-\d{2}-\d{2}'
    OR (sensor_value IS NOT NULL AND sensor_value !~ '^-?\d+\.?\d*$')
  );

-- Step 2: Insert valid deduplicated equipment telemetry into staging
INSERT INTO staging.stg_equipment_telemetry (
    equipment_id,
    sensor_type,
    reading_timestamp,
    sensor_value,
    unit,
    _raw_id,
    _batch_id
)
SELECT
    equipment_id,
    sensor_type,
    reading_timestamp::TIMESTAMP AS reading_timestamp,
    sensor_value::DECIMAL(12, 4) AS sensor_value,
    COALESCE(unit, 'N/A') AS unit,
    id AS _raw_id,
    _batch_id
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY equipment_id, sensor_type, reading_timestamp
            ORDER BY _loaded_at DESC
        ) AS rn
    FROM raw.raw_equipment_telemetry
    WHERE _batch_id = %(batch_id)s
      AND reading_timestamp ~ '^\d{4}-\d{2}-\d{2}'
      AND (sensor_value IS NULL OR sensor_value ~ '^-?\d+\.?\d*$')
) deduped
WHERE rn = 1
ON CONFLICT (equipment_id, sensor_type, reading_timestamp)
DO UPDATE SET
    sensor_value = EXCLUDED.sensor_value,
    unit = EXCLUDED.unit,
    _raw_id = EXCLUDED._raw_id,
    _batch_id = EXCLUDED._batch_id,
    _loaded_at = NOW();
