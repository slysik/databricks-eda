# ADR-004: MLflow Model Training & Unity Catalog Registration

**Status:** Accepted  
**Date:** 2025-07-11  
**Decision Makers:** ML Engineering, Tech Lead  
**Consulted:** Analytics Engineering, Business Stakeholders

---

## Context

The business wants to identify high-risk return orders before they happen. Returns cost the retailer significant margin (GBP 1.46M in cancellations/refunds from the dataset). A predictive model scoring return propensity at checkout could enable proactive intervention (e.g., quality check, customer outreach). The model must be trained reproducibly, logged with full lineage, and registered in a governed registry for deployment.

## Decision

Train a **Random Forest Return Propensity classifier** using RFM (Recency, Frequency, Monetary) features derived from Gold customer features. Use **MLflow** for:

1. **Experiment tracking:** Log parameters, metrics (ROC-AUC), and artifacts for every run.
2. **Model registration:** Register the trained model in **Unity Catalog** as `retail_prod.gold.return_propensity_model`.

The model operates as a **probabilistic capability** — it provides a risk score, not a definitive prediction. The output is advisory and supports human-in-the-loop decision-making.

## Alternatives Considered

| Alternative | Pros | Cons |
|:---|:---|:---|
| **Gradient Boosted Trees (XGBoost)** | Often higher accuracy | More hyperparameter tuning; less interpretable; overkill for this dataset size |
| **Logistic Regression** | Highly interpretable, fast | Lower accuracy on non-linear relationships in RFM data |
| **Deep Learning** | Handles complex patterns | Massive overkill for tabular data; requires more data; training cost |
| **Rule-based scoring** | Deterministic, explainable | Misses non-linear patterns; brittle to data changes |

## Consequences

### Positive
- **Reproducibility:** MLflow logs every run with full parameter/metric context.
- **Governed deployment:** UC model registry enforces access control and version management.
- **Demonstrated capability:** 0.8899 ROC-AUC on the included dataset.
- **Separation of concerns:** Model is probabilistic and clearly separated from deterministic pipeline logic.

### Negative
- **Model drift risk:** RFM patterns may change over time (mitigated by future drift monitoring).
- **Training data dependency:** Model quality depends on Silver data quality.
- **No online serving yet:** Currently batch-scored; real-time scoring would need model serving endpoint.

## Model Card Summary

| Attribute | Value |
|:---|:---|
| **Model Type** | Random Forest Classifier |
| **Target** | Return propensity (binary: will customer return?) |
| **Features** | RFM scores (recency, frequency, monetary), order_count, total_spend, return_rate_pct |
| **ROC-AUC** | 0.8899 |
| **Training Data** | Silver sales_stitched → Gold customer features (Online Retail II, Dec 2009–Dec 2011) |
| **Registry** | Unity Catalog: `retail_prod.gold.return_propensity_model` |
| **Intended Use** | Advisory risk scoring for return intervention (not automated decision-making) |
| **Limitations** | Trained on single retailer's historical data; not validated on other retailers or time periods |

---

## References
- Source code: notebook `eda-online-retail-gold-V1-2026-10-02 17_48_41.ipynb` (ML section)
- MLflow model registry: `retail_prod.gold.return_propensity_model`
