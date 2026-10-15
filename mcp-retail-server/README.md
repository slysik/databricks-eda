# Retail EDA MCP Server

**Purpose-built MCP server for retail analytics** — not a raw SQL passthrough.

Tools are shaped to the actual business questions executives ask about retail performance, customer behavior, and operational health.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Client (Claude, Cursor, Pi)                            │
│  └── stdio → retail-mcp-server                              │
├─────────────────────────────────────────────────────────────┤
│  FastMCP Pure Functions                                      │
│  ┌─────────────┬─────────────┬─────────────┬──────────────┐ │
│  │ get_kpis    │ analyze_    │ check_      │ predict_     │ │
│  │             │ customers   │ quality     │ return_risk  │ │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬───────┘ │
│         │             │             │             │          │
│  ┌──────▼─────────────▼─────────────▼─────────────▼───────┐ │
│  │  Databricks SDK (UC-secured, service principal)        │ │
│  └────────────────────────┬───────────────────────────────┘ │
│                           │                                 │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │  Unity Catalog: retail_prod.gold.*                     │ │
│  │  - gold_daily_kpis (daily aggregations)                │ │
│  │  - gold_customer_features (RFM + LTV)                  │ │
│  │  - Column masks + row filters inherited                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  MLflow Traces: every tool call logged                 │ │
│  │  - Input args, SQL generated, row count, latency       │ │
│  │  - Failure modes captured (timeout, empty, auth)       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Tools (Not Endpoints)

| Tool | What It Answers | Why It Exists |
|------|-----------------|---------------|
| `get_executive_kpis` | "How are we doing this quarter?" | Executives need headline numbers, not SQL |
| `analyze_customer_segment` | "Who are our VIP customers?" | RFM segmentation with actionable thresholds |
| `compare_periods` | "Is this holiday better than last?" | YoY/MoM with significance testing |
| `get_revenue_breakdown` | "Where is revenue coming from?" | By country, channel (guest vs identified), time |
| `check_data_quality` | "Are there data issues I should know?" | Quarantine stats, constraint violations, gaps |
| `predict_return_risk` | "Will this customer return their order?" | Rule-based heuristic (RF model trained but not wired in) |

## Why These Tools (Not Raw SQL)

Raw `execute_sql` means the LLM has to:
1. Know the schema
2. Write correct SQL
3. Interpret the results
4. Handle edge cases (nulls, masks, filters)

Purpose-built tools mean the LLM just asks a question and gets a structured answer. The tool owns the SQL, the edge cases, and the interpretation.

**This is the difference Itai calls out:** "generic wrappers weren't enough — each server's tools had to map to real workflows."

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Databricks auth
export DATABRICKS_HOST=https://your-workspace.databricks.com
export DATABRICKS_TOKEN=dapi-...
# Or use a profile: export DATABRICKS_CONFIG_PROFILE=prod

# 3. Run the server
python server.py

# 4. Configure in Claude/Cursor/Pi
# Add to your MCP config:
{
  "mcpServers": {
    "retail-analytics": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "DATABRICKS_HOST": "...",
        "DATABRICKS_TOKEN": "..."
      }
    }
  }
}
```

## MLflow Tracing

Every tool call is traced to MLflow:
- Input arguments
- SQL generated (if applicable)
- Row count returned
- Latency
- Error details (if failed)

View traces: `mlflow experiments search --filter-name="retail-mcp"`