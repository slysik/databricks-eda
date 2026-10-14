from pyspark import pipelines as dp
from pyspark.sql import functions as F

CATALOG = spark.conf.get("catalog", "retail_prod")


@dp.materialized_view(
    name=f"{CATALOG}.gold_sdp.gold_daily_kpis",
    comment="Gold: daily revenue, order and cancellation KPIs",
    cluster_by=["invoice_date"],
)
def gold_daily_kpis():
    daily_base = (spark.read.table(f"{CATALOG}.silver_sdp.sales_cleaned")
        .select(
            F.col("invoice_date").cast("date").alias("invoice_date"),
            "invoice", "quantity", "price", "is_cancellation",
            (F.col("quantity") * F.col("price")).alias("line_revenue")))

    return (daily_base
        .groupBy("invoice_date")
        .agg(
            F.sum(F.when(F.col("quantity") > 0, F.col("line_revenue")).otherwise(0)).alias("gross_revenue"),
            F.abs(F.sum(F.when(F.col("quantity") < 0, F.col("line_revenue")).otherwise(0))).alias("refunds"),
            F.sum("line_revenue").alias("net_revenue"),
            F.countDistinct("invoice").alias("total_orders"),
            F.countDistinct(F.when(F.col("is_cancellation"), F.col("invoice"))).alias("cancellations"),
        )
        .withColumn("cancellation_rate_pct",
            F.round(F.col("cancellations") * 100.0 / F.when(F.col("total_orders") != 0, F.col("total_orders")), 2))
        .withColumn("avg_order_value",
            F.round(F.col("net_revenue") / F.when(F.col("total_orders") != 0, F.col("total_orders")), 2)))
