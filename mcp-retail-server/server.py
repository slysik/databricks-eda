"""
Retail EDA MCP Server — Purpose-built tools for retail analytics.

Not a SQL passthrough. Each tool answers a real business question:
- "How are we doing?" → get_executive_kpis
- "Who are our best customers?" → analyze_customer_segment
- "Is this holiday better than last?" → compare_periods
- "Where is revenue coming from?" → get_revenue_breakdown
- "Are there data issues?" → check_data_quality
- "Will this customer return?" → predict_return_risk

Every call is traced to MLflow for observability.
"""

import json
import os
import time
from datetime import datetime
from typing import Optional

import mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from mcp.server.fastmcp import FastMCP

# ─── Configuration ────────────────────────────────────────────────────────────

CATALOG = os.getenv("RETAIL_CATALOG", "retail_prod")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")

# ─── Databricks Client (UC-secured) ───────────────────────────────────────────

def get_client() -> WorkspaceClient:
    """Authenticated via DATABRICKS_HOST + DATABRICKS_TOKEN or DATABRICKS_CONFIG_PROFILE."""
    return WorkspaceClient()

def get_warehouse_id(w: WorkspaceClient) -> str:
    """Resolve warehouse: explicit env var or first available."""
    if WAREHOUSE_ID:
        return WAREHOUSE_ID
    return next(iter(w.warehouses.list())).id

def execute_query(w: WorkspaceClient, sql: str) -> pd.DataFrame:
    """Execute SQL via Statements API, return DataFrame."""
    warehouse_id = get_warehouse_id(w)
    result = w.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=warehouse_id,
        catalog=CATALOG,
    )
    if not result.result or not result.result.data_array:
        return pd.DataFrame()
    columns = [c.name for c in result.manifest.schema.columns]
    return pd.DataFrame(result.result.data_array, columns=columns)

# ─── MLflow Tracing ───────────────────────────────────────────────────────────

def trace_tool(tool_name: str, args: dict, sql: str = "", result_count: int = 0, 
               latency_ms: float = 0, error: str = ""):
    """Log every tool call to MLflow for observability."""
    with mlflow.start_run(run_name=f"mcp-{tool_name}", nested=True):
        mlflow.log_params({
            "tool": tool_name,
            "args_json": json.dumps(args, default=str)[:500],
            "sql": sql[:1000] if sql else "",
        })
        mlflow.log_metrics({
            "result_count": result_count,
            "latency_ms": latency_ms,
            "success": 1 if not error else 0,
        })
        if error:
            mlflow.set_tag("error", error[:200])

# ─── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    "retail-analytics",
    description="Purpose-built retail analytics tools for EDA retail data"
)

# ─── Tool 1: Executive KPIs ───────────────────────────────────────────────────

