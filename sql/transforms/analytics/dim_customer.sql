-- sql/transforms/analytics/dim_customer.sql
-- 
-- Purpose: Populate dim_customer using SCD Type 2 tracking
-- Source: raw.raw_customers
-- Target: analytics.dim_customer

-- Step 1: Expire changed records
-- If customer details (name, tariff, status) have changed, close the active version of the record
UPDATE analytics.dim_customer dc
SET 
    valid_to = NOW(),
    is_current = FALSE
FROM raw.raw_customers rc
WHERE dc.customer_id = rc.customer_id
  AND dc.is_current = TRUE
  AND (
      dc.customer_name IS DISTINCT FROM rc.customer_name OR
      dc.tariff_type IS DISTINCT FROM rc.tariff_type OR
      dc.status IS DISTINCT FROM rc.status
  );

-- Step 2: Insert new records (including the new versions of expired records)
-- We insert records from raw that don't currently have an active match in analytics
INSERT INTO analytics.dim_customer (
    customer_id,
    customer_name,
    tariff_type,
    segment,
    status,
    valid_from,
    valid_to,
    is_current
)
SELECT 
    rc.customer_id,
    rc.customer_name,
    rc.tariff_type,
    CASE 
        WHEN LOWER(rc.tariff_type) LIKE '%commercial%' THEN 'commercial'
        WHEN LOWER(rc.tariff_type) LIKE '%industrial%' THEN 'industrial'
        ELSE 'residential'
    END AS segment,
    rc.status,
    COALESCE(rc.signup_date::TIMESTAMP, NOW()) AS valid_from,
    NULL AS valid_to,
    TRUE AS is_current
FROM raw.raw_customers rc
LEFT JOIN analytics.dim_customer dc
  ON rc.customer_id = dc.customer_id
  AND dc.is_current = TRUE
WHERE dc.customer_key IS NULL;
