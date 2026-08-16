"""
==================================================================
PHASE 3 — STEP 6: RFM SEGMENTATION (Python version)
==================================================================
Same business logic as the SQL RFM query (Phase 2), reimplemented
in Python with pandas. Useful to show both SQL and Python skills,
and this version is what feeds the churn/segmentation charts and
any further ML work (e.g. clustering) if you extend the project.

Run:
    python 06_rfm_segmentation.py
==================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import os
PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

REFERENCE_DATE = pd.Timestamp("2025-12-31")

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("Loading data...")
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")

completed = orders[orders["order_status"] == "Completed"].copy()
items_full = order_items.merge(completed[["order_id", "customer_id", "order_date", "discount"]],
                                on="order_id", how="inner")
items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

# ------------------------------------------------------------------
# CALCULATE RAW R, F, M PER CUSTOMER
# ------------------------------------------------------------------
print("Calculating RFM values...")
rfm = items_full.groupby("customer_id").agg(
    last_purchase=("order_date", "max"),
    frequency=("order_id", "nunique"),
    monetary=("net_value", "sum")
).reset_index()

rfm["recency_days"] = (REFERENCE_DATE - rfm["last_purchase"]).dt.days

print(f"Customers with purchase history: {len(rfm):,}")

# ------------------------------------------------------------------
# SCORE EACH DIMENSION 1-5 (using pandas qcut, same idea as SQL NTILE)
# ------------------------------------------------------------------
# recency: lower days = better = score 5. So we reverse the labels.
rfm["r_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)

rfm["rfm_total_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

# ------------------------------------------------------------------
# SEGMENT LABELS (same business rules as SQL version)
# ------------------------------------------------------------------
def assign_segment(row):
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif r >= 3 and f >= 3:
        return "Loyal Customers"
    elif r >= 4 and f <= 2:
        return "New Customers"
    elif r >= 3 and f <= 3 and m >= 3:
        return "Potential Loyalists"
    elif r <= 2 and f >= 4 and m >= 4:
        return "Cannot Lose Them"
    elif r <= 2 and f >= 3:
        return "At Risk"
    elif r <= 2 and f <= 2 and m <= 2:
        return "Lost"
    elif r <= 3 and f <= 2:
        return "Hibernating"
    else:
        return "Others"

rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)

rfm_out = rfm[["customer_id", "recency_days", "frequency", "monetary",
               "r_score", "f_score", "m_score", "rfm_total_score", "rfm_segment"]]
rfm_out.to_csv(f"{OUTPUT_DIR}/rfm_segments.csv", index=False)
print(f"\nRFM table saved: {OUTPUT_DIR}/rfm_segments.csv")

# ------------------------------------------------------------------
# SEGMENT SUMMARY
# ------------------------------------------------------------------
segment_summary = rfm_out.groupby("rfm_segment").agg(
    num_customers=("customer_id", "count"),
    avg_monetary=("monetary", "mean"),
    total_monetary=("monetary", "sum"),
    avg_recency_days=("recency_days", "mean"),
    avg_frequency=("frequency", "mean")
).round(2).sort_values("total_monetary", ascending=False)

print("\n" + "="*70)
print("SEGMENT SUMMARY")
print("="*70)
print(segment_summary)

segment_summary.to_csv(f"{OUTPUT_DIR}/rfm_segment_summary.csv")

# ------------------------------------------------------------------
# BUSINESS ACTIONS PER SEGMENT (documented recommendation table)
# ------------------------------------------------------------------
segment_actions = {
    "Champions": "VIP treatment, early access to new products, upsell premium items",
    "Loyal Customers": "Cross-sell complementary products, loyalty rewards program",
    "Potential Loyalists": "Membership/loyalty program invite to increase frequency",
    "New Customers": "Onboarding sequence, first-purchase follow-up, education content",
    "At Risk": "Targeted win-back campaign with personalized offer before they're lost",
    "Cannot Lose Them": "Urgent high-touch outreach — high past value, going cold",
    "Hibernating": "Low-cost reactivation email, otherwise low priority",
    "Lost": "Win-back campaign only if CAC-justified; otherwise deprioritize",
    "Others": "Monitor — doesn't fit a clean pattern yet"
}
actions_df = pd.DataFrame(list(segment_actions.items()), columns=["rfm_segment", "recommended_action"])
actions_df = actions_df.merge(segment_summary[["num_customers", "total_monetary"]], on="rfm_segment", how="left")
actions_df.to_csv(f"{OUTPUT_DIR}/rfm_segment_actions.csv", index=False)
print(f"\nSegment action plan saved: {OUTPUT_DIR}/rfm_segment_actions.csv")

# ------------------------------------------------------------------
# CHART: segment sizes
# ------------------------------------------------------------------
plt.figure(figsize=(10, 6))
segment_summary["num_customers"].sort_values().plot(kind="barh", color="darkcyan")
plt.title("Customer Count by RFM Segment")
plt.xlabel("Number of Customers")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/12_rfm_segment_sizes.png", dpi=100)
plt.close()

# ------------------------------------------------------------------
# CHART: segment value (total monetary contribution)
# ------------------------------------------------------------------
plt.figure(figsize=(10, 6))
segment_summary["total_monetary"].sort_values().plot(kind="barh", color="darkorange")
plt.title("Total Revenue Contribution by RFM Segment")
plt.xlabel("Total Monetary Value")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/13_rfm_segment_value.png", dpi=100)
plt.close()

print(f"\nCharts saved: 12_rfm_segment_sizes.png, 13_rfm_segment_value.png")
print("\nDone.")
