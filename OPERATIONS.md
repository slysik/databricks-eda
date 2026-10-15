# Operations Runbook

**Project:** Databricks EDA & Lakehouse Reference Implementation  
**Last Updated:** 2025-07-11  
**Scope:** Service health signals, monitoring, alerting, incident response, and operational ownership

---

## Purpose

This runbook defines how a delivery team would monitor, operate, and respond to issues in the Databricks EDA lakehouse. It lists actionable health signals, their owners, escalation paths, and remediation steps.

> **Note:** This is a production-oriented reference implementation. The signals and procedures below define what would be monitored and how incidents would be handled in a real production deployment.

---

## Operational Ownership (RACI)

| Component | Responsible | Accountable | Consulted | Informed |
|:---|:---|:---|:---|:---|
| Bronze Ingestion | Data Engineering | Tech Lead | Data Provider | Analytics |
| Silver Cleaning & DQ | Data Engineering | Tech Lead | Analytics Eng | ML Eng |
| Gold Aggregates | Analytics Engineering | Tech Lead | Data Eng | BI / Genie Users |
| ML Model (Return Propensity) | ML Engineering | ML Lead | Analytics Eng | Business Stakeholders |
| Genie Agent | AI/Platform Eng | Tech Lead | Analytics Eng | End Users |
| MCP Server | Platform Engineering | Tech Lead | AI/Platform Eng | Client Applications |
| Unity Catalog Governance | Security / Governance | CISO / Data Steward | Data Eng | All |
| DAB / Job Orchestration | Platform Engineering | Tech Lead | Data Eng | All |

---

## Service Health Signals

### 1. Pipeline Health (Bronze → Silver → Gold)

| Signal | What It Measures | Healthy Range | Alert Threshold | Owner |
|:---|:---|:---|:---|:---|
| **Task Success Rate** | % of job runs that complete without error | 100% (daily) | Any failure | Data Eng |
| **Pipeline Duration** | End-to-end execution time (5-task DAG) | < 15 min | > 30 min | Data Eng |
| **Bronze Row Count** | Rows in `bronze.transactions_raw` after dedup | Stable (~1.05M ± 5%) | > 10% deviation from prior run | Data Eng |
| **Deduplication Delta** | Rows removed by window dedup | ~22,523 (known overlap) | > 30,000 or < 15,000 | Data Eng |
| **Silver Quarantine Rate** | % of rows quarantined vs. clean | < 5% | > 10% | Data Eng + Analytics |
| **Gold Freshness** | Time since `gold_daily_kpis` last updated | < 24 hours | > 48 hours | Analytics Eng |

### 2. Data Quality Signals

| Signal | What It Measures | Healthy Range | Alert Threshold | Owner |
|:---|:---|:---|:---|:---|
| **CHECK Constraint Violations** | Rows failing `price >= 0` or `invoice_date IS NOT NULL` | 0 (all dropped) | > 100 rows dropped per run | Data Eng |
| **Null Rate (customer_id)** | % of `sales_cleaned` rows with null `customer_id` | 16-18% (guest checkout rate) | > 25% or < 5% | Analytics Eng |
| **Schema Drift** | Unexpected column additions/removals/changes | None | Any unapproved schema change | Data Eng |
| **Duplicate Detection** | Post-dedup duplicates on composite key | 0 | > 0 | Data Eng |
| **Revenue Reconciliation** | Gold `net_revenue` vs. Silver sum | Match to 2 decimal places | Any mismatch | Analytics Eng |

### 3. ML Model Signals

| Signal | What It Measures | Healthy Range | Alert Threshold | Owner |
|:---|:---|:---|:---|:---|
| **Prediction Latency** | Time for `predict_return_risk` tool call | < 500ms | > 2000ms | ML Eng |
| **Feature Drift** | KL divergence on RFM feature distributions | < 0.1 | > 0.3 | ML Eng |
| **Prediction Distribution** | % of predictions in "high risk" (>0.15) | 5-15% | > 30% or < 1% | ML Eng |
| **Model Version** | Active model version in UC registry | Latest approved | Any unapproved version serving | ML Eng |

### 4. Serving Layer Signals

| Signal | What It Measures | Healthy Range | Alert Threshold | Owner |
|:---|:---|:---|:---|:---|
| **Genie Response Time** | Time to first response (NL question) | < 5 seconds | > 15 seconds | AI/Platform Eng |
| **Genie Error Rate** | % of questions returning errors | < 5% | > 15% | AI/Platform Eng |
| **MCP Tool Call Latency** | Per-tool response time (p50, p95) | p50 < 500ms, p95 < 2s | p95 > 5s | Platform Eng |
| **MCP Tool Error Rate** | % of tool calls returning errors | < 2% | > 10% | Platform Eng |
| **SQL Warehouse Status** | Warehouse state for Genie/MCP queries | RUNNING | STOPPED or RESTARTING > 5min | Platform Eng |

### 5. Governance Signals

| Signal | What It Measures | Healthy Range | Alert Threshold | Owner |
|:---|:---|:---|:---|:---|
| **Mask Coverage** | % of `customer_id` queries hitting mask | 100% for non-admin | Any non-admin sees unmasked | Security |
| **Row Filter Effectiveness** | Non-admin rows returned for non-UK data | 0 | > 0 | Security |
| **Privilege Escalation Attempts** | Unauthorized GRANT/ALTER attempts | 0 | Any attempt | Security |
| **Audit Log Completeness** | UC audit events captured | 100% | < 99% | Security |

---

## Alerting Configuration (Reference)

