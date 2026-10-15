set shell := ["bash", "-uc"]

default:
    @just --list

# -----------------------------------------------------------------------------
# Quick Start (new team members: run `just` to see all commands)
# -----------------------------------------------------------------------------

# Show this help
help:
    @just --list

# Validate everything (Python syntax, JSON, YAML, docs, DAB)
validate:
    @bash scripts/validate.sh

# Open the executive HTML presentation in your browser
preview:
    @open eda_online_retail_ii_presentation.html || xdg-open eda_online_retail_ii_presentation.html 2>/dev/null || echo "Open eda_online_retail_ii_presentation.html in your browser"

# Play the 36-second Genie Agent demo video
demo:
    @open demo/genie_agent_demo.mp4 || xdg-open demo/genie_agent_demo.mp4 2>/dev/null || echo "Open demo/genie_agent_demo.mp4"

# Recompile presentation from a notebook run export (requires: just build <notebook.html>)
build notebook_html="":
    @if [ -z "{{notebook_html}}" ]; then echo "Usage: just build <notebook-export.html>"; exit 1; fi
    @uv run --with markdown python build_presentation.py "{{notebook_html}}" eda_online_retail_ii_presentation.html
    @echo "✅ Rebuilt eda_online_retail_ii_presentation.html"

# -----------------------------------------------------------------------------
# Databricks & Genie AI/BI
# -----------------------------------------------------------------------------

# Ask the live Genie One Agent a plain-English question
ask question="What percentage of revenue comes from guest checkouts?" profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/ask_genie.py "{{question}}" --profile {{profile}}

# Deploy or refresh the Genie Space definition
deploy-genie profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/deploy_genie.py --profile {{profile}}

# Sync the Databricks Git folder to the latest commit on main
sync profile="primary-aws-user" repo_id="4146773228775435":
    @databricks -p {{profile}} repos update {{repo_id}} --branch main
    @echo "✅ Databricks Git folder synced to latest main"

# -----------------------------------------------------------------------------
# Databricks Asset Bundles (DAB)
# -----------------------------------------------------------------------------

# Validate the DAB config
dab-validate target="dev":
    @databricks bundle validate --target {{target}}

# Preview what will be deployed (dry run)
dab-plan target="dev":
    @databricks bundle plan --target {{target}}

# Deploy notebooks + create/update the job
dab-deploy target="dev":
    @databricks bundle deploy --target {{target}}
    @echo "✅ Deployed to {{target}}"

# Run the pipeline job
dab-run target="dev":
    @databricks bundle run eda_retail_pipeline --target {{target}}

# Show bundle summary (job URL, workspace path)
dab-summary target="dev":
    @databricks bundle summary --target {{target}}

# Open the job in the browser
dab-open target="dev":
    @open "$$(databricks bundle summary --target {{target}} 2>/dev/null | grep 'URL:' | awk '{print $$2}')" 2>/dev/null || echo "Run: just dab-summary {{target}} to get the URL"

# Destroy deployed resources (careful!)
dab-destroy target="dev":
    @databricks bundle destroy --target {{target}}

# Deploy metric views to Unity Catalog
metric-views profile="primary-aws-user":
    @echo "Deploying metric views to retail_prod.metrics..."
    @for f in src/metrics/*.sql; do echo "  $$f"; databricks -p {{profile}} sql -f $$f; done
    @echo "✅ Metric views deployed"

# Full cycle: validate → deploy → run
dab target="dev":
    @just dab-validate {{target}}
    @just dab-deploy {{target}}
    @just dab-run {{target}}

# -----------------------------------------------------------------------------
# Validation & Linting
# -----------------------------------------------------------------------------

# Run health checks against the live Databricks workspace
health profile="primary-aws-user":
    @bash scripts/health_check.sh {{profile}}

# Quick check: Python syntax + JSON schemas
check:
    @python3 -m py_compile build_presentation.py
    @python3 -m json.tool genie/space_config.json > /dev/null
    @echo "✅ All build scripts and JSON schemas valid"