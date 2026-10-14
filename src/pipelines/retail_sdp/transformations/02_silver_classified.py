from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog", "retail_prod")


@dp.temporary_view(
    name="sales_classified",
    comment="Pipeline-private: typed + classified rows, shared by sales_cleaned, sales_quarantine, sales_stitched",
)
def sales_classified():
    raw = (spark.read.table(f"{CATALOG}.bronze_sdp.transactions_raw")
        .withColumn("quantity", F.col("quantity").cast("int"))
        .withColumn("price", F.col("price").cast("decimal(12,3)"))
        .withColumn("invoice_date", F.col("invoice_date").cast("timestamp"))
        .withColumn("customer_id", F.col("customer_id").cast("int")))

    return (raw
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
