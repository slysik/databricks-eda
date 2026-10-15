# Deployment Guide

**Project:** Databricks EDA & Lakehouse Reference Implementation  
**Last Updated:** 2025-07-11  
**Audience:** Delivery engineers deploying this reference implementation

---

## Purpose

This guide provides tested, accurate commands for deploying the lakehouse pipeline, validating the deployment, and running the analytical workloads. All commands have been verified against the current codebase.

> **Note:** This is a production-oriented reference implementation. The commands below deploy to a Databricks workspace. No specific SLA or uptime is guaranteed.

---

## Prerequisites

| Requirement | Version | Verify |
|:---|:---|:---|
| Databricks CLI | >= 0.228.0 | `databricks --version` |
| Python | >= 3.10 | `python3 --version` |
| `uv` (Python runner) | Latest | `uv --version` |
| `just` (command runner) | Latest | `just --version` |
| Databricks workspace auth | Configured | `databricks current-user me` |
| Databricks Asset Bundles | Supported in CLI | `databricks bundle --help` |

### Authentication

```bash
# Option 1: Databricks CLI profile
databricks auth profiles
databricks auth login --profile primary-aws-user

# Option 2: Environment variables
export DATABRICKS_HOST=https://dbc-61514402-8451.cloud.databricks.com
export DATABRICKS_TOKEN=dapi-...

# Verify
databricks current-user me
```

---

## Deployment Options

### Option A: Databricks Asset Bundle (Recommended)

The DAB-based deployment packages notebooks, the SDP pipeline, and a scheduled job into a single deployable artifact.

```bash
# 1. Validate the bundle configuration
just dab-validate dev

# 2. Preview what will be deployed (dry run)
just dab-plan dev

# 3. Deploy notebooks + create/update the job
just dab-deploy dev

# 4. Run the pipeline job
just dab-run dev

# 5. View deployment summary (job URL, workspace path)
just dab-summary dev

# Or full cycle: validate → deploy → run
just dab dev
```

### Option B: Git Folder (For Exploration)

Link the repository as a Databricks Git folder:

1. In Databricks workspace: **Workspace → Create → Git folder**
2. Enter: `https://github.com/slysik/databricks-eda`
3. Navigate to `src/` and open notebooks directly

### Option C: Import Individual Notebooks

1. In Databricks: **Workspace → Import**
2. Select `eda-online-retail-gold-V1-2026-10-02 17_48_41.ipynb`
3. Attach to **Serverless Compute** or cluster (DBR 14.3+)
4. Run all cells

---

## Step-by-Step: Full Pipeline Deployment

### Step 1: Prerequisites Check

```bash
# Verify CLI and auth
databricks current-user me
# Expected: your username and workspace URL

# Verify source table exists
databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT COUNT(*) FROM retail_source.online_retail.transactions_raw"
# Expected: ~1,067,558 rows
```

### Step 2: Deploy Pipeline

```bash
# From repository root
just dab-validate dev      # Validates YAML + variables
just dab-deploy dev        # Deploys notebooks + creates job
```

### Step 3: Run Pipeline

```bash
# Trigger the 5-task pipeline
just dab-run dev

# Monitor in workspace:
# Jobs → EDA Retail Lakehouse Pipeline → Latest run
```

### Step 4: Verify Deployment

```bash
# Check Bronze
databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT COUNT(*) as rows FROM retail_prod.bronze.transactions_raw"

# Check Silver
databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT COUNT(*) as clean_rows FROM retail_prod.silver.sales_cleaned"

databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT COUNT(*) as quarantine_rows FROM retail_prod.silver.sales_quarantine"

# Check Gold
databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT COUNT(*) as days, SUM(net_revenue) as total_net FROM retail_prod.gold.gold_daily_kpis"

# Verify governance
databricks sql query --warehouse-id 4bbaafe9538467a0 \
  "SELECT customer_id FROM retail_prod.gold.gold_customer_features LIMIT 5"
# Expected: NULL for non-admin users
```

### Step 5: Deploy Genie Agent

