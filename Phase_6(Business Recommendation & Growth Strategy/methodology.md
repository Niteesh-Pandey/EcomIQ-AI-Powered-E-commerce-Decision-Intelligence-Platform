# Methodology

This document explains the key analytical choices made across the project —
useful for interview prep, since every non-obvious decision here has a
"why" behind it.

## 1. Churn Definition

**Rule:** A customer is churned if no completed order in the last 90 days,
AND they have purchased at least once before.

**Why 90 days, not some other number:** This is a business assumption, not
a derived constant. `sql/09_churn_definition.sql` (query G1) calculates the
actual median repurchase interval from the data — in a real deployment, the
threshold should be set relative to that median (e.g. 2-3x the median gap),
not picked arbitrarily. This project documents the assumption explicitly
rather than presenting 90 days as a fact.

**Why exclude never-purchased customers from the churn label:** Someone who
signed up but never bought anything hasn't "stopped" doing anything — they
never started. Labeling them churned would conflate acquisition failure
with retention failure, which need different fixes.

## 2. Churn Model — avoiding data leakage

The churn label is defined using `days_since_last_purchase > 90`. That
column is deliberately **excluded** from the model's feature set — including
it would let the model "cheat" by learning the threshold instead of learning
actual behavioral patterns. The model instead uses `purchase_frequency`,
`total_spend`, `avg_order_value`, `number_of_sessions`, `cart_abandonment`,
`returns`, and `discount_usage` — genuine behavioral signals available
before the churn outcome is known.

## 3. Why PR-AUC alongside ROC-AUC for churn evaluation

The churn base rate in this dataset is close to 50/50, which is unusually
balanced for a real churn problem (real-world churn is often 5-20%). Even
so, the project reports PR-AUC and the full precision/recall/F1 breakdown,
not just accuracy — accuracy alone is a poor metric for any classification
task where getting the minority class right matters more than overall
correctness, and it's good practice to default to precision/recall/PR-AUC
reporting regardless of how balanced a particular dataset happens to be.

## 4. RFM Scoring Method

Recency, Frequency, and Monetary values are each split into 5 quantile-based
bins (`NTILE(5)` in SQL, `pd.qcut()` in Python) rather than fixed thresholds
(e.g. "recency < 30 days = score 5"). Quantile-based scoring adapts to the
actual distribution of the customer base, so the definition of "top 20%
recency" is always relative to this specific business, not a number
imported from a different company's context.

## 5. Statistical vs Business Significance (A/B test)

These are checked **separately** and can disagree:
- Statistical significance asks: "is this result likely to be real, not
  random noise?" (the p-value / confidence interval question)
- Business significance asks: "even if real, is the effect size large
  enough to be worth the cost of shipping?" (a judgment call, made explicit
  via the `MIN_BUSINESS_UPLIFT_PCT` threshold in the script)

A result can be statistically significant but business-insignificant (a
real but tiny effect not worth the engineering cost), or the reverse
(a promising-looking effect that isn't yet distinguishable from chance).
This project's checkout test happened to pass both checks — but the code
is structured to handle and report the case where they disagree.

## 6. Forecasting — why linear regression instead of ARIMA/Prophet

The forecasting model (Phase 3) uses linear trend + day-of-week/month
seasonality via `LinearRegression` on engineered date features, rather than
`statsmodels`/`Prophet`. This was partly a dependency-availability decision
in this environment, but it's also a legitimate methodology choice to
document: it's fully transparent (every coefficient is inspectable), has no
hidden hyperparameters to tune, and is easy to explain end-to-end in an
interview. The tradeoff, stated explicitly in the script's own output, is
that it can't capture non-linear regime changes the way ARIMA/Prophet can.
The 49.5% backtest MAPE is reported honestly rather than masked.

## 7. Anomaly Detection Method

Rolling 30-day z-score (`|z| > 2.5` threshold) was chosen over more complex
methods (isolation forests, seasonal-hybrid ESD) because it's fully
interpretable — "this day's revenue is 2.7 standard deviations below its
trailing 30-day average" is something a business stakeholder can understand
without a machine-learning background, which matters for a tool meant to
flag things for human investigation, not replace human judgment.

## 8. Marketing Attribution Model

CAC and channel-level revenue attribution use **first-touch attribution**
(a customer's `acquisition_channel` field, set at signup). This is the
simplest attribution model and was chosen for transparency and to keep the
SQL/DAX logic tractable for a portfolio project. A production system serving
a real marketing team would likely need multi-touch attribution (crediting
multiple touchpoints across the customer journey), which is a natural
extension noted but not implemented here.

## 9. Data Cleaning — general philosophy

Every cleaning decision in `python/01_data_cleaning_simple.py` follows one
rule: **document the business rule, don't silently guess.** For example,
missing product cost is imputed with the category median cost, but the row
is also flagged `cost_is_estimated = True` so downstream margin analysis can
choose to exclude or discount those rows rather than treating imputed data
as equally reliable as real data. See `documentation/data_dictionary.md`
for the complete list of cleaning rules applied.
