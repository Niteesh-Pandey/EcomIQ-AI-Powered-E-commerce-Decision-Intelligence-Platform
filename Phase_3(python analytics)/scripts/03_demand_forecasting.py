"""
==================================================================
PHASE 3 — STEP 3: DEMAND / REVENUE FORECASTING
==================================================================
Forecasts daily revenue for the next 30/60/90 days.

Approach: uses a simple, transparent linear-trend + day-of-week
seasonality model (via scikit-learn LinearRegression on engineered
date features). This avoids heavier dependencies (e.g. statsmodels /
Prophet) while still producing a genuine trend+seasonality forecast
you can explain end-to-end in an interview.

IMPORTANT: this is a directional forecast for portfolio purposes,
not a production-grade forecasting system. Real deployments should
compare multiple models (ARIMA/Prophet/ML) and validate on rolling
backtests. Uncertainty bands here are approximate (based on
residual std dev), not a formal prediction interval.

Run:
    python 03_demand_forecasting.py
==================================================================
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

import os
PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# LOAD + PREPARE DAILY REVENUE SERIES
# ------------------------------------------------------------------
print("Loading data...")
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")

completed = orders[orders["order_status"] == "Completed"].copy()
items_full = order_items.merge(completed[["order_id", "order_date", "discount"]], on="order_id", how="inner")
items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))
items_full["order_day"] = items_full["order_date"].dt.date

daily_revenue = items_full.groupby("order_day")["net_value"].sum().reset_index()
daily_revenue["order_day"] = pd.to_datetime(daily_revenue["order_day"])
daily_revenue = daily_revenue.sort_values("order_day").reset_index(drop=True)

# fill missing calendar days with 0 revenue (days with no completed orders)
full_range = pd.date_range(daily_revenue["order_day"].min(), daily_revenue["order_day"].max(), freq="D")
daily_revenue = daily_revenue.set_index("order_day").reindex(full_range, fill_value=0).rename_axis("order_day").reset_index()

print(f"Daily revenue series: {len(daily_revenue)} days, "
      f"{daily_revenue['order_day'].min().date()} to {daily_revenue['order_day'].max().date()}")

# ------------------------------------------------------------------
# FEATURE ENGINEERING: trend (day index) + day-of-week seasonality
# ------------------------------------------------------------------
daily_revenue["day_index"] = np.arange(len(daily_revenue))
daily_revenue["day_of_week"] = daily_revenue["order_day"].dt.dayofweek
daily_revenue["month"] = daily_revenue["order_day"].dt.month

dow_dummies = pd.get_dummies(daily_revenue["day_of_week"], prefix="dow", drop_first=True)
month_dummies = pd.get_dummies(daily_revenue["month"], prefix="month", drop_first=True)

X = pd.concat([daily_revenue[["day_index"]], dow_dummies, month_dummies], axis=1)
y = daily_revenue["net_value"]

# ------------------------------------------------------------------
# TRAIN/TEST SPLIT (last 60 days held out to validate forecast accuracy)
# ------------------------------------------------------------------
HOLDOUT_DAYS = 60
X_train, X_test = X.iloc[:-HOLDOUT_DAYS], X.iloc[-HOLDOUT_DAYS:]
y_train, y_test = y.iloc[:-HOLDOUT_DAYS], y.iloc[-HOLDOUT_DAYS:]

model = LinearRegression()
model.fit(X_train, y_train)

y_pred_test = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred_test)
mape = mean_absolute_percentage_error(y_test.replace(0, np.nan).dropna(),
                                       pd.Series(y_pred_test, index=y_test.index).loc[y_test.replace(0, np.nan).dropna().index])

print(f"\nBacktest on last {HOLDOUT_DAYS} days:")
print(f"  MAE:  {mae:,.2f}")
print(f"  MAPE: {mape*100:.1f}%")
print("  (MAPE excludes zero-revenue days, which would cause divide-by-zero)")

# residual std dev -> approximate uncertainty band
residuals = y_test.values - y_pred_test
resid_std = residuals.std()
print(f"  Residual std dev (used for uncertainty band): {resid_std:,.2f}")

# ------------------------------------------------------------------
# REFIT ON FULL DATA, FORECAST NEXT 90 DAYS
# ------------------------------------------------------------------
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
# align columns with training data (some months/days may not appear in future window)
X_future = X_future.reindex(columns=X.columns, fill_value=0)

future["forecast_revenue"] = model_full.predict(X_future)
future["forecast_revenue"] = future["forecast_revenue"].clip(lower=0)  # revenue can't be negative
future["lower_bound"] = (future["forecast_revenue"] - 1.96 * resid_std).clip(lower=0)
future["upper_bound"] = future["forecast_revenue"] + 1.96 * resid_std

future_out = future[["order_day", "forecast_revenue", "lower_bound", "upper_bound"]]
future_out.to_csv(f"{OUTPUT_DIR}/revenue_forecast_90days.csv", index=False)

print(f"\nForecast summary:")
print(f"  Next 30 days total: {future_out.head(30)['forecast_revenue'].sum():,.2f}")
print(f"  Next 60 days total: {future_out.head(60)['forecast_revenue'].sum():,.2f}")
print(f"  Next 90 days total: {future_out['forecast_revenue'].sum():,.2f}")

# ------------------------------------------------------------------
# CHART: history + forecast with uncertainty band
# ------------------------------------------------------------------
plt.figure(figsize=(14, 6))
# show last 180 days of history for context
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

print("\n" + "="*60)
print("LIMITATIONS (document these — do not oversell the forecast):")
print("="*60)
print("- Linear trend assumption: won't capture sudden regime changes")
print("  (e.g. a new product launch, a major promotion, a market shock).")
print("- Day-of-week + month seasonality only — no holiday-specific effects.")
print(f"- Backtest MAPE was {mape*100:.1f}% on last {HOLDOUT_DAYS} days — use this")
print("  as the expected error range, not the point forecast, when reporting.")
print("- Longer horizons (60-90 days) are less reliable than 30 days.")