```bash
# Deploy or update the Genie Space definition
just deploy-genie

# Or manually:
uv run --with databricks-sdk python genie/deploy_genie.py --profile primary-aws-user
```

### Step 6: Test Genie

```bash
# Ask a question via CLI
just ask "What percentage of revenue comes from guest checkouts?"

# Or open Genie in the browser
open "https://dbc-61514402-8451.cloud.databricks.com/genie/rooms/01f1beaa006c1e47ab3758b127b2442d?o=7474656067656578"
```

---

## Validation Procedures

### Local Validation (No Databricks Required)

```bash
# Run full validation suite
bash scripts/validate.sh

# Or individually:
just check
```

**Expected output:**
```
✅ Python syntax valid
✅ JSON schema valid
✅ All build scripts and JSON schemas valid
```

### Deployment Validation (Databricks Required)

```bash
# Validate DAB configuration
databricks bundle validate --target dev

# Preview deployment plan
databricks bundle plan --target dev

# Verify job was created
databricks jobs list --output json | jq '.jobs[] | select(.name=="EDA Retail Lakehouse Pipeline") | {id, name}'
```

### Data Validation (Post-Pipeline Run)

```bash
# Run the parity validation
# (This is built into the pipeline — all 6 metrics must show diff = 0.00)

# Verify key data invariants:
databricks sql query --warehouse-id 4bbaafe9538467a0 "
  SELECT
    (SELECT COUNT(*) FROM retail_prod.bronze.transactions_raw) as bronze_rows,
    (SELECT COUNT(*) FROM retail_prod.silver.sales_cleaned) as silver_clean,
    (SELECT COUNT(*) FROM retail_prod.silver.sales_quarantine) as silver_quarantine,
    (SELECT SUM(net_revenue) FROM retail_prod.gold.gold_daily_kpis) as gold_net_revenue
"
```

**Expected values:**
| Metric | Expected | Tolerance |
|:---|---:|:---|
| Bronze rows | ~1,045,035 | ±1,000 |
| Silver clean rows | 1,033,034 | Exact |
| Silver quarantine rows | ~12,000 | ±2,000 |
| Gold net revenue | £18,854,981.85 | ±£0.01 |

---

## Rollback Procedures

### Rollback Pipeline Deployment

```bash
# Destroy deployed DAB resources (per target)
just dab-destroy dev

# Redeploy previous version
git checkout <previous-commit>
just dab-deploy dev
```

### Rollback Data (Idempotent by Design)

The pipeline uses `overwrite` mode for Bronze and `CREATE OR REPLACE TABLE` for Gold, so re-running the pipeline **always produces consistent state**:

```bash
# Simply re-run the full pipeline
just dab-run dev
```

### Rollback Genie Configuration

```bash
# Re-deploy previous Genie config
git checkout <previous-commit> -- genie/space_config.json
just deploy-genie
```

---

## Cleanup

```bash
# Remove DAB-deployed resources
just dab-destroy dev

# Drop tables (optional — requires admin)
databricks sql query --warehouse-id 4bbaafe9538467a0 "
  DROP SCHEMA IF EXISTS retail_prod.bronze CASCADE;
  DROP SCHEMA IF EXISTS retail_prod.silver CASCADE;
  DROP SCHEMA IF EXISTS retail_prod.gold CASCADE;
"
```

---

## Troubleshooting

| Error | Cause | Fix |
|:---|:---|:---|
| `databricks: command not found` | CLI not installed | `brew install databricks/tap/databricks-cli` |
| `Error: cannot find profile` | Auth not configured | `databricks auth login --profile primary-aws-user` |
| `Source table not found` | UC source table missing | Verify `retail_source.online_retail.transactions_raw` exists |
| `Permission denied` | UC grants insufficient | Check `SHOW GRANTS ON CATALOG retail_prod` |
| `Job timeout` | Pipeline exceeds 30min | Check source table size; consider cluster sizing |
| `Warehouse not found` | SQL warehouse ID incorrect | Verify warehouse ID in `databricks.yml` variables |
