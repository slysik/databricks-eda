-- 02_gold_medallion.sql
-- Pre-aggregates Silver data into optimized Gold tables for sub-second BI & Genie Q&A.

CREATE SCHEMA IF NOT EXISTS retail_prod.gold;

-- 1. Gold Daily KPIs
CREATE OR REPLACE TABLE retail_prod.gold.gold_daily_kpis AS
WITH daily_base AS (
    SELECT
        CAST(invoice_date AS DATE) AS invoice_date,
        invoice,
        quantity,
        price,
        is_cancellation,
        (quantity * price) AS line_revenue
    FROM retail_prod.silver.sales_cleaned
)
SELECT
    invoice_date,
    SUM(CASE WHEN quantity > 0 THEN line_revenue ELSE 0 END) AS gross_revenue,
    SUM(CASE WHEN quantity < 0 THEN line_revenue ELSE 0 END) AS refund_total,
    SUM(line_revenue) AS net_revenue,
    COUNT(DISTINCT invoice) AS total_orders,
    COUNT(DISTINCT CASE WHEN is_cancellation = FALSE THEN invoice END) AS completed_orders,
    COUNT(DISTINCT CASE WHEN is_cancellation = TRUE THEN invoice END) AS cancelled_orders,
    SUM(CASE WHEN quantity > 0 THEN line_revenue ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN is_cancellation = FALSE THEN invoice END), 0) AS avg_order_value,
    CAST(CAST(COUNT(DISTINCT CASE WHEN is_cancellation = TRUE THEN invoice END) AS DOUBLE) / NULLIF(COUNT(DISTINCT invoice), 0) * 100 AS DECIMAL(5,2)) AS cancellation_rate_pct
FROM daily_base
GROUP BY invoice_date;

COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.invoice_date IS 'Calendar date of the invoice';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.gross_revenue IS 'Revenue from positive-quantity sales lines';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.refund_total IS 'Revenue from negative-quantity return lines';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.net_revenue IS 'Gross revenue plus refund total';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.total_orders IS 'Distinct invoices for the day';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.completed_orders IS 'Distinct non-cancellation invoices';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.cancelled_orders IS 'Distinct cancellation invoices';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.avg_order_value IS 'Net revenue per completed order';
COMMENT ON COLUMN retail_prod.gold.gold_daily_kpis.cancellation_rate_pct IS 'Cancelled orders as pct of total';

-- 2. Gold Customer Features (customer_id as STRING for masking compatibility)
CREATE OR REPLACE TABLE retail_prod.gold.gold_customer_features AS
WITH customer_base AS (
    SELECT customer_id, invoice, invoice_date, quantity,
           (quantity * price) AS line_revenue, is_cancellation
    FROM retail_prod.silver.sales_cleaned
    WHERE customer_id IS NOT NULL
)
SELECT
    CAST(customer_id AS STRING) AS customer_id,
    MIN(invoice_date) AS first_purchase_date,
    MAX(invoice_date) AS last_purchase_date,
    COUNT(DISTINCT invoice) AS lifetime_orders,
    SUM(quantity) AS total_units_bought,
    SUM(CASE WHEN quantity > 0 THEN line_revenue ELSE 0 END) AS lifetime_gross_revenue,
    SUM(CASE WHEN quantity < 0 THEN line_revenue ELSE 0 END) AS lifetime_refund_amount,
    SUM(line_revenue) AS net_lifetime_spend,
    CAST(CAST(SUM(CASE WHEN quantity < 0 THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0) * 100 AS DECIMAL(5,2)) AS refund_propensity_pct
FROM customer_base
GROUP BY customer_id;

COMMENT ON COLUMN retail_prod.gold.gold_customer_features.customer_id IS 'Unique customer identifier (STRING for masking)';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.first_purchase_date IS 'Earliest invoice timestamp';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.last_purchase_date IS 'Most recent invoice timestamp';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.lifetime_orders IS 'Distinct invoices over lifetime';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.total_units_bought IS 'Sum of quantity across all orders';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.lifetime_gross_revenue IS 'Revenue from positive-quantity sales lines';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.lifetime_refund_amount IS 'Revenue from negative-quantity return lines';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.net_lifetime_spend IS 'Gross revenue plus refund amount';
COMMENT ON COLUMN retail_prod.gold.gold_customer_features.refund_propensity_pct IS 'Return lines as pct of total lines';

-- 3. Optimization and Statistics for Genie Query Speed
ANALYZE TABLE retail_prod.gold.gold_daily_kpis COMPUTE STATISTICS;
OPTIMIZE retail_prod.gold.gold_daily_kpis;

ANALYZE TABLE retail_prod.gold.gold_customer_features COMPUTE STATISTICS;
OPTIMIZE retail_prod.gold.gold_customer_features;
