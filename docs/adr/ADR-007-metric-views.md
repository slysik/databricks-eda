# ADR-007: Unity Catalog Metric Views for Genie Governance

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** Analytics Engineering, Platform Engineering  
**Consulted:** Tech Lead

---

## Context

The Genie agent queries Gold tables directly using `SELECT SUM(net_revenue)` style SQL. This works but has limitations:

1. **Metric definitions are implicit** — each consumer must know that `net_revenue = gross_revenue - refunds`.
2. **No reusable segments** — customer segmentation logic (VIP, Regular, Low Value) is written ad-hoc in each query.
3. **Genie accuracy depends on column descriptions** — the LLM must infer aggregation logic from metadata.
4. **No enforcement** — a dashboard developer might calculate `cancellation_rate` differently than the Genie agent.

Databricks **Metric Views** (v1.1, YAML-based) allow defining metrics declaratively with dimensions, measures, and filters. Genie, dashboards, and SQL consumers all use the same `MEASURE()` syntax.

## Decision

Create three **Unity Catalog Metric Views** in `retail_prod.metrics`:

| Metric View | Source | Purpose |
|:---|:---|:---|
| `daily_kpis` | `gold.gold_daily_kpis` | Revenue, orders, cancellation rate, AOV |
| `customer_features` | `gold.gold_customer_features` | Customer count, spend, segments, guest share |
| `sales_by_country` | `silver.sales_cleaned` | Country/product revenue, units, orders |

Each view defines reusable dimensions (time periods, segments, country) and governed measures (aggregations with business logic).

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Continue with direct table queries** | No new infrastructure | Implicit metric definitions; no governance; Genie must infer logic |
| **Standard SQL views** | Familiar, simple | Measures locked at view creation; no `MEASURE()` re-aggregation; no Genie-native integration |
| **dbt metrics** | Industry standard | Additional tool dependency; not native to Databricks; requires dbt project |
| **Materialized views** | Pre-computed performance | Overkill at this scale; adds maintenance; not metric-aware |

## Performance Benchmark

Benchmarked on a Serverless Starter Warehouse (2X-Small, Photon enabled) with 5 representative queries, 3 runs each, warmed cache:

| Query | Before (direct) | After (metric view) | Delta |
|:---|---:|---:|---:|
| Total net revenue | 0.57s | 0.64s | +0.08s |
| Top 5 revenue days | 0.60s | 0.65s | +0.05s |
| Monthly revenue trend | 0.59s | 0.68s | +0.09s |
| Customer segmentation | 0.66s | 0.75s | +0.10s |
| Country revenue | 0.58s | 0.66s | +0.07s |
| **Average** | **0.60s** | **0.68s** | **+0.08s (+13%)** |

The ~13% overhead is from YAML parsing and metric resolution. At this scale (< 5K rows per Gold table), the overhead is negligible. The value is in governance and Genie accuracy, not raw speed.

## Consequences

### Positive
- **Single source of truth:** All consumers (Genie, dashboards, SQL) use the same metric definitions.
- **Reusable segments:** Customer value segments (VIP, Regular, Low Value) defined once, used everywhere.
- **Genie-native:** Metric views integrate directly with Genie for better NL-to-SQL accuracy.
- **Governed:** Metric definitions are version-controlled in SQL files, auditable in UC.
- **Queryable:** `SELECT MEASURE(\`Net Revenue\`) FROM daily_kpis GROUP BY \`Invoice Month\`` is self-documenting.

### Negative
- **~13% query overhead:** YAML parsing adds latency (negligible at this scale).
- **MEASURE() syntax:** All consumers must use `MEASURE()` for measures — `SELECT net_revenue` won't work.
- **No `SELECT *`:** Metric views require explicit dimension/measure references.
- **DBR version dependency:** Requires Runtime 17.2+ for YAML v1.1 syntax.

## Implementation

```sql
-- Query example: Monthly revenue trend
SELECT
  `Invoice Month`,
  MEASURE(`Gross Revenue`) AS gross,
  MEASURE(`Net Revenue`) AS net
FROM retail_prod.metrics.daily_kpis
GROUP BY `Invoice Month`
ORDER BY `Invoice Month`
```

---

## References
- Metric view definitions: `src/metrics/01_daily_kpis.sql`, `02_customer_features.sql`, `03_sales_by_country.sql`
- Databricks Metric Views docs: https://docs.databricks.com/en/metric-views/