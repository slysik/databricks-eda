#!/usr/bin/env bash
# =============================================================================
# EDA Health Check — Run from CLI to verify system health
# =============================================================================
# Usage: bash scripts/health_check.sh [--profile PROFILE]
# =============================================================================

set -euo pipefail

PROFILE="${1:-primary-aws-user}"
WAREHOUSE_ID="4bbaafe9538467a0"

echo "━━━ EDA Health Check ━━━"
echo "Profile: $PROFILE"
echo "Warehouse: $WAREHOUSE_ID"
echo ""

run_query() {
    local label="$1"
    local sql="$2"
    local result
    result=$(databricks -p "$PROFILE" sql -w "$WAREHOUSE_ID" "$sql" 2>&1) || true
    echo "  $label: $result"
}

# 1. Pipeline Health
echo "=== Pipeline Health ==="
run_query "Last pipeline run" "
SELECT
  CASE WHEN MAX(period_end_time) >= CURRENT_TIMESTAMP() - INTERVAL 24 HOURS
    THEN 'HEALTHY' ELSE 'STALE' END AS status,
  MAX(period_end_time) AS last_run
FROM system.lakeflow.job_run_timeline
WHERE job_id = (SELECT job_id FROM system.lakeflow.jobs WHERE name = 'EDA Retail Lakehouse Pipeline' LIMIT 1)
"

# 2. Data Freshness
echo ""
echo "=== Data Freshness ==="
run_query "Gold daily_kpis" "
SELECT MAX(invoice_date) AS latest_date, COUNT(*) AS rows
FROM retail_prod.gold.gold_daily_kpis
"
run_query "Gold customer_features" "
SELECT COUNT(*) AS rows FROM retail_prod.gold.gold_customer_features
"

# 3. Data Quality
echo ""
echo "=== Data Quality ==="
run_query "Silver clean rows" "
SELECT COUNT(*) AS rows FROM retail_prod.silver.sales_cleaned
"
run_query "Quarantine rows" "
SELECT COUNT(*) AS rows FROM retail_prod.silver.sales_quarantine
"
run_query "Quarantine rate" "
SELECT ROUND(
  (SELECT COUNT(*) FROM retail_prod.silver.sales_quarantine) * 100.0 /
  NULLIF((SELECT COUNT(*) FROM retail_prod.silver.sales_cleaned), 0), 2
) AS pct
"

# 4. Metric Views
echo ""
echo "=== Metric Views ==="
run_query "daily_kpis rows" "SELECT COUNT(*) FROM retail_prod.metrics.daily_kpis"
run_query "customer_features rows" "SELECT COUNT(*) FROM retail_prod.metrics.customer_features"
run_query "sales_by_country rows" "SELECT COUNT(*) FROM retail_prod.metrics.sales_by_country"

# 5. Governance
echo ""
echo "=== Governance ==="
run_query "Column masking active" "
SELECT CASE WHEN customer_id IS NULL THEN 'MASKED' ELSE 'EXPOSED' END AS status
FROM retail_prod.gold.gold_customer_features LIMIT 1
"

echo ""
echo "━━━ Health Check Complete ━━━"