from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

CATALOG = spark.conf.get("catalog", "retail_prod")
SOURCE_TABLE = "retail_source.online_retail.transactions_raw"


@dp.materialized_view(
    name=f"{CATALOG}.bronze_sdp.transactions_raw",
    comment="Bronze: deduplicated ingest from retail_source.online_retail.transactions_raw",
)
def transactions_raw():
    raw = spark.read.table(SOURCE_TABLE)

    w = (Window
         .partitionBy("invoice", "stock_code", "invoice_date", "quantity", "price", "customer_id", "country")
         .orderBy(F.monotonically_increasing_id()))

    return (raw
        .withColumn("_rn", F.row_number().over(w))
        .filter("_rn = 1")
        .drop("_rn"))
