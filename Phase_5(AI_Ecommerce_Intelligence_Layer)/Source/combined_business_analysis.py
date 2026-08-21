"""
==================================================================
PHASE 3 — COMBINED ANALYSIS PIPELINE
==================================================================
All 6 analyses combined into a single script:
  1. Exploratory Data Analysis (EDA)
  2. Churn Prediction (Random Forest)
  3. Demand / Revenue Forecasting (Linear Trend + Seasonality)
  4. Anomaly Detection (Rolling Z-Score)
  5. A/B Testing — Checkout Redesign (Two-proportion Z-test)
  6. RFM Customer Segmentation

Reads cleaned data from data/processed/, produces summary stats,
CSVs, and PNG charts (matching the original 6 individual scripts
exactly — same logic, same file names, same outputs).

Run:
    python combined_business_analysis.py
==================================================================
"""

import os
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
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from scipy import stats

PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

REFERENCE_DATE = pd.Timestamp("2025-12-31")   # "today" for this dataset
CHURN_THRESHOLD_DAYS = 90
ROLLING_WINDOW = 30
Z_THRESHOLD = 2.5
ALPHA = 0.05
MIN_BUSINESS_UPLIFT_PCT = 1.0


# ==================================================================
# SHARED DATA LOADING (loaded once, reused across all 6 sections)
# ==================================================================
def load_all_data():
    print("Loading data...")
    data = {}
    data["customers"] = pd.read_csv(f"{PROCESSED_DIR}/customers.csv", parse_dates=["signup_date"])
    data["orders"] = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
    data["order_items"] = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")
    data["products"] = pd.read_csv(f"{PROCESSED_DIR}/products.csv")
    data["web_events"] = pd.read_csv(f"{PROCESSED_DIR}/web_events.csv", parse_dates=["event_timestamp"])
    data["returns"] = pd.read_csv(f"{PROCESSED_DIR}/returns.csv", parse_dates=["return_date"])
    data["marketing"] = pd.read_csv(f"{PROCESSED_DIR}/marketing_campaigns.csv", parse_dates=["date"])
    data["experiments"] = pd.read_csv(f"{PROCESSED_DIR}/experiments.csv")

    data["completed"] = data["orders"][data["orders"]["order_status"] == "Completed"].copy()
    items_full = data["order_items"].merge(
        data["completed"][["order_id", "order_date", "customer_id", "discount"]],
        on="order_id", how="inner"
    )
    items_full["net_line_total"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))
    items_full["net_value"] = items_full["net_line_total"]  # alias used in some sections
    data["items_full"] = items_full
    return data


# ==================================================================
# SECTION 1 — EXPLORATORY DATA ANALYSIS (EDA)
# ==================================================================
def run_eda(data):
    print("\n" + "=" * 70)
    print("SECTION 1: EXPLORATORY DATA ANALYSIS")
    print("=" * 70)

    customers = data["customers"]
    orders = data["orders"]
    products = data["products"]
    completed_orders = data["completed"]
    items_full = data["items_full"]

    print(f"Customers: {len(customers):,}")
    print(f"Orders (completed): {len(completed_orders):,}")
    print(f"Order items (matched to completed orders): {len(items_full):,}")

    # 1. Revenue over time
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

    # 2. Order status distribution
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

    # 3. Customer acquisition by channel
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

    # 4. AOV distribution
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

    # 5. Category revenue share
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

    # 6. Device-wise orders
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

    print("\n" + "=" * 60)
    print("KEY SUMMARY STATS")
    print("=" * 60)
    print(f"Total customers:            {len(customers):,}")
    print(f"Total completed orders:     {len(completed_orders):,}")
    print(f"Total net revenue:          {items_full['net_line_total'].sum():,.2f}")
    print(f"Average Order Value (AOV):  {order_value.mean():,.2f}")
    print(f"Median Order Value:         {order_value.median():,.2f}")
    print(f"Date range:                 {orders['order_date'].min().date()} to {orders['order_date'].max().date()}")
    print("=" * 60)


