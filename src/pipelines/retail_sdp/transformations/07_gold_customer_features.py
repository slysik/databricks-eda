from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

CATALOG = spark.conf.get("catalog", "retail_prod")

SCHEMA = f"""
    customer_id INT MASK {CATALOG}.gold.mask_customer_id,
    resolved_customer_id STRING,
    is_guest_checkout BOOLEAN,
    order_count BIGINT,
    total_spend DECIMAL(33,3),
    avg_order_value DECIMAL(27,7),
    days_since_last_order INT,
    customer_tenure_days INT,
    active_days BIGINT,
    return_rate_pct DECIMAL(35,2),
    recency_score INT,
    frequency_score INT,
    monetary_score INT
"""


@dp.materialized_view(
    name=f"{CATALOG}.gold_sdp.gold_customer_features",
    comment="Gold: RFM + LTV features per resolved customer; customer_id masked for non-admins",
    schema=SCHEMA,
)
def gold_customer_features():
    customer_base = (spark.read.table(f"{CATALOG}.silver_sdp.sales_stitched")
        .filter((F.col("line_type") == "sale") & (F.col("quantity") > 0))
        .select(
            "customer_id", "resolved_customer_id", "is_guest_checkout",
            "invoice", "invoice_date", "quantity", "price",
            (F.col("quantity") * F.col("price")).alias("line_revenue")))

    recency_w = Window.orderBy(F.desc("days_since_last_order"))
    frequency_w = Window.orderBy("order_count")
    monetary_w = Window.orderBy("total_spend")

    grouped = (customer_base
        .groupBy("customer_id", "resolved_customer_id", "is_guest_checkout")
        .agg(
            F.countDistinct("invoice").alias("order_count"),
            F.sum("line_revenue").alias("total_spend"),
            F.avg("line_revenue").alias("avg_order_value"),
            F.datediff(F.current_date(), F.max("invoice_date")).alias("days_since_last_order"),
            F.datediff(F.max("invoice_date"), F.min("invoice_date")).alias("customer_tenure_days"),
            F.countDistinct(F.col("invoice_date").cast("date")).alias("active_days"),
            F.round(
                F.sum(F.when(F.col("quantity") < 0, F.col("line_revenue")).otherwise(0))
                / F.nullif(F.sum("line_revenue"), F.lit(0)) * 100, 2
            ).alias("return_rate_pct"),
        ))

    return (grouped
        .withColumn("recency_score", F.ntile(5).over(recency_w))
        .withColumn("frequency_score", F.ntile(5).over(frequency_w))
        .withColumn("monetary_score", F.ntile(5).over(monetary_w)))
