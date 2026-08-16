"""
==================================================================
PHASE 3 — STEP 4: ANOMALY DETECTION
==================================================================
Flags unusual days in: daily revenue, marketing spend/CAC, refund
amounts, and order volume — using a rolling z-score method (simple,
explainable, no black-box model needed for this kind of task).

Method: for each day, compare its value to the mean/std of a
trailing 30-day window. Flag as anomaly if |z-score| > 2.5
(~book-standard threshold for "notably unusual").

Run:
    python 04_anomaly_detection.py
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

ROLLING_WINDOW = 30
Z_THRESHOLD = 2.5

def flag_anomalies(series, window=ROLLING_WINDOW, z_thresh=Z_THRESHOLD):
    """Rolling z-score anomaly flagging. Returns z-scores and boolean flags."""
    rolling_mean = series.rolling(window, min_periods=window//2).mean()
    rolling_std = series.rolling(window, min_periods=window//2).std()
    z_scores = (series - rolling_mean) / rolling_std.replace(0, np.nan)
    is_anomaly = z_scores.abs() > z_thresh
    return z_scores, is_anomaly.fillna(False)


# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("Loading data...")
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")
marketing = pd.read_csv(f"{PROCESSED_DIR}/marketing_campaigns.csv", parse_dates=["date"])
returns = pd.read_csv(f"{PROCESSED_DIR}/returns.csv", parse_dates=["return_date"])

completed = orders[orders["order_status"] == "Completed"].copy()
items_full = order_items.merge(completed[["order_id", "order_date", "discount"]], on="order_id", how="inner")
items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

# ------------------------------------------------------------------
# 1. DAILY REVENUE ANOMALIES
# ------------------------------------------------------------------
print("\n[1/4] Checking daily revenue...")
daily_rev = items_full.groupby(items_full["order_date"].dt.date)["net_value"].sum()
daily_rev.index = pd.to_datetime(daily_rev.index)
daily_rev = daily_rev.asfreq("D", fill_value=0).sort_index()

z, anomaly = flag_anomalies(daily_rev)
revenue_anomalies = pd.DataFrame({"revenue": daily_rev, "z_score": z, "is_anomaly": anomaly})
revenue_anomalies_flagged = revenue_anomalies[revenue_anomalies["is_anomaly"]]
print(f"  Anomalous days found: {len(revenue_anomalies_flagged)}")

# ------------------------------------------------------------------
# 2. DAILY ORDER VOLUME ANOMALIES
# ------------------------------------------------------------------
print("[2/4] Checking daily order volume...")
daily_orders = completed.groupby(completed["order_date"].dt.date)["order_id"].nunique()
daily_orders.index = pd.to_datetime(daily_orders.index)
daily_orders = daily_orders.asfreq("D", fill_value=0).sort_index()

z2, anomaly2 = flag_anomalies(daily_orders)
order_anomalies = pd.DataFrame({"order_count": daily_orders, "z_score": z2, "is_anomaly": anomaly2})
order_anomalies_flagged = order_anomalies[order_anomalies["is_anomaly"]]
print(f"  Anomalous days found: {len(order_anomalies_flagged)}")

# ------------------------------------------------------------------
# 3. MARKETING SPEND / CAC ANOMALIES (daily total spend)
# ------------------------------------------------------------------
print("[3/4] Checking marketing spend...")
daily_spend = marketing.groupby("date")["spend"].sum()
daily_spend = daily_spend.asfreq("D", fill_value=0).sort_index()

z3, anomaly3 = flag_anomalies(daily_spend)
spend_anomalies = pd.DataFrame({"spend": daily_spend, "z_score": z3, "is_anomaly": anomaly3})
spend_anomalies_flagged = spend_anomalies[spend_anomalies["is_anomaly"]]
print(f"  Anomalous days found: {len(spend_anomalies_flagged)}")

# ------------------------------------------------------------------
# 4. REFUND AMOUNT ANOMALIES
# ------------------------------------------------------------------
print("[4/4] Checking daily refund amounts...")
daily_refunds = returns.groupby(returns["return_date"].dt.date)["refund_amount"].sum()
daily_refunds.index = pd.to_datetime(daily_refunds.index)
daily_refunds = daily_refunds.asfreq("D", fill_value=0).sort_index()

z4, anomaly4 = flag_anomalies(daily_refunds)
refund_anomalies = pd.DataFrame({"refund_amount": daily_refunds, "z_score": z4, "is_anomaly": anomaly4})
refund_anomalies_flagged = refund_anomalies[refund_anomalies["is_anomaly"]]
print(f"  Anomalous days found: {len(refund_anomalies_flagged)}")

# ------------------------------------------------------------------
# SAVE FULL ANOMALY REPORT (one CSV per metric, kept simple/no extra deps)
# ------------------------------------------------------------------
revenue_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_revenue.csv")
order_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_order_volume.csv")
spend_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_marketing_spend.csv")
refund_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_refunds.csv")

# ------------------------------------------------------------------
# CHART: revenue with anomalies highlighted
# ------------------------------------------------------------------
plt.figure(figsize=(14, 6))
plt.plot(revenue_anomalies.index, revenue_anomalies["revenue"], label="Daily Revenue", color="steelblue", linewidth=1)
plt.scatter(revenue_anomalies_flagged.index, revenue_anomalies_flagged["revenue"],
            color="red", label="Anomaly", zorder=5, s=40)
plt.title(f"Daily Revenue Anomaly Detection (|z-score| > {Z_THRESHOLD})")
plt.xlabel("Date")
plt.ylabel("Revenue")
plt.legend()
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/11_revenue_anomalies.png", dpi=100)
plt.close()

# ------------------------------------------------------------------
# BUSINESS-STYLE ROOT CAUSE HINTS (basic heuristic layer)
# ------------------------------------------------------------------
print("\n" + "="*60)
print("ANOMALY INVESTIGATION — sample root-cause hypotheses")
print("="*60)

if len(revenue_anomalies_flagged) > 0:
    worst_drop = revenue_anomalies_flagged.sort_values("z_score").iloc[0]
    worst_date = revenue_anomalies_flagged.sort_values("z_score").index[0]
    print(f"\nBiggest revenue drop: {worst_date.date()} "
          f"(z-score {worst_drop['z_score']:.2f}, revenue {worst_drop['revenue']:,.0f})")
    # check if order volume also dropped that day
    if worst_date in order_anomalies.index:
        same_day_orders = order_anomalies.loc[worst_date]
        print(f"  Same-day order volume z-score: {same_day_orders['z_score']:.2f}")
        if same_day_orders["is_anomaly"] and same_day_orders["z_score"] < 0:
            print("  -> Hypothesis: order volume also dropped -- likely a traffic/")
            print("     conversion issue rather than a change in average order size.")
        else:
            print("  -> Hypothesis: order volume normal -- investigate average order")
            print("     value / discounting / product mix that day instead.")

print("\n(This is a starting hypothesis, not a conclusion -- pair with the")
print(" SQL funnel/marketing queries from Phase 2 to confirm root cause.)")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Revenue anomalies:        {len(revenue_anomalies_flagged)}")
print(f"Order volume anomalies:   {len(order_anomalies_flagged)}")
print(f"Marketing spend anomalies:{len(spend_anomalies_flagged)}")
print(f"Refund anomalies:         {len(refund_anomalies_flagged)}")
print(f"\nAll anomaly CSVs + chart saved to: {OUTPUT_DIR}/")
