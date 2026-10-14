# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 01. Bronze Ingestion & Deduplication
# MAGIC
# MAGIC **Input:** Existing `retail_source.online_retail.transactions_raw` table
# MAGIC **Output:** `retail_dev.bronze.transactions_raw` (deduplicated)
# MAGIC
# MAGIC Key data trap: the two sheets overlap by 22,523 rows (1-9 Dec 2010).
# MAGIC Naive stacking double-counts ~£377k.

# COMMAND ----------
# Parameters
dbutils.widgets.text("catalog", "retail_dev")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# -- Read from existing table (already in workspace) --
raw = spark.table("retail_source.online_retail.transactions_raw")

# -- Deduplicate: keep first occurrence by composite key --
# Note: input_file_name() not supported in UC, use _metadata.file_path if needed
w = (Window
     .partitionBy("invoice", "stock_code", "invoice_date", "quantity", "price", "customer_id", "country")
     .orderBy(F.monotonically_increasing_id()))

deduped = (raw
    .withColumn("_rn", F.row_number().over(w))
    .filter("_rn = 1")
    .drop("_rn"))

overlap_count = raw.count() - deduped.count()
print(f"Deduplicated: {overlap_count:,} overlap rows removed | Clean: {deduped.count():,} rows")

# -- Create schema if needed --
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.bronze")

# -- Write to Bronze (overwrite for idempotency) --
(deduped.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable(f"{catalog}.bronze.transactions_raw"))

print(f"✓ Written to {catalog}.bronze.transactions_raw")