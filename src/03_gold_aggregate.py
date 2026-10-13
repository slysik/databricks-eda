# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 03. Gold: Business Aggregations
# MAGIC
# MAGIC **Input:** `retail_prod.silver.sales_cleaned`
# MAGIC **Output:** `retail_prod.gold.gold_daily_kpis` + `retail_prod.gold.gold_customer_features`
# MAGIC
# MAGIC Pre-aggregated for sub-second BI and Genie response.

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.gold")

# -- Table 1: Daily KPIs --
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.gold_daily_kpis AS
WITH daily_base AS (
    SELECT
        CAST(invoice_date AS DATE) AS invoice_date,
        invoice,
        quantity,
        price,
        is_cancellation,
        (quantity * price) AS line_revenue
    FROM {catalog}.silver.sales_cleaned
)
SELECT
    invoice_date,
    SUM(CASE WHEN quantity > 0 THEN line_revenue ELSE 0 END) AS gross_revenue,
    ABS(SUM(CASE WHEN quantity < 0 THEN line_revenue ELSE 0 END)) AS refunds,
    SUM(line_revenue) AS net_revenue,
    COUNT(DISTINCT invoice) AS total_orders,
    COUNT(DISTINCT CASE WHEN is_cancellation THEN invoice END) AS cancellations,
    ROUND(COUNT(DISTINCT CASE WHEN is_cancellation THEN invoice END) * 100.0
          / NULLIF(COUNT(DISTINCT invoice), 0), 2) AS cancellation_rate_pct,
    ROUND(SUM(line_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2) AS avg_order_value
FROM daily_base
GROUP BY invoice_date
ORDER BY invoice_date
""")

# -- Table 2: Customer Features (RFM + LTV) --
spark.sql(f"""
CREATE OR REPLACE TABLE {catalog}.gold.gold_customer_features AS
WITH customer_base AS (
    SELECT
        customer_id,
        resolved_customer_id,
        is_guest_checkout,
        invoice,
        invoice_date,
        quantity,
        price,
        line_type,
        (quantity * price) AS line_revenue
    FROM {catalog}.silver.sales_stitched
    WHERE line_type = 'sale' AND quantity > 0
)
SELECT
    customer_id,
    resolved_customer_id,
    is_guest_checkout,
    COUNT(DISTINCT invoice) AS order_count,
    SUM(line_revenue) AS total_spend,
    AVG(line_revenue) AS avg_order_value,
    DATEDIFF(CURRENT_DATE(), MAX(invoice_date)) AS days_since_last_order,
    DATEDIFF(MAX(invoice_date), MIN(invoice_date)) AS customer_tenure_days,
    COUNT(DISTINCT CAST(invoice_date AS DATE)) AS active_days,
    ROUND(SUM(CASE WHEN quantity < 0 THEN line_revenue ELSE 0 END) / NULLIF(SUM(line_revenue), 0) * 100, 2) AS return_rate_pct,
    -- RFM scoring
    NTILE(5) OVER (ORDER BY DATEDIFF(CURRENT_DATE(), MAX(invoice_date)) DESC) AS recency_score,
    NTILE(5) OVER (ORDER BY COUNT(DISTINCT invoice)) AS frequency_score,
    NTILE(5) OVER (ORDER BY SUM(line_revenue)) AS monetary_score
FROM customer_base
GROUP BY customer_id, resolved_customer_id, is_guest_checkout
""")

print(f"✓ Gold tables created in {catalog}.gold")
print(f"  - gold_daily_kpis: daily aggregations")
print(f"  - gold_customer_features: RFM + LTV per customer")