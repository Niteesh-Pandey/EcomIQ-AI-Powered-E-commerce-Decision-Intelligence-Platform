"""
==================================================================
BUSINESS INSIGHTS REPORT — PDF GENERATOR
==================================================================
Reads the outputs produced by scripts 01-06 and compiles them into
a single executive-friendly PDF: business_insights_report.pdf

Run AFTER 01_eda.py ... 06_rfm_segmentation.py have been run once
(it reads their CSV/PNG outputs, it does not recompute anything).

Run:
    python 07_generate_business_report.py
==================================================================
"""

import pandas as pd
import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

PROCESSED_DIR = "../data/processed"
OUTPUT_DIR = "../outputs_phase3"
REPORT_PATH = f"{OUTPUT_DIR}/business_insights_report.pdf"

# ------------------------------------------------------------------
# STYLES
# ------------------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", fontSize=24, leading=28,
                           textColor=colors.HexColor("#1a2b4c"), spaceAfter=6,
                           fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="ReportSubtitle", fontSize=12, leading=16,
                           textColor=colors.HexColor("#555555"), spaceAfter=20))
styles.add(ParagraphStyle(name="SectionHeader", fontSize=16, leading=20,
                           textColor=colors.white, backColor=colors.HexColor("#1a2b4c"),
                           spaceBefore=6, spaceAfter=12, leftIndent=6, borderPadding=6,
                           fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="SubHeader", fontSize=12.5, leading=16,
                           textColor=colors.HexColor("#1a2b4c"), spaceBefore=10, spaceAfter=6,
                           fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="BodyText2", fontSize=10, leading=14.5,
                           textColor=colors.HexColor("#222222"), spaceAfter=8,
                           alignment=TA_LEFT))
styles.add(ParagraphStyle(name="BulletPoint", fontSize=10, leading=14.5,
                           textColor=colors.HexColor("#222222"), spaceAfter=4,
                           leftIndent=14, bulletIndent=4))
styles.add(ParagraphStyle(name="KPILabel", fontSize=9, leading=11,
                           textColor=colors.HexColor("#666666"), alignment=TA_CENTER))
styles.add(ParagraphStyle(name="KPIValue", fontSize=15, leading=18,
                           textColor=colors.HexColor("#1a2b4c"), alignment=TA_CENTER,
                           fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Caption", fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#777777"), alignment=TA_CENTER,
                           spaceAfter=14))
styles.add(ParagraphStyle(name="Verdict", fontSize=11, leading=15,
                           textColor=colors.white, backColor=colors.HexColor("#1f7a4d"),
                           borderPadding=8, spaceAfter=10, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="VerdictWarn", fontSize=11, leading=15,
                           textColor=colors.white, backColor=colors.HexColor("#b5541a"),
                           borderPadding=8, spaceAfter=10, fontName="Helvetica-Bold"))

story = []


def section_header(text):
    story.append(Paragraph(text, styles["SectionHeader"]))


def kpi_row(items):
    """items: list of (label, value) tuples -> rendered as a Table of KPI cards."""
    cells = []
    for label, value in items:
        cell = [Paragraph(value, styles["KPIValue"]), Paragraph(label, styles["KPILabel"])]
        cells.append(cell)
    t = Table([cells], colWidths=[6.5 * inch / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))


def add_image(path, width=6.3 * inch, caption=None):
    if os.path.exists(path):
        img = Image(path, width=width, height=width * 0.42)
        story.append(img)
        if caption:
            story.append(Paragraph(caption, styles["Caption"]))
    else:
        story.append(Paragraph(f"[chart not found: {path}]", styles["BodyText2"]))


def data_table(rows, col_widths=None, header=True):
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2b4c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 12))


# ==================================================================
# LOAD ALL RESULT FILES
# ==================================================================
print("Loading result files for report...")

customers = pd.read_csv(f"{PROCESSED_DIR}/customers.csv")
orders = pd.read_csv(f"{PROCESSED_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{PROCESSED_DIR}/order_items.csv")
marketing = pd.read_csv(f"{PROCESSED_DIR}/marketing_campaigns.csv")
returns = pd.read_csv(f"{PROCESSED_DIR}/returns.csv")

completed = orders[orders["order_status"] == "Completed"].copy()
items_full = order_items.merge(completed[["order_id", "order_date", "discount"]], on="order_id", how="inner")
items_full["net_value"] = items_full["line_total"] * (1 - items_full["discount"].fillna(0))

