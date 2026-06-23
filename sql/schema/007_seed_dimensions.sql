-- ==============================================================================
-- 007: Seed Dimension Tables (dim_date and dim_time)
-- ==============================================================================
-- Pre-populates dim_date (2010-01-01 to 2030-12-31) and dim_time (96 intervals).
-- These are static dimensions that don't change with pipeline runs.
-- ==============================================================================

-- ---------------------------------------------------------------------------
-- Seed dim_date: one row per day, 2010–2030
-- ---------------------------------------------------------------------------
INSERT INTO analytics.dim_date (
    date_key, full_date, year, quarter, month, month_name,
    week_of_year, day_of_month, day_of_week, day_name,
    is_weekend, is_holiday, fiscal_year, fiscal_quarter
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER         AS date_key,
    d::DATE                                  AS full_date,
    EXTRACT(YEAR FROM d)::SMALLINT           AS year,
    EXTRACT(QUARTER FROM d)::SMALLINT        AS quarter,
    EXTRACT(MONTH FROM d)::SMALLINT          AS month,
    TO_CHAR(d, 'Month')                      AS month_name,
    EXTRACT(WEEK FROM d)::SMALLINT           AS week_of_year,
    EXTRACT(DAY FROM d)::SMALLINT            AS day_of_month,
    EXTRACT(ISODOW FROM d)::SMALLINT - 1     AS day_of_week,  -- 0=Mon, 6=Sun
    TO_CHAR(d, 'Day')                        AS day_name,
    EXTRACT(ISODOW FROM d) IN (6, 7)         AS is_weekend,
    FALSE                                    AS is_holiday,
    -- Fiscal year = calendar year (customize per org)
    EXTRACT(YEAR FROM d)::SMALLINT           AS fiscal_year,
    EXTRACT(QUARTER FROM d)::SMALLINT        AS fiscal_quarter
FROM generate_series('2010-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (date_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Seed dim_time: one row per 15-minute interval (96 rows)
-- ---------------------------------------------------------------------------
INSERT INTO analytics.dim_time (
    time_key, hour, minute, time_of_day, period_name, is_peak, is_business_hr
)
SELECT
    (h * 100 + m)::INTEGER                   AS time_key,
    h::SMALLINT                              AS hour,
    m::SMALLINT                              AS minute,
    MAKE_TIME(h, m, 0)                       AS time_of_day,
    CASE
        WHEN h BETWEEN 6  AND 11 THEN 'morning'
        WHEN h BETWEEN 12 AND 16 THEN 'afternoon'
        WHEN h BETWEEN 17 AND 21 THEN 'evening'
        ELSE 'night'
    END                                      AS period_name,
    -- Peak hours: 07:00–21:00 (used for time-of-use tariff calculations)
    h BETWEEN 7 AND 20                       AS is_peak,
    -- Business hours: 09:00–17:00
    h BETWEEN 9 AND 16                       AS is_business_hr
FROM
    generate_series(0, 23) AS h,
    generate_series(0, 45, 15) AS m
ON CONFLICT (time_key) DO NOTHING;
