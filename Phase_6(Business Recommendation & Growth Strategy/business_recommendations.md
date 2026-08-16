# Business Recommendations — AI-Powered E-commerce Intelligence Platform

**Prepared from:** SQL analytics (Phase 2) + Python ML/statistics (Phase 3) +
Power BI dashboards (Phase 4) + AI Analyst layer (Phase 5)

**Period covered:** January 2023 – December 2025 (3 years)

---

## The Story

> A growing e-commerce company suspected several problems — unclear marketing
> ROI, customers not returning, some products underperforming, and no
> systematic way to know what action to take next. This project analyzed
> customer, product, and marketing data end-to-end, quantified the size of
> each problem, tested one proposed fix, and built a system that turns
> ongoing data into decisions rather than just charts.

---

## 1. Headline Numbers (What Happened)

| Metric | Value |
|---|---|
| Total net revenue (3 years) | ₹71.4 crore |
| Total completed orders | 34,254 |
| Average Order Value | ₹20,841 |
| Total customers | 15,000 |
| Repeat purchase rate | 69.1% (among purchasers) |
| Overall gross margin | 16.0% |
| Overall funnel conversion (page view → purchase) | 6.98% |

**Latest month (Dec 2025) vs previous month:** revenue up 48.98%, orders up
46.52%, CAC down 20.26% — a genuinely good month. This is the kind of
month-over-month comparison the [[AI Analyst]] layer (Phase 5) can generate
for *any* month, on demand, in natural language.

---

## 2. Diagnostic Findings (Why) — the 5 problems, quantified

### 2.1 Marketing spend is inefficient — paid channels cost 15–45x more per customer than they're worth relative to organic

| Channel | CAC | Avg CLV | CLV:CAC Ratio |
|---|---|---|---|
| Organic Search | ₹139 | ₹71,329 | **514:1** |
| Referral | ₹180 | ₹65,847 | **367:1** |
| Direct | ₹250 | ₹68,780 | **275:1** |
| Meta Ads | ₹2,818 | ₹66,680 | 24:1 |
| Google Ads | ₹3,160 | ₹69,021 | 22:1 |
| YouTube Ads | ₹3,883 | ₹71,386 | 18:1 |
| Affiliate | ₹4,626 | ₹65,785 | 14:1 |
| Email | ₹5,614 | ₹66,154 | 12:1 |

**Key insight:** customers acquired via paid channels are **not** worth more
over their lifetime than customers acquired organically — CLV is roughly flat
(₹65k–₹71k) across every channel. The entire difference in ROI comes from
acquisition cost, not customer quality. This directly answers the question
posed in the original project brief: *"Highest ROAS channel ka highest CLV
bhi hai?"* — **No.** Paid channels are not buying better customers, just
more expensive ones.

**Recommendation:** Shift incremental budget toward Organic Search/SEO and
Referral program investment before scaling any paid channel further. If
paid spend must continue (e.g. for volume/reach goals the organic channels
can't hit alone), Email (12:1) and Affiliate (14:1) are the weakest paid
performers and are the first candidates to cut or renegotiate.

---

### 2.2 Customer value is extremely concentrated — 13% of customers drive ~34% of revenue

| RFM Segment | Customers | % of Base | Total Revenue | Avg Recency (days) |
|---|---|---|---|---|
| Champions | 1,972 | 13.1% | ₹29.30 crore | 21.6 |
| Loyal Customers | 2,549 | 17.0% | ₹18.85 crore | 63.9 |
| Cannot Lose Them | 646 | 4.3% | ₹7.40 crore | 252.4 |
| At Risk | 1,094 | 7.3% | ₹5.24 crore | 310.5 |
| Lost | 1,913 | 12.8% | ₹3.16 crore | 393.7 |
| Hibernating | 1,025 | 6.8% | ₹3.62 crore | 233.5 |
| New Customers | 1,055 | 7.0% | ₹2.84 crore | 25.1 |
| Potential Loyalists | 182 | 1.2% | ₹0.97 crore | 98.7 |

**Key insight:** "Cannot Lose Them" (646 customers) carries ₹7.4 crore in
historical value but hasn't purchased in an average of 252 days — this is
the single highest-leverage retention opportunity in the dataset. Losing
even a fraction of this segment has outsized revenue impact compared to
acquiring new customers.

**Recommendation:** Build a dedicated high-touch win-back flow (not a
generic email blast) for the "Cannot Lose Them" segment specifically —
personal outreach, high-value personalized offers. Treat "At Risk"
(₹5.24 crore, also going cold) as the second priority tier.

---

### 2.3 51.4% of purchasers are predicted at churn risk, concentrated in a specific behavioral pattern

The churn model (Random Forest, Phase 3) found:
- **3,501 customers** classified High Risk (churn probability > 60%)
- Model performance: ROC-AUC 0.698, PR-AUC 0.675 (evaluated on
  precision/recall, not just accuracy, because churn is imbalanced ~51%/49%)
- Top predictive features: purchase frequency, total spend, and cart
  abandonment count — customers who add to cart repeatedly without
  converting are a distinct at-risk signature, separate from simply "haven't
  bought in a while"

**Recommendation:** The `retention_priority_list.csv` output (high-value +
high-risk customers) should be handed directly to the retention/CRM team as
an actionable weekly list, not just a report.

---

### 2.4 Return rate is fairly uniform across categories (~7%) — no single category is a standout problem, but Fashion is the highest

| Category | Return Rate % | Revenue |
|---|---|---|
| Fashion | 7.24% | ₹9.88 crore |
| Sports | 7.08% | ₹10.07 crore |
| Books | 7.07% | ₹9.53 crore |
| Grocery | 7.07% | ₹10.49 crore |
| Electronics | 7.00% | ₹10.92 crore |
| Home | 6.98% | ₹10.15 crore |
| Beauty | 6.75% | ₹10.36 crore |

**Key insight:** Unlike a typical retail assumption ("Electronics/Fashion
must have the worst returns"), this data shows return rate is **not**
strongly category-dependent — it's closer to a uniform ~7% baseline across
the board. This itself is a useful finding: it suggests the return problem
(if the business considers 7% high) is systemic — likely a checkout/product-
description/sizing-info issue — rather than a specific-category defect
problem.

**Recommendation:** Don't over-invest in category-specific return fixes.
Investigate cross-category causes instead: product photography/description
accuracy, sizing charts (Fashion is highest, consistent with a sizing-
related hypothesis), and delivery packaging.

---

### 2.5 The proposed checkout redesign works — and the business should ship it

**A/B Test Results (Phase 3):**

| Metric | Control | Treatment |
|---|---|---|
| Sample size | 3,981 | 4,019 |
| Conversion rate | 11.73% | 14.01% |
| Absolute uplift | +2.28 percentage points | |
| 95% Confidence Interval | [0.81, 3.74] pts — entirely positive | |
| P-value | 0.0024 (statistically significant, p < 0.05) | |
| Revenue lift in experiment | ₹3,08,259 | |

**Statistical vs business significance — evaluated separately:**
- Statistically significant: **Yes** (p < 0.05, confidence interval doesn't cross zero)
- Business significant: **Yes** (uplift exceeds the 1-percentage-point
  threshold set as the minimum to justify engineering/rollout cost)

**Decision: SHIP** ✅

This is a case where both statistical rigor and business judgment agree —
worth noting in interviews that the project treated these as two genuinely
separate checks, not one.

---

## 3. Predictive Layer (What May Happen)

**Revenue Forecast (Phase 3, linear trend + seasonality model):**
- Next 30 days: ₹4.66 crore
- Next 60 days: ₹9.56 crore
- Next 90 days: ₹14.64 crore
- Backtest MAPE: 49.5% — **documented as a real limitation**, not hidden.
  This dataset's daily revenue doesn't have strong learnable seasonality
  (by construction, since it's synthetic), so the honest takeaway is:
  *use this as a directional trend indicator, not a committed forecast* —
  and in a real deployment, this would be the trigger to try an ensemble of
  models (Prophet, ARIMA, gradient boosting) rather than trust one linear
  model at this error rate.

**Anomaly Detection (Phase 3, rolling z-score method):**
- 28 revenue anomaly days, 24 order-volume anomaly days, 14 marketing-spend
  anomaly days, 28 refund anomaly days flagged over the 3-year period
- The detection includes a root-cause hint layer: e.g., the largest revenue
  drop (27 Nov 2024) was cross-checked against same-day order volume to
  distinguish "fewer customers" vs. "smaller average orders" as the likely
  cause — a structured investigation path, not just a flag.

---

## 4. Decision Intelligence Layer (What Should We Do)

Phase 5 (AI Analyst) turns all of the above into an on-demand system: any
manager can ask a question in plain language ("Why did revenue change last
month?", "Which customers are at risk of churning?") and receive an answer
built **only** from validated, pre-calculated metrics — never from an LLM
guessing at numbers. This is the layer that makes the other four phases
usable day-to-day, instead of requiring a fresh SQL query or dashboard build
for every new question a stakeholder has.

---

## 5. Consolidated Action List (priority order)

| # | Action | Backed by | Expected Impact |
|---|---|---|---|
| 1 | Ship the checkout redesign to 100% of traffic | A/B test, Phase 3 | +2.28pp conversion, statistically confirmed |
| 2 | Reallocate marketing budget toward Organic/Referral, away from Email/Affiliate | CAC:CLV analysis, Phase 2 | Same CLV at 12–45x lower CAC |
| 3 | Launch high-touch win-back for "Cannot Lose Them" segment (646 customers) | RFM segmentation, Phase 2/3 | ₹7.4 crore in at-risk historical value |
| 4 | Deploy retention_priority_list.csv to CRM/retention team | Churn model, Phase 3 | Targets the 3,501 highest-probability churners |
| 5 | Investigate checkout/product-description accuracy as a cross-category return driver | Return rate analysis, Phase 2 | ~7% baseline return rate across all categories |
| 6 | Adopt the AI Analyst layer for ad-hoc management questions | Phase 5 | Reduces dependency on analyst availability for routine questions |

---

## 6. Honest Limitations (say this in interviews — it builds credibility, not doubt)

- This is a **synthetic dataset** generated for portfolio purposes — real
  business data would likely show stronger, more learnable seasonality and
  less uniform return rates across categories. The methodology transfers
  directly; the specific numbers are illustrative.
- The churn definition (90-day no-purchase rule) is a **documented business
  assumption**, not a universal fact — see `sql/09_churn_definition.sql`
  for the query that validates this threshold against the actual median
  repurchase interval.
- The revenue forecast has a 49.5% backtest MAPE — explicitly not
  presented as a precise prediction.
- Channel attribution (CAC/CLV by channel) uses a simple first-touch
  (acquisition_channel) model — a production system would likely use
  multi-touch attribution, which could shift these numbers.

---

## Where each number in this document comes from

| Section | Source file |
|---|---|
| Headline numbers | `sql/03_sales_analytics.sql`, `sql/04_customer_analytics.sql` |
| CAC/CLV by channel | `sql/08_cac_clv_marketing.sql` (query F3) |
| RFM segments | `python_phase3/06_rfm_segmentation.py` → `rfm_segment_summary.csv` |
| Churn model | `python_phase3/02_churn_prediction.py` → `customer_churn_risk_scores.csv` |
| Return rate by category | `sql/10_product_analytics.sql` (query H1) |
| A/B test | `python_phase3/05_ab_testing.py` → `ab_test_summary.csv` |
| Forecast | `python_phase3/03_demand_forecasting.py` → `revenue_forecast_90days.csv` |
| Anomalies | `python_phase3/04_anomaly_detection.py` |
| Latest month snapshot | `ai_analyst/01_metrics_engine.py` |

Every number in this document can be regenerated by re-running the
corresponding script against `data/processed/`.
