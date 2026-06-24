-- sql/transforms/analytics/fact_consumption.sql
-- 
-- Purpose: Build the fact_consumption table from staging data and dimensions
-- Source: staging.stg_meter_readings joined with dimensions and staging.stg_weather_data
-- Target: analytics.fact_consumption
-- Grain: one row per (meter_key, date_key, time_key)

INSERT INTO analytics.fact_consumption (
    meter_key,
    customer_key,
    location_key,
    date_key,
    time_key,
    consumption_kwh,
    cost_usd,
    peak_demand_kw,
    temperature_c,
    is_peak_hour,
    is_weekend,
    _stg_id
)
SELECT
    dm.meter_key,
    dc.customer_key,
    dl.location_key,
    TO_CHAR(s.reading_date, 'YYYYMMDD')::INTEGER AS date_key,
    (EXTRACT(HOUR FROM s.reading_timestamp) * 100 + 
     EXTRACT(MINUTE FROM s.reading_timestamp))::INTEGER AS time_key,
    
    -- Measures
    s.consumption_kwh,
    
    -- Cost calculation based on customer tariff and peak pricing window
    CASE 
        WHEN dt.is_peak AND dc.tariff_type = 'residential' 
            THEN s.consumption_kwh * 0.28  -- peak residential rate
        WHEN NOT dt.is_peak AND dc.tariff_type = 'residential' 
            THEN s.consumption_kwh * 0.12  -- off-peak residential
        WHEN dt.is_peak AND dc.tariff_type = 'commercial' 
            THEN s.consumption_kwh * 0.22  -- peak commercial
        ELSE s.consumption_kwh * 0.10      -- off-peak commercial
    END AS cost_usd,
    
    -- Peak demand: max consumption in the 15-min window, scaled to hourly rate (kW)
    s.consumption_kwh * 4.0 AS peak_demand_kw,  -- 15-min reading × 4 = hourly rate
    
    -- Weather temperature enrichment (left join - optional)
    w.temperature_c,
    
    -- Flags
    dt.is_peak AS is_peak_hour,
    dd.is_weekend,
    
    s.meter_reading_id AS _stg_id

FROM staging.stg_meter_readings s

-- Join to meter dimension
INNER JOIN analytics.dim_meter dm 
    ON s.meter_id = dm.meter_id

-- Join to active customer dimension
INNER JOIN analytics.dim_customer dc 
    ON dm.customer_key = dc.customer_key
    AND dc.is_current = TRUE

-- Join to location dimension
INNER JOIN analytics.dim_location dl 
    ON dm.location_key = dl.location_key

-- Join to pre-populated date dimension
INNER JOIN analytics.dim_date dd 
    ON TO_CHAR(s.reading_date, 'YYYYMMDD')::INTEGER = dd.date_key

-- Join to pre-populated time dimension
INNER JOIN analytics.dim_time dt 
    ON (EXTRACT(HOUR FROM s.reading_timestamp) * 100 + 
        EXTRACT(MINUTE FROM s.reading_timestamp))::INTEGER = dt.time_key

-- Left join weather data for hourly matching
LEFT JOIN staging.stg_weather_data w 
    ON dl.location_id = w.location_id
    AND s.reading_date = w.observation_date
    AND s.reading_hour = w.observation_hour

WHERE s._batch_id = %(batch_id)s

ON CONFLICT (meter_key, date_key, time_key)
DO UPDATE SET
    consumption_kwh = EXCLUDED.consumption_kwh,
    cost_usd = EXCLUDED.cost_usd,
    peak_demand_kw = EXCLUDED.peak_demand_kw,
    temperature_c = EXCLUDED.temperature_c,
    is_peak_hour = EXCLUDED.is_peak_hour,
    is_weekend = EXCLUDED.is_weekend,
    _stg_id = EXCLUDED._stg_id,
    _loaded_at = NOW();
