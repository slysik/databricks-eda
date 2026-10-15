-- Metric View: Sales by Country
-- Source: retail_prod.silver.sales_cleaned
-- Purpose: Governed country-level and product-level sales metrics
-- Usage: SELECT `Country`, MEASURE(`Revenue`) AS rev FROM retail_prod.metrics.sales_by_country GROUP BY `Country` ORDER BY rev DESC

CREATE OR REPLACE VIEW retail_prod.metrics.sales_by_country
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: retail_prod.silver.sales_cleaned
comment: "Sales metrics by country, product, and time period"
filter: "line_type = 'sale' AND quantity > 0"
dimensions:
  - name: Country
    expr: country
  - name: Sale Month
    expr: DATE_TRUNC('MONTH', invoice_date)
  - name: Stock Code
    expr: stock_code
  - name: Product Description
    expr: description
measures:
  - name: Revenue
    expr: SUM(net_line_revenue)
  - name: Units Sold
    expr: SUM(quantity)
  - name: Order Count
    expr: COUNT(DISTINCT invoice)
  - name: Avg Unit Price
    expr: ROUND(AVG(price), 2)
$$