# ==================================================================
# SECTION 2 — CHURN PREDICTION
# ==================================================================
def run_churn_prediction(data):
    print("\n" + "=" * 70)
    print("SECTION 2: CHURN PREDICTION")
    print("=" * 70)

    orders = data["orders"]
    completed = data["completed"]
    order_items = data["order_items"]
    web_events = data["web_events"]
    returns = data["returns"]

    items_full = order_items.merge(
        completed[["order_id", "customer_id", "order_date", "discount"]], on="order_id", how="inner"
    )
    items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

    print("Building features...")
    purchasers = items_full["customer_id"].unique()
    feat = pd.DataFrame({"customer_id": purchasers}).set_index("customer_id")

    last_purchase = items_full.groupby("customer_id")["order_date"].max()
    feat["days_since_last_purchase"] = (REFERENCE_DATE - last_purchase).dt.days

    order_freq = completed[completed["customer_id"].isin(purchasers)].groupby("customer_id")["order_id"].nunique()
    feat["purchase_frequency"] = order_freq

    total_spend = items_full.groupby("customer_id")["net_value"].sum()
    feat["total_spend"] = total_spend

    order_value = items_full.groupby(["customer_id", "order_id"])["net_value"].sum().reset_index()
    avg_ov = order_value.groupby("customer_id")["net_value"].mean()
    feat["avg_order_value"] = avg_ov

    sessions = web_events[web_events["session_id"] != "UNKNOWN_SESSION"]
    n_sessions = sessions.groupby("customer_id")["session_id"].nunique()
    feat["number_of_sessions"] = n_sessions

    cart_events = sessions[sessions["event_name"].isin(["add_to_cart", "purchase"])]
    session_stage = cart_events.groupby(["customer_id", "session_id"])["event_name"].apply(set)
    abandoned = session_stage.apply(lambda s: "add_to_cart" in s and "purchase" not in s)
    abandon_count = abandoned.groupby("customer_id").sum()
    feat["cart_abandonment"] = abandon_count

    return_counts = returns.groupby("customer_id").size()
    feat["returns"] = return_counts

    disc_usage = completed[completed["customer_id"].isin(purchasers)].copy()
    disc_usage["used_discount"] = disc_usage["discount"].fillna(0) > 0
    discount_rate = disc_usage.groupby("customer_id")["used_discount"].mean()
    feat["discount_usage"] = discount_rate

    feat = feat.fillna(0)

    feat["churned"] = (feat["days_since_last_purchase"] > CHURN_THRESHOLD_DAYS).astype(int)

    print(f"\nTotal customers with purchase history: {len(feat):,}")
    print(f"Churned: {feat['churned'].sum():,} ({100*feat['churned'].mean():.1f}%)")
    print(f"Active:  {(feat['churned']==0).sum():,} ({100*(1-feat['churned'].mean()):.1f}%)")

    feat.to_csv(f"{OUTPUT_DIR}/churn_features.csv")
    print(f"\nFeature table saved: {OUTPUT_DIR}/churn_features.csv")

    FEATURE_COLS = [
        "purchase_frequency", "total_spend", "avg_order_value",
        "number_of_sessions", "cart_abandonment", "returns", "discount_usage"
    ]
    # NOTE: days_since_last_purchase is EXCLUDED from features because it's
    # literally how the churn label is defined — including it would leak
    # the answer into the model.

    X = feat[FEATURE_COLS]
    y = feat["churned"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    print(f"\nTrain size: {len(X_train):,}  Test size: {len(X_test):,}")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("\nTraining Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=200, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)
    print("\nClassification Report (Precision / Recall / F1):")
    print(classification_report(y_test, y_pred, target_names=["Active", "Churned"]))

    roc_auc = roc_auc_score(y_test, y_proba)
    pr_auc = average_precision_score(y_test, y_proba)
    print(f"ROC-AUC: {roc_auc:.3f}")
    print(f"PR-AUC (average precision): {pr_auc:.3f}")

    cm = confusion_matrix(y_test, y_pred)
    print(f"\nConfusion Matrix:\n{cm}")
    print("(rows = actual, cols = predicted; order = [Active, Churned])")

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

    print("\nGenerating full customer risk scores...")
    all_proba = model.predict_proba(X)[:, 1]

    risk_table = feat.copy()
    risk_table["churn_probability"] = all_proba
    risk_table["risk_segment"] = pd.cut(
        risk_table["churn_probability"], bins=[0, 0.3, 0.6, 1.0],
        labels=["Low Risk", "Medium Risk", "High Risk"]
    )
    risk_table = risk_table.sort_values("churn_probability", ascending=False)
    risk_table.to_csv(f"{OUTPUT_DIR}/customer_churn_risk_scores.csv")

    priority = risk_table[
        (risk_table["risk_segment"] == "High Risk") &
        (risk_table["total_spend"] > risk_table["total_spend"].median())
    ].sort_values("total_spend", ascending=False)
    priority.to_csv(f"{OUTPUT_DIR}/retention_priority_list.csv")

    print(f"\nFull risk scores saved: {OUTPUT_DIR}/customer_churn_risk_scores.csv")
    print(f"High-value + high-risk priority list saved: {OUTPUT_DIR}/retention_priority_list.csv")
    print(f"({len(priority):,} customers flagged for immediate retention outreach)")


# ==================================================================
# SECTION 3 — DEMAND / REVENUE FORECASTING
# ==================================================================
def run_demand_forecasting(data):
    print("\n" + "=" * 70)
    print("SECTION 3: DEMAND / REVENUE FORECASTING")
    print("=" * 70)

    completed = data["completed"]
    order_items = data["order_items"]

    items_full = order_items.merge(completed[["order_id", "order_date", "discount"]], on="order_id", how="inner")
    items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))
    items_full["order_day"] = items_full["order_date"].dt.date

    daily_revenue = items_full.groupby("order_day")["net_value"].sum().reset_index()
    daily_revenue["order_day"] = pd.to_datetime(daily_revenue["order_day"])
    daily_revenue = daily_revenue.sort_values("order_day").reset_index(drop=True)

    full_range = pd.date_range(daily_revenue["order_day"].min(), daily_revenue["order_day"].max(), freq="D")
    daily_revenue = daily_revenue.set_index("order_day").reindex(full_range, fill_value=0).rename_axis("order_day").reset_index()

    print(f"Daily revenue series: {len(daily_revenue)} days, "
          f"{daily_revenue['order_day'].min().date()} to {daily_revenue['order_day'].max().date()}")

    daily_revenue["day_index"] = np.arange(len(daily_revenue))
    daily_revenue["day_of_week"] = daily_revenue["order_day"].dt.dayofweek
    daily_revenue["month"] = daily_revenue["order_day"].dt.month

    dow_dummies = pd.get_dummies(daily_revenue["day_of_week"], prefix="dow", drop_first=True)
    month_dummies = pd.get_dummies(daily_revenue["month"], prefix="month", drop_first=True)

    X = pd.concat([daily_revenue[["day_index"]], dow_dummies, month_dummies], axis=1)
    y = daily_revenue["net_value"]

    HOLDOUT_DAYS = 60
    X_train, X_test = X.iloc[:-HOLDOUT_DAYS], X.iloc[-HOLDOUT_DAYS:]
    y_train, y_test = y.iloc[:-HOLDOUT_DAYS], y.iloc[-HOLDOUT_DAYS:]

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred_test = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred_test)
    mape = mean_absolute_percentage_error(
        y_test.replace(0, np.nan).dropna(),
        pd.Series(y_pred_test, index=y_test.index).loc[y_test.replace(0, np.nan).dropna().index]
    )

    print(f"\nBacktest on last {HOLDOUT_DAYS} days:")
    print(f"  MAE:  {mae:,.2f}")
    print(f"  MAPE: {mape*100:.1f}%")

    residuals = y_test.values - y_pred_test
    resid_std = residuals.std()
    print(f"  Residual std dev (used for uncertainty band): {resid_std:,.2f}")

    print("\nRefitting on full history and forecasting next 90 days...")
    model_full = LinearRegression()
    model_full.fit(X, y)

    last_day_index = daily_revenue["day_index"].max()
    last_date = daily_revenue["order_day"].max()

    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=90, freq="D")
    future = pd.DataFrame({"order_day": future_dates})
    future["day_index"] = np.arange(last_day_index + 1, last_day_index + 1 + 90)
    future["day_of_week"] = future["order_day"].dt.dayofweek
    future["month"] = future["order_day"].dt.month

    future_dow = pd.get_dummies(future["day_of_week"], prefix="dow", drop_first=True)
    future_month = pd.get_dummies(future["month"], prefix="month", drop_first=True)

    X_future = pd.concat([future[["day_index"]], future_dow, future_month], axis=1)
    X_future = X_future.reindex(columns=X.columns, fill_value=0)

    future["forecast_revenue"] = model_full.predict(X_future)
    future["forecast_revenue"] = future["forecast_revenue"].clip(lower=0)
    future["lower_bound"] = (future["forecast_revenue"] - 1.96 * resid_std).clip(lower=0)
    future["upper_bound"] = future["forecast_revenue"] + 1.96 * resid_std

    future_out = future[["order_day", "forecast_revenue", "lower_bound", "upper_bound"]]
    future_out.to_csv(f"{OUTPUT_DIR}/revenue_forecast_90days.csv", index=False)

    print(f"\nForecast summary:")
    print(f"  Next 30 days total: {future_out.head(30)['forecast_revenue'].sum():,.2f}")
    print(f"  Next 60 days total: {future_out.head(60)['forecast_revenue'].sum():,.2f}")
    print(f"  Next 90 days total: {future_out['forecast_revenue'].sum():,.2f}")

    plt.figure(figsize=(14, 6))
    hist_recent = daily_revenue.tail(180)
    plt.plot(hist_recent["order_day"], hist_recent["net_value"], label="Historical Revenue", color="steelblue")
    plt.plot(future_out["order_day"], future_out["forecast_revenue"], label="Forecast", color="darkorange")
    plt.fill_between(future_out["order_day"], future_out["lower_bound"], future_out["upper_bound"],
                      color="darkorange", alpha=0.2, label="Approx. 95% Uncertainty Band")
    plt.axvline(last_date, color="gray", linestyle="--", linewidth=1)
    plt.title("Daily Revenue: Historical + 90-Day Forecast")
    plt.xlabel("Date")
    plt.ylabel("Revenue")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/10_revenue_forecast.png", dpi=100)
    plt.close()

    print(f"\nChart saved: 10_revenue_forecast.png")
    print(f"Forecast data saved: {OUTPUT_DIR}/revenue_forecast_90days.csv")

    print("\nLIMITATIONS: linear trend won't capture regime changes; day-of-week/month")
    print(f"seasonality only; backtest MAPE was {mape*100:.1f}% — treat as expected error range,")
    print("not the point forecast; 60-90 day horizons are less reliable than 30 days.")


