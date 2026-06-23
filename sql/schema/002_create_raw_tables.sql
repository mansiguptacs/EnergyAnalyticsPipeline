-- ==============================================================================
-- 002: Create Raw Layer Tables
-- ==============================================================================
-- All columns stored as VARCHAR to faithfully capture source data.
-- Metadata columns (_source_file, _loaded_at, _batch_id) track lineage.
-- ==============================================================================

-- ---------------------------------------------------------------------------
-- Meter Readings (primary data)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_meter_readings (
    id                  BIGSERIAL       PRIMARY KEY,
    meter_id            VARCHAR(50)     NOT NULL,
    reading_timestamp   VARCHAR(50)     NOT NULL,
    consumption_kwh     VARCHAR(50),
    unit                VARCHAR(20),

    -- Pipeline metadata
    _source_file        VARCHAR(500)    NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL
);

COMMENT ON TABLE raw.raw_meter_readings IS 'Raw smart meter readings – data lands here exactly as received from CSV/JSON source files.';
COMMENT ON COLUMN raw.raw_meter_readings._source_file IS 'Absolute path or URI of the source file this row was loaded from.';
COMMENT ON COLUMN raw.raw_meter_readings._batch_id IS 'UUID identifying the pipeline run that loaded this row.';

-- ---------------------------------------------------------------------------
-- Equipment Telemetry
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_equipment_telemetry (
    id                  BIGSERIAL       PRIMARY KEY,
    equipment_id        VARCHAR(50)     NOT NULL,
    sensor_type         VARCHAR(50),
    reading_timestamp   VARCHAR(50)     NOT NULL,
    sensor_value        VARCHAR(50),
    unit                VARCHAR(20),

    _source_file        VARCHAR(500)    NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL
);

COMMENT ON TABLE raw.raw_equipment_telemetry IS 'Raw sensor/telemetry data from energy equipment (transformers, inverters, HVAC).';

-- ---------------------------------------------------------------------------
-- Weather Data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_weather_data (
    id                  BIGSERIAL       PRIMARY KEY,
    location_id         VARCHAR(50)     NOT NULL,
    observation_time    VARCHAR(50)     NOT NULL,
    temperature_c       VARCHAR(20),
    humidity_pct        VARCHAR(20),
    wind_speed_ms       VARCHAR(20),
    cloud_cover_pct     VARCHAR(20),
    precipitation_mm    VARCHAR(20),

    _source_file        VARCHAR(500)    NOT NULL,
    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    _batch_id           UUID            NOT NULL
);

COMMENT ON TABLE raw.raw_weather_data IS 'Raw weather observations used for consumption-vs-weather enrichment.';

-- ---------------------------------------------------------------------------
-- Reference Data: Customers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_customers (
    customer_id         VARCHAR(50)     PRIMARY KEY,
    customer_name       VARCHAR(200),
    tariff_type         VARCHAR(50),
    signup_date         DATE,
    status              VARCHAR(20),

    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE raw.raw_customers IS 'Customer master data from the billing system.';

-- ---------------------------------------------------------------------------
-- Reference Data: Meters
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_meters (
    meter_id            VARCHAR(50)     PRIMARY KEY,
    customer_id         VARCHAR(50)     REFERENCES raw.raw_customers(customer_id),
    meter_type          VARCHAR(50),
    install_date        DATE,
    location_id         VARCHAR(50),
    status              VARCHAR(20),

    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE raw.raw_meters IS 'Meter registry – maps each physical meter to a customer and location.';

-- ---------------------------------------------------------------------------
-- Reference Data: Locations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.raw_locations (
    location_id         VARCHAR(50)     PRIMARY KEY,
    address             VARCHAR(500),
    city                VARCHAR(100),
    region              VARCHAR(100),
    country             VARCHAR(50)     DEFAULT 'UK',
    latitude            DECIMAL(10, 7),
    longitude           DECIMAL(10, 7),
    timezone            VARCHAR(50)     DEFAULT 'Europe/London',

    _loaded_at          TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE raw.raw_locations IS 'Physical locations where meters are installed.';