### Databricks Job Alerting
```yaml
# In databricks.yml — add to the job definition
email_notifications:
  on_failure:
    - data-eng@example.com
  on_duration_warning_threshold_exceeded:
    - data-eng@example.com
timeout_seconds: 1800
max_retries: 2
min_retry_interval_millis: 30000
```

### Data Quality Alerting (Post-Deployment)
```
# Recommended: Databricks SQL Alert on quarantine rate
SELECT 
  COUNT(CASE WHEN line_type NOT IN ('sale','cancellation') THEN 1 END) * 100.0 / COUNT(*) AS quarantine_rate
FROM retail_prod.silver.sales_cleaned;
# Alert if quarantine_rate > 10
```

### Model Monitoring (Post-Deployment)
```
# Recommended: Scheduled query for feature drift
# Compare current RFM distributions to training baseline
# Alert if KL divergence > 0.3 on any feature
```

---

## Incident Response Procedures

### Severity Levels

| Severity | Definition | Response Time | Escalation |
|:---|:---|:---|:---|
| **SEV1 — Critical** | Gold tables stale > 48h, model serving down, governance breach | 1 hour | Tech Lead → Engineering Director |
| **SEV2 — High** | Pipeline task failed, quarantine rate > 15%, Genie error rate > 25% | 4 hours | Tech Lead |
| **SEV3 — Medium** | Slow queries, model drift detected, schema drift | 24 hours | Component owner |
| **SEV4 — Low** | Cosmetic issues, documentation gaps, minor performance degradation | Next sprint | Backlog |

### Common Incident Scenarios

#### Scenario 1: Pipeline Task Failure
```
1. Check job run in Databricks workspace (Jobs → EDA Retail Lakehouse Pipeline)
2. Identify failed task (bronze_ingest → silver_clean → gold_aggregate → apply_governance → create_genie)
3. Review task error log
4. Common causes:
   - Source table unavailable → check upstream data provider
   - Constraint violation → check Silver input data
   - Permission denied → check UC grants
5. Fix and re-run failed task (or full pipeline for idempotent layers)
6. Verify downstream Gold tables are consistent
```

#### Scenario 2: Elevated Quarantine Rate
```
1. Query: SELECT line_type, COUNT(*) FROM retail_prod.silver.sales_quarantine GROUP BY line_type
2. Identify which line_type increased (non_product, bad_debt, stock_adjustment)
3. Check source data for new stock codes or invoice prefixes
4. If new non-inventory codes: update classification rules in 02_silver_clean.py
5. If data quality issue: contact data provider
6. Re-run Silver pipeline after fix
```

#### Scenario 3: Model Drift Detected
```
1. Confirm drift signal (feature distribution comparison)
2. Check if source data distribution changed (new products, seasonal shift)
3. If transient: continue monitoring for 1 week
4. If sustained: trigger retraining with updated data
5. Validate new model (ROC-AUC must be >= current model)
6. Register new model version to UC
7. Update model alias (champion → new version)
```

#### Scenario 4: Governance Breach (Mask Bypass)
```
1. SEV1 — immediate escalation to Security / CISO
2. Identify affected queries from UC audit logs
3. Determine scope (which users, which data)
4. Revoke affected user's access immediately
5. Patch mask/row-filter function if vulnerable
6. Post-incident review within 48 hours
```

---

## Health Check Commands

### Quick Health Check (Run Anytime)
```bash
# Verify job status
databricks jobs list --output json | jq '.jobs[] | select(.name=="EDA Retail Lakehouse Pipeline")'

# Check table freshness
databricks sql query --warehouse-id $WAREHOUSE_ID \
  "SELECT MAX(invoice_date) as latest, COUNT(*) as rows FROM retail_prod.gold.gold_daily_kpis"

# Check quarantine rate
databricks sql query --warehouse-id $WAREHOUSE_ID \
  "SELECT COUNT(*) as quarantine_rows FROM retail_prod.silver.sales_quarantine"

# Verify model registration
databricks unity-catalog registered-models get --full-name retail_prod.gold.return_propensity_model
```

### Full Validation Suite
```bash
# Run the local validation script
bash scripts/validate.sh

# Or individually:
python3 -m py_compile build_presentation.py   # Python syntax
python3 -m json.tool genie/space_config.json  # JSON schema
databricks bundle validate --target dev       # DAB config
```

---

## Capacity Planning

| Resource | Current | Scaling Trigger | Scaling Action |
|:---|:---|:---|:---|
| SQL Warehouse | `4bbaafe9538467a0` | Query queue > 5 concurrent | Enable auto-scale or add warehouse |
| Serverless Compute | Auto-managed | Task duration > 30min | Review Spark configs, partition strategy |
| Storage (Delta) | ~2GB total | > 50GB | Enable liquid clustering, review retention |

---

## Operational Runbook Checklist (Daily / Weekly)

### Daily (Automated — 5 min)
- [ ] Pipeline job completed successfully
- [ ] Gold tables updated within freshness SLA
- [ ] No critical alerts fired

### Weekly (Manual — 15 min)
- [ ] Review quarantine rate trend
- [ ] Check model prediction distribution
- [ ] Review Genie/MCP error rates
- [ ] Check for schema drift notifications
- [ ] Review cost dashboard for anomalies

### Monthly (Manual — 30 min)
- [ ] Review and update SLIs/SLOs
- [ ] Model performance review (if drift detected)
- [ ] Access review (UC grants, audit logs)
- [ ] Capacity planning review
- [ ] Update runbook with new incident learnings
