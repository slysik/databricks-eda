# ADR-005: Spark Declarative Pipelines (SDP) as Parallel Implementation

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** Data Engineering, Tech Lead  
**Consulted:** Platform Engineering

---

## Context

The project has two audiences: (1) engineers who need fine-grained control over transformations (PySpark scripts in `src/`), and (2) platform teams who want declarative, self-managing pipeline infrastructure. Databricks offers **Spark Declarative Pipelines** (SDP, formerly Delta Live Tables) as a managed pipeline framework with built-in data quality expectations, lineage tracking, and automatic orchestration.

## Decision

Implement the **same medallion logic as a parallel Spark Declarative Pipeline** in `src/pipelines/retail_sdp/transformations/`, using:

- `@dp.materialized_view` for persistent tables (Bronze, Silver clean/quarantine/stitched, Gold)
- `@dp.temporary_view` for intermediate shared computation (sales_classified)
- `@dp.expect_or_drop` for declarative data quality (instead of manual CHECK constraint management)
- `row_filter` and `schema` parameters for inline governance

The notebook-based scripts (`src/01-05_*.py`) remain the **canonical reference implementation**. The SDP pipeline is an alternative deployment path that demonstrates platform-native pipeline management.

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Notebook-only (no SDP)** | Simpler; one codebase | No declarative DQ; manual orchestration; harder to demonstrate platform capabilities |
| **SDP-only** | Managed, self-healing | Less transparent for learning/debugging; abstractions can hide issues |
| **dbt on Databricks** | Familiar to analytics engineers | Additional tool dependency; less native to Databricks |

## Consequences

### Positive
- **Demonstrates both patterns:** Interviewers see notebook expertise AND platform-native SDP skills.
- **Declarative DQ:** `@dp.expect_or_drop` is more maintainable than manual constraint management.
- **Automatic lineage:** SDP tracks data lineage across all materialized views.
- **Self-managing:** SDP handles orchestration, retry, and incremental computation.
- **Same logic:** Both implementations use identical business rules (5-class categorization, dedup, guest surrogate id).

### Negative
- **Dual maintenance:** Changes to business logic must be applied to both implementations.
- **Learning curve:** SDP decorators and pipeline configuration add complexity.
- **Slight behavior differences:** `@dp.expect_or_drop` drops failing rows (vs. CHECK constraints that reject at write time) — documented in ADR-002.

## SDP File Structure

```
src/pipelines/retail_sdp/transformations/
├── 01_bronze_transactions_raw.py    # @dp.materialized_view — dedup + write
├── 02_silver_classified.py          # @dp.temporary_view — 5-class categorization
├── 03_silver_sales_cleaned.py       # @dp.materialized_view — @dp.expect_or_drop x2
├── 04_silver_sales_quarantine.py    # @dp.materialized_view — non-product lines
├── 05_silver_sales_stitched.py      # @dp.materialized_view — identity stitching + row_filter
├── 06_gold_daily_kpis.py            # @dp.materialized_view — cluster_by(invoice_date)
└── 07_gold_customer_features.py     # @dp.materialized_view — schema with MASK
```

---

## References
- Databricks SDP documentation: https://docs.databricks.com/en/dlt/index.html
- Source: `src/pipelines/retail_sdp/transformations/`
- DAB pipeline definition: `databricks.yml` → `resources.pipelines.retail_sdp`
