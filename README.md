# Databricks EDA & Lakehouse Production Blueprint
### Online Retail II Transaction Analysis & Architecture

A dual-engine (**PySpark + Spark SQL**) exploratory data analysis with programmatic parity verification, extending to an enterprise Lakehouse blueprint featuring Gold medallion aggregates, MLflow predictive modeling, Unity Catalog governance, and Genie AI/BI self-service analytics.

---

## Executive Summary

Analyzing 1.07M raw transaction line items from a UK-based online gift retailer (Dec 2009 – Dec 2011). 

* **Headline Top-Line (+1.2% YoY):** Flat top-line growth hides two opposing dynamics:
  * **Identified Wholesale Accounts:** Fell **−2.8%** (units purchased dropped 10.8%, partially offset by higher ticket value per unit).
  * **Anonymous / Dotcom Web Channel:** Grew **+32.1%** and accounts for 100% of the retailer's net growth.
* **Volume Concentration & Seasonality:** 
  * Top 10% of customer accounts generate **63.2%** of revenue.
  * Q4 holiday rush (Sep–Nov) accounts for **~38%** of annual revenue.
  * Export markets are heavily concentrated in single corporate wholesale accounts (e.g., Netherlands = 1 customer driving 96% of sales).
* **Data Traps Discovered & Neutralized:**
  * **Sheet Overlap (1–9 Dec 2010):** 22,523 rows (~GBP 377k) were duplicated across annual sheets, inflating previously published Kaggle benchmarks.
  * **Cancellation Linkage:** Disentangled true returns (`C` prefix) from accounting adjustments (`A` prefix) and admin write-offs.

### Key Financials (Dual-Engine Parity Verified)

| Metric | PySpark | Spark SQL | Parity Status |
| :--- | :--- | :--- | :---: |
| **Gross Sales** | GBP 20,317,406.03 | GBP 20,317,406.03 | **PASS (Diff = 0.00)** |
| **Refunds & Cancellations** | GBP 1,462,424.18 | GBP 1,462,424.18 | **PASS (Diff = 0.00)** |
| **Net Revenue** | GBP 18,854,981.85 | GBP 18,854,981.85 | **PASS (Diff = 0.00)** |
| **Active Customer Accounts** | 5,942 | 5,942 | **PASS (Diff = 0.00)** |
| **Guest Checkout Share** | 16.3% | 16.3% | **PASS (Diff = 0.00)** |
| **Cleaned Line Items** | 1,033,034 | 1,033,034 | **PASS (Diff = 0.00)** |

---

## Production Blueprint & Lakehouse Architecture

```
graph TD
    %% Tonal Palette Styling
    classDef source fill:#F1F5F9,stroke:#94A3B8,stroke-width:1.5px,color:#0F172A;
    classDef bronze fill:#FFFBEB,stroke:#F59E0B,stroke-width:1.5px,color:#92400E;
    classDef silver fill:#EEF2FF,stroke:#6366F1,stroke-width:1.5px,color:#3730A3;
    classDef gold fill:#ECFDF5,stroke:#10B981,stroke-width:1.5px,color:#065F46;
    classDef serving fill:#F3E8FF,stroke:#A855F7,stroke-width:1.5px,color:#6B21A8;
    classDef uc fill:#0F172A,stroke:#334155,stroke-width:1.5px,color:#F8FAFC;

    %% Pipeline Nodes
    S[1. Data Landing Zone<br/><b>UCI Online Retail II Dataset</b><br/><i>1.07M Raw Transaction Line Items</i>]
    B[2. Bronze Layer<br/><b>synaptiq.online_retail.transactions_raw</b><br/><i>Monotonically Increasing PKs • Raw Types Preserved</i>]
    SLV[3. Silver Layer<br/><b>retail_prod.silver.transactions_clean & sales_stitched</b><br/><i>Deduplicated (_rn=1) • Non-Inventory Quarantine • Guest Identity Stitching</i>]
    G[4. Gold Layer<br/><b>gold_daily_kpis & gold_customer_features</b><br/><i>Sub-Second Aggregations • Dual-Engine Parity Verified (PySpark == Spark SQL)</i>]
    SRV[5. Serving & Machine Learning<br/><b>MLflow Model & Databricks Genie AI/BI</b><br/><i>Random Forest Return Propensity (ROC 0.89) • Natural Language SQL</i>]
    UC[6. Unity Catalog Governance<br/><i>Dynamic Masking (customer_id UDF) • Row-Level Security • End-to-End Lineage</i>]

    %% Data Flow
    S -->|Raw Batch Import| B
    B -->|Window Dedup & Quarantine| SLV
    SLV -->|Feature Eng & Aggregation| G
    G -->|Model Training & SQL Serving| SRV
    SRV -.- UC

    %% Styling Assignments
    class S source;
    class B bronze;
    class SLV silver;
    class G gold;
    class SRV serving;
    class UC uc;
```
      

