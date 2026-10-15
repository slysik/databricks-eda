# ADR-002: Dual-Engine Parity Validation (PySpark + Spark SQL)

**Status:** Accepted. **Implementation:** in the analysis notebook, which is not committed to this repo ([KNOWN_GAPS](../KNOWN_GAPS.md) 1)  
**Date:** 2025-07-11  
**Decision Makers:** Data Engineering, Analytics Engineering  
**Consulted:** Tech Lead

---

## Context

Headline financial metrics (Gross Sales, Refunds, Net Revenue, Active Customers, Guest Checkout Share, Cleaned Line Items) drive business decisions. A single implementation in one engine (PySpark DataFrame API or Spark SQL) carries the risk of subtle bugs: incorrect aggregation logic, type coercion errors, window function misuse, or SQL operator precedence issues. These bugs are hard to detect in code review and can silently corrupt downstream decisions.

## Decision

Implement **every critical analytical metric in two independent engines** — PySpark DataFrame API and Spark SQL — then compare results programmatically with a **zero-tolerance assertion harness** (all diffs must equal 0.00).

Both implementations consume the same Silver tables and produce the same output schema. The assertion harness runs after both complete and halts the pipeline if any metric differs.

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Single engine + code review** | Faster to build, less code | Review misses subtle logic bugs; no runtime proof of correctness |
| **Golden dataset testing** | Catches regressions | Doesn't validate the logic itself; depends on maintaining test fixtures |
| **Formal verification (e.g., Alloy)** | Proves correctness | Impractical for data pipeline logic; steep learning curve |

## Consequences

### Positive
- **Provable correctness:** Every published metric has a runtime proof of independence.
- **Catches logic bugs:** Two independent implementations are unlikely to share the same bug.
- **Builds trust:** Interviewers and stakeholders can see a concrete verification mechanism.
- **Documentation value:** The SQL version is more readable for analysts; the PySpark version shows API fluency.

### Negative
- **2x implementation effort:** Every metric must be written twice.
- **Maintenance overhead:** Changes to business logic require updates in both engines.
- **Performance overhead:** Running two engines doubles compute for validation queries (acceptable at this scale).

## Results

All six headline metrics pass with **diff = 0.00**:

| Metric | PySpark | Spark SQL | Diff |
|:---|---:|---:|---:|
| Gross Sales | £20,317,406.03 | £20,317,406.03 | 0.00 |
| Refunds & Cancellations | £1,462,424.18 | £1,462,424.18 | 0.00 |
| Net Revenue | £18,854,981.85 | £18,854,981.85 | 0.00 |
| Active Customer Accounts | 5,942 | 5,942 | 0.00 |
| Guest Checkout Share | 16.3% | 16.3% | 0.00 |
| Cleaned Line Items | 1,033,034 | 1,033,034 | 0.00 |

---

## References
- Parity assertion harness: notebook `eda-online-retail-gold-V1-2026-10-02 17_48_41.ipynb`
- SQL EDA notebook: `eda_online_retail_ii_sql.py`
