from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog", "retail_prod")


@dp.materialized_view(
    name=f"{CATALOG}.silver_sdp.sales_quarantine",
    comment="Silver: non-inventory / bad-debt / stock-adjustment lines, isolated from clean sales",
)
def sales_quarantine():
    return (spark.read.table("sales_classified")
        .filter(~F.col("line_type").isin("sale", "cancellation")))
