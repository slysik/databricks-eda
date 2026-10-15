# System Architecture — Annotated Diagram

Layer colours follow the medallion tokens in [`design/tokens.json`](../design/tokens.json): Bronze copper, Silver slate, Gold yellow, Serving blue.

This document provides a detailed, annotated view of the EDA Retail Lakehouse architecture. For a quick overview, see the diagram in the main [README](../README.md).

---

## End-to-End Data Flow

```mermaid
flowchart TB
    subgraph L0["Data Source"]
        direction LR
        SRC[("retail_source.online_retail<br/>.transactions_raw<br/>~1.07M rows")]
    end

    subgraph L1["Bronze Layer — Ingestion"]
        direction LR
        B1["Window Dedup<br/>(invoice, SKU, date, qty,<br/>price, customer, country)"]
        B2[("bronze.transactions_raw<br/>idempotent overwrite")]
        SRC -->|"spark.table()"| B1
        B1 -->|"22,523 overlap<br/>rows removed"| B2
    end

    subgraph L2["Silver Layer — Cleaning & Classification"]
        direction TB
        S1["Type Casting<br/>(int, decimal(12,3),<br/>timestamp)"]
        S2["6-Class Categorization"]
        S3A[("sales_cleaned<br/>sale + cancellation")]
        S3B[("sales_quarantine<br/>non_product, bad_debt,<br/>stock_adjustment")]
        S4["Identity Stitching<br/>(SHA-256 guest resolution)"]
        S5[("sales_stitched<br/>+ resolved_customer_id")]
        B2 --> S1 --> S2
        S2 -->|"sale / cancellation"| S3A
        S2 -->|"other"| S3B
        S3A --> S4 --> S5
    end

    subgraph L3["Gold Layer — Business Aggregates"]
        direction LR
        G1[("gold_daily_kpis<br/>Revenue, Orders, AOV,<br/>Cancellation Rate")]
        G2[("gold_customer_features<br/>RFM scores, LTV,<br/>Return Rate")]
        S3A --> G1
        S5 --> G2
    end

    subgraph L4["Governance — Unity Catalog"]
        direction TB
        UC1["Column Mask<br/>customer_id → ***MASKED***<br/>(non-admin roles)"]
        UC2["Row Filter<br/>country = 'United Kingdom'<br/>(non-admin roles)"]
    end

    subgraph L5["Serving & AI Layer"]
        direction LR
        SV1["Genie Agent<br/>NL → SQL → Charts"]
        SV2["MCP Server<br/>Purpose-built tools<br/>(6 business endpoints)"]
        SV3["MLflow Model<br/>Return Propensity RF<br/>ROC-AUC: 0.8899"]
    end

    subgraph XC["Cross-Cutting Controls"]
        direction TB
        X1["Delta CHECK Constraints<br/>price >= 0<br/>invoice_date IS NOT NULL"]
        X2["Dual-Engine Parity<br/>PySpark = Spark SQL<br/>(zero-tolerance assertion)"]
        X3["Idempotent Writes<br/>overwrite mode<br/>(re-runnable)"]
        X4["Audit Trail<br/>sales_quarantine<br/>(non-product lines preserved)"]
    end

    %% Governance links
    UC1 -.->|"applied at query time"| G2
    UC2 -.->|"applied at query time"| S5

    %% Serving links
    G1 --> SV1
    G2 --> SV1
    G1 --> SV2
    G2 --> SV2
    G2 --> SV3

    %% Cross-cutting links
    X1 -.->|"enforces"| S3A
    X2 -.->|"validates"| G1
    X3 -.->|"ensures"| B2
    X4 -.->|"isolates"| S3B

    style L0 fill:#f1f5f9,stroke:#64748b
    style L1 fill:#f6e6d8,stroke:#9a5b2e
    style L2 fill:#e8ecf1,stroke:#6b7a8d
    style L3 fill:#fbf0c8,stroke:#a87b00
    style L4 fill:#f8fafc,stroke:#1e3a5f
    style L5 fill:#dbeafe,stroke:#2563eb
    style XC fill:#fff3e0,stroke:#ef6c00
```

---

## Dual-Engine Parity Architecture

The core trust mechanism: every critical metric is computed independently in two engines and compared with zero tolerance.

```mermaid
flowchart LR
    subgraph Input["Shared Silver Input"]
        SIL[("sales_cleaned<br/>sales_stitched")]
    end

    subgraph PySpark["PySpark Engine"]
        PS1["DataFrame API<br/>groupBy / agg /<br/>window functions"]
        PS2["Result Set A"]
    end

    subgraph SparkSQL["Spark SQL Engine"]
        SQ1["SQL Dialect<br/>GROUP BY / CTE /<br/>CASE WHEN"]
        SQ2["Result Set B"]
    end

    subgraph Validation["Assertion Harness"]
        V1{"Diff == 0.00?"}
        V2["✓ PASS"]
        V3["✗ FAIL → halt"]
    end

    SIL --> PS1 --> PS2 --> V1
    SIL --> SQ1 --> SQ2 --> V1
    V1 -->|"Yes"| V2
    V1 -->|"No"| V3

    style Validation fill:#e8f5e9,stroke:#43a047
    style V3 fill:#ffebee,stroke:#e53935
```

---

## Declarative Pipeline (SDP) Variant

The same medallion logic is implemented as a Spark Declarative Pipeline with materialized views and expectations:

```mermaid
flowchart TB
    subgraph Pipeline["Spark Declarative Pipeline"]
        direction TB
        P1["01_bronze_transactions_raw<br/>@dp.materialized_view<br/>Dedup + write"]
        P2["02_silver_classified<br/>@dp.temporary_view<br/>6-class categorization"]
        P3["03_silver_sales_cleaned<br/>@dp.materialized_view<br/>@dp.expect_or_drop (x2)"]
        P4["04_silver_sales_quarantine<br/>@dp.materialized_view"]
        P5["05_silver_sales_stitched<br/>@dp.materialized_view<br/>row_filter applied"]
        P6["06_gold_daily_kpis<br/>@dp.materialized_view<br/>cluster_by(invoice_date)"]
        P7["07_gold_customer_features<br/>@dp.materialized_view<br/>schema with MASK"]
    end

    SRC2[("retail_source<br/>transactions_raw")] --> P1 --> P2
    P2 --> P3
    P2 --> P4
    P3 --> P5
    P5 --> P6
    P5 --> P7

    style Pipeline fill:#f5f5f5,stroke:#757575
```

---

## Component Boundaries & Ownership

| Layer | Components | Owned By | SLA Expectation |
|:---|:---|:---|:---|
| **Source** | UC source table | Data provider / upstream | Freshness per upstream SLA |
| **Bronze** | `bronze.transactions_raw` | Data Engineering | Near real-time (SDP) or batch (job) |
| **Silver** | `sales_cleaned`, `sales_quarantine`, `sales_stitched` | Data Engineering + Data Quality | Batch (daily/hourly) |
| **Gold** | `gold_daily_kpis`, `gold_customer_features` | Analytics Engineering | Batch, pre-aggregated |
| **Governance** | UC masks, row filters | Security / Governance | Enforced at query time |
| **ML** | `return_propensity_model` | ML Engineering | Batch scoring / on-demand |
| **Serving** | Genie, MCP Server | Platform / AI Engineering | Interactive (sub-second) |
