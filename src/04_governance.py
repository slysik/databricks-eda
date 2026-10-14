# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 04. Unity Catalog Governance
# MAGIC
# MAGIC **Applies:** Column masking (PII) + Row-level security (regional access)
# MAGIC
# MAGIC - `customer_id` masked as `***MASKED***` for non-admin roles
# MAGIC - UK managers see only UK rows; global leadership sees all 43 countries
# MAGIC - Genie inherits both automatically

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
dbutils.widgets.text("warehouse_id", "")
catalog = dbutils.widgets.get("catalog")
warehouse_id = dbutils.widgets.get("warehouse_id")

# COMMAND ----------
# -- Column mask: hide customer_id from non-admin --
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.mask_customer_id(customer_id INT)
RETURN
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('admins') THEN customer_id
       ELSE NULL
  END
""")

spark.sql(f"""
ALTER TABLE {catalog}.gold.gold_customer_features
ALTER COLUMN customer_id SET MASK {catalog}.gold.mask_customer_id
""")

# -- Row filter: UK managers see only UK data --
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.filter_uk_region(country STRING)
RETURN
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('admins') THEN TRUE
       ELSE country = 'United Kingdom'
  END
""")

spark.sql(f"""
ALTER TABLE {catalog}.silver.sales_stitched
SET ROW FILTER {catalog}.gold.filter_uk_region ON (country)
""")

print(f"✓ Governance applied:")
print(f"  - Column mask: customer_id masked for non-admin")
print(f"  - Row filter: UK-only for non-admin role (on sales_stitched)")
print(f"  - Genie will inherit both automatically")