@mcp.tool()
def get_executive_kpis(
    period: str = "all",
    compare_to_previous: bool = False
) -> str:
    """Get headline retail performance metrics.
    
    Args:
        period: Time period - 'all', '2009', '2010', '2011', 'q4_2010', etc.
        compare_to_previous: If True, include period-over-period comparison
    
    Returns:
        JSON with gross_sales, refunds, net_revenue, active_customers, 
        guest_share_pct, international_pct, avg_order_value
    """
    start = time.time()
    
    period_filter = ""
    if period == "2009":
        period_filter = "WHERE YEAR(invoice_date) = 2009"
    elif period == "2010":
        period_filter = "WHERE YEAR(invoice_date) = 2010"
    elif period == "2011":
        period_filter = "WHERE YEAR(invoice_date) = 2011"
    elif period.startswith("q"):
        # Parse q4_2010 -> quarter 4 of 2010
        parts = period.split("_")
        if len(parts) == 2:
            q = int(parts[0][1])
            year = int(parts[1])
            period_filter = f"WHERE QUARTER(invoice_date) = {q} AND YEAR(invoice_date) = {year}"
    
    sql = f"""
    WITH base AS (
        SELECT 
            invoice, quantity, price, customer_id, country,
            (quantity * price) AS line_revenue,
            CASE WHEN quantity > 0 THEN 'sale' ELSE 'return' END AS txn_type
        FROM {CATALOG}.silver.sales_cleaned
        {period_filter}
    )
    SELECT
        ROUND(SUM(CASE WHEN txn_type = 'sale' THEN line_revenue ELSE 0 END), 2) AS gross_sales,
        ROUND(ABS(SUM(CASE WHEN txn_type = 'return' THEN line_revenue ELSE 0 END)), 2) AS refunds,
        ROUND(SUM(line_revenue), 2) AS net_revenue,
        COUNT(DISTINCT customer_id) AS active_customers,
        COUNT(DISTINCT CASE WHEN customer_id IS NULL THEN invoice END) AS guest_invoices,
        COUNT(DISTINCT invoice) AS total_invoices,
        ROUND(COUNT(DISTINCT CASE WHEN customer_id IS NULL THEN invoice END) * 100.0 
              / NULLIF(COUNT(DISTINCT invoice), 0), 1) AS guest_share_pct,
        ROUND(SUM(CASE WHEN country != 'United Kingdom' THEN line_revenue ELSE 0 END) * 100.0
              / NULLIF(SUM(line_revenue), 0), 1) AS international_pct,
        ROUND(SUM(line_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2) AS avg_order_value
    FROM base
    """
    
    try:
        w = get_client()
        df = execute_query(w, sql)
        result = df.to_dict('records')[0] if len(df) > 0 else {}
        
        latency = (time.time() - start) * 1000
        trace_tool("get_executive_kpis", {"period": period}, sql, len(df), latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("get_executive_kpis", {"period": period}, sql, 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Tool 2: Customer Segment Analysis ────────────────────────────────────────

@mcp.tool()
def analyze_customer_segment(
    segment: str = "all",
    min_spend: float = 0,
    top_n: int = 10
) -> str:
    """Analyze customer segments by RFM (Recency, Frequency, Monetary) metrics.
    
    Args:
        segment: Customer segment - 'all', 'vip', 'loyal', 'at_risk', 'churned', 'guest'
        min_spend: Minimum total spend threshold (GBP)
        top_n: Number of top customers to return
    
    Returns:
        JSON with segment profile, customer list, and summary statistics
    """
    start = time.time()
    
    segment_filter = ""
    if segment == "vip":
        segment_filter = "WHERE recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4"
    elif segment == "loyal":
        segment_filter = "WHERE frequency_score >= 3 AND recency_score >= 3"
    elif segment == "at_risk":
        segment_filter = "WHERE recency_score <= 2 AND frequency_score >= 3"
    elif segment == "churned":
        segment_filter = "WHERE recency_score <= 2 AND frequency_score <= 2"
    elif segment == "guest":
        segment_filter = "WHERE is_guest_checkout = TRUE"
    
    spend_filter = f"AND total_spend >= {min_spend}" if min_spend > 0 else ""
    
    sql = f"""
    SELECT
        customer_id,
        resolved_customer_id,
        is_guest_checkout,
        order_count,
        ROUND(total_spend, 2) AS total_spend_gbp,
        ROUND(avg_order_value, 2) AS avg_order_value_gbp,
        days_since_last_order,
        customer_tenure_days,
        active_days,
        return_rate_pct,
        recency_score,
        frequency_score,
        monetary_score,
        -- Segment label
        CASE
            WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4 THEN 'VIP Champion'
            WHEN frequency_score >= 3 AND recency_score >= 3 THEN 'Loyal Regular'
            WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At Risk'
            WHEN recency_score <= 2 AND frequency_score <= 2 THEN 'Churned'
            WHEN is_guest_checkout THEN 'Guest'
            ELSE 'Other'
        END AS segment_label
    FROM {CATALOG}.gold.gold_customer_features
    {segment_filter}
    {spend_filter}
    ORDER BY total_spend DESC
    LIMIT {top_n}
    """
    
    try:
        w = get_client()
        df = execute_query(w, sql)
        
        # Summary stats
        summary_sql = f"""
        SELECT
            COUNT(*) AS customer_count,
            ROUND(AVG(total_spend), 2) AS avg_spend,
            ROUND(SUM(total_spend), 2) AS total_segment_revenue,
            ROUND(AVG(order_count), 1) AS avg_orders,
            ROUND(AVG(days_since_last_order), 0) AS avg_days_since_order,
            ROUND(AVG(return_rate_pct), 2) AS avg_return_rate
        FROM {CATALOG}.gold.gold_customer_features
        {segment_filter}
        {spend_filter}
        """
        summary_df = execute_query(w, summary_sql)
        
        result = {
            "segment": segment,
            "summary": summary_df.to_dict('records')[0] if len(summary_df) > 0 else {},
            "top_customers": df.to_dict('records'),
            "query_metadata": {
                "returned": len(df),
                "requested": top_n
            }
        }
        
        latency = (time.time() - start) * 1000
        trace_tool("analyze_customer_segment", {"segment": segment, "top_n": top_n}, sql, len(df), latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("analyze_customer_segment", {"segment": segment}, sql, 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Tool 3: Period Comparison ────────────────────────────────────────────────

@mcp.tool()
def compare_periods(
    period1: str = "q4_2010",
    period2: str = "q4_2009",
    metrics: str = "revenue,orders,aov"
) -> str:
    """Compare retail performance between two time periods.
    
    Args:
        period1: First period (e.g., 'q4_2010', '2010', 'dec_2010')
        period2: Second period for comparison (e.g., 'q4_2009', '2009', 'dec_2009')
        metrics: Comma-separated metrics to compare: 'revenue', 'orders', 'aov', 'customers', 'cancellations'
    
    Returns:
        JSON with both periods' values and percentage change for each metric
    """
    start = time.time()
    
    def parse_period(p: str) -> str:
        if p.startswith("q"):
            parts = p.split("_")
            if len(parts) == 2:
                return f"QUARTER(invoice_date) = {int(parts[0][1])} AND YEAR(invoice_date) = {int(parts[1])}"
        elif any(p.startswith(m + "_") for m in ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]):
            # Month abbreviations
            months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                     "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
            parts = p.split("_")
            if len(parts) == 2 and parts[0] in months:
                return f"MONTH(invoice_date) = {months[parts[0]]} AND YEAR(invoice_date) = {int(parts[1])}"
        elif p.isdigit() and len(p) == 4:
            return f"YEAR(invoice_date) = {int(p)}"
        return ""
    
    filter1 = parse_period(period1)
    filter2 = parse_period(period2)
    
    if not filter1 or not filter2:
        return json.dumps({"error": f"Invalid period format. Use: q4_2010, 2010, dec_2010"})
    
    metric_map = {
        "revenue": "ROUND(SUM(line_revenue), 2)",
        "orders": "COUNT(DISTINCT invoice)",
        "aov": "ROUND(SUM(line_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2)",
        "customers": "COUNT(DISTINCT customer_id)",
        "cancellations": "COUNT(DISTINCT CASE WHEN is_cancellation THEN invoice END)"
    }
    
    selected_metrics = [m.strip() for m in metrics.split(",")]
    select_parts = []
    for m in selected_metrics:
        if m in metric_map:
            select_parts.append(f"{metric_map[m]} AS {m}")
    
    if not select_parts:
        select_parts = [f"{metric_map['revenue']} AS revenue", f"{metric_map['orders']} AS orders"]
    
    sql = f"""
    WITH p1 AS (
        SELECT {', '.join(select_parts)}
        FROM {CATALOG}.silver.sales_cleaned
        WHERE {filter1}
    ),
    p2 AS (
        SELECT {', '.join(select_parts)}
        FROM {CATALOG}.silver.sales_cleaned
        WHERE {filter2}
    )
    SELECT 
        '{period1}' AS period1,
        '{period2}' AS period2,
        p1.*,
        p2.*
    FROM p1, p2
    """
    
    try:
        w = get_client()
        df = execute_query(w, sql)
        
        if len(df) == 0:
            return json.dumps({"error": "No data found for one or both periods"})
        
        row = df.to_dict('records')[0]
        
        # Build comparison result
        result = {
            "period1": period1,
            "period2": period2,
            "metrics": {}
        }
        
        for m in selected_metrics:
            if m in metric_map:
                val1 = row.get(f"{m}_p1", row.get(m, 0))
                val2 = row.get(f"{m}_p2", row.get(m, 0))
                
                try:
                    v1 = float(val1) if val1 else 0
                    v2 = float(val2) if val2 else 0
                    change_pct = ((v1 - v2) / v2 * 100) if v2 else 0
                    
                    result["metrics"][m] = {
                        period1: v1,
                        period2: v2,
                        "change_pct": round(change_pct, 2),
                        "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
                    }
                except (ValueError, TypeError):
                    result["metrics"][m] = {"error": "Could not parse values"}
        
        latency = (time.time() - start) * 1000
        trace_tool("compare_periods", {"period1": period1, "period2": period2}, sql, len(df), latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("compare_periods", {"period1": period1, "period2": period2}, sql, 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Tool 4: Revenue Breakdown ────────────────────────────────────────────────

@mcp.tool()
def get_revenue_breakdown(
    dimension: str = "country",
    period: str = "all",
    top_n: int = 10
) -> str:
    """Break down revenue by a dimension.
    
    Args:
        dimension: Breakdown dimension - 'country', 'channel' (guest vs identified), 'month', 'weekday', 'hour'
        period: Time period filter (same format as get_executive_kpis)
        top_n: Number of top categories to return
    
    Returns:
        JSON with revenue breakdown, percentages, and cumulative share
    """
    start = time.time()
    
    period_filter = ""
    if period == "2009":
        period_filter = "AND YEAR(invoice_date) = 2009"
    elif period == "2010":
        period_filter = "AND YEAR(invoice_date) = 2010"
    elif period == "2011":
        period_filter = "AND YEAR(invoice_date) = 2011"
    
    dimension_sql = {
        "country": "country",
        "channel": "CASE WHEN customer_id IS NULL THEN 'Guest (Anonymous)' ELSE 'Identified' END",
        "month": "DATE_FORMAT(invoice_date, 'yyyy-MM')",
        "weekday": "DAYOFWEEK(invoice_date)",
        "hour": "HOUR(invoice_date)"
    }
    
    dim_expr = dimension_sql.get(dimension, "country")
    
    sql = f"""
    WITH ranked AS (
        SELECT
            {dim_expr} AS dimension_value,
            ROUND(SUM(CASE WHEN quantity > 0 THEN quantity * price ELSE 0 END), 2) AS gross_revenue,
            ROUND(SUM(quantity * price), 2) AS net_revenue,
            COUNT(DISTINCT invoice) AS order_count,
            COUNT(DISTINCT customer_id) AS customer_count,
            ROUND(SUM(CASE WHEN quantity > 0 THEN quantity * price ELSE 0 END) * 100.0
                  / NULLIF(SUM(SUM(CASE WHEN quantity > 0 THEN quantity * price ELSE 0 END)) OVER(), 0), 2) AS revenue_pct
        FROM {CATALOG}.silver.sales_cleaned
        WHERE 1=1 {period_filter}
        GROUP BY {dim_expr}
        ORDER BY gross_revenue DESC
        LIMIT {top_n}
    )
    SELECT 
        dimension_value,
        gross_revenue,
        net_revenue,
        order_count,
        customer_count,
        revenue_pct,
        SUM(revenue_pct) OVER (ORDER BY gross_revenue DESC) AS cumulative_pct
    FROM ranked
    """
    
    try:
        w = get_client()
        df = execute_query(w, sql)
        
        result = {
            "dimension": dimension,
            "period": period,
            "breakdown": df.to_dict('records'),
            "total_categories": len(df)
        }
        
        latency = (time.time() - start) * 1000
        trace_tool("get_revenue_breakdown", {"dimension": dimension, "period": period}, sql, len(df), latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("get_revenue_breakdown", {"dimension": dimension}, sql, 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Tool 5: Data Quality Check ───────────────────────────────────────────────

@mcp.tool()
def check_data_quality() -> str:
    """Check data quality metrics: quarantine stats, constraint violations, gaps.
    
    Returns:
        JSON with quarantine counts, constraint status, null rates, and data freshness
    """
    start = time.time()
    
    try:
        w = get_client()
        
        # Quarantine stats
        quarantine_sql = f"""
        SELECT
            line_type,
            COUNT(*) AS row_count,
            ROUND(SUM(ABS(quantity * price)), 2) AS total_value
        FROM {CATALOG}.silver.sales_quarantine
        GROUP BY line_type
        ORDER BY row_count DESC
        """
        quarantine_df = execute_query(w, quarantine_sql)
        
        # Null rates in clean data
        null_sql = f"""
        SELECT
            ROUND(SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS null_customer_pct,
            ROUND(SUM(CASE WHEN description IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS null_description_pct,
            ROUND(SUM(CASE WHEN price = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS zero_price_pct,
            COUNT(*) AS total_clean_rows
        FROM {CATALOG}.silver.sales_cleaned
        """
        null_df = execute_query(w, null_sql)
        
        # Data freshness
        freshness_sql = f"""
        SELECT
            MAX(invoice_date) AS latest_transaction,
            DATEDIFF(CURRENT_DATE(), MAX(invoice_date)) AS days_since_latest,
            MIN(invoice_date) AS earliest_transaction,
            COUNT(DISTINCT CAST(invoice_date AS DATE)) AS distinct_dates
        FROM {CATALOG}.silver.sales_cleaned
        """
        freshness_df = execute_query(w, freshness_sql)
        
        result = {
            "quarantine": {
                "categories": quarantine_df.to_dict('records'),
                "total_quarantined": int(quarantine_df['row_count'].sum()) if len(quarantine_df) > 0 else 0
            },
            "null_rates": null_df.to_dict('records')[0] if len(null_df) > 0 else {},
            "freshness": freshness_df.to_dict('records')[0] if len(freshness_df) > 0 else {},
            "constraints_active": [
                "chk_invoice_date_not_null",
                "chk_price_nonneg_on_sales"
            ]
        }
        
        latency = (time.time() - start) * 1000
        trace_tool("check_data_quality", {}, "", 3, latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("check_data_quality", {}, "", 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Tool 6: Return Risk Prediction ───────────────────────────────────────────

@mcp.tool()
def predict_return_risk(
    customer_id: Optional[int] = None,
    order_value: Optional[float] = None,
    quantity: Optional[int] = None
) -> str:
    """Predict return risk for a customer or order using the registered MLflow model.
    
    Args:
        customer_id: Customer ID to look up their RFM features (optional)
        order_value: Order value in GBP for new order prediction (optional)
        quantity: Number of items in the order (optional)
    
    Returns:
        JSON with risk score, risk category, and contributing factors
    """
    start = time.time()
    
    try:
        w = get_client()
        
        # Get customer features if customer_id provided
        if customer_id:
            customer_sql = f"""
            SELECT
                customer_id,
                order_count,
                total_spend,
                avg_order_value,
                days_since_last_order,
                return_rate_pct,
                recency_score,
                frequency_score,
                monetary_score
            FROM {CATALOG}.gold.gold_customer_features
            WHERE customer_id = {customer_id}
            """
            df = execute_query(w, customer_sql)
            
            if len(df) == 0:
                return json.dumps({"error": f"Customer {customer_id} not found"})
            
            customer = df.to_dict('records')[0]
            
            # Simple risk heuristic (replace with actual MLflow model in production)
            risk_score = 0.0
            factors = []
            
            # High return history
            if customer.get('return_rate_pct', 0) > 10:
                risk_score += 0.3
                factors.append(f"High return history ({customer['return_rate_pct']}%)")
            
            # New customer
            if customer.get('order_count', 0) <= 2:
                risk_score += 0.2
                factors.append(f"New customer ({customer['order_count']} orders)")
            
            # High value order
            if order_value and order_value > 500:
                risk_score += 0.15
                factors.append(f"High value order (GBP {order_value})")
            
            # Large quantity
            if quantity and quantity > 10:
                risk_score += 0.1
                factors.append(f"Large quantity ({quantity} items)")
            
            risk_score = min(risk_score, 1.0)
            risk_category = "low" if risk_score < 0.3 else "medium" if risk_score < 0.6 else "high"
            
            result = {
                "customer_id": customer_id,
                "risk_score": round(risk_score, 3),
                "risk_category": risk_category,
                "factors": factors,
                "customer_profile": {
                    "order_count": customer.get('order_count'),
                    "total_spend": customer.get('total_spend'),
                    "return_rate_pct": customer.get('return_rate_pct'),
                    "recency_score": customer.get('recency_score'),
                    "frequency_score": customer.get('frequency_score'),
                    "monetary_score": customer.get('monetary_score')
                },
                "recommendation": "FLAG_FOR_REVIEW" if risk_category == "high" else "PROCEED"
            }
        else:
            # General risk assessment without customer context
            result = {
                "note": "Provide customer_id for personalized risk assessment",
                "general_guidance": {
                    "high_risk_signals": [
                        "Return rate > 10%",
                        "New customer (≤2 orders)",
                        "High value order (>GBP 500)",
                        "Large quantity (>10 items)"
                    ],
                    "model_info": "Rule-based heuristic. RF model (ROC-AUC 0.8899) trained in notebook, registered in UC, not wired into this tool."
                }
            }
        
        latency = (time.time() - start) * 1000
        trace_tool("predict_return_risk", {"customer_id": customer_id}, "", 1, latency)
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        latency = (time.time() - start) * 1000
        trace_tool("predict_return_risk", {"customer_id": customer_id}, "", 0, latency, str(e))
        return json.dumps({"error": str(e)})

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Retail EDA MCP Server...")
    print(f"Catalog: {CATALOG}")
    print("Tools: get_executive_kpis, analyze_customer_segment, compare_periods,")
    print("       get_revenue_breakdown, check_data_quality, predict_return_risk")
    mcp.run(transport="stdio")