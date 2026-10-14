from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog", "retail_prod")


@dp.materialized_view(
    name=f"{CATALOG}.silver_sdp.sales_cleaned",
    comment="Silver: clean sale/cancellation lines, quality-checked",
)
@dp.expect_or_drop("chk_invoice_date_not_null", "invoice_date IS NOT NULL")
@dp.expect_or_drop("chk_price_nonneg_on_sales", "price >= 0")
def sales_cleaned():
    return (spark.read.table("sales_classified")
        .filter(F.col("line_type").isin("sale", "cancellation")))
