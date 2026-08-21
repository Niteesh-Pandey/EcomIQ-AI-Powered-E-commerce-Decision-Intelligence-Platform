from __future__ import annotations
import json
import os
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / os.getenv("PYTHON_RESULTS_DIR", "python_results")

def collect_ml_context() -> dict:
    risk_path = RESULTS_DIR / "customer_churn_risk_scores.csv"
    priority_path = RESULTS_DIR / "retention_priority_list.csv"
    result = {
        "model": "Random Forest classifier",
        "churn_definition": "No completed order in the last 90 days",
        "roc_auc": 0.70,
        "roc_auc_source": "supplied project report",
    }
    if priority_path.exists():
        result["high_value_high_risk_customers"] = int(len(pd.read_csv(priority_path)))
    if risk_path.exists():
        risk = pd.read_csv(risk_path)
        result["customers_with_purchase_history"] = int(len(risk))
        if "risk_segment" in risk.columns:
            result["risk_segments"] = risk["risk_segment"].value_counts(dropna=False).to_dict()
    # If a future model_metrics.json exists, prefer it over the report fallback.
    metrics = RESULTS_DIR / "model_metrics.json"
    if metrics.exists():
        try:
            data = json.loads(metrics.read_text(encoding="utf-8"))
            if "roc_auc" in data:
                result["roc_auc"] = data["roc_auc"]
                result["roc_auc_source"] = "model_metrics.json"
        except Exception:
            pass
    return result
