# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## EDA Pipeline & Genie Health Monitoring
# MAGIC
# MAGIC Runs all health monitoring queries and logs results.
# MAGIC Schedule: Daily at 8 AM ET via DAB job.

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 1. Pipeline Health

# COMMAND ----------
pipeline_status = spark.sql("""
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
AND completed_time >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS
""")
display(pipeline_status)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Data Freshness

# COMMAND ----------
freshness = spark.sql(f"""
SELECT
    'gold_daily_kpis' AS table_name,
    CASE WHEN MAX(invoice_date) >= CURRENT_DATE() - INTERVAL 1 DAY THEN 'FRESH' ELSE 'STALE' END AS status,
    MAX(invoice_date) AS latest_date,
    COUNT(*) AS total_rows
FROM {catalog}.gold.gold_daily_kpis

UNION ALL

SELECT
    'gold_customer_features',
    CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'EMPTY' END,
    NULL,
    COUNT(*)
FROM {catalog}.gold.gold_customer_features
""")
display(freshness)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Data Quality

# COMMAND ----------
quality = spark.sql(f"""
SELECT
    (SELECT COUNT(*) FROM {catalog}.silver.sales_cleaned) AS clean_rows,
    (SELECT COUNT(*) FROM {catalog}.silver.sales_quarantine) AS quarantine_rows,
    ROUND(
        (SELECT COUNT(*) FROM {catalog}.silver.sales_quarantine) * 100.0 /
        NULLIF((SELECT COUNT(*) FROM {catalog}.silver.sales_cleaned), 0), 2
    ) AS quarantine_rate_pct
""")
display(quality)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 4. Metric View Health

# COMMAND ----------
metric_health = spark.sql(f"""
SELECT
    'daily_kpis' AS metric_view,
    COUNT(*) AS row_count,
    CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'EMPTY' END AS status
FROM {catalog}.metrics.daily_kpis

UNION ALL

SELECT
    'customer_features',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'EMPTY' END
FROM {catalog}.metrics.customer_features

UNION ALL

SELECT
    'sales_by_country',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN 'HEALTHY' ELSE 'EMPTY' END
FROM {catalog}.metrics.sales_by_country
""")
display(metric_health)

# COMMAND ----------
# MAGIC %md
# MAGIC ### 5. Governance Check

# COMMAND ----------
governance = spark.sql(f"""
SELECT
    CASE WHEN customer_id IS NULL THEN 'MASKED' ELSE 'EXPOSED' END AS mask_status,
    COUNT(*) AS sample_rows
FROM {catalog}.gold.gold_customer_features
LIMIT 1
""")
display(governance)

# COMMAND ----------
# MAGIC %md
# MAGIC ### Summary

# COMMAND ----------
print("=" * 60)
print("EDA HEALTH CHECK COMPLETE")
print("=" * 60)
print(f"Pipeline: {pipeline_status.collect()[0]['pipeline_status']}")
print(f"Freshness: {freshness.collect()[0]['status']}")
print(f"Quarantine Rate: {quality.collect()[0]['quarantine_rate_pct']}%")
print(f"Metric Views: {metric_health.count()} views checked")
print(f"Governance: {governance.collect()[0]['mask_status']}")
print("=" * 60)