-- Metric View: Sales by Country (with materialization)
-- Source: retail_prod.silver.sales_cleaned
-- Purpose: Governed country-level and product-level sales metrics
-- Materialization: Pre-computes country aggregations for fast geo dashboards

CREATE OR REPLACE VIEW retail_prod.metrics.sales_by_country
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: retail_prod.silver.sales_cleaned
comment: "Sales metrics by country, product, and time period (materialized)"
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
materialization:
  schedule: every 6 hours
  mode: relaxed
  materialized_views:
    - name: country_baseline
      type: unaggregated
    - name: country_monthly
      type: aggregated
      dimensions:
        - Country
        - Sale Month
      measures:
        - Revenue
        - Units Sold
        - Order Count
    - name: product_summary
      type: aggregated
      dimensions:
        - Country
        - Stock Code
        - Product Description
      measures:
        - Revenue
        - Units Sold
        - Order Count
        - Avg Unit Price
$$