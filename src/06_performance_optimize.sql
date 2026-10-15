-- Performance Optimizations for Genie Queries
-- Run after Gold tables are built
-- These optimizations reduce Genie exploration time and improve query performance

-- 1. Column Statistics (helps Genie understand data distribution)
ANALYZE TABLE retail_prod.gold.gold_daily_kpis COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE retail_prod.gold.gold_customer_features COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE retail_prod.silver.sales_cleaned COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE retail_prod.silver.sales_stitched COMPUTE STATISTICS FOR ALL COLUMNS;

-- 2. Liquid Clustering (organizes data by common filter columns)
ALTER TABLE retail_prod.gold.gold_daily_kpis CLUSTER BY (invoice_date);
ALTER TABLE retail_prod.gold.gold_customer_features CLUSTER BY (customer_id);
ALTER TABLE retail_prod.silver.sales_cleaned CLUSTER BY (invoice_date, country);
ALTER TABLE retail_prod.silver.sales_stitched CLUSTER BY (invoice_date, country);

-- 3. Optimize tables (compacts small files, applies clustering)
OPTIMIZE retail_prod.gold.gold_daily_kpis;
OPTIMIZE retail_prod.gold.gold_customer_features;
OPTIMIZE retail_prod.silver.sales_cleaned;
OPTIMIZE retail_prod.silver.sales_stitched;

-- 4. Lean summary view (fewer columns = less Genie exploration)
CREATE OR REPLACE VIEW retail_prod.gold.gold_customer_summary AS
SELECT 
    customer_id,
    resolved_customer_id,
    is_guest_checkout,
    order_count,
    total_spend,
    avg_order_value,
    days_since_last_order,
    recency_score,
    frequency_score,
    monetary_score,
    return_rate_pct
FROM retail_prod.gold.gold_customer_features;

-- 5. Pre-joined table (avoids runtime joins for common queries)
CREATE OR REPLACE TABLE retail_prod.gold.gold_customer_orders AS
SELECT 
    c.resolved_customer_id,
    c.is_guest_checkout,
    c.recency_score,
    c.frequency_score,
    c.monetary_score,
    s.invoice,
    s.invoice_date,
    s.stock_code,
    s.description,
    s.quantity,
    s.price,
    s.net_line_revenue,
    s.country
FROM retail_prod.gold.gold_customer_features c
JOIN retail_prod.silver.sales_stitched s 
    ON c.resolved_customer_id = s.resolved_customer_id
WHERE s.line_type = 'sale';

-- 6. Cluster and optimize the pre-joined table
ALTER TABLE retail_prod.gold.gold_customer_orders CLUSTER BY (country, invoice_date);
OPTIMIZE retail_prod.gold.gold_customer_orders;
ANALYZE TABLE retail_prod.gold.gold_customer_orders COMPUTE STATISTICS FOR ALL COLUMNS;

-- 7. Enable IO cache (run on warehouse)
SET spark.databricks.io.cache.enabled = true;
SET spark.sql.autoBroadcastJoinThreshold = 104857600;  -- 100MB