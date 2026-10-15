-- Metric View: Daily KPIs
-- Source: retail_prod.gold.gold_daily_kpis
-- Purpose: Governed revenue, order, and cancellation metrics
-- Usage: SELECT MEASURE(`Net Revenue`) AS net_rev FROM retail_prod.metrics.daily_kpis GROUP BY `Invoice Month`

CREATE OR REPLACE VIEW retail_prod.metrics.daily_kpis
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: retail_prod.gold.gold_daily_kpis
comment: "Daily retail KPIs - revenue, orders, cancellations, AOV"
dimensions:
  - name: Invoice Date
    expr: invoice_date
    comment: "Calendar date of transactions"
  - name: Invoice Month
    expr: DATE_TRUNC('MONTH', invoice_date)
    comment: "Month of transactions"
  - name: Invoice Quarter
    expr: "CONCAT('Q', QUARTER(invoice_date), ' ', YEAR(invoice_date))"
    comment: "Quarter label"
  - name: Invoice Year
    expr: YEAR(invoice_date)
    comment: "Year of transactions"
measures:
  - name: Gross Revenue
    expr: SUM(gross_revenue)
    comment: "Total revenue from positive-quantity sales"
  - name: Net Revenue
    expr: SUM(net_revenue)
    comment: "Gross revenue minus refunds and cancellations"
  - name: Refunds
    expr: SUM(refunds)
    comment: "Total refunds and cancellations"
  - name: Total Orders
    expr: SUM(total_orders)
    comment: "Count of distinct invoices"
  - name: Cancellations
    expr: SUM(cancellations)
    comment: "Count of cancellation invoices"
  - name: Cancellation Rate
    expr: "ROUND(SUM(cancellations) * 100.0 / NULLIF(SUM(total_orders), 0), 2)"
    comment: "Cancellation rate as percentage of total orders"
  - name: Avg Order Value
    expr: "ROUND(SUM(net_revenue) / NULLIF(SUM(total_orders), 0), 2)"
    comment: "Average net revenue per order"
  - name: Revenue per Day
    expr: "ROUND(SUM(net_revenue) / NULLIF(COUNT(DISTINCT invoice_date), 0), 2)"
    comment: "Average daily net revenue"
$$