# Databricks notebook source
# COMMAND ----------
%pip install openpyxl
%restart_python

# COMMAND ----------
# MAGIC %md
# MAGIC ## 01. Bronze Ingestion & Deduplication
# MAGIC
# MAGIC **Input:** UCI Online Retail II Excel (two sheets)
# MAGIC **Output:** `retail_prod.bronze.transactions_raw` (deduplicated)
# MAGIC
# MAGIC Key data trap: the two sheets overlap by 22,523 rows (1-9 Dec 2010).
# MAGIC Naive stacking double-counts ~£377k.

# COMMAND ----------
# Parameters
dbutils.widgets.text("catalog", "retail_prod")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# -- Load raw data (assumes already in Volume) --
raw_path = f"/Volumes/{catalog}/raw/online_retail_II.xlsx"
raw = (spark.read
       .format("com.crealytics.spark.excel")
       .option("header", "true")
       .load(raw_path))

# -- Tag source sheet for dedup traceability --
raw = raw.withColumn("source_sheet", F.input_file_name())

# -- Deduplicate: keep first occurrence by composite key --
w = (Window
     .partitionBy("invoice", "stock_code", "invoice_date", "quantity", "price", "customer_id", "country")
     .orderBy("source_sheet"))

deduped = (raw
    .withColumn("_rn", F.row_number().over(w))
    .filter("_rn = 1")
    .drop("_rn"))

overlap_count = raw.count() - deduped.count()
print(f"Deduplicated: {overlap_count:,} overlap rows removed | Clean: {deduped.count():,} rows")

# -- Write to Bronze (append-only, Delta) --
(deduped.write
    .mode("append")
    .format("delta")
    .saveAsTable(f"{catalog}.bronze.transactions_raw"))

print(f"✓ Written to {catalog}.bronze.transactions_raw")