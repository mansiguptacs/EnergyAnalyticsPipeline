-- sql/transforms/staging/stg_weather_data.sql
-- 
-- Purpose: Clean, type-cast, quarantine invalid rows, and deduplicate raw weather readings
-- Source: raw.raw_weather_data
-- Target: staging.stg_weather_data
-- Grain: one row per (location_id, observation_time)

-- Step 1: Insert quarantined records (rows that fail type casting)
INSERT INTO dq.dq_quarantine (source_table, source_id, reason, raw_data)
SELECT 
    'raw.raw_weather_data',
    id,
    CASE 
        WHEN observation_time !~ '^\d{4}-\d{2}-\d{2}' 
            THEN 'invalid_observation_time: ' || COALESCE(observation_time, 'null')
        WHEN temperature_c IS NOT NULL AND temperature_c !~ '^-?\d+\.?\d*$' 
            THEN 'invalid_temperature_format: ' || COALESCE(temperature_c, 'null')
        WHEN humidity_pct IS NOT NULL AND humidity_pct !~ '^-?\d+\.?\d*$' 
            THEN 'invalid_humidity_format: ' || COALESCE(humidity_pct, 'null')
    END,
    jsonb_build_object(
        'location_id', location_id,
        'observation_time', observation_time,
        'temperature_c', temperature_c,
        'humidity_pct', humidity_pct
    )
FROM raw.raw_weather_data
WHERE _batch_id = %(batch_id)s
  AND (
    observation_time !~ '^\d{4}-\d{2}-\d{2}'
    OR (temperature_c IS NOT NULL AND temperature_c !~ '^-?\d+\.?\d*$')
    OR (humidity_pct IS NOT NULL AND humidity_pct !~ '^-?\d+\.?\d*$')
  );

-- Step 2: Insert valid deduplicated weather records into staging
INSERT INTO staging.stg_weather_data (
    location_id,
    observation_time,
    observation_date,
    observation_hour,
    temperature_c,
    humidity_pct,
    wind_speed_ms,
    cloud_cover_pct,
    precipitation_mm,
    _raw_id,
    _batch_id
)
SELECT
    location_id,
    observation_time::TIMESTAMP AS observation_time,
    (observation_time::TIMESTAMP)::DATE AS observation_date,
    EXTRACT(HOUR FROM observation_time::TIMESTAMP)::SMALLINT AS observation_hour,
    temperature_c::DECIMAL(5, 1) AS temperature_c,
    humidity_pct::DECIMAL(5, 1) AS humidity_pct,
    wind_speed_ms::DECIMAL(5, 1) AS wind_speed_ms,
    cloud_cover_pct::DECIMAL(5, 1) AS cloud_cover_pct,
    precipitation_mm::DECIMAL(6, 2) AS precipitation_mm,
    id AS _raw_id,
    _batch_id
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY location_id, observation_time
            ORDER BY _loaded_at DESC
        ) AS rn
    FROM raw.raw_weather_data
    WHERE _batch_id = %(batch_id)s
      AND observation_time ~ '^\d{4}-\d{2}-\d{2}'
      AND (temperature_c IS NULL OR temperature_c ~ '^-?\d+\.?\d*$')
      AND (humidity_pct IS NULL OR humidity_pct ~ '^-?\d+\.?\d*$')
) deduped
WHERE rn = 1
ON CONFLICT (location_id, observation_time)
DO UPDATE SET
    temperature_c = EXCLUDED.temperature_c,
    humidity_pct = EXCLUDED.humidity_pct,
    wind_speed_ms = EXCLUDED.wind_speed_ms,
    cloud_cover_pct = EXCLUDED.cloud_cover_pct,
    precipitation_mm = EXCLUDED.precipitation_mm,
    _raw_id = EXCLUDED._raw_id,
    _batch_id = EXCLUDED._batch_id,
    _loaded_at = NOW();
