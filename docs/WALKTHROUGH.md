# 10-Minute Walkthrough

A talk track, in the order I would say it. Each step names the file to have open. Every claim here is checked against the code; where the code falls short, that is said out loud.

## 1. The problem (1 min)
Two yearly sheets overlap by 22,523 rows and carry postage, bank charges and cancellations. Naive stacking overstates revenue by about GBP 377k. The goal is numbers a finance lead can sign off, queryable by non-engineers without loosening governance.

## 2. The flow (3 min): open `assets/architecture-light.svg`
Left to right: one UC source table, Lakeflow builds Bronze, Silver, Gold, then a Gold tables card that Genie and the MCP server read. Governance sits across the top.
- **Bronze** (`src/01_bronze_ingest.py`): dedup on a 7-column key, overwrite. Safe to rerun.
- **Silver** (`src/02_silver_clean.py:33-37`): one `when` chain turns every line into one of five types. Sales and cancellations go on; the rest go to `sales_quarantine`. Nothing is silently lost.
- **Gold** (`src/03_gold_aggregate.py`): daily KPIs and customer RFM, pre-aggregated.
- **Serving**: Genie over two Gold tables; six MCP tools.
The same logic runs as a declarative pipeline (`src/pipelines/retail_sdp/`) where bad rows are dropped and counted instead of failing the task.

## 3. Deterministic vs model judgment (2 min)
Show the table in the [README](../README.md#deterministic-vs-probabilistic). The principle: figures in a report are SQL. The model only picks the query (Genie) or gives an advisory score. Concrete examples to say: the `C` invoice prefix is a cancellation, always; the stock code `POST` is quarantined, always; Genie turns "revenue by country last quarter" into SQL, and the SQL is shown so a person can check it.
Be upfront on the risk score: the MCP tool uses fixed rules today. The random-forest model (ROC-AUC 0.8899, reported) was trained in the notebook and is not served.

## 4. Decisions and trade-offs (2 min)
Pick three from the README table and give the cost with each:
- Quarantine instead of fail: expected junk should not stop the pipeline, but quarantine growth then needs an alert.
- Overwrite instead of incremental: right for a static two-year file, wrong for a live feed.
- Purpose-built MCP tools instead of SQL passthrough: agents get safe, named questions; every new question costs a tool.

## 5. How I know it is healthy (1 min)
Today: fail-fast 5-task job with a timeout; CHECK constraints; quarantine as an audit trail; `check_data_quality`; every MCP call logged to MLflow with latency and success. Next: failure notifications and a quarantine-rate alert, then drift checks once the model is served.

## 6. Fit to a real client (1 min)
The rules (prefixes, stock codes, UK filter, KPIs) are this client's and stay local. The parts (quarantine pattern, mask and filter functions, MCP tool wrapper, bundle layout) carry over. For a new client I would start from their questions, not from this template.

## If asked "what would you fix first?"
1. Commit the training and parity code and wire the model into the MCP tool, or call it rule-based.
2. Fix `return_rate_pct` (always 0) and the `resolved_customer_id` mask bypass.
3. Separate dev and prod catalogs.