### Key Technical Capabilities

1. **Dual-Engine Mathematical Parity:**
   Every analytical figure and KPI is implemented in two independent engines (PySpark DataFrame API and Spark SQL dialect), then programmatically evaluated against a zero-tolerance assertion harness.
2. **Deterministic Data Quality & Quarantine:**
   Delta `CHECK` constraints prevent fatal anomalies (`quantity != 0`, `price >= 0`), while non-inventory service codes (`POST`, `D`, `BANK CHARGES`, `AMAZONFEE`) are isolated into an audit quarantine table without breaking ingestion pipelines.
3. **Customer Identity Stitching:**
   Heuristic attribution resolves unauthenticated guest checkouts by linking invoice temporal locality, country metadata, and order velocity to recover fractured customer journeys.
4. **Predictive Machine Learning (MLflow + UC):**
   A Random Forest Return Propensity classifier trained on RFM features achieves **0.8899 ROC-AUC**, fully logged with parameters and artifacts, and registered to Unity Catalog as `retail_prod.gold.return_propensity_model`.
5. **Unity Catalog Dynamic Governance:**
   Dynamic column masks (`MASK()` user-defined function) mask `customer_id` into `***MASKED***` for non-administrative roles while preserving complete operational utility.

---

## Deliverables & Repository Layout

| File | Description |
| :--- | :--- |
| **`eda-online-retail-gold-V1-2026-10-02 17_48_41.ipynb`** | **Latest & Greatest Gold Notebook (v1):** 28 cells with gradient cards, pre-rendered outputs, and Genie Agent creation (§14). |
| **`eda_online_retail_ii.ipynb`** | **Interactive Jupyter Notebook:** Identical latest copy for standard reference. |
| **`eda_online_retail_ii.py`** | **Databricks Source Script:** Clean Databricks `# MAGIC` source format for Workspace imports, CI/CD, and DABs. |
| **`eda_online_retail_ii_presentation.html`** | **Executive Presentation:** Standalone single-file HTML presentation deliverable (214 KB) with zero external assets. |
| **`build_presentation.py`** | **Report Compiler:** Builds the presentation directly from notebook execution models, ensuring report-to-code alignment. |
| **`eda_interview_exercise.md`** | **Analytical Brief:** Project prompt, problem statement, and interview evaluation criteria. |

---

## Quickstart

### 1. Import into Databricks Workspace
1. In your Databricks workspace, navigate to **Workspace**.
2. Click **Import** &rarr; select **`eda_online_retail_ii.ipynb`**.
3. Attach to any **Serverless Compute** or standard cluster (DBR 14.3+).
4. Run all cells or view in **Results only** mode for clean presentation display.

### 2. Run Presentation Compiler Locally
The analytical HTML presentation can be recompiled directly from the notebook run export:
```bash
uv run --with markdown python build_presentation.py eda_online_retail_ii_run_export.html eda_online_retail_ii_presentation.html
```

---

## Strategic Recommendations

1. **Formalize the Dotcom Channel:** Transition unauthenticated web orders to a dedicated digital brand journey with persistent guest sessions and targeted email recapture.
2. **Mitigate Account Concentration Risk:** Implement proactive account retention monitoring for top wholesale accounts (top 1% drive 34% of volume).
3. **Automate High-Risk Return Intervention:** Deploy the registered `return_propensity_model` to flag high-probability returns (>15% risk) in real time during checkout.
