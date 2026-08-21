from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

RESULTS_DIR = BASE_DIR / os.getenv("PYTHON_RESULTS_DIR", "python_results")
AUTO_RUN_SOURCE = os.getenv("AUTO_RUN_PYTHON_SOURCE", "false").lower() == "true"


def _read_csv(name: str, rows: int = 30) -> Any:
    path = RESULTS_DIR / name
    if not path.exists():
        return {"status": "not_found", "file": name}

    df = pd.read_csv(path)
    return {
        "status": "success",
        "rows_returned": min(len(df), rows),
        "data": df.head(rows).where(pd.notna(df.head(rows)), None).to_dict("records"),
    }


def _summary_csv(name: str) -> dict:
    path = RESULTS_DIR / name
    if not path.exists():
        return {"status": "not_found", "file": name}

    df = pd.read_csv(path)
    return {
        "status": "success",
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "sample": df.head(20).where(pd.notna(df.head(20)), None).to_dict("records"),
    }


def collect_python_context() -> dict:
    """
    Adapter for your supplied Phase 3 output.

    The original analysis code is preserved under source/.
    Its generated CSV outputs are already copied into python_results/.

    You can replace/add your own Python calculations here. Return only
    verified outputs.
    """
    result = {
        "source_analyses": [
            "EDA",
            "Churn Prediction",
            "Revenue Forecasting",
            "Anomaly Detection",
            "A/B Testing",
            "RFM Customer Segmentation",
        ],
        "monthly_revenue": _read_csv("monthly_revenue.csv"),
        "churn_risk_scores": _summary_csv("customer_churn_risk_scores.csv"),
        "retention_priority": _summary_csv("retention_priority_list.csv"),
        "revenue_forecast_90_days": _summary_csv("revenue_forecast_90days.csv"),
        "revenue_anomalies": _summary_csv("anomalies_revenue.csv"),
        "order_anomalies": _summary_csv("anomalies_order_volume.csv"),
        "marketing_spend_anomalies": _summary_csv("anomalies_marketing_spend.csv"),
        "refund_anomalies": _summary_csv("anomalies_refunds.csv"),
        "rfm_segments": _summary_csv("rfm_segments.csv"),
        "rfm_segment_summary": _summary_csv("rfm_segment_summary.csv"),
        "rfm_segment_actions": _summary_csv("rfm_segment_actions.csv"),
    }

    # Add your own Python analytics here:
    #
    # result["my_analysis"] = {
    #     "metric": float(metric),
    #     "finding": "verified finding"
    # }

    return result


def run_custom_python_analysis(df: pd.DataFrame) -> dict:
    """
    Optional generic hook if you want to analyze a single CSV directly.

    Example:
        if "revenue" in df.columns:
            return {"total_revenue": float(df["revenue"].sum())}

    This function is intentionally simple so you can paste your own
    completed Python analytics into it.
    """
    if df.empty:
        return {"status": "empty_dataframe"}

    return {
        "status": "ready_for_custom_analysis",
        "rows": int(len(df)),
        "columns": list(df.columns),
    }
