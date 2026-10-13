-- 04_golden_queries.sql
-- Five verified benchmark SQL queries serving as Genie ground truth.

-- Golden Query 1: Top 5 revenue days in Q4 2010
SELECT
    invoice_date,
    net_revenue,
    total_orders,
    cancellation_rate_pct
FROM retail_prod.gold.gold_daily_kpis
WHERE invoice_date >= '2010-10-01' AND invoice_date < '2011-01-01'
ORDER BY net_revenue DESC
LIMIT 5;

-- Golden Query 2: Top 10 VIP customers at risk of churn
SELECT
    customer_id,
    last_purchase_date,
    lifetime_orders,
    net_lifetime_spend,
    DATEDIFF('2011-12-09', last_purchase_date) AS days_inactive
FROM retail_prod.gold.gold_customer_features
WHERE DATEDIFF('2011-12-09', last_purchase_date) > 180
  AND lifetime_orders > 5
ORDER BY net_lifetime_spend DESC
LIMIT 10;

-- Golden Query 3: Return rate by country
SELECT
    country,
    COUNT(DISTINCT CASE WHEN is_cancellation = TRUE THEN invoice END) AS cancelled_orders,
    COUNT(DISTINCT invoice) AS total_orders,
    CAST(CAST(COUNT(DISTINCT CASE WHEN is_cancellation = TRUE THEN invoice END) AS DOUBLE) / COUNT(DISTINCT invoice) * 100 AS DECIMAL(5,2)) AS return_rate_pct
FROM retail_prod.silver.sales_cleaned
GROUP BY country
ORDER BY return_rate_pct DESC;

-- Golden Query 4: Holiday 2010 vs 2009 YoY comparison
SELECT
    YEAR(invoice_date) AS year,
    SUM(gross_revenue) AS gross_revenue,
    SUM(net_revenue) AS net_revenue,
    SUM(total_orders) AS total_orders
FROM retail_prod.gold.gold_daily_kpis
WHERE (invoice_date >= '2009-12-01' AND invoice_date < '2010-01-01')
   OR (invoice_date >= '2010-12-01' AND invoice_date < '2011-01-01')
GROUP BY YEAR(invoice_date)
ORDER BY year;

-- Golden Query 5: Guest checkout revenue share
SELECT
    CASE WHEN customer_id IS NULL THEN 'Guest' ELSE 'Identified' END AS checkout_type,
    SUM(CASE WHEN quantity > 0 THEN net_line_revenue ELSE 0 END) AS gross_revenue,
    CAST(CAST(SUM(CASE WHEN quantity > 0 THEN net_line_revenue ELSE 0 END) AS DOUBLE) / SUM(SUM(CASE WHEN quantity > 0 THEN net_line_revenue ELSE 0 END)) OVER () * 100 AS DECIMAL(5,2)) AS revenue_pct
FROM retail_prod.silver.sales_cleaned
GROUP BY CASE WHEN customer_id IS NULL THEN 'Guest' ELSE 'Identified' END
ORDER BY checkout_type;
