"""
==================================================================
PHASE 3 — STEP 5: A/B TESTING — STATISTICAL SIGNIFICANCE
==================================================================
Checkout redesign experiment: control vs treatment.

SQL (Phase 2) gave us the raw conversion numbers. This script adds
the actual statistical test: two-proportion z-test, confidence
interval on the uplift, and a clear SHIP / DO NOT SHIP / CONTINUE
TEST decision — with statistical significance and business
significance discussed SEPARATELY (a common real-world distinction:
a result can be statistically significant but too small to matter
business-wise, or vice versa with a promising-but-noisy result).

Run:
    python 05_ab_testing.py
==================================================================
"""

import pandas as pd
import numpy as np
from scipy import stats

import os
PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALPHA = 0.05  # significance level (95% confidence)
MIN_BUSINESS_UPLIFT_PCT = 1.0  # minimum uplift (percentage points) to matter for the business

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("Loading experiment data...")
experiments = pd.read_csv(f"{PROCESSED_DIR}/experiments.csv")

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

# ------------------------------------------------------------------
# TWO-PROPORTION Z-TEST
# ------------------------------------------------------------------
print("\n" + "="*60)
print("STATISTICAL SIGNIFICANCE TEST (two-proportion z-test)")
print("="*60)

# pooled proportion under null hypothesis (no difference)
p_pooled = (conv_control + conv_treatment) / (n_control + n_treatment)
se_pooled = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_control + 1/n_treatment))

z_stat = (p_treatment - p_control) / se_pooled
p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))  # two-tailed test

print(f"Pooled conversion rate:     {p_pooled*100:.2f}%")
print(f"Z-statistic:                {z_stat:.3f}")
print(f"P-value:                    {p_value:.4f}")
print(f"Significance threshold:     alpha = {ALPHA}")

is_statistically_significant = p_value < ALPHA
print(f"Statistically significant?  {'YES' if is_statistically_significant else 'NO'}")

# ------------------------------------------------------------------
# CONFIDENCE INTERVAL ON THE UPLIFT (unpooled SE, standard for CI)
# ------------------------------------------------------------------
se_unpooled = np.sqrt(
    p_control * (1 - p_control) / n_control +
    p_treatment * (1 - p_treatment) / n_treatment
)
uplift = p_treatment - p_control
z_critical = stats.norm.ppf(1 - ALPHA/2)
ci_lower = uplift - z_critical * se_unpooled
ci_upper = uplift + z_critical * se_unpooled

print(f"\nAbsolute uplift:            {uplift*100:.2f} percentage points")
print(f"95% Confidence Interval:    [{ci_lower*100:.2f}, {ci_upper*100:.2f}] percentage points")

if ci_lower > 0:
    print("-> The entire confidence interval is positive: we can be confident")
    print("   the true effect is an improvement, not just noise.")
elif ci_upper < 0:
    print("-> The entire confidence interval is negative: treatment likely hurts conversion.")
else:
    print("-> The confidence interval crosses zero: we cannot rule out 'no real effect'.")

# ------------------------------------------------------------------
# BUSINESS SIGNIFICANCE (separate from statistical significance!)
# ------------------------------------------------------------------
print("\n" + "="*60)
print("BUSINESS SIGNIFICANCE (separate consideration from statistics)")
print("="*60)

uplift_pct_points = uplift * 100
is_business_significant = uplift_pct_points >= MIN_BUSINESS_UPLIFT_PCT

print(f"Observed uplift:            {uplift_pct_points:.2f} percentage points")
print(f"Business significance bar:  >= {MIN_BUSINESS_UPLIFT_PCT} percentage points")
print(f"                             (this threshold is a business assumption --")
print(f"                              set by estimated cost of shipping vs expected gain,")
print(f"                              not a statistical rule)")
print(f"Business significant?       {'YES' if is_business_significant else 'NO'}")

# ------------------------------------------------------------------
# ESTIMATED REVENUE IMPACT
# ------------------------------------------------------------------
avg_rev_per_conversion_treatment = treatment.loc[treatment["converted"] == 1, "revenue"].mean()
avg_rev_per_conversion_control = control.loc[control["converted"] == 1, "revenue"].mean()

print(f"\nAvg revenue per conversion (control):   {avg_rev_per_conversion_control:,.2f}")
print(f"Avg revenue per conversion (treatment):  {avg_rev_per_conversion_treatment:,.2f}")

total_revenue_control = control["revenue"].sum()
total_revenue_treatment = treatment["revenue"].sum()
revenue_lift = total_revenue_treatment - total_revenue_control

print(f"Total revenue (control):    {total_revenue_control:,.2f}")
print(f"Total revenue (treatment):  {total_revenue_treatment:,.2f}")
print(f"Revenue lift in experiment: {revenue_lift:,.2f}")

# ------------------------------------------------------------------
# FINAL DECISION
# ------------------------------------------------------------------
print("\n" + "="*60)
print("FINAL DECISION")
print("="*60)

if is_statistically_significant and is_business_significant and ci_lower > 0:
    decision = "SHIP"
    reason = ("Result is both statistically significant (p < 0.05, CI entirely "
              "positive) AND business-significant (uplift exceeds the minimum "
              "threshold that justifies the engineering/rollout cost).")
elif is_statistically_significant and not is_business_significant:
    decision = "DO NOT SHIP (as-is)"
    reason = ("Statistically real, but the uplift is too small to be worth the "
              "cost of shipping. Consider whether the change can be simplified/"
              "cheapened to still be worth it, or look for a bigger intervention.")
elif not is_statistically_significant and uplift_pct_points > 0:
    decision = "CONTINUE TEST"
    reason = ("Direction looks promising but we can't yet rule out random chance. "
              "Recommend collecting more samples before deciding.")
else:
    decision = "DO NOT SHIP"
    reason = "No credible positive effect detected."

print(f"Decision: {decision}")
print(f"Reason:   {reason}")

# ------------------------------------------------------------------
# SAVE SUMMARY
# ------------------------------------------------------------------
summary = pd.DataFrame([{
    "n_control": n_control,
    "n_treatment": n_treatment,
    "conversion_rate_control_pct": round(p_control*100, 2),
    "conversion_rate_treatment_pct": round(p_treatment*100, 2),
    "absolute_uplift_pct_points": round(uplift_pct_points, 2),
    "ci_95_lower_pct_points": round(ci_lower*100, 2),
    "ci_95_upper_pct_points": round(ci_upper*100, 2),
    "z_statistic": round(z_stat, 3),
    "p_value": round(p_value, 4),
    "statistically_significant": is_statistically_significant,
    "business_significant": is_business_significant,
    "revenue_lift_in_experiment": round(revenue_lift, 2),
    "decision": decision
}])
summary.to_csv(f"{OUTPUT_DIR}/ab_test_summary.csv", index=False)
print(f"\nSummary saved: {OUTPUT_DIR}/ab_test_summary.csv")
