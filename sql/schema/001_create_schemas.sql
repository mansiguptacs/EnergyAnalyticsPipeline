-- ==============================================================================
-- 001: Create Schemas
-- ==============================================================================
-- Creates the four schema layers of the medallion architecture.
--
-- raw       → Bronze layer: exact copy of source data, no transformations
-- staging   → Silver layer: cleaned, typed, deduplicated data
-- analytics → Gold layer: business-ready star schema tables
-- dq        → Data quality: check results, quarantine, pipeline metrics
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS dq;

COMMENT ON SCHEMA raw       IS 'Raw/Bronze layer – exact copy of source data, no transformations';
COMMENT ON SCHEMA staging   IS 'Staging/Silver layer – cleaned, typed, deduplicated data';
COMMENT ON SCHEMA analytics IS 'Analytics/Gold layer – business-ready star schema tables';
COMMENT ON SCHEMA dq        IS 'Data quality – check results, quarantine, pipeline metrics';
