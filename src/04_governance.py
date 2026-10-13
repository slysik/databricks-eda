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
# -- Create governance roles (idempotent) --
spark.sql("CREATE ROLE IF NOT EXISTS retail_analyst")
spark.sql("CREATE ROLE IF NOT EXISTS retail_admin")

# -- Grant base access --
spark.sql(f"GRANT USE SCHEMA ON SCHEMA {catalog}.gold TO retail_analyst")
spark.sql(f"GRANT SELECT ON SCHEMA {catalog}.gold TO retail_analyst")
spark.sql(f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.gold TO retail_admin")

# -- Column mask: hide customer_id from non-admin --
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.mask_customer_id(customer_id INT)
RETURN
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('retail_admin') THEN customer_id
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
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('retail_admin') THEN TRUE
       ELSE country = 'United Kingdom'
  END
""")

spark.sql(f"""
ALTER TABLE {catalog}.silver.sales_cleaned
SET ROW FILTER {catalog}.gold.filter_uk_region ON (country)
""")

print(f"✓ Governance applied:")
print(f"  - Column mask: customer_id masked for non-admin")
print(f"  - Row filter: UK-only for retail_analyst role")
print(f"  - Genie will inherit both automatically")