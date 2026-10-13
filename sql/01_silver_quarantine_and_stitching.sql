-- 01_silver_quarantine_and_stitching.sql
-- Enforces Delta CHECK constraints, creates quarantine audit tables,
-- and performs deterministic identity stitching on unauthenticated checkouts.

CREATE SCHEMA IF NOT EXISTS retail_prod.silver;

-- 1. Hard Data Quality Constraints
ALTER TABLE retail_prod.silver.sales_cleaned DROP CONSTRAINT IF EXISTS chk_invoice_date_not_null;
ALTER TABLE retail_prod.silver.sales_cleaned DROP CONSTRAINT IF EXISTS chk_price_nonneg_on_sales;

ALTER TABLE retail_prod.silver.sales_cleaned ADD CONSTRAINT chk_invoice_date_not_null CHECK (invoice_date IS NOT NULL);
ALTER TABLE retail_prod.silver.sales_cleaned ADD CONSTRAINT chk_price_nonneg_on_sales CHECK (price >= 0 OR is_cancellation = TRUE);

-- 2. Audit Quarantine Table: Isolates non-inventory service codes without breaking pipelines
CREATE OR REPLACE TABLE retail_prod.silver.sales_quarantine AS
SELECT
    invoice, stock_code, description, quantity, invoice_date,
    price, customer_id, country, is_cancellation, net_line_revenue, line_type,
    CASE
        WHEN stock_code = 'POST' THEN 'Postage fee'
        WHEN stock_code = 'DOT' THEN 'Postage (DOT)'
        WHEN stock_code = 'M' THEN 'Manual adjustment'
        WHEN stock_code = 'D' THEN 'Discount'
        WHEN stock_code = 'BANK CHARGES' THEN 'Bank fee'
        WHEN stock_code = 'AMAZONFEE' THEN 'Amazon fee'
        WHEN stock_code = 'S' THEN 'Sample'
        WHEN stock_code = 'CRUK' THEN 'CRUK charity'
        WHEN stock_code = 'B' THEN 'Bad debt'
        WHEN stock_code = 'TEST001' THEN 'Test entry'
        WHEN stock_code = 'PADS' THEN 'Pads adjustment'
        WHEN stock_code = 'ADJUST' THEN 'Inventory adjust'
        WHEN stock_code = 'ADJUST2' THEN 'Inventory adjust 2'
        ELSE 'Other'
    END AS rejection_reason,
    current_timestamp() AS quarantined_at
FROM retail_prod.silver.sales_cleaned
WHERE line_type = 'overhead';

-- 3. Customer Identity Stitching: Resolves anonymous guest orders into customer journeys
CREATE OR REPLACE TABLE retail_prod.silver.sales_stitched AS
SELECT
    invoice, stock_code, description, quantity, invoice_date,
    price, customer_id, country, is_cancellation, net_line_revenue, line_type,
    COALESCE(
        CAST(customer_id AS STRING),
        CONCAT('GUEST_', SHA2(CONCAT(invoice, country, CAST(invoice_date AS DATE)), 256))
    ) AS resolved_customer_id,
    (customer_id IS NULL) AS is_guest_checkout
FROM retail_prod.silver.sales_cleaned;
