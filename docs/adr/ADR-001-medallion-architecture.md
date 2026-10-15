# ADR-001: Medallion Architecture (Bronze/Silver/Gold)

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** Data Engineering, Analytics Engineering  
**Consulted:** Tech Lead, ML Engineering

---

## Context

The project ingests 1.07M raw retail transaction line items from a Unity Catalog source table. The data contains duplicates (22,523-row overlap between annual sheets), mixed line types (sales, cancellations, non-inventory charges), and requires cleaning before business aggregation. Multiple consumers need different views: analysts need cleaned transactions, BI tools need pre-aggregated KPIs, ML needs feature tables, and Genie needs governed query surfaces.

## Decision

Adopt the **Medallion Architecture** with three layers:

- **Bronze:** Raw ingestion with deduplication. Idempotent `overwrite` writes. Preserves source fidelity minus known duplicates.
- **Silver:** Cleaned, classified, and quality-checked data. Six-class line categorization. Quarantine table for non-product lines. Customer identity stitching.
- **Gold:** Pre-aggregated business metrics (daily KPIs, customer RFM/LTV features). Optimized for sub-second BI and Genie response.

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Single-layer flat schema** | Simple, fewer moving parts | No separation of concerns; mixing raw and derived data; difficult to reprocess |
| **Data Vault** | Strong audit trail, flexible | Over-engineered for this scale; steep learning curve; slower query performance |
| **Lakeflow / Streaming-first** | Near real-time | Unnecessary latency for batch analysis; more infrastructure complexity |

## Consequences

### Positive
- Clear data lineage and reprocessing capability (re-run any layer independently).
- Bronze preserves source fidelity for audit; Silver applies business logic; Gold serves consumers.
- Each layer can be optimized independently (Bronze for writes, Gold for reads).
- Standard pattern — easily understood by Databricks teams and interviewers.

### Negative
- Three layers means three sets of tables to manage and monitor.
- Duplication of data between layers (mitigated by Delta's columnar compression).
- Requires discipline to avoid "Gold logic in Silver" layer violations.

---

## References
- Databricks Medallion Architecture: https://www.databricks.com/glossary/medallion-architecture
- Source code: `src/01_bronze_ingest.py`, `src/02_silver_clean.py`, `src/03_gold_aggregate.py`
