from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from sqlalchemy import create_engine, text
except ImportError:
    create_engine = None
    text = None


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_URL = os.getenv("DB_URL", "").strip()
MAX_SQL_ROWS = int(os.getenv("MAX_SQL_ROWS", "30"))

# These are the actual analytical views from your supplied Phase 2 SQL file.
# The views contain the business logic; this adapter simply queries their
# verified outputs and exposes them to the AI layer.
VIEW_NAMES = [
    "vw_a1_daily_revenue",
    "vw_a2_monthly_revenue",
    "vw_a3_month_over_month",
    "vw_a4_year_over_year",
    "vw_a5_average_order_value",
    "vw_a6_units_sold_by_category",
    "vw_b1_new_customers_per_month",
    "vw_b2_new_vs_returning_customers_per_month",
    "vw_b3_repeat_purchase_rate",
    "vw_b4_customer_purchase_frequency",
    "vw_b5_customer_lifetime",
    "vw_b6_average_customer_lifetime",
    "vw_f1_cac_per_channel",
    "vw_f2_clv_per_customer",
    "vw_f3_average_clv_per_acquisition_channel",
    "vw_f4_marketing_channel_performance",
    "vw_c1_overall_funnel_sessions_reaching_each_stage",
    "vw_c2_conversion_rate_at_each_funnel_step",
    "vw_c3_device_wise_conversion_rate",
    "vw_c4_channel_wise_conversion_rate",
    "vw_c5_biggest_drop_off_stage",
    "vw_d1_cohort_retention_table",
    "vw_d2_retention_by_acquisition_channel",
    "vw_e1_raw_rfm_values_per_customer",
    "vw_e2_rfm_scores",
    "vw_e3_full_rfm_segmentation",
    "vw_e4_segment_summary",
    "vw_g1_median_repurchase_interval",
    "vw_g2_churn_status_per_customer",
    "vw_g3_overall_churn_rate",
    "vw_g4_churn_rate_by_customer_segment",
    "vw_g5_high_value_churned_customers",
    "vw_h1_product_performance",
    "vw_h2_product_classification",
    "vw_h3_category_level_summary",
    "vw_h4_return_reasons_breakdown",
    "vw_h5_basket_analysis_products_frequently_bought_together",
    "vw_i1_conversion_rate_by_variant",
    "vw_i2_uplift_calculation",
    "vw_i3_estimated_annualized_business_impact",
]


def _safe(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def _engine():
    if not DB_URL:
        return None
    if create_engine is None:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt")
    return create_engine(DB_URL, pool_pre_ping=True)


def query_view(conn, view_name: str) -> dict:
    # View names are from our fixed allow-list; no user text is interpolated.
    result = conn.execute(
        text(f'SELECT * FROM "{view_name}" LIMIT :limit'),
        {"limit": MAX_SQL_ROWS},
    )
    rows = []
    for row in result.fetchall():
        rows.append({k: _safe(v) for k, v in row._mapping.items()})
    return {
        "status": "success",
        "rows": rows,
        "rows_returned": len(rows),
    }


def collect_sql_context() -> dict:
    engine = _engine()

    if engine is None:
        return {
            "status": "db_not_configured",
            "message": (
                "DB_URL is blank. Put your PostgreSQL connection string in .env. "
                "Your supplied SQL file is bundled under sql/."
            ),
            "available_views": VIEW_NAMES,
        }

    results = {}
    with engine.connect() as conn:
        for view_name in VIEW_NAMES:
            try:
                results[view_name] = query_view(conn, view_name)
            except Exception as exc:
                results[view_name] = {
                    "status": "error",
                    "error": str(exc),
                }

    return results
