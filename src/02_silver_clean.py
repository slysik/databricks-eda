# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 02. Silver: Cleaning, Classification & Quarantine
# MAGIC
# MAGIC **Input:** `retail_prod.bronze.transactions_raw`
# MAGIC **Output:** `retail_prod.silver.sales_cleaned` + `retail_prod.silver.sales_quarantine` + `retail_prod.silver.sales_stitched`
# MAGIC
# MAGIC - 5-class line categorization: sale, cancellation, stock_adjustment, non_product, bad_debt
# MAGIC - Delta CHECK constraints enforce quality
# MAGIC - Non-inventory codes go to quarantine, not failure
# MAGIC - Guest surrogate id: one hashed id per guest invoice (does not link a guest's separate invoices)

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
from pyspark.sql import functions as F

raw = spark.table(f"{catalog}.bronze.transactions_raw")

# -- Cast types (source data has string columns) --
raw = (raw
    .withColumn("quantity", F.col("quantity").cast("int"))
    .withColumn("price", F.col("price").cast("decimal(12,3)"))
    .withColumn("invoice_date", F.col("invoice_date").cast("timestamp"))
    .withColumn("customer_id", F.col("customer_id").cast("int")))

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
         .otherwise(F.lit(0).cast("decimal(12,3)"))
         .cast("decimal(12,3)"))
    .withColumn("is_cancellation", F.col("line_type") == "cancellation"))

# -- Split: clean sales vs quarantine --
clean_sales = classified.filter(F.col("line_type").isin("sale", "cancellation"))
quarantine = classified.filter(~F.col("line_type").isin("sale", "cancellation"))

# -- Customer identity stitching --
stitched = (clean_sales
    .withColumn("resolved_customer_id",
        F.coalesce(
            F.col("customer_id").cast("string"),
            F.concat(F.lit("GUEST_"), F.sha2(F.concat(F.col("invoice"), F.col("country"), F.col("invoice_date").cast("date")), 256))
        ))
    .withColumn("is_guest_checkout", F.col("customer_id").isNull()))

# -- Write Silver --
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.silver")

# Drop existing tables for clean rebuild (idempotent)
for table in ["sales_cleaned", "sales_quarantine", "sales_stitched"]:
    spark.sql(f"DROP TABLE IF EXISTS {catalog}.silver.{table}")

(clean_sales.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.silver.sales_cleaned"))

(quarantine.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.silver.sales_quarantine"))

(stitched.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.silver.sales_stitched"))

# -- Apply CHECK constraints (idempotent) --
for constraint, check in [
    ("chk_invoice_date_not_null", "invoice_date IS NOT NULL"),
    ("chk_price_nonneg_on_sales", "price >= 0"),
]:
    spark.sql(f"ALTER TABLE {catalog}.silver.sales_cleaned DROP CONSTRAINT IF EXISTS {constraint}")
    spark.sql(f"ALTER TABLE {catalog}.silver.sales_cleaned ADD CONSTRAINT {constraint} CHECK ({check})")

print(f"✓ Silver: {clean_sales.count():,} clean rows | {quarantine.count():,} quarantined")
print(f"✓ Customer stitching: {stitched.filter(F.col('is_guest_checkout')).count():,} guest checkouts identified")
print(f"✓ Constraints applied: chk_invoice_date_not_null, chk_price_nonneg_on_sales")