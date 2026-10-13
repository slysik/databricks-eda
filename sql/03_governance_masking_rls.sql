-- 03_governance_masking_rls.sql
-- Enforces Unity Catalog dynamic column masking and row-level security.

-- 1. Dynamic Column Mask: Protect Customer PII for Non-Admin Roles
CREATE OR REPLACE FUNCTION retail_prod.gold.mask_customer_id(customer_id STRING)
RETURNS STRING
RETURN CASE
    WHEN is_member('admin_group') THEN customer_id
    ELSE '***MASKED***'
END;

ALTER TABLE retail_prod.gold.gold_customer_features
    ALTER COLUMN customer_id SET MASK retail_prod.gold.mask_customer_id;

-- 2. Row Filter: Enforce Regional Access Control (UK Domestic vs Global)
CREATE OR REPLACE FUNCTION retail_prod.silver.filter_uk_region(country STRING)
RETURNS BOOLEAN
RETURN country = 'United Kingdom' OR is_member('global_sales_group');

ALTER TABLE retail_prod.silver.sales_stitched
    SET ROW FILTER retail_prod.silver.filter_uk_region ON (country);

-- 3. Policy Verification
SELECT 'Column mask: gold_customer_features.customer_id' AS governance_rule
UNION ALL
SELECT 'Row filter: sales_stitched (country)'
UNION ALL
SELECT 'NOTE: Non-admin users see masked IDs and UK-only rows';
