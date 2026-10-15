# Databricks EDA: Retail Lakehouse

Raw retail transactions in, trusted Gold tables out, three ways to ask questions of them: Genie, MCP tools, a return-risk score. Built on 1.07M line items from a UK online gift retailer (Online Retail II, Dec 2009 to Dec 2011).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/architecture-dark.svg">
  <img src="assets/architecture-light.svg" alt="Architecture: a Unity Catalog source table flows into Lakeflow, which builds Bronze, Silver and Gold layers, then into Gold tables that Genie and an MCP server read. A dashed MLflow model card is trained in a notebook and not yet served. A governance panel lists Unity Catalog access controls, Delta quality checks and dual-engine parity." width="100%">
</picture>

*Solid boxes are in this repo. Dashed boxes exist only in the analysis notebook, which is not committed ([gap 1](docs/KNOWN_GAPS.md)). Diagram source: [`design/tokens.json`](design/tokens.json) and [`scripts/render_architecture.py`](scripts/render_architecture.py).*

## The problem

The source is two annual sheets that overlap by 22,523 rows (1 to 9 Dec 2010), mixed with non-product lines (postage, bank charges) and cancellations. Stacked naively, revenue is overstated by about GBP 377k. The job: produce numbers a finance lead can trust, and let non-engineers query them without breaking governance.

## Data flow

| Stage | Code | What happens | Guard |
|:---|:---|:---|:---|
| Bronze | [`01_bronze_ingest.py`](src/01_bronze_ingest.py) | Read the UC source table; drop exact duplicates on a 7-column key; overwrite | Idempotent: rerun gives the same table |
| Silver | [`02_silver_clean.py`](src/02_silver_clean.py) | Cast types; classify each line into 5 types by rule; route non-sales to quarantine; add a guest surrogate id | Delta CHECK constraints; quarantine keeps what was excluded |
| Gold | [`03_gold_aggregate.py`](src/03_gold_aggregate.py) | Daily KPIs from cleaned sales; RFM features per customer | Pre-aggregated, so BI and Genie queries are cheap |
| Governance | [`04_governance.py`](src/04_governance.py) | Column mask on `customer_id`; UK row filter | Unity Catalog, enforced at query time |
| Serving | [`05_genie_agent.py`](src/05_genie_agent.py), [`mcp-retail-server/`](mcp-retail-server/) | Genie space over two Gold tables; 6 MCP tools shaped to business questions | Only Gold is exposed |

The same medallion logic also exists as a Lakeflow declarative pipeline in [`src/pipelines/retail_sdp/`](src/pipelines/retail_sdp/), using expectations in place of CHECK constraints ([ADR-005](docs/adr/ADR-005-spark-declarative-pipelines.md)).

## Deterministic vs model judgment

Rule: anything that ends up in a report is deterministic. A model only chooses which query to run, or scores risk with its result shown.

| Task | Type | How |
|:---|:---:|:---|
| Dedup | Deterministic | `row_number()` over the 7-column key |
| Line classification | Deterministic | Invoice prefix `C` = cancellation, `A` = bad debt; stock codes `POST`, `DOT`, `M`, `BANK CHARGES`, `AMAZONFEE` = non-product; negative quantity = stock adjustment |
| Guest customer id | Deterministic | `sha256(invoice + country + date)` |
| KPIs, RFM scores | Deterministic | SQL aggregation |
| Mask, row filter | Deterministic | `IS_ACCOUNT_GROUP_MEMBER('admins')` |
| MCP tools 1 to 5 | Deterministic | Parameterised SQL over Gold |
| MCP `predict_return_risk` | Deterministic | Fixed weights on RFM signals (not the model; [gap 2](docs/KNOWN_GAPS.md)) |
| Genie question to SQL | **Model judgment** | An LLM writes the SQL. Contained by two curated Gold tables, written instructions, sample questions, UC governance, and the SQL shown beside each answer |
| Return-propensity model | **Model judgment** | Random forest, ROC-AUC 0.8899 as reported in the notebook. Advisory, not served |

## Decisions and trade-offs

| Decision | Why | Cost, and what I'd change |
|:---|:---|:---|
| Medallion layers ([ADR-001](docs/adr/ADR-001-medallion-architecture.md)) | Reprocess any layer alone; each consumer reads the right shape | Three tables per concept to run and monitor |
| Quarantine, do not fail | Postage and bank-charge lines are expected, not errors; kept for audit | Quarantine growth needs watching |
| Overwrite, not incremental | Simple and idempotent for a static 2-year dataset | Does not scale to a live feed; I would move to streaming tables or MERGE |
| Notebooks and a declarative pipeline | Shows both; the pipeline reports dropped-row counts | Rules are written twice ([gap 12](docs/KNOWN_GAPS.md)) |
| Genie over Gold only | Smaller search space, governed by default | Cannot answer line-level questions |
| Purpose-built MCP tools, not SQL passthrough ([ADR-006](docs/adr/ADR-006-purpose-built-mcp-server.md)) | Agents get questions the business asks; no arbitrary SQL | Each new question needs a new tool |
| UC mask and row filter ([ADR-003](docs/adr/ADR-003-unity-catalog-governance.md)) | One policy, enforced for every client | Holes found: [gaps 4 to 6](docs/KNOWN_GAPS.md) |

## How I'd know it is healthy

**Running today**
- The job is a 5-task chain that stops at the first failure, with an 1800 s timeout ([`databricks.yml`](databricks.yml)).
- CHECK constraints fail the Silver task on a bad row. The declarative pipeline drops the row and records the count in its event log.
- Every excluded row stays in `sales_quarantine`.
- The MCP `check_data_quality` tool reports quarantine counts, null rates and freshness on demand.
- Every MCP call is logged to MLflow with latency and success.

**Designed, not built** ([OPERATIONS.md](OPERATIONS.md)): failure notifications, quarantine-rate and freshness alerts, feature-drift checks, warehouse status. I would add failure notifications and a quarantine-rate SQL alert first.

## Built for this client, reusable elsewhere

- **Client-specific, keep local:** the line-classification rules (`C`/`A` prefixes, the stock-code list), the 7-column dedup key, the UK row filter, the Gold KPIs.
- **Reusable as parts, not as a template:** the quarantine pattern, the mask and row-filter function shape, the MCP tool wrapper with tracing, the bundle layout, the diagram generator. A new client changes the rules and Gold tables; the parts stay.

## Known gaps

Found by reading the code against these docs; full list with line references in [`docs/KNOWN_GAPS.md`](docs/KNOWN_GAPS.md). The three that matter most:
1. The model-training and parity code are in a notebook that is not committed, so ROC-AUC 0.8899 and "diff = 0.00" cannot be reproduced from here.
2. `return_rate_pct` is always 0 (the Gold filter removes the negative rows it sums).
3. The `customer_id` mask is bypassed by `resolved_customer_id`, and the row filter sits on a table Genie does not read.

## Run it

```bash
just validate                  # local checks, no workspace needed
databricks bundle deploy -t dev && databricks bundle run eda_retail_pipeline
just ask "What percentage of revenue comes from guest checkouts?"
```

More: [WALKTHROUGH.md](docs/WALKTHROUGH.md) (10-minute tour) · [FINDINGS.md](docs/FINDINGS.md) (business results) · [DEPLOYMENT.md](DEPLOYMENT.md) · [OPERATIONS.md](OPERATIONS.md) · [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) · [ADRs](docs/adr/) · [DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)