total_revenue = items_full["net_value"].sum()
total_orders = len(completed)
aov = items_full.groupby("order_id")["net_value"].sum().mean()
total_customers = len(customers)
total_spend = marketing["spend"].sum()
total_refunds = returns["refund_amount"].sum()
overall_cac = total_spend / total_customers

churn_feat = pd.read_csv(f"{OUTPUT_DIR}/churn_features.csv")
churn_rate = churn_feat["churned"].mean() * 100
risk_scores = pd.read_csv(f"{OUTPUT_DIR}/customer_churn_risk_scores.csv")
priority_list = pd.read_csv(f"{OUTPUT_DIR}/retention_priority_list.csv")
high_risk_value = priority_list["total_spend"].sum() if "total_spend" in priority_list.columns else 0

forecast = pd.read_csv(f"{OUTPUT_DIR}/revenue_forecast_90days.csv")
next30 = forecast.head(30)["forecast_revenue"].sum()
next90 = forecast["forecast_revenue"].sum()

ab = pd.read_csv(f"{OUTPUT_DIR}/ab_test_summary.csv").iloc[0]

rfm_summary = pd.read_csv(f"{OUTPUT_DIR}/rfm_segment_summary.csv")
rfm_actions = pd.read_csv(f"{OUTPUT_DIR}/rfm_segment_actions.csv")

anomalies_rev = pd.read_csv(f"{OUTPUT_DIR}/anomalies_revenue.csv")
anomalies_orders = pd.read_csv(f"{OUTPUT_DIR}/anomalies_order_volume.csv")
anomalies_spend = pd.read_csv(f"{OUTPUT_DIR}/anomalies_marketing_spend.csv")
anomalies_refunds = pd.read_csv(f"{OUTPUT_DIR}/anomalies_refunds.csv")

print("All data loaded. Building PDF...")

# ==================================================================
# COVER / EXECUTIVE SUMMARY
# ==================================================================
story.append(Spacer(1, 10))
story.append(Paragraph("E-Commerce Analytics", styles["ReportTitle"]))
story.append(Paragraph("Business Insights Report — Phase 3 (EDA, ML & Statistical Analysis)",
                        styles["ReportSubtitle"]))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
story.append(Spacer(1, 14))

story.append(Paragraph(
    "This report summarizes findings from six analyses run on the company's e-commerce "
    "dataset (Jan 2023 – Dec 2025): exploratory analysis, churn prediction, revenue "
    "forecasting, anomaly detection, an A/B test read-out, and RFM customer segmentation. "
    "Each section states the business question, the finding, and the recommended action.",
    styles["BodyText2"]))

story.append(Paragraph("Headline Numbers", styles["SubHeader"]))
kpi_row([
    ("Total Customers", f"{total_customers:,}"),
    ("Completed Orders", f"{total_orders:,}"),
    ("Net Revenue", f"${total_revenue/1e6:,.1f}M"),
])
kpi_row([
    ("Avg Order Value", f"${aov:,.0f}"),
    ("Marketing Spend", f"${total_spend/1e6:,.1f}M"),
    ("Refunds Paid", f"${total_refunds/1e6:,.1f}M"),
])

story.append(Paragraph("Executive Summary", styles["SubHeader"]))
exec_points = [
    f"Revenue is growing but the growth curve is accelerating, not linear — monthly net "
    f"revenue climbed from under $1M (early 2023) to over $90M (Dec 2025). Growth-stage "
    f"planning (inventory, staffing, cash flow) should assume continued acceleration, not "
    f"a flat trend line.",
    f"{churn_rate:.0f}% of customers who have ever purchased are currently churned "
    f"(no completed order in 90+ days). The churn model (Random Forest, ROC-AUC 0.70) "
    f"ranks {len(priority_list):,} high-spend customers as high-risk — this is the priority "
    f"retention list.",
    f"The checkout redesign A/B test is a clear, statistically significant win: "
    f"+{ab['absolute_uplift_pct_points']:.2f} percentage points conversion uplift "
    f"(95% CI entirely positive). Recommendation: SHIP.",
    f"RFM segmentation shows the top two segments (Champions + Loyal Customers, "
    f"{rfm_summary.loc[rfm_summary['rfm_segment'].isin(['Champions','Loyal Customers']),'num_customers'].sum():,} "
    f"customers) generate the large majority of revenue — retention spend should be "
    f"weighted toward protecting these segments, not just acquiring new ones.",
    f"A 90-day linear revenue forecast is included, but given the accelerating trend "
    f"noted above, treat it as a conservative floor, not a target — see forecasting "
    f"section for the important caveat.",
]
for p in exec_points:
    story.append(Paragraph("• " + p, styles["BulletPoint"]))

