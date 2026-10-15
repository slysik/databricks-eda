# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 05. Genie Agent Configuration
# MAGIC
# MAGIC **Input:** `retail_prod.metrics.*` metric views (governed)
# MAGIC **Output:** Genie agent configuration printed for review
# MAGIC
# MAGIC The agent inherits UC column masks and row filters automatically.

# COMMAND ----------
dbutils.widgets.text("catalog", "retail_prod")
dbutils.widgets.text("warehouse_id", "")
dbutils.widgets.text("genie_space_name", "EDA Governed Gold Analytics")
catalog = dbutils.widgets.get("catalog")
warehouse_id = dbutils.widgets.get("warehouse_id")
genie_space_name = dbutils.widgets.get("genie_space_name")

# COMMAND ----------
import json

# -- Build Genie space definition --
space_config = {
    "title": genie_space_name,
    "description": "Governed retail analytics over metric views: revenue, orders, cancellations, customer segmentation, and country-level sales.",
    "warehouse_id": warehouse_id,
    "tables": [
        f"{catalog}.metrics.daily_kpis",
        f"{catalog}.metrics.customer_features",
        f"{catalog}.metrics.sales_by_country"
    ],
    "instructions": """## PURPOSE
- Answer questions about retail revenue, orders, cancellations, customer segmentation, and country-level sales.
- Users are retail analysts and executives — assume business fluency.

## DISAMBIGUATION
- When the user asks about 'revenue' without qualification, use Net Revenue.
- 'Q4' means calendar Q4 (Oct-Dec). Data covers Dec 2009 to Dec 9, 2011.
- 'VIP customer' means Value Segment = 'VIP' (monetary_score >= 4 AND frequency_score >= 4).

## DATA QUALITY NOTES
- Dec 2011 is truncated (ends Dec 9) — do not compare to full Dec 2010 without noting this.
- customer_id is masked for non-admin users (appears as NULL).
- All monetary values are in GBP.

## CONSTRAINTS
- Use MEASURE() for all aggregations against metric views.
- Do not use SELECT * against metric views.
- Always qualify column references with the metric view name.

## Instructions you must follow when providing summaries
- Round percentages to two decimal places.
- Always state the date range used in the analysis.
- When comparing periods, note if one period is truncated.
""",
    "sample_questions": [
        "What were the top 5 revenue days in Q4 2010?",
        "Which customer segments have the highest spend?",
        "What are the top 10 countries by revenue?",
        "Show monthly revenue trend over time",
        "What is the cancellation rate by month?",
        "How many customers are in each value segment?",
        "Compare Q4 2010 vs Q4 2009 revenue",
        "What percentage of customers are guest checkouts?"
    ]
}

# -- Print config for review --
print("=" * 60)
print("GENIE AGENT CONFIGURATION")
print("=" * 60)
print(json.dumps(space_config, indent=2))
print("=" * 60)
print(f"\n✓ Genie agent '{genie_space_name}' configured")
print(f"  - Tables: {', '.join(space_config['tables'])}")
print(f"  - Sample questions: {len(space_config['sample_questions'])}")
print(f"  - Inherits UC masks and row filters automatically")
print(f"\nTo create the Genie agent, use the Databricks UI or Genie API.")