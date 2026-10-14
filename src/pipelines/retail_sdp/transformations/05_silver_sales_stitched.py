from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog", "retail_prod")


@dp.materialized_view(
    name=f"{CATALOG}.silver_sdp.sales_stitched",
    comment="Silver: clean sales with guest-checkout identity stitching",
    row_filter=f"ROW FILTER {CATALOG}.gold.filter_uk_region ON (country)",
)
def sales_stitched():
    return (spark.read.table(f"{CATALOG}.silver_sdp.sales_cleaned")
        .withColumn("resolved_customer_id",
            F.coalesce(
                F.col("customer_id").cast("string"),
                F.concat(F.lit("GUEST_"), F.sha2(
                    F.concat(F.col("invoice"), F.col("country"), F.col("invoice_date").cast("date")), 256))
            ))
        .withColumn("is_guest_checkout", F.col("customer_id").isNull()))
