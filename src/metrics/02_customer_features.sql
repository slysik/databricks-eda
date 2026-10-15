-- Metric View: Customer Features
-- Source: retail_prod.gold.gold_customer_features
-- Purpose: Governed customer segmentation and RFM metrics
-- Note: Materialization not supported — source table has UC column mask on
--       customer_id using IS_ACCOUNT_GROUP_MEMBER() (invoker-dependent).
--       Queries still work; they scan the source table directly.

CREATE OR REPLACE VIEW retail_prod.metrics.customer_features
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: retail_prod.gold.gold_customer_features
comment: "Customer RFM and LTV metrics for segmentation and analysis"
dimensions:
  - name: Is Guest Checkout
    expr: is_guest_checkout
    comment: "TRUE for anonymous guest orders"
  - name: Recency Segment
    expr: "CASE WHEN recency_score >= 4 THEN 'Recent' WHEN recency_score >= 2 THEN 'Moderate' ELSE 'Lapsed' END"
  - name: Value Segment
    expr: "CASE WHEN monetary_score >= 4 AND frequency_score >= 4 THEN 'VIP' WHEN monetary_score >= 3 THEN 'Regular' ELSE 'Low Value' END"
measures:
  - name: Customer Count
    expr: COUNT(*)
  - name: Total Spend
    expr: SUM(total_spend)
  - name: Avg Spend
    expr: ROUND(AVG(total_spend), 2)
  - name: Avg Orders
    expr: ROUND(AVG(order_count), 2)
  - name: Avg Return Rate
    expr: ROUND(AVG(return_rate_pct), 2)
  - name: Guest Checkout Share
    expr: "ROUND(SUM(CASE WHEN is_guest_checkout THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)"
$$