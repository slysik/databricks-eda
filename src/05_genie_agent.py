# Databricks notebook source
# COMMAND ----------
# MAGIC %md
# MAGIC ## 05. Genie Agent Configuration
# MAGIC
# MAGIC **Input:** `retail_prod.gold.*` tables (governed)
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
    "description": "Self-service analytics over governed gold retail tables with UC column masking and row-level security",
    "warehouse_id": warehouse_id,
    "tables": [
        f"{catalog}.gold.gold_daily_kpis",
        f"{catalog}.gold.gold_customer_features"
    ],
    "instructions": """You are a retail analytics assistant. Key facts:
- Data covers Dec 2009 to Dec 2011 from a UK-based online gift retailer
- 'guest checkouts' = orders with no customer_id (anonymous web purchases)
- The 2010-11 sheet overlap was deduplicated; early Dec 2010 is not double-counted
- Cancellations (C-prefix invoices) are separate from sales
- Revenue = quantity × price; negative quantity = returns/cancellations
- customer_id may appear as ***MASKED*** due to UC governance (this is expected)
""",
    "sample_questions": [
        "What were the top 5 revenue days in Q4 2010?",
        "What percentage of revenue comes from guest checkouts?",
        "Which customers are at risk of churning?",
        "How does holiday 2010 compare to 2009?",
        "What is the return rate by country?",
        "Show daily net revenue trend over time",
        "What are the top 10 countries by net revenue?",
        "Compare gross revenue vs net revenue by month"
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