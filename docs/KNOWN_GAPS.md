# Known Gaps

Found by reading the code against the docs. Each item says where, what is true today, and the fix. Ordered by how much it changes what you can claim.

| # | Gap | Where | What is true today | Fix |
|:-:|:---|:---|:---|:---|
| 1 | Model training and parity harness are not in the repo | [ADR-002](adr/ADR-002-dual-engine-parity.md), [ADR-004](adr/ADR-004-mlflow-model-training.md) cite a notebook that is not committed | ROC-AUC 0.8899 and "diff = 0.00" cannot be reproduced from this repo | Commit the notebook, or move training to `src/06_train_model.py` and parity to `src/07_parity_check.py` |
| 2 | `predict_return_risk` does not call the model | `mcp-retail-server/server.py:580` ("Simple risk heuristic (replace with actual MLflow model in production)") | It adds fixed weights (+0.3, +0.2, +0.15, +0.1); it is deterministic | Load `models:/retail_prod.gold.return_propensity_model@champion`, or say "rule-based" everywhere |
| 3 | `return_rate_pct` is always 0 | `src/03_gold_aggregate.py:61` keeps only `quantity > 0`; line 73 then sums `quantity < 0` | The model feature and the MCP rule (`server.py:585`, `> 10`) never see a return | Compute it from `silver.sales_cleaned`, where cancellations are present |
| 4 | The customer mask can be bypassed | `src/04_governance.py` masks `customer_id`; `resolved_customer_id` carries the same value as a string, unmasked (`src/03_gold_aggregate.py:79`, SDP `07_gold_customer_features.py:9`) | A non-admin can read the id from the other column | Mask or drop `resolved_customer_id`; hash guest ids only |
| 5 | The mask returns NULL, not `***MASKED***` | `src/04_governance.py:21-26` (`ELSE NULL`, column is INT) | Docs, ADR-003 and the Genie instructions say `***MASKED***` | Fix the wording, or cast to STRING and return the literal |
| 6 | The UK row filter does not reach Genie | `src/04_governance.py:44` filters `silver.sales_stitched`; Genie reads only the two Gold tables | "Genie inherits both automatically" is true for the mask only | Add `country` to Gold and filter there, or point Genie at filtered views |
| 7 | "Identity stitching" is a per-invoice surrogate key | `src/02_silver_clean.py:50-54` hashes invoice + country + date | A guest who buys twice gets two ids; nothing links journeys | Say "guest surrogate id", or build real resolution (email, device) |
| 8 | Five line classes, not six | `src/02_silver_clean.py:33-37`; the "reversed_within_hour" class is documented but never coded | Docs say 6 | Implement it or drop it from the docs (done in the docs here) |
| 9 | Dedup removes every exact duplicate, not only the sheet overlap | `src/01_bronze_ingest.py:27-28` partitions on 7 columns | A legitimately repeated line on one invoice is also dropped; the 22,523 figure is the total removed, not proof it is all overlap | Restrict dedup to the 1-9 Dec 2010 window, or add a line number to the key |
| 10 | Recency uses today's date on 2009-2011 data | `src/03_gold_aggregate.py:70,75` use `CURRENT_DATE()` | `days_since_last_order` is over 5,000; the RFM ranks are still valid, the absolute number is meaningless | Use `MAX(invoice_date)` over the dataset as the as-of date |
| 11 | `dev` and `prod` write to the same catalog | `databricks.yml:98,108`; `src/01_bronze_ingest.py:14` defaults to `retail_dev`, the rest to `retail_prod` | `bundle deploy -t dev` can overwrite prod tables | Separate catalogs per target; one default |
| 12 | Classification rules are written twice | `src/02_silver_clean.py:33-37` and `src/pipelines/retail_sdp/transformations/02_silver_classified.py` | The two paths can drift | Share one module, or keep only the SDP path |
| 13 | CHECK constraints fail the task; they do not drop rows | `src/02_silver_clean.py:80-85`; SDP uses `expect_or_drop` instead | [OPERATIONS.md](../OPERATIONS.md) described "dropped"; true only on the SDP path | Wording fixed in OPERATIONS.md |
| 14 | README listed files that are not committed | an `.ipynb` and `eda_online_retail_ii_sql.py` | Marked "not in this repo" | Commit them |

Not verified: the figures 1.07M rows, 22,523 removed, GBP 20.3M gross and the Genie space ID (`build_presentation.py:372` differs from every other file).
