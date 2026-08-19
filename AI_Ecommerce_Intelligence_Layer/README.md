# AI-Powered E-commerce Customer, Revenue & Growth Intelligence Platform
## Customized AI Intelligence Layer

This package is customized from the supplied project files.

### Your supplied analytics incorporated

SQL:
- ecommerce_phase2_views_fixed.sql
- 39 PostgreSQL analytical views across Sales, Customer Growth, Marketing,
  Funnel, Cohort Retention, RFM, Churn, Product/Basket and A/B Testing.

Python:
- combined_business_analysis (2).py
- EDA
- Random Forest churn prediction
- 90-day revenue forecasting
- rolling z-score anomaly detection
- checkout redesign A/B testing
- RFM segmentation

Python output CSVs are copied into `python_results/`.

## Architecture

PostgreSQL analytical views
        ↓
SQL result adapter
        ↓
Python/ML/A-B verified outputs
        ↓
Verified Analytics Context
        ↓
Gemini API
        ↓
Business answer
        ↓
Root cause / recommendation / growth action

## Setup

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. API key

Open `.env`:

```text
GEMINI_API_KEY=YOUR_KEY
```

Do NOT commit `.env` to GitHub.

### 3. PostgreSQL

Put your PostgreSQL connection string in:

```text
DB_URL=postgresql+psycopg2://USERNAME:PASSWORD@HOST:5432/DATABASE
```

Your exact Phase 2 SQL file is included here:

```text
sql/ecommerce_phase2_views_fixed.sql
```

Run the supplied SQL file in the same database where the project tables
(customers, products, orders, order_items, payments, returns,
marketing_campaigns, web_events, experiments) exist.

The AI adapter then queries the supplied analytical views.

### 4. Python results

Your supplied Python result CSVs are already in:

```text
python_results/
```

The adapter reads verified results from those files.

Your original Python source is preserved at:

```text
source/combined_business_analysis.py
```

If you change or rerun your Python analytics, replace the CSV outputs in
`python_results/`.

### 5. Test the pipeline without an API call

Keep:

```text
MOCK_MODE=true
```

Then:

```bash
python main.py
```

This tests the context-building layer.

### 6. Use the real GenAI API

Change:

```text
MOCK_MODE=false
GEMINI_API_KEY=YOUR_KEY
```

Then:

```bash
python main.py
```

Ask:

```text
Why should we prioritize retention?
```

```text
Should we ship the checkout redesign?
```

```text
What is the strongest growth opportunity?
```

```text
Which customer segments should receive retention investment?
```

## Important design choice

The LLM is NOT the calculation engine.

### Context routing
The AI layer routes each question to relevant evidence first. Critical ML and A/B testing sections are prioritized and section-aware compaction preserves valid JSON; the system never cuts a JSON string in the middle. The default context budget is 120,000 characters, but routing normally sends much less.

SQL/Python/ML/A-B testing produce the verified evidence.
The LLM explains that evidence and turns it into decision support.

This reduces hallucinated business numbers.

## Your actual project evidence

The supplied business report identifies:
- 15,000 customers
- 34,254 completed orders
- $713.9M net revenue
- 51.4% churn among customers with purchase history
- Random Forest ROC-AUC 0.70
- 407 high-value/high-risk customers
- checkout redesign +2.28 percentage-point uplift
- p=0.0024
- observed experiment revenue lift $308,259.38
- Champions + Loyal Customers = 4,521 customers and 67.4% of revenue
- 90-day forecast is explicitly caveated because the linear model under-predicts
  the accelerating growth curve.

The AI should use these only when they are present in the assembled context.

## Next layer: UI

Do not build HTML first.

First verify:

```text
SQL → Python/ML/A-B outputs → Verified Context → Gemini
```

After this works, connect your existing `ai_analyst_demo.html` or a Streamlit
front end to `main.py`.
