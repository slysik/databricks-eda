set shell := ["bash", "-uc"]

default:
    @just --list

# -----------------------------------------------------------------------------
# Presentation & Deliverables
# -----------------------------------------------------------------------------

# Recompile the HTML executive presentation from notebook run export
build:
    @uv run --with markdown python build_presentation.py "eda-online-retail-gold-V1-2026-10-02 17_48_41.html" eda_online_retail_ii_presentation.html
    @echo "✅ Rebuilt eda_online_retail_ii_presentation.html"

# Open the HTML presentation in your default browser
preview:
    @open eda_online_retail_ii_presentation.html || xdg-open eda_online_retail_ii_presentation.html 2>/dev/null || echo "Open eda_online_retail_ii_presentation.html in your browser"

# Open the full pre-rendered executed notebook in your default browser
notebook:
    @open "eda-online-retail-gold-V1-2026-10-02 17_48_41.html" || xdg-open "eda-online-retail-gold-V1-2026-10-02 17_48_41.html" 2>/dev/null || echo "Open eda-online-retail-gold-V1-2026-10-02 17_48_41.html in your browser"

# Play the 36-second Genie Agent demo video
demo:
    @open demo/genie_agent_demo.mp4 || xdg-open demo/genie_agent_demo.mp4 2>/dev/null || echo "Open demo/genie_agent_demo.mp4"

# -----------------------------------------------------------------------------
# Databricks & Genie AI/BI
# -----------------------------------------------------------------------------

# Ask the live Genie One Agent a plain-English question from the CLI
ask question="What percentage of revenue comes from guest checkouts?" profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/ask_genie.py "{{question}}" --profile {{profile}}

# Deploy or refresh the Genie Space definition in the workspace
deploy-genie profile="primary-aws-user":
    @uv run --with databricks-sdk python genie/deploy_genie.py --profile {{profile}}

# Sync the Databricks Git folder to the latest commit on main
sync profile="primary-aws-user" repo_id="2455351154855299":
    @databricks -p {{profile}} repos update {{repo_id}} --branch main
    @echo "✅ Databricks Git folder synced to latest main"

# -----------------------------------------------------------------------------
# Validation & Linting
# -----------------------------------------------------------------------------

# Validate Python syntax and JSON schemas
check:
    @python3 -m py_compile build_presentation.py
    @python3 -m json.tool genie/eda_governed_gold_space.json > /dev/null
    @echo "✅ All build scripts and JSON schemas valid"