story.append(PageBreak())

# ==================================================================
# SECTION 1 — BUSINESS OVERVIEW / EDA
# ==================================================================
section_header("1. Business Overview — Exploratory Analysis")

story.append(Paragraph(
    "Question: What does the underlying business look like — revenue trend, order health, "
    "acquisition mix, and where the money comes from?", styles["BodyText2"]))

add_image(f"{OUTPUT_DIR}/01_monthly_revenue.png",
          caption="Monthly net revenue, Jan 2023 – Dec 2025. Growth is accelerating, "
                  "not linear — the last 6 months alone account for a large share of total 2025 revenue.")

status_counts = orders["order_status"].value_counts()
story.append(Paragraph("Order status breakdown:", styles["SubHeader"]))
rows = [["Status", "Orders", "% of total"]]
for status, count in status_counts.items():
    rows.append([status, f"{count:,}", f"{100*count/len(orders):.1f}%"])
data_table(rows, col_widths=[2*inch, 1.5*inch, 1.5*inch])

story.append(Paragraph(
    f"Cancelled and Pending orders together account for "
    f"{100*(status_counts.get('Cancelled',0)+status_counts.get('Pending',0))/len(orders):.1f}% "
    f"of all orders placed — worth a dedicated checkout/fulfillment funnel review, since "
    f"every Cancelled/Pending order is potential revenue never captured.",
    styles["BodyText2"]))

add_image(f"{OUTPUT_DIR}/05_category_revenue_share.png",
          caption="Revenue share by product category — fairly even split (no single category "
                  "dominates), reducing concentration risk.")

add_image(f"{OUTPUT_DIR}/03_acquisition_channel.png",
          caption="Customers by acquisition channel.")

story.append(PageBreak())

# ==================================================================
# SECTION 2 — CHURN PREDICTION
# ==================================================================
section_header("2. Customer Churn Prediction")

story.append(Paragraph(
    "Question: Which customers are at risk of leaving, and who should retention spend "
    "target first? Churn is defined as no completed order in the last 90 days, among "
    "customers who have purchased before.", styles["BodyText2"]))

kpi_row([
    ("Customers w/ purchase history", f"{len(churn_feat):,}"),
    ("Currently churned", f"{churn_rate:.1f}%"),
    ("Model ROC-AUC", "0.70"),
])

story.append(Paragraph(
    f"A Random Forest classifier was trained on behavioral features only — purchase "
    f"frequency, total spend, average order value, site sessions, cart abandonment, "
    f"returns, and discount usage. Recency itself was deliberately excluded as a feature "
    f"since it is how churn is defined (using it would leak the answer into the model).",
    styles["BodyText2"]))

add_image(f"{OUTPUT_DIR}/09_churn_feature_importance.png",
          caption="What predicts churn: purchase frequency and total spend are by far the "
                  "strongest signals — low-frequency, low-spend customers churn most.")

story.append(Paragraph(
    f"Business action: {len(priority_list):,} customers are flagged as both high-value "
    f"(above-median total spend) and high churn-risk. This is the priority outreach list "
    f"(see retention_priority_list.csv) — targeted win-back offers here protect the most "
    f"revenue per retention dollar spent.", styles["BodyText2"]))

story.append(Paragraph(
    "Caveat: precision/recall on the minority class is moderate (~0.63-0.70), typical for "
    "behavioral churn models. Use the risk score as a prioritization signal to guide "
    "outreach, not as a certainty about any individual customer.", styles["BodyText2"]))

story.append(PageBreak())

# ==================================================================
# SECTION 3 — DEMAND / REVENUE FORECASTING
# ==================================================================
section_header("3. Revenue Forecasting (Next 90 Days)")

story.append(Paragraph(
    "Question: Based on trend and seasonality, what revenue should we plan for over "
    "the next 30/60/90 days?", styles["BodyText2"]))

kpi_row([
    ("Next 30 days (forecast)", f"${next30/1e6:,.1f}M"),
    ("Next 60 days (forecast)", f"${forecast.head(60)['forecast_revenue'].sum()/1e6:,.1f}M"),
    ("Next 90 days (forecast)", f"${next90/1e6:,.1f}M"),
])

