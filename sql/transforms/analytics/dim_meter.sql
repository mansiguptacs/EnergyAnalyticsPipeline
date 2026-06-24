-- sql/transforms/analytics/dim_meter.sql
-- 
-- Purpose: Clean and load meters into the analytics dimension, resolving customer and location FKs
-- Source: raw.raw_meters join dim_customer and dim_location
-- Target: analytics.dim_meter

INSERT INTO analytics.dim_meter (
    meter_id,
    meter_type,
    install_date,
    status,
    customer_key,
    location_key
)
SELECT 
    rm.meter_id,
    rm.meter_type,
    rm.install_date,
    rm.status,
    dc.customer_key,
    dl.location_key
FROM raw.raw_meters rm
-- Join active customer SCD Type 2 record
LEFT JOIN analytics.dim_customer dc 
  ON rm.customer_id = dc.customer_id
  AND dc.is_current = TRUE
-- Join location record
LEFT JOIN analytics.dim_location dl 
  ON rm.location_id = dl.location_id
ON CONFLICT (meter_id) 
DO UPDATE SET
    meter_type = EXCLUDED.meter_type,
    install_date = EXCLUDED.install_date,
    status = EXCLUDED.status,
    customer_key = EXCLUDED.customer_key,
    location_key = EXCLUDED.location_key;
