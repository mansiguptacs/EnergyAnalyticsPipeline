-- sql/transforms/analytics/dim_location.sql
-- 
-- Purpose: Clean and upsert locations from raw into the analytics dimension
-- Source: raw.raw_locations
-- Target: analytics.dim_location

INSERT INTO analytics.dim_location (
    location_id,
    address,
    city,
    region,
    country,
    latitude,
    longitude,
    timezone
)
SELECT 
    location_id,
    address,
    city,
    region,
    country,
    latitude,
    longitude,
    timezone
FROM raw.raw_locations
ON CONFLICT (location_id) 
DO UPDATE SET
    address = EXCLUDED.address,
    city = EXCLUDED.city,
    region = EXCLUDED.region,
    country = EXCLUDED.country,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    timezone = EXCLUDED.timezone;