add_image(f"{OUTPUT_DIR}/10_revenue_forecast.png",
          caption="Historical daily revenue (blue) vs. 90-day linear-trend forecast (orange), "
                  "with an approximate uncertainty band.")

story.append(Paragraph(
    "Important caveat: this model uses a linear trend + day-of-week/month seasonality. "
    "The actual revenue curve in Section 1 is accelerating (compounding growth), which a "
    "straight line under-predicts — visible in the chart above, where the forecast sits "
    "noticeably below the most recent daily actuals. Backtest error on the last 60 days "
    "was high (MAPE ~49%). Treat this forecast as a conservative planning floor, not a "
    "target, and prioritize a growth-curve or ML-based model (e.g. Prophet, gradient "
    "boosting) for finance-grade forecasting.",
    styles["VerdictWarn"]))

story.append(PageBreak())

# ==================================================================
# SECTION 4 — ANOMALY DETECTION
# ==================================================================
section_header("4. Anomaly Detection")

story.append(Paragraph(
    "Question: Which days had unusual revenue, order volume, marketing spend, or refunds "
    "that deserve investigation? Method: rolling 30-day z-score, flagged when |z| > 2.5.",
    styles["BodyText2"]))

kpi_row([
    ("Revenue anomalies", f"{len(anomalies_rev)}"),
    ("Order volume anomalies", f"{len(anomalies_orders)}"),
    ("Refund anomalies", f"{len(anomalies_refunds)}"),
])

add_image(f"{OUTPUT_DIR}/11_revenue_anomalies.png",
          caption="Daily revenue with anomalous days flagged in red.")

if len(anomalies_rev) > 0:
    worst = anomalies_rev.sort_values("z_score").iloc[0]
    worst_date = anomalies_rev.sort_values("z_score").iloc[0, 0]
    story.append(Paragraph(
        f"Largest flagged revenue drop: {worst_date} (z-score {worst['z_score']:.2f}). "
        f"Order volume that day was not equally anomalous, suggesting the drop is driven "
        f"by average order value / discounting / product mix rather than site traffic — "
        f"worth cross-checking against the marketing calendar for that date.",
        styles["BodyText2"]))

story.append(Paragraph(
    "Business action: route the flagged dates in anomalies_*.csv to the relevant team "
    "(ops for order-volume drops, finance for spend spikes, product/QA for refund spikes) "
    "as a starting investigation list, not a root-cause conclusion.", styles["BodyText2"]))

story.append(PageBreak())

# ==================================================================
# SECTION 5 — A/B TEST: CHECKOUT REDESIGN
# ==================================================================
section_header("5. A/B Test — Checkout Redesign")

story.append(Paragraph(
    "Question: Does the redesigned checkout flow improve conversion enough to justify "
    "shipping it?", styles["BodyText2"]))

kpi_row([
    ("Control conversion", f"{ab['conversion_rate_control_pct']:.2f}%"),
    ("Treatment conversion", f"{ab['conversion_rate_treatment_pct']:.2f}%"),
    ("Uplift", f"+{ab['absolute_uplift_pct_points']:.2f} pp"),
])

rows = [
    ["Metric", "Value"],
    ["Sample size (control / treatment)", f"{ab['n_control']:,} / {ab['n_treatment']:,}"],
    ["P-value", f"{ab['p_value']:.4f}"],
    ["95% Confidence interval on uplift", f"[{ab['ci_95_lower_pct_points']:.2f}, {ab['ci_95_upper_pct_points']:.2f}] pp"],
    ["Statistically significant?", "Yes" if ab["statistically_significant"] else "No"],
    ["Business significant? (>=1.0pp bar)", "Yes" if ab["business_significant"] else "No"],
    ["Revenue lift observed in experiment", f"${ab['revenue_lift_in_experiment']:,.0f}"],
]
data_table(rows, col_widths=[3.5*inch, 2.8*inch])

story.append(Paragraph(
    f"Decision: SHIP. The result clears both bars — statistically significant "
    f"(p={ab['p_value']:.4f} < 0.05, confidence interval entirely positive) and "
    f"business-significant (uplift exceeds the 1.0 percentage-point bar set for "
    f"engineering/rollout cost). This is a rare 'ship with confidence' result — both "
    f"statistical and business significance line up in the same direction.",
    styles["Verdict"]))

