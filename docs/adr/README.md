# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records documenting the key technical choices in the Databricks EDA & Lakehouse reference implementation.

ADRs follow the standard format: **Context → Decision → Alternatives → Consequences**.

---

## Index

| ADR | Title | Status | Key Decision |
|:---|:---|:---:|:---|
| [ADR-001](ADR-001-medallion-architecture.md) | Medallion Architecture | Accepted | Bronze/Silver/Gold layer separation |
| [ADR-002](ADR-002-dual-engine-parity.md) | Dual-Engine Parity Validation | Accepted | PySpark + Spark SQL with zero-tolerance assertions |
| [ADR-003](ADR-003-unity-catalog-governance.md) | Unity Catalog Governance | Accepted | Dynamic column masking + row-level security |
| [ADR-004](ADR-004-mlflow-model-training.md) | MLflow Model Training & UC Registration | Accepted | Random Forest + MLflow + UC registry |
| [ADR-005](ADR-005-spark-declarative-pipelines.md) | Spark Declarative Pipelines (SDP) | Accepted | Parallel SDP implementation alongside notebook scripts |
| [ADR-006](ADR-006-purpose-built-mcp-server.md) | Purpose-Built MCP Server | Accepted | Business-shaped tools instead of raw SQL passthrough |
| [ADR-007](ADR-007-metric-views.md) | Unity Catalog Metric Views | Accepted | Declarative YAML metrics for Genie governance |

---

## How to Use This

- **Interviewers:** Read the "Context" and "Consequences" sections to understand the trade-offs being made.
- **Engineers:** Read the "Decision" and "Implementation Details" to understand the pattern.
- **Architects:** Compare the "Alternatives Considered" to evaluate the judgment behind the choice.

## Template

New ADRs should follow this template:

```markdown
# ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Date:** YYYY-MM-DD
**Decision Makers:** [roles]
**Consulted:** [roles]

---

## Context
[What is the problem or opportunity?]

## Decision
[What did we decide to do?]

## Alternatives Considered
[Table of alternatives with pros/cons]

## Consequences
### Positive
### Negative

---

## References
```
