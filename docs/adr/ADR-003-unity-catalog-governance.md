# ADR-003: Unity Catalog Governance (Column Masking + Row-Level Security)

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** Security/Governance, Data Engineering  
**Consulted:** Tech Lead, Analytics Engineering

---

## Context

The dataset contains customer identifiers (`customer_id`) that constitute PII under GDPR and similar regulations. Different user roles need different access: administrators need full data for operations, while analysts and Genie users should see masked identifiers. Additionally, regional managers should only see data for their region (e.g., UK managers see only UK transactions). The governance model must be inherited automatically by all query surfaces (notebooks, BI tools, Genie, MCP server) without application-level filtering.

## Decision

Use **Unity Catalog dynamic data governance** with two mechanisms:

1. **Dynamic Column Masking:** A `MASK()` user-defined function (`mask_customer_id`) replaces `customer_id` with `***MASKED***` for non-administrative roles. Applied at query time — no data transformation required.

2. **Row-Level Security:** A row filter function (`filter_uk_region`) restricts non-admin users to UK-only data on `sales_stitched`. Applied at query time via `IS_ACCOUNT_GROUP_MEMBER()`.

Both mechanisms are enforced at the Unity Catalog layer and are **automatically inherited** by all downstream consumers: Spark SQL, PySpark, JDBC/ODBC, Genie, MCP server, and any future application.

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Application-level filtering** | Simple to implement | Every consumer must remember to filter; easy to bypass; doesn't protect against direct table access |
| **Separate tables per role** | No runtime overhead | Data duplication; operational complexity; doesn't scale with roles |
| **View-based access control** | Familiar pattern | Doesn't mask columns; views can be bypassed with base table access |
| **External IAM (e.g., Okta groups)** | Centralized identity | Still needs UC integration; adds dependency |

## Consequences

### Positive
- **Zero-trust by default:** Even if a user queries the base table directly, UC enforces masking and filtering.
- **Automatic inheritance:** Genie, MCP server, and all clients get governance without code changes.
- **Auditability:** UC logs all access, including masked queries.
- **Separation of duties:** Security team owns UDFs; data team owns data.

### Negative
- **Performance overhead:** Mask/filter functions execute per query (minimal at this scale).
- **Complexity in debugging:** Users may be confused by `***MASKED***` values (mitigated by documentation and Genie instructions).
- **Account group dependency:** Masking relies on `IS_ACCOUNT_GROUP_MEMBER()` — group membership must be maintained correctly.

## Implementation Details

```sql
-- Column mask
CREATE OR REPLACE FUNCTION retail_prod.gold.mask_customer_id(customer_id INT)
RETURN
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('admins') THEN customer_id
       ELSE NULL
  END;

ALTER TABLE retail_prod.gold.gold_customer_features
ALTER COLUMN customer_id SET MASK retail_prod.gold.mask_customer_id;

-- Row filter
CREATE OR REPLACE FUNCTION retail_prod.gold.filter_uk_region(country STRING)
RETURN
  CASE WHEN IS_ACCOUNT_GROUP_MEMBER('admins') THEN TRUE
       ELSE country = 'United Kingdom'
  END;

ALTER TABLE retail_prod.silver.sales_stitched
SET ROW FILTER retail_prod.gold.filter_uk_region ON (country);
```

---

## References
- Source code: `src/04_governance.py`
- SDP variant: `src/pipelines/retail_sdp/transformations/07_gold_customer_features.py` (schema-level MASK)