# ==================================================================
# SECTION 4 — ANOMALY DETECTION
# ==================================================================
def flag_anomalies(series, window=ROLLING_WINDOW, z_thresh=Z_THRESHOLD):
    """Rolling z-score anomaly flagging. Returns z-scores and boolean flags."""
    rolling_mean = series.rolling(window, min_periods=window // 2).mean()
    rolling_std = series.rolling(window, min_periods=window // 2).std()
    z_scores = (series - rolling_mean) / rolling_std.replace(0, np.nan)
    is_anomaly = z_scores.abs() > z_thresh
    return z_scores, is_anomaly.fillna(False)


def run_anomaly_detection(data):
    print("\n" + "=" * 70)
    print("SECTION 4: ANOMALY DETECTION")
    print("=" * 70)

    completed = data["completed"]
    order_items = data["order_items"]
    marketing = data["marketing"]
    returns = data["returns"]

    items_full = order_items.merge(completed[["order_id", "order_date", "discount"]], on="order_id", how="inner")
    items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

    print("\n[1/4] Checking daily revenue...")
    daily_rev = items_full.groupby(items_full["order_date"].dt.date)["net_value"].sum()
    daily_rev.index = pd.to_datetime(daily_rev.index)
    daily_rev = daily_rev.asfreq("D", fill_value=0).sort_index()

    z, anomaly = flag_anomalies(daily_rev)
    revenue_anomalies = pd.DataFrame({"revenue": daily_rev, "z_score": z, "is_anomaly": anomaly})
    revenue_anomalies_flagged = revenue_anomalies[revenue_anomalies["is_anomaly"]]
    print(f"  Anomalous days found: {len(revenue_anomalies_flagged)}")

    print("[2/4] Checking daily order volume...")
    daily_orders = completed.groupby(completed["order_date"].dt.date)["order_id"].nunique()
    daily_orders.index = pd.to_datetime(daily_orders.index)
    daily_orders = daily_orders.asfreq("D", fill_value=0).sort_index()

    z2, anomaly2 = flag_anomalies(daily_orders)
    order_anomalies = pd.DataFrame({"order_count": daily_orders, "z_score": z2, "is_anomaly": anomaly2})
    order_anomalies_flagged = order_anomalies[order_anomalies["is_anomaly"]]
    print(f"  Anomalous days found: {len(order_anomalies_flagged)}")

    print("[3/4] Checking marketing spend...")
    daily_spend = marketing.groupby("date")["spend"].sum()
    daily_spend = daily_spend.asfreq("D", fill_value=0).sort_index()

    z3, anomaly3 = flag_anomalies(daily_spend)
    spend_anomalies = pd.DataFrame({"spend": daily_spend, "z_score": z3, "is_anomaly": anomaly3})
    spend_anomalies_flagged = spend_anomalies[spend_anomalies["is_anomaly"]]
    print(f"  Anomalous days found: {len(spend_anomalies_flagged)}")

    print("[4/4] Checking daily refund amounts...")
    daily_refunds = returns.groupby(returns["return_date"].dt.date)["refund_amount"].sum()
    daily_refunds.index = pd.to_datetime(daily_refunds.index)
    daily_refunds = daily_refunds.asfreq("D", fill_value=0).sort_index()

    z4, anomaly4 = flag_anomalies(daily_refunds)
    refund_anomalies = pd.DataFrame({"refund_amount": daily_refunds, "z_score": z4, "is_anomaly": anomaly4})
    refund_anomalies_flagged = refund_anomalies[refund_anomalies["is_anomaly"]]
    print(f"  Anomalous days found: {len(refund_anomalies_flagged)}")

    revenue_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_revenue.csv")
    order_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_order_volume.csv")
    spend_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_marketing_spend.csv")
    refund_anomalies_flagged.to_csv(f"{OUTPUT_DIR}/anomalies_refunds.csv")

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

    print("\n" + "=" * 60)
    print("ANOMALY INVESTIGATION — sample root-cause hypotheses")
    print("=" * 60)
    if len(revenue_anomalies_flagged) > 0:
        worst_drop = revenue_anomalies_flagged.sort_values("z_score").iloc[0]
        worst_date = revenue_anomalies_flagged.sort_values("z_score").index[0]
        print(f"\nBiggest revenue drop: {worst_date.date()} "
              f"(z-score {worst_drop['z_score']:.2f}, revenue {worst_drop['revenue']:,.0f})")
        if worst_date in order_anomalies.index:
            same_day_orders = order_anomalies.loc[worst_date]
            print(f"  Same-day order volume z-score: {same_day_orders['z_score']:.2f}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Revenue anomalies:        {len(revenue_anomalies_flagged)}")
    print(f"Order volume anomalies:   {len(order_anomalies_flagged)}")
    print(f"Marketing spend anomalies:{len(spend_anomalies_flagged)}")
    print(f"Refund anomalies:         {len(refund_anomalies_flagged)}")


# ==================================================================
# SECTION 5 — A/B TESTING (CHECKOUT REDESIGN)
# ==================================================================
def run_ab_testing(data):
    print("\n" + "=" * 70)
    print("SECTION 5: A/B TESTING — CHECKOUT REDESIGN")
    print("=" * 70)

    experiments = data["experiments"]
    control = experiments[experiments["variant"] == "control"]
    treatment = experiments[experiments["variant"] == "treatment"]

    n_control = len(control)
    n_treatment = len(treatment)
    conv_control = control["converted"].sum()
    conv_treatment = treatment["converted"].sum()

    p_control = conv_control / n_control
    p_treatment = conv_treatment / n_treatment

    print(f"\nControl:   n={n_control:,}, conversions={conv_control:,}, rate={p_control*100:.2f}%")
    print(f"Treatment: n={n_treatment:,}, conversions={conv_treatment:,}, rate={p_treatment*100:.2f}%")

    p_pooled = (conv_control + conv_treatment) / (n_control + n_treatment)
    se_pooled = np.sqrt(p_pooled * (1 - p_pooled) * (1 / n_control + 1 / n_treatment))

    z_stat = (p_treatment - p_control) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    print(f"\nZ-statistic: {z_stat:.3f}   P-value: {p_value:.4f}")
    is_statistically_significant = p_value < ALPHA
    print(f"Statistically significant?  {'YES' if is_statistically_significant else 'NO'}")

    se_unpooled = np.sqrt(
        p_control * (1 - p_control) / n_control + p_treatment * (1 - p_treatment) / n_treatment
    )
    uplift = p_treatment - p_control
    z_critical = stats.norm.ppf(1 - ALPHA / 2)
    ci_lower = uplift - z_critical * se_unpooled
    ci_upper = uplift + z_critical * se_unpooled

    print(f"\nAbsolute uplift: {uplift*100:.2f} pp   95% CI: [{ci_lower*100:.2f}, {ci_upper*100:.2f}] pp")

    uplift_pct_points = uplift * 100
    is_business_significant = uplift_pct_points >= MIN_BUSINESS_UPLIFT_PCT
    print(f"Business significant? {'YES' if is_business_significant else 'NO'}")

    total_revenue_control = control["revenue"].sum()
    total_revenue_treatment = treatment["revenue"].sum()
    revenue_lift = total_revenue_treatment - total_revenue_control
    print(f"\nRevenue lift in experiment: {revenue_lift:,.2f}")

    if is_statistically_significant and is_business_significant and ci_lower > 0:
        decision = "SHIP"
        reason = ("Result is both statistically significant (p < 0.05, CI entirely "
                  "positive) AND business-significant (uplift exceeds the minimum "
                  "threshold that justifies the engineering/rollout cost).")
    elif is_statistically_significant and not is_business_significant:
        decision = "DO NOT SHIP (as-is)"
        reason = "Statistically real, but the uplift is too small to be worth the cost of shipping."
    elif not is_statistically_significant and uplift_pct_points > 0:
        decision = "CONTINUE TEST"
        reason = "Direction looks promising but we can't yet rule out random chance."
    else:
        decision = "DO NOT SHIP"
        reason = "No credible positive effect detected."

    print(f"\nDecision: {decision}")
    print(f"Reason:   {reason}")

    summary = pd.DataFrame([{
        "n_control": n_control, "n_treatment": n_treatment,
        "conversion_rate_control_pct": round(p_control * 100, 2),
        "conversion_rate_treatment_pct": round(p_treatment * 100, 2),
        "absolute_uplift_pct_points": round(uplift_pct_points, 2),
        "ci_95_lower_pct_points": round(ci_lower * 100, 2),
        "ci_95_upper_pct_points": round(ci_upper * 100, 2),
        "z_statistic": round(z_stat, 3), "p_value": round(p_value, 4),
        "statistically_significant": is_statistically_significant,
        "business_significant": is_business_significant,
        "revenue_lift_in_experiment": round(revenue_lift, 2),
        "decision": decision
    }])
    summary.to_csv(f"{OUTPUT_DIR}/ab_test_summary.csv", index=False)
    print(f"\nSummary saved: {OUTPUT_DIR}/ab_test_summary.csv")


# ==================================================================
# SECTION 6 — RFM CUSTOMER SEGMENTATION
# ==================================================================
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


def run_rfm_segmentation(data):
    print("\n" + "=" * 70)
    print("SECTION 6: RFM CUSTOMER SEGMENTATION")
    print("=" * 70)

    completed = data["completed"]
    order_items = data["order_items"]

    items_full = order_items.merge(
        completed[["order_id", "customer_id", "order_date", "discount"]], on="order_id", how="inner"
    )
    items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

    print("Calculating RFM values...")
    rfm = items_full.groupby("customer_id").agg(
        last_purchase=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("net_value", "sum")
    ).reset_index()

    rfm["recency_days"] = (REFERENCE_DATE - rfm["last_purchase"]).dt.days
    print(f"Customers with purchase history: {len(rfm):,}")

    rfm["r_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_total_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    rfm["rfm_segment"] = rfm.apply(assign_segment, axis=1)

    rfm_out = rfm[["customer_id", "recency_days", "frequency", "monetary",
                   "r_score", "f_score", "m_score", "rfm_total_score", "rfm_segment"]]
    rfm_out.to_csv(f"{OUTPUT_DIR}/rfm_segments.csv", index=False)
    print(f"\nRFM table saved: {OUTPUT_DIR}/rfm_segments.csv")

    segment_summary = rfm_out.groupby("rfm_segment").agg(
        num_customers=("customer_id", "count"),
        avg_monetary=("monetary", "mean"),
        total_monetary=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean")
    ).round(2).sort_values("total_monetary", ascending=False)

    print("\n" + "=" * 70)
    print("SEGMENT SUMMARY")
    print("=" * 70)
    print(segment_summary)
    segment_summary.to_csv(f"{OUTPUT_DIR}/rfm_segment_summary.csv")

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

    plt.figure(figsize=(10, 6))
    segment_summary["num_customers"].sort_values().plot(kind="barh", color="darkcyan")
    plt.title("Customer Count by RFM Segment")
    plt.xlabel("Number of Customers")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/12_rfm_segment_sizes.png", dpi=100)
    plt.close()

    plt.figure(figsize=(10, 6))
    segment_summary["total_monetary"].sort_values().plot(kind="barh", color="darkorange")
    plt.title("Total Revenue Contribution by RFM Segment")
    plt.xlabel("Total Monetary Value")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/13_rfm_segment_value.png", dpi=100)
    plt.close()

    print(f"\nCharts saved: 12_rfm_segment_sizes.png, 13_rfm_segment_value.png")


# ==================================================================
# MAIN — RUN ALL 6 SECTIONS IN SEQUENCE
# ==================================================================
def main():
    data = load_all_data()
    run_eda(data)
    run_churn_prediction(data)
    run_demand_forecasting(data)
    run_anomaly_detection(data)
    run_ab_testing(data)
    run_rfm_segmentation(data)

    print("\n" + "=" * 70)
    print("ALL 6 ANALYSES COMPLETE")
    print(f"All CSVs and charts saved to: {OUTPUT_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
