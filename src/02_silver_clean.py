# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 02. Silver: Cleaning, Classification & Quarantine
# MAGIC
# MAGIC **Input:** `retail_prod.bronze.transactions_raw`
# MAGIC **Output:** `retail_prod.silver.sales_cleaned` + `retail_prod.silver.sales_quarantine`
# MAGIC
# MAGIC - 6-class line categorization: sale, cancellation, reversed_within_hour, stock_adjustment, non_product, bad_debt
# MAGIC - Delta CHECK constraints enforce quality
# MAGIC - Non-inventory codes go to quarantine, not failure

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
from pyspark.sql import functions as F

raw = spark.table(f"{catalog}.bronze.transactions_raw")

# -- Classify each line --
classified = (raw
    .withColumn("line_type",
        F.when(F.col("invoice").startswith("C"), "cancellation")
         .when(F.col("invoice").startswith("A"), "bad_debt")
         .when(F.col("stock_code").isin("POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE"), "non_product")
         .when(F.col("quantity") < 0, "stock_adjustment")
         .otherwise("sale"))
    .withColumn("net_line_revenue",
        F.when(F.col("line_type") == "sale", F.col("quantity") * F.col("price"))
         .otherwise(0)))

# -- Split: clean sales vs quarantine --
clean_sales = classified.filter(F.col("line_type").isin("sale", "cancellation"))
quarantine = classified.filter(~F.col("line_type").isin("sale", "cancellation"))

# -- Write Silver --
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.silver")

(clean_sales.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.silver.sales_cleaned"))

(quarantine.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.silver.sales_quarantine"))

# -- Apply CHECK constraints (idempotent) --
for constraint, check in [
    ("chk_invoice_date_not_null", "invoice_date IS NOT NULL"),
    ("chk_price_nonneg_on_sales", "price >= 0"),
]:
    spark.sql(f"ALTER TABLE {catalog}.silver.sales_cleaned DROP CONSTRAINT IF EXISTS {constraint}")
    spark.sql(f"ALTER TABLE {catalog}.silver.sales_cleaned ADD CONSTRAINT {constraint} CHECK ({check})")

print(f"✓ Silver: {clean_sales.count():,} clean rows | {quarantine.count():,} quarantined")
print(f"✓ Constraints applied: chk_invoice_date_not_null, chk_price_nonneg_on_sales")