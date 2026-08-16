"""
==================================================================
PHASE 3 — STEP 2: CHURN PREDICTION (Machine Learning)
==================================================================
Builds features per customer, trains a classification model to
predict churn probability, and evaluates it properly for imbalanced
data (not just accuracy).

Churn definition (business rule, same as SQL phase):
  Customer is CHURNED if no completed order in the last 90 days,
  AND they have purchased before (excludes brand-new customers).

Run:
    python 02_churn_prediction.py
==================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, precision_recall_curve, average_precision_score
)

import os
PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

REFERENCE_DATE = pd.Timestamp("2025-12-31")  # "today" for this dataset (last date in data)
CHURN_THRESHOLD_DAYS = 90

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("Loading data...")
customers = pd.read_csv(f"{PROCESSED_DIR}/customers.csv", parse_dates=["signup_date"])
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")
web_events = pd.read_csv(f"{PROCESSED_DIR}/web_events.csv", parse_dates=["event_timestamp"])
returns = pd.read_csv(f"{PROCESSED_DIR}/returns.csv", parse_dates=["return_date"])

completed = orders[orders["order_status"] == "Completed"].copy()
items_full = order_items.merge(completed[["order_id", "customer_id", "order_date", "discount"]],
                                on="order_id", how="inner")
items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

# ------------------------------------------------------------------
# FEATURE ENGINEERING (per customer)
# ------------------------------------------------------------------
print("Building features...")

# only customers who have purchased at least once are eligible for churn labeling
purchasers = items_full["customer_id"].unique()

feat = pd.DataFrame({"customer_id": purchasers}).set_index("customer_id")

# 1. days_since_last_purchase
last_purchase = items_full.groupby("customer_id")["order_date"].max()
feat["days_since_last_purchase"] = (REFERENCE_DATE - last_purchase).dt.days

# 2. purchase_frequency (number of distinct completed orders)
order_freq = completed[completed["customer_id"].isin(purchasers)].groupby("customer_id")["order_id"].nunique()
feat["purchase_frequency"] = order_freq

# 3. total_spend
total_spend = items_full.groupby("customer_id")["net_value"].sum()
feat["total_spend"] = total_spend

# 4. avg_order_value
order_value = items_full.groupby(["customer_id", "order_id"])["net_value"].sum().reset_index()
avg_ov = order_value.groupby("customer_id")["net_value"].mean()
feat["avg_order_value"] = avg_ov

# 5. number_of_sessions (from web_events)
sessions = web_events[web_events["session_id"] != "UNKNOWN_SESSION"]
n_sessions = sessions.groupby("customer_id")["session_id"].nunique()
feat["number_of_sessions"] = n_sessions

# 6. cart_abandonment (had add_to_cart but never purchase, count of such sessions)
cart_events = sessions[sessions["event_name"].isin(["add_to_cart", "purchase"])]
session_stage = cart_events.groupby(["customer_id", "session_id"])["event_name"].apply(set)
abandoned = session_stage.apply(lambda s: "add_to_cart" in s and "purchase" not in s)
abandon_count = abandoned.groupby("customer_id").sum()
feat["cart_abandonment"] = abandon_count

# 7. returns (count of returned items)
return_counts = returns.groupby("customer_id").size()
feat["returns"] = return_counts

# 8. discount_usage (fraction of orders that used a discount > 0)
disc_usage = completed[completed["customer_id"].isin(purchasers)].copy()
disc_usage["used_discount"] = disc_usage["discount"].fillna(0) > 0
discount_rate = disc_usage.groupby("customer_id")["used_discount"].mean()
feat["discount_usage"] = discount_rate

# fill missing engineered features with 0 (customer had none of that activity)
feat = feat.fillna(0)

# ------------------------------------------------------------------
# TARGET LABEL: churned (1) or active (0)
# ------------------------------------------------------------------
feat["churned"] = (feat["days_since_last_purchase"] > CHURN_THRESHOLD_DAYS).astype(int)

print(f"\nTotal customers with purchase history: {len(feat):,}")
print(f"Churned: {feat['churned'].sum():,} ({100*feat['churned'].mean():.1f}%)")
print(f"Active:  {(feat['churned']==0).sum():,} ({100*(1-feat['churned'].mean()):.1f}%)")

feat.to_csv(f"{OUTPUT_DIR}/churn_features.csv")
print(f"\nFeature table saved: {OUTPUT_DIR}/churn_features.csv")

# ------------------------------------------------------------------
# TRAIN / TEST SPLIT
# ------------------------------------------------------------------
FEATURE_COLS = [
    "purchase_frequency", "total_spend", "avg_order_value",
    "number_of_sessions", "cart_abandonment", "returns", "discount_usage"
]
# NOTE: days_since_last_purchase is EXCLUDED from features because it's
# literally how we defined the churn label — including it would leak
# the answer into the model (a well-known mistake to avoid & explain
# in interviews). The model has to predict churn from BEHAVIOR instead.

X = feat[FEATURE_COLS]
y = feat["churned"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)
print(f"\nTrain size: {len(X_train):,}  Test size: {len(X_test):,}")

# scale features (helps some models, doesn't hurt tree-based ones)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ------------------------------------------------------------------
# MODEL: Random Forest (handles imbalance via class_weight)
# ------------------------------------------------------------------
print("\nTraining Random Forest classifier...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    class_weight="balanced",   # important: dataset is imbalanced (few churners)
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)  # tree models don't need scaling, using raw X

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# ------------------------------------------------------------------
# EVALUATION — proper metrics for imbalanced classification
# ------------------------------------------------------------------
print("\n" + "="*60)
print("MODEL EVALUATION")
print("="*60)
print("\nClassification Report (Precision / Recall / F1):")
print(classification_report(y_test, y_pred, target_names=["Active", "Churned"]))

roc_auc = roc_auc_score(y_test, y_proba)
pr_auc = average_precision_score(y_test, y_proba)
print(f"ROC-AUC: {roc_auc:.3f}")
print(f"PR-AUC (average precision): {pr_auc:.3f}")
print("\nNote: with imbalanced churn data, PR-AUC is often more informative")
print("than ROC-AUC, since it focuses on performance on the minority")
print("(churned) class rather than being inflated by the easy majority class.")

cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:\n{cm}")
print("(rows = actual, cols = predicted; order = [Active, Churned])")

# ------------------------------------------------------------------
# CHARTS: ROC curve, PR curve, feature importance
# ------------------------------------------------------------------
fpr, tpr, _ = roc_curve(y_test, y_proba)
plt.figure(figsize=(7, 6))
plt.plot(fpr, tpr, label=f"ROC-AUC = {roc_auc:.3f}")
plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("Churn Model — ROC Curve")
plt.legend()
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/07_churn_roc_curve.png", dpi=100)
plt.close()

precision, recall, _ = precision_recall_curve(y_test, y_proba)
plt.figure(figsize=(7, 6))
plt.plot(recall, precision, label=f"PR-AUC = {pr_auc:.3f}")
plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("Churn Model — Precision-Recall Curve")
plt.legend()
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/08_churn_pr_curve.png", dpi=100)
plt.close()

importances = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values()
plt.figure(figsize=(9, 5))
importances.plot(kind="barh", color="teal")
plt.title("Churn Model — Feature Importance")
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/09_churn_feature_importance.png", dpi=100)
plt.close()

print(f"\nCharts saved: 07_churn_roc_curve.png, 08_churn_pr_curve.png, 09_churn_feature_importance.png")

# ------------------------------------------------------------------
# BUSINESS OUTPUT: risk scores for ALL customers + priority list
# ------------------------------------------------------------------
print("\nGenerating full customer risk scores...")
all_proba = model.predict_proba(X)[:, 1]

risk_table = feat.copy()
risk_table["churn_probability"] = all_proba
risk_table["risk_segment"] = pd.cut(
    risk_table["churn_probability"],
    bins=[0, 0.3, 0.6, 1.0],
    labels=["Low Risk", "Medium Risk", "High Risk"]
)

risk_table = risk_table.sort_values("churn_probability", ascending=False)
risk_table.to_csv(f"{OUTPUT_DIR}/customer_churn_risk_scores.csv")

# priority action list: high spend + high risk
priority = risk_table[
    (risk_table["risk_segment"] == "High Risk") &
    (risk_table["total_spend"] > risk_table["total_spend"].median())
].sort_values("total_spend", ascending=False)

priority.to_csv(f"{OUTPUT_DIR}/retention_priority_list.csv")

print(f"\nFull risk scores saved: {OUTPUT_DIR}/customer_churn_risk_scores.csv")
print(f"High-value + high-risk priority list saved: {OUTPUT_DIR}/retention_priority_list.csv")
print(f"({len(priority):,} customers flagged for immediate retention outreach)")

print("\n" + "="*60)
print("DONE — churn model trained and business outputs generated.")
print("="*60)
