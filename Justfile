set shell := ["bash", "-uc"]

default:
    @just --list

# ─────────────────────────────────────────────────────────────────────────────
# Local (no Databricks connection needed)
# ─────────────────────────────────────────────────────────────────────────────

# Install full demo: validate, deploy pipeline, metric views, Genie, alerts
install profile="primary-aws-user" target="dev":
    @echo "=== Installing EDA Demo ==="
    @echo ""
    @echo "1/5 Validating..."
    @just validate
    @echo ""
    @echo "2/5 Deploying pipeline + alerts (DAB)..."
    @just dab-deploy {{target}}
    @echo ""
    @echo "3/5 Deploying metric views..."
    @just metric-views {{profile}}
    @echo ""
    @echo "4/5 Deploying Genie agent..."
    @just deploy-genie {{profile}}
    @echo ""
    @echo "5/5 Running pipeline..."
    @just dab-run {{target}}
    @echo ""
    @echo "=== Demo Installed ==="
    @echo ""
    @echo "Next steps:"
    @echo "  just health        # Check everything is healthy"
    @echo "  just ask "..."      # Ask Genie a question"
    @echo "  just preview       # Open presentation"
    @echo "  just demo          # Play demo video"

# Validate everything: Python syntax, JSON, YAML, docs, DAB config
validate:
    @bash scripts/validate.sh

# Open the executive presentation in your browser
preview:
    @open eda_online_retail_ii_presentation.html 2>/dev/null || echo "Open eda_online_retail_ii_presentation.html"

# Play the Genie demo video
demo:
    @open demo/genie_agent_demo.mp4 2>/dev/null || echo "Open demo/genie_agent_demo.mp4"

# Recompile presentation from notebook export
build notebook_html="":
    @if [ -z "{{notebook_html}}" ]; then echo "Usage: just build <notebook-export.html>"; exit 1; fi
    @uv run --with markdown python build_presentation.py "{{notebook_html}}" eda_online_retail_ii_presentation.html
    @echo "✅ Rebuilt presentation"

# ─────────────────────────────────────────────────────────────────────────────
# Databricks (requires: databricks CLI + auth)
# ─────────────────────────────────────────────────────────────────────────────

# Run health checks against live workspace
health profile="primary-aws-user":
    @bash scripts/health_check.sh {{profile}}

# Ask Genie a question
ask question="What percentage of revenue comes from guest checkouts?" profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/ask_genie.py "{{question}}" --profile {{profile}}

# Deploy Genie space definition
deploy-genie profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/deploy_genie.py --profile {{profile}}

# Deploy metric views to Unity Catalog
metric-views profile="primary-aws-user":
    @echo "Deploying metric views..."
    @for f in src/metrics/*.sql; do databricks -p {{profile}} sql -f $$f; done
    @echo "✅ Metric views deployed"

# Sync Git folder in Databricks workspace
sync profile="primary-aws-user" repo_id="4146773228775435":
    @databricks -p {{profile}} repos update {{repo_id}} --branch main
    @echo "✅ Synced to latest main"

# ─────────────────────────────────────────────────────────────────────────────
# DAB: validate, deploy, run, destroy
# ─────────────────────────────────────────────────────────────────────────────

# Validate DAB config
dab-validate target="dev":
    @databricks bundle validate --target {{target}}

# Deploy notebooks + alerts + jobs
dab-deploy target="dev":
    @databricks bundle deploy --target {{target}}
    @echo "✅ Deployed to {{target}}"

# Run the pipeline job
dab-run target="dev":
    @databricks bundle run eda_retail_pipeline --target {{target}}

# Full cycle: validate → deploy → run
dab target="dev":
    @just dab-validate {{target}}
    @just dab-deploy {{target}}
    @just dab-run {{target}}

# Destroy deployed resources
dab-destroy target="dev":
    @databricks bundle destroy --target {{target}}