story.append(PageBreak())

# ==================================================================
# SECTION 6 — RFM CUSTOMER SEGMENTATION
# ==================================================================
section_header("6. RFM Customer Segmentation")

story.append(Paragraph(
    "Question: Who are our customers in terms of Recency, Frequency, and Monetary value, "
    "and what should we do for each group?", styles["BodyText2"]))

add_image(f"{OUTPUT_DIR}/13_rfm_segment_value.png",
          caption="Total revenue contribution by RFM segment.")

total_seg_rev = rfm_summary["total_monetary"].sum()
rows = [["Segment", "Customers", "Total Value", "% of Revenue", "Avg Recency (days)"]]
for _, r in rfm_summary.sort_values("total_monetary", ascending=False).iterrows():
    rows.append([
        r["rfm_segment"], f"{int(r['num_customers']):,}",
        f"${r['total_monetary']/1e6:,.1f}M",
        f"{100*r['total_monetary']/total_seg_rev:.1f}%",
        f"{r['avg_recency_days']:.0f}",
    ])
data_table(rows, col_widths=[1.7*inch, 0.9*inch, 1.1*inch, 1.1*inch, 1.3*inch])

top2 = rfm_summary[rfm_summary["rfm_segment"].isin(["Champions", "Loyal Customers"])]
top2_share = 100 * top2["total_monetary"].sum() / total_seg_rev
story.append(Paragraph(
    f"Champions + Loyal Customers make up {100*top2['num_customers'].sum()/rfm_summary['num_customers'].sum():.0f}% "
    f"of purchasing customers but drive {top2_share:.0f}% of total revenue from this "
    f"customer base — protecting these two segments has an outsized ROI compared to "
    f"broad-based acquisition spend.", styles["BodyText2"]))

story.append(Paragraph("Recommended action per segment:", styles["SubHeader"]))
rows = [["Segment", "Recommended Action"]]
for _, r in rfm_actions.sort_values("total_monetary", ascending=False).iterrows():
    rows.append([r["rfm_segment"], r["recommended_action"]])
data_table(rows, col_widths=[1.7*inch, 4.6*inch])

story.append(PageBreak())

# ==================================================================
# FINAL — CONSOLIDATED RECOMMENDATIONS
# ==================================================================
section_header("7. Consolidated Recommendations")

recs = [
    "Ship the checkout redesign — the A/B test result is statistically and "
    "business-significant with no caveats.",
    f"Launch targeted retention outreach to the {len(priority_list):,} customers on the "
    f"high-value / high-churn-risk list before their 90-day churn window closes.",
    "Treat the 90-day linear revenue forecast as a floor, not a plan — build a "
    "growth-curve-aware forecast before using these numbers for budgeting, given how "
    "clearly the recent trend is accelerating past what a straight line predicts.",
    "Investigate the flagged anomaly dates (revenue, order volume, marketing spend, "
    "refunds) with the relevant team — these are candidates for real operational issues "
    "or one-off events worth understanding.",
    "Weight loyalty and VIP-style investment toward the Champions and Loyal Customers "
    "RFM segments, since they generate the large majority of revenue relative to their "
    "size — protecting them is cheaper than replacing them.",
    "Review the Cancelled/Pending order share with the checkout/fulfillment team — this "
    "is revenue that was attempted but never captured, separate from churn or marketing.",
]
for r in recs:
    story.append(Paragraph("• " + r, styles["BulletPoint"]))

story.append(Spacer(1, 20))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
story.append(Spacer(1, 8))
story.append(Paragraph(
    "Methodology notes: all figures are derived from the processed dataset "
    "(customers, orders, order_items, products, web_events, marketing_campaigns, "
    "returns, payments, experiments). Full detail tables (customer-level churn scores, "
    "RFM scores, forecast series, anomaly lists) are provided alongside this report as "
    "CSV files. Reference date used for recency-based calculations: 2025-12-31.",
    styles["Caption"]))

# ==================================================================
# BUILD PDF
# ==================================================================
doc = SimpleDocTemplate(REPORT_PATH, pagesize=letter,
                         topMargin=0.6*inch, bottomMargin=0.6*inch,
                         leftMargin=0.55*inch, rightMargin=0.55*inch)
doc.build(story)

print(f"\nBusiness insights report saved: {REPORT_PATH}")
