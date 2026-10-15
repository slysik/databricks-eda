#!/usr/bin/env bash
# =============================================================================
# Validation Script — Databricks EDA & Lakehouse Reference Implementation
# =============================================================================
# Runs local validation checks that do not require a Databricks connection.
# Usage: bash scripts/validate.sh [--verbose]
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

VERBOSE="${1:-}"

pass_count=0
fail_count=0
warn_count=0

log_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    pass_count=$((pass_count + 1))
}

log_fail() {
    echo -e "  ${RED}✗${NC} $1"
    fail_count=$((fail_count + 1))
}

log_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    warn_count=$((warn_count + 1))
}

log_info() {
    echo -e "  ${BOLD}ℹ${NC} $1"
}

section() {
    echo ""
    echo -e "${BOLD}━━━ $1 ━━━${NC}"
}

# =============================================================================
# 1. Python Syntax Validation
# =============================================================================
section "Python Syntax Validation"

PYTHON_FILES=(
    "build_presentation.py"
    "src/01_bronze_ingest.py"
    "src/02_silver_clean.py"
    "src/03_gold_aggregate.py"
    "src/04_governance.py"
    "src/05_genie_agent.py"
    "src/pipelines/retail_sdp/transformations/01_bronze_transactions_raw.py"
    "src/pipelines/retail_sdp/transformations/02_silver_classified.py"
    "src/pipelines/retail_sdp/transformations/03_silver_sales_cleaned.py"
    "src/pipelines/retail_sdp/transformations/04_silver_sales_quarantine.py"
    "src/pipelines/retail_sdp/transformations/05_silver_sales_stitched.py"
    "src/pipelines/retail_sdp/transformations/06_gold_daily_kpis.py"
    "src/pipelines/retail_sdp/transformations/07_gold_customer_features.py"
    "genie/ask_genie.py"
    "genie/deploy_genie.py"
    "mcp-retail-server/server.py"
)

for file in "${PYTHON_FILES[@]}"; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            log_pass "Python syntax valid: $file"
        else
            log_fail "Python syntax error: $file"
        fi
    else
        log_warn "File not found: $file"
    fi
done

# =============================================================================
# 2. JSON Schema Validation
# =============================================================================
section "JSON Schema Validation"

JSON_FILES=(
    "genie/space_config.json"
)

for file in "${JSON_FILES[@]}"; do
    if [ -f "$file" ]; then
        if python3 -m json.tool "$file" > /dev/null 2>&1; then
            log_pass "JSON valid: $file"
        else
            log_fail "JSON parse error: $file"
        fi
    else
        log_warn "File not found: $file"
    fi
done

# =============================================================================
# 3. YAML Configuration Validation
# =============================================================================
section "YAML Configuration Validation"

if [ -f "databricks.yml" ]; then
    if python3 -c "
import yaml
with open('databricks.yml') as f:
    config = yaml.safe_load(f)
assert 'bundle' in config, 'Missing bundle key'
assert 'resources' in config, 'Missing resources key'
assert 'targets' in config, 'Missing targets key'
print('YAML structure valid')
" 2>/dev/null; then
        log_pass "Databricks bundle config: databricks.yml"
    else
        log_fail "Databricks bundle config: databricks.yml"
    fi
else
    log_warn "File not found: databricks.yml"
fi

# =============================================================================
# 4. Documentation Completeness
# =============================================================================
section "Documentation Completeness"

DOC_FILES=(
    "README.md"
    "PRODUCTION_READINESS.md"
    "OPERATIONS.md"
    "DEPLOYMENT.md"
    "docs/adr/README.md"
    "docs/adr/ADR-001-medallion-architecture.md"
    "docs/adr/ADR-002-dual-engine-parity.md"
    "docs/adr/ADR-003-unity-catalog-governance.md"
    "docs/adr/ADR-004-mlflow-model-training.md"
    "docs/adr/ADR-005-spark-declarative-pipelines.md"
    "docs/adr/ADR-006-purpose-built-mcp-server.md"
    "docs/adr/ADR-007-metric-views.md"
    "assets/architecture_diagram.md"
    "mcp-retail-server/README.md"
)

for file in "${DOC_FILES[@]}"; do
    if [ -f "$file" ] && [ -s "$file" ]; then
        log_pass "Document exists and non-empty: $file"
    elif [ -f "$file" ]; then
        log_fail "Document is empty: $file"
    else
        log_fail "Document missing: $file"
    fi
done

# =============================================================================
# 5. Mermaid Diagram Syntax (Basic Check)
# =============================================================================
section "Architecture Diagram Check"

if grep -q '```mermaid' assets/architecture_diagram.md 2>/dev/null; then
    log_pass "Mermaid diagrams found in architecture_diagram.md"
else
    log_fail "No Mermaid diagrams in architecture_diagram.md"
fi

if grep -q '```mermaid' README.md 2>/dev/null; then
    log_pass "Mermaid diagrams found in README.md"
else
    log_fail "No Mermaid diagrams in README.md"
fi

# =============================================================================
# 6. Databricks CLI Check (Optional — requires auth)
# =============================================================================
section "Databricks CLI Check (Optional)"

if command -v databricks &> /dev/null; then
    log_pass "Databricks CLI is installed"
    
    if databricks current-user me &> /dev/null; then
        log_pass "Databricks authentication verified"
    else
        log_warn "Databricks CLI present but not authenticated (run 'databricks auth login')"
    fi
else
    log_warn "Databricks CLI not installed (skipping Databricks checks)"
fi

# =============================================================================
# 7. DAB Configuration Validation (Optional)
# =============================================================================
section "DAB Configuration Validation (Optional)"

if command -v databricks &> /dev/null && databricks bundle validate --target dev &> /dev/null 2>&1; then
    log_pass "Databricks bundle configuration valid"
elif command -v databricks &> /dev/null; then
    log_warn "Databricks bundle validation failed (may need auth or workspace access)"
else
    log_warn "Databricks CLI not available (skipping bundle validation)"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BOLD}━━━ Validation Summary ━━━${NC}"
echo -e "  ${GREEN}Passed:${NC}  $pass_count"
echo -e "  ${RED}Failed:${NC}  $fail_count"
echo -e "  ${YELLOW}Warnings:${NC} $warn_count"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ All validation checks passed${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ $fail_count validation check(s) failed${NC}"
    exit 1
fi
