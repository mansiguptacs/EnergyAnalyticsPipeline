-- ==============================================================================
-- 003: Create Staging Layer Tables
-- ==============================================================================
-- Staging tables have proper data types, unique constraints for deduplication,
-- and derived columns for easier analytics joins.
-- ==============================================================================

-- ---------------------------------------------------------------------------
-- Staged Meter Readings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.stg_meter_readings (
    meter_reading_id    BIGSERIAL       PRIMARY KEY,
    meter_id            VARCHAR(50)     NOT NULL,
    reading_timestamp   TIMESTAMP       NOT NULL,
    consumption_kwh     DECIMAL(12, 4)  NOT NULL,
    reading_date        DATE            NOT NULL,
    reading_hour        SMALLINT        NOT NULL,

    -- Lineage back to raw
    _raw_id             BIGINT          NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL,

    -- Enforce uniqueness for deduplication
    CONSTRAINT uq_stg_readings_meter_ts UNIQUE (meter_id, reading_timestamp)
);

COMMENT ON TABLE staging.stg_meter_readings IS 'Cleaned, typed, deduplicated meter readings. Source: raw.raw_meter_readings.';

-- ---------------------------------------------------------------------------
-- Staged Equipment Telemetry
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.stg_equipment_telemetry (
    telemetry_id        BIGSERIAL       PRIMARY KEY,
    equipment_id        VARCHAR(50)     NOT NULL,
    sensor_type         VARCHAR(50)     NOT NULL,
    reading_timestamp   TIMESTAMP       NOT NULL,
    sensor_value        DECIMAL(12, 4)  NOT NULL,
    unit                VARCHAR(20)     NOT NULL,

    _raw_id             BIGINT          NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL,

    CONSTRAINT uq_stg_telemetry UNIQUE (equipment_id, sensor_type, reading_timestamp)
);

COMMENT ON TABLE staging.stg_equipment_telemetry IS 'Cleaned telemetry data. Source: raw.raw_equipment_telemetry.';

-- ---------------------------------------------------------------------------
-- Staged Weather Data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.stg_weather_data (
    weather_id          BIGSERIAL       PRIMARY KEY,
    location_id         VARCHAR(50)     NOT NULL,
    observation_time    TIMESTAMP       NOT NULL,
    observation_date    DATE            NOT NULL,
    observation_hour    SMALLINT        NOT NULL,
    temperature_c       DECIMAL(5, 1),
    humidity_pct        DECIMAL(5, 1),
    wind_speed_ms       DECIMAL(5, 1),
    cloud_cover_pct     DECIMAL(5, 1),
    precipitation_mm    DECIMAL(6, 2),

    _raw_id             BIGINT          NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL,

    CONSTRAINT uq_stg_weather UNIQUE (location_id, observation_time)
);

COMMENT ON TABLE staging.stg_weather_data IS 'Cleaned weather observations. Source: raw.raw_weather_data.';
