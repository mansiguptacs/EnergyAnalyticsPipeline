-- ==============================================================================
-- 004: Create Analytics Layer Tables (Star Schema)
-- ==============================================================================
-- Dimension and fact tables following the star schema pattern.
-- Uses surrogate integer keys for join performance.
-- ==============================================================================

-- ---------------------------------------------------------------------------
-- dim_date — Pre-populated date dimension (one row per day)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key        INTEGER     PRIMARY KEY,    -- YYYYMMDD format
    full_date       DATE        NOT NULL UNIQUE,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(20) NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,       -- 0=Mon, 6=Sun (ISO)
    day_name        VARCHAR(20) NOT NULL,
    is_weekend      BOOLEAN     NOT NULL,
    is_holiday      BOOLEAN     NOT NULL DEFAULT FALSE,
    fiscal_year     SMALLINT,
    fiscal_quarter  SMALLINT
);

COMMENT ON TABLE analytics.dim_date IS 'Date dimension – one row per calendar day. Pre-populated for 2010-2030.';

-- ---------------------------------------------------------------------------
-- dim_time — Pre-populated time dimension (one row per 15-min interval)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.dim_time (
    time_key        INTEGER     PRIMARY KEY,    -- HHMM format (e.g., 1430)
    hour            SMALLINT    NOT NULL,
    minute          SMALLINT    NOT NULL,
    time_of_day     TIME        NOT NULL,
    period_name     VARCHAR(20) NOT NULL,       -- morning, afternoon, evening, night
    is_peak         BOOLEAN     NOT NULL,       -- peak pricing window (07:00-21:00 weekdays)
    is_business_hr  BOOLEAN     NOT NULL        -- 09:00-17:00
);

COMMENT ON TABLE analytics.dim_time IS 'Time dimension – one row per 15-minute interval (96 rows total).';

-- ---------------------------------------------------------------------------
-- dim_customer — SCD Type 2 (tracks historical changes)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    customer_key    SERIAL      PRIMARY KEY,
    customer_id     VARCHAR(50) NOT NULL,
    customer_name   VARCHAR(200),
    tariff_type     VARCHAR(50),
    segment         VARCHAR(50),
    status          VARCHAR(20),

    -- SCD Type 2 tracking
    valid_from      TIMESTAMP   NOT NULL,
    valid_to        TIMESTAMP,                  -- NULL = current record
    is_current      BOOLEAN     NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE analytics.dim_customer IS 'Customer dimension with SCD Type 2 for tariff/status changes.';

-- ---------------------------------------------------------------------------
-- dim_location
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.dim_location (
    location_key    SERIAL      PRIMARY KEY,
    location_id     VARCHAR(50) NOT NULL UNIQUE,
    address         VARCHAR(500),
    city            VARCHAR(100),
    region          VARCHAR(100),
    country         VARCHAR(50),
    latitude        DECIMAL(10, 7),
    longitude       DECIMAL(10, 7),
    timezone        VARCHAR(50)
);

COMMENT ON TABLE analytics.dim_location IS 'Location dimension – physical sites where meters are installed.';

-- ---------------------------------------------------------------------------
-- dim_meter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.dim_meter (
    meter_key       SERIAL      PRIMARY KEY,
    meter_id        VARCHAR(50) NOT NULL UNIQUE,
    meter_type      VARCHAR(50),
    install_date    DATE,
    status          VARCHAR(20),
    customer_key    INTEGER     REFERENCES analytics.dim_customer(customer_key),
    location_key    INTEGER     REFERENCES analytics.dim_location(location_key)
);

COMMENT ON TABLE analytics.dim_meter IS 'Meter dimension – maps physical meters to customers and locations.';

-- ---------------------------------------------------------------------------
-- fact_consumption — Central fact table (partitioned by date_key)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics.fact_consumption (
    consumption_id  BIGSERIAL   PRIMARY KEY,

    -- Dimension foreign keys
    meter_key       INTEGER     NOT NULL,
    customer_key    INTEGER     NOT NULL,
    location_key    INTEGER     NOT NULL,
    date_key        INTEGER     NOT NULL,
    time_key        INTEGER     NOT NULL,

    -- Measures
    consumption_kwh DECIMAL(12, 4)  NOT NULL,
    cost_usd        DECIMAL(10, 2),
    peak_demand_kw  DECIMAL(10, 2),
    temperature_c   DECIMAL(5, 1),

    -- Derived flags
    is_peak_hour    BOOLEAN     NOT NULL,
    is_weekend      BOOLEAN     NOT NULL,

    -- Lineage
    _stg_id         BIGINT      NOT NULL,
    _loaded_at      TIMESTAMP   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_fact_consumption UNIQUE (meter_key, date_key, time_key)
);

COMMENT ON TABLE analytics.fact_consumption IS 'Central fact table – grain: one row per (meter, 15-minute reading).';
COMMENT ON COLUMN analytics.fact_consumption.consumption_kwh IS 'Energy consumed in this 15-minute interval (kWh).';
COMMENT ON COLUMN analytics.fact_consumption.cost_usd IS 'Calculated cost based on tariff type and time-of-use.';
COMMENT ON COLUMN analytics.fact_consumption.peak_demand_kw IS 'Instantaneous demand: consumption_kwh * 4 (scaled from 15min to hourly rate).';
