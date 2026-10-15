# ADR-006: Purpose-Built MCP Server (Not Raw SQL Passthrough)

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** AI/Platform Engineering, Tech Lead  
**Consulted:** Analytics Engineering

---

## Context

Large Language Models (LLMs) and AI agents need to query retail data. The naive approach is a "raw SQL passthrough" MCP server that lets the LLM write arbitrary SQL. This approach has well-known problems:

1. The LLM must know the full schema (which changes).
2. The LLM must write correct SQL (which it often doesn't for complex aggregations).
3. The LLM must interpret results correctly (edge cases, masks, nulls).
4. No observability into what queries are being run.

## Decision

Build a **purpose-shaped MCP server** where each tool answers a specific business question:

| Tool | Business Question |
|:---|:---|
| `get_executive_kpis` | "How are we doing?" |
| `analyze_customer_segment` | "Who are our best customers?" |
| `compare_periods` | "Is this holiday better than last?" |
| `get_revenue_breakdown` | "Where is revenue coming from?" |
| `check_data_quality` | "Are there data issues?" |
| `predict_return_risk` | "Will this customer return?" |

Each tool owns the SQL, the edge cases, and the result interpretation. Every call is traced to MLflow for observability (input args, SQL, row count, latency, errors).

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Raw SQL passthrough** | Maximum flexibility | LLM writes wrong SQL; no guardrails; no observability; security risk |
| **Generated SQL from schema** | Flexible + some guardrails | Still relies on LLM SQL correctness; no business logic encapsulation |
| **BI tool API (e.g., Looker)** | Mature, tested | Not Databricks-native; adds dependency; not purpose-shaped for agents |
| **Direct Genie API** | Native NL interface | Not an MCP tool; different integration pattern |

## Consequences

### Positive
- **Reliability:** Each tool returns structured, pre-validated results.
- **Security:** Tools query only Gold tables (UC-governed); no arbitrary SQL.
- **Observability:** Every call is traced to MLflow with latency, row count, and errors.
- **Business-shaped:** LLMs can answer real questions without schema knowledge.
- **Maintainable:** SQL changes are isolated to tool implementations.

### Negative
- **Flexibility trade-off:** Can't answer questions not covered by existing tools.
- **Tool proliferation:** New business questions may require new tools.
- **Single point of failure:** If MCP server is down, agent capabilities degrade.

## MLflow Tracing

Every tool call logs:
```python
mlflow.log_params({"tool": tool_name, "args_json": json.dumps(args), "sql": sql})
mlflow.log_metrics({"result_count": result_count, "latency_ms": latency_ms, "success": 1})
mlflow.set_tag("error", error)  # if failed
```

---

## References
- Source code: `mcp-retail-server/server.py`
- MCP server README: `mcp-retail-server/README.md`
- FastMCP documentation: https://github.com/modelcontextprotocol
