"""
==================================================================
PHASE 3 — STEP 1: EXPLORATORY DATA ANALYSIS (EDA)
==================================================================
Reads cleaned data from data/processed/, produces summary stats
and saves charts as PNG files (for README / portfolio use).

Run:
    python 01_eda.py
==================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # no display needed, just save files
import matplotlib.pyplot as plt

PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("Loading data...")
customers = pd.read_csv(f"{PROCESSED_DIR}/customers.csv", parse_dates=["signup_date"])
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")
products = pd.read_csv(f"{PROCESSED_DIR}/products.csv")

# only completed orders count as real revenue
completed_orders = orders[orders["order_status"] == "Completed"].copy()

# join order_items to orders to get order_date on each line item
items_full = order_items.merge(completed_orders[["order_id", "order_date", "customer_id", "discount"]],
                                on="order_id", how="inner")
items_full["net_line_total"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

print(f"Customers: {len(customers):,}")
print(f"Orders (completed): {len(completed_orders):,}")
print(f"Order items (matched to completed orders): {len(items_full):,}")

# ------------------------------------------------------------------
# 1. REVENUE OVER TIME
# ------------------------------------------------------------------
print("\n[1/6] Revenue trend...")
monthly_rev = items_full.groupby(items_full["order_date"].dt.to_period("M"))["net_line_total"].sum()

plt.figure(figsize=(12, 5))
monthly_rev.plot(kind="line", marker="o")
plt.title("Monthly Net Revenue")
plt.xlabel("Month")
plt.ylabel("Revenue")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/01_monthly_revenue.png", dpi=100)
plt.close()
print("  Saved: 01_monthly_revenue.png")

# ------------------------------------------------------------------
# 2. ORDER STATUS DISTRIBUTION
# ------------------------------------------------------------------
print("[2/6] Order status distribution...")
status_counts = orders["order_status"].value_counts()

plt.figure(figsize=(7, 5))
status_counts.plot(kind="bar", color="steelblue")
plt.title("Order Status Distribution")
plt.xlabel("Status")
plt.ylabel("Count")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/02_order_status.png", dpi=100)
plt.close()
print("  Saved: 02_order_status.png")
print(status_counts)

# ------------------------------------------------------------------
# 3. CUSTOMER ACQUISITION BY CHANNEL
# ------------------------------------------------------------------
print("\n[3/6] Acquisition channel mix...")
channel_counts = customers["acquisition_channel"].value_counts()

plt.figure(figsize=(9, 5))
channel_counts.plot(kind="barh", color="coral")
plt.title("Customers by Acquisition Channel")
plt.xlabel("Number of Customers")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/03_acquisition_channel.png", dpi=100)
plt.close()
print("  Saved: 03_acquisition_channel.png")

# ------------------------------------------------------------------
# 4. AOV DISTRIBUTION
# ------------------------------------------------------------------
print("[4/6] AOV distribution...")
order_value = items_full.groupby("order_id")["net_line_total"].sum()

plt.figure(figsize=(9, 5))
plt.hist(order_value[order_value < order_value.quantile(0.99)], bins=50, color="seagreen")
plt.title("Order Value Distribution (excluding top 1% outliers)")
plt.xlabel("Order Value")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/04_order_value_distribution.png", dpi=100)
plt.close()
print(f"  Mean order value: {order_value.mean():.2f}")
print(f"  Median order value: {order_value.median():.2f}")
print("  Saved: 04_order_value_distribution.png")

# ------------------------------------------------------------------
# 5. CATEGORY REVENUE SHARE
# ------------------------------------------------------------------
print("\n[5/6] Category revenue share...")
items_with_cat = items_full.merge(products[["product_id", "category"]], on="product_id", how="left")
cat_rev = items_with_cat.groupby("category")["net_line_total"].sum().sort_values(ascending=False)

plt.figure(figsize=(8, 8))
plt.pie(cat_rev, labels=cat_rev.index, autopct="%1.1f%%", startangle=90)
plt.title("Revenue Share by Category")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/05_category_revenue_share.png", dpi=100)
plt.close()
print("  Saved: 05_category_revenue_share.png")

# ------------------------------------------------------------------
# 6. DEVICE-WISE ORDERS
# ------------------------------------------------------------------
print("[6/6] Device distribution...")
device_orders = completed_orders.merge(customers[["customer_id", "device"]], on="customer_id", how="left")
device_counts = device_orders["device"].value_counts()

plt.figure(figsize=(7, 5))
device_counts.plot(kind="bar", color="mediumpurple")
plt.title("Orders by Device")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/06_device_orders.png", dpi=100)
plt.close()
print("  Saved: 06_device_orders.png")

# ------------------------------------------------------------------
# SUMMARY STATS TABLE (for quick reference)
# ------------------------------------------------------------------
print("\n" + "="*60)
print("KEY SUMMARY STATS")
print("="*60)
print(f"Total customers:            {len(customers):,}")
print(f"Total completed orders:     {len(completed_orders):,}")
print(f"Total net revenue:          {items_full['net_line_total'].sum():,.2f}")
print(f"Average Order Value (AOV):  {order_value.mean():,.2f}")
print(f"Median Order Value:         {order_value.median():,.2f}")
print(f"Date range:                 {orders['order_date'].min().date()} to {orders['order_date'].max().date()}")
print("="*60)
print(f"\nAll charts saved to: {OUTPUT_DIR}/")
