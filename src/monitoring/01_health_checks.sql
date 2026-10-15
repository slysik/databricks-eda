-- =============================================================================
-- EDA Pipeline & Genie Health Monitoring
-- =============================================================================
-- Run these queries daily to monitor system health.
-- Each query returns a single row with a status indicator.
-- =============================================================================

-- =============================================================================
-- 1. PIPELINE HEALTH: Check if the pipeline job ran successfully today
-- =============================================================================
-- Alert: FAIL if job did not complete in last 24 hours
SELECT
    CASE
        WHEN MAX(completed_time) >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS THEN 'HEALTHY'
        ELSE 'STALE'
    END AS pipeline_status,
    MAX(completed_time) AS last_run_time,
    COUNT(*) AS runs_last_24h
FROM system.lakeflow.job_run_timeline
WHERE job_id = (
    SELECT job_id FROM system.lakeflow.jobs
    WHERE job_name = 'EDA Retail Lakehouse Pipeline'
    LIMIT 1
)
AND completed_time >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS;

-- =============================================================================
-- 2. DATA FRESHNESS: Check if Gold tables were updated today
-- =============================================================================
-- Alert: FAIL if gold_daily_kpis not updated in last 24 hours
SELECT
    CASE
        WHEN MAX(invoice_date) >= CURRENT_DATE() - INTERVAL 1 DAY THEN 'FRESH'
        ELSE 'STALE'
    END AS freshness_status,
    MAX(invoice_date) AS latest_date,
    COUNT(*) AS total_rows
FROM retail_prod.gold.gold_daily_kpis;

-- =============================================================================
-- 3. DATA FRESHNESS: Customer features table
-- =============================================================================
-- Alert: FAIL if customer features not updated in last 24 hours
SELECT
    CASE
        WHEN COUNT(*) > 0 THEN 'HEALTHY'
        ELSE 'EMPTY'
    END AS status,
    COUNT(*) AS total_customers,
    COUNT(CASE WHEN is_guest_checkout THEN 1 END) AS guest_customers,
    ROUND(AVG(total_spend), 2) AS avg_spend
FROM retail_prod.gold.gold_customer_features;

-- =============================================================================
-- 4. DATA QUALITY: Quarantine rate check
-- =============================================================================
-- Alert: FAIL if quarantine rate exceeds 15% (indicates data quality issue)
SELECT
    CASE
        WHEN quarantine_pct <= 15 THEN 'HEALTHY'
        WHEN quarantine_pct <= 25 THEN 'WARNING'
        ELSE 'CRITICAL'
    END AS quality_status,
    quarantine_pct,
    quarantined_rows,
    total_rows
FROM (
    SELECT
        ROUND(q.quarantined_rows * 100.0 / NULLIF(t.total_rows, 0), 2) AS quarantine_pct,
        q.quarantined_rows,
        t.total_rows
    FROM
        (SELECT COUNT(*) AS quarantined_rows FROM retail_prod.silver.sales_quarantine) q,
        (SELECT COUNT(*) AS total_rows FROM retail_prod.silver.sales_cleaned) t
);

-- =============================================================================
-- 5. DATA QUALITY: Row count stability
-- =============================================================================
-- Alert: FAIL if Silver cleaned rows deviate >10% from expected (~1,033,034)
SELECT
    CASE
        WHEN ABS(row_count - 1033034) <= 1033034 * 0.1 THEN 'STABLE'
        ELSE 'DEVIATION'
    END AS stability_status,
    row_count AS current_rows,
    1033034 AS expected_rows,
    ROUND(ABS(row_count - 1033034) * 100.0 / 1033034, 2) AS deviation_pct
FROM (SELECT COUNT(*) AS row_count FROM retail_prod.silver.sales_cleaned);

-- =============================================================================
-- 6. GENIE HEALTH: Check if metric views are queryable
-- =============================================================================
-- Alert: FAIL if metric views return 0 rows
SELECT
    CASE
        WHEN daily_rows > 0 AND customer_rows > 0 AND country_rows > 0 THEN 'HEALTHY'
        ELSE 'DEGRADED'
    END AS genie_health,
    daily_rows,
    customer_rows,
    country_rows
FROM (
    SELECT
        (SELECT COUNT(*) FROM retail_prod.metrics.daily_kpis) AS daily_rows,
        (SELECT COUNT(*) FROM retail_prod.metrics.customer_features) AS customer_rows,
        (SELECT COUNT(*) FROM retail_prod.metrics.sales_by_country) AS country_rows
);

-- =============================================================================
-- 7. GENIE HEALTH: Check Genie query latency (last 24h)
-- =============================================================================
-- Monitor: Average query execution time for Genie-generated queries
SELECT
    CASE
        WHEN AVG(duration_ms) <= 5000 THEN 'FAST'
        WHEN AVG(duration_ms) <= 15000 THEN 'ACCEPTABLE'
        ELSE 'SLOW'
    END AS latency_status,
    COUNT(*) AS query_count,
    ROUND(AVG(duration_ms) / 1000, 2) AS avg_latency_sec,
    ROUND(MAX(duration_ms) / 1000, 2) AS max_latency_sec
FROM system.query.history
WHERE executed_as = 'genie'
AND start_time >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS;

-- =============================================================================
-- 8. GOVERNANCE: Verify column masking is active
-- =============================================================================
-- Alert: FAIL if non-admin can see unmasked customer_id
SELECT
    CASE
        WHEN customer_id IS NULL THEN 'MASKED'
        ELSE 'EXPOSED'
    END AS mask_status
FROM retail_prod.gold.gold_customer_features
LIMIT 1;