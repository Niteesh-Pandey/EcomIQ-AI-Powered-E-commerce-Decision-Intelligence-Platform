-- ============================================================
-- ECOMMERCE PHASE 2 - PRESENTATION VIEW LAYER
-- All analytical queries below are wrapped as PostgreSQL VIEWS.
-- A view acts as a saved, reusable virtual table: it does not
-- store data itself, it re-runs its underlying query every time
-- it is queried. This lets a stakeholder simply run:
--     SELECT * FROM vw_a1_daily_revenue;
-- instead of re-pasting a long analytical query.
-- ============================================================

-- Drop views first if re-running this script (safe / idempotent)
DROP VIEW IF EXISTS vw_a1_daily_revenue CASCADE;
DROP VIEW IF EXISTS vw_a2_monthly_revenue CASCADE;
DROP VIEW IF EXISTS vw_a3_month_over_month CASCADE;
DROP VIEW IF EXISTS vw_a4_year_over_year CASCADE;
DROP VIEW IF EXISTS vw_a5_average_order_value CASCADE;
DROP VIEW IF EXISTS vw_a6_units_sold_by_category CASCADE;
DROP VIEW IF EXISTS vw_b1_new_customers_per_month CASCADE;
DROP VIEW IF EXISTS vw_b2_new_vs_returning_customers_per_month CASCADE;
DROP VIEW IF EXISTS vw_b3_repeat_purchase_rate CASCADE;
DROP VIEW IF EXISTS vw_b4_customer_purchase_frequency CASCADE;
DROP VIEW IF EXISTS vw_b5_customer_lifetime CASCADE;
DROP VIEW IF EXISTS vw_b6_average_customer_lifetime CASCADE;
DROP VIEW IF EXISTS vw_f1_cac_per_channel CASCADE;
DROP VIEW IF EXISTS vw_f2_clv_per_customer CASCADE;
DROP VIEW IF EXISTS vw_f3_average_clv_per_acquisition_channel CASCADE;
DROP VIEW IF EXISTS vw_f4_marketing_channel_performance CASCADE;
DROP VIEW IF EXISTS vw_c1_overall_funnel_sessions_reaching_each_stage CASCADE;
DROP VIEW IF EXISTS vw_c2_conversion_rate_at_each_funnel_step CASCADE;
DROP VIEW IF EXISTS vw_c3_device_wise_conversion_rate CASCADE;
DROP VIEW IF EXISTS vw_c4_channel_wise_conversion_rate CASCADE;
DROP VIEW IF EXISTS vw_c5_biggest_drop_off_stage CASCADE;
DROP VIEW IF EXISTS vw_d1_cohort_retention_table CASCADE;
DROP VIEW IF EXISTS vw_d2_retention_by_acquisition_channel CASCADE;
DROP VIEW IF EXISTS vw_e1_raw_rfm_values_per_customer CASCADE;
DROP VIEW IF EXISTS vw_e2_rfm_scores CASCADE;
DROP VIEW IF EXISTS vw_e3_full_rfm_segmentation CASCADE;
DROP VIEW IF EXISTS vw_e4_segment_summary CASCADE;
DROP VIEW IF EXISTS vw_g1_median_repurchase_interval CASCADE;
DROP VIEW IF EXISTS vw_g2_churn_status_per_customer CASCADE;
DROP VIEW IF EXISTS vw_g3_overall_churn_rate CASCADE;
DROP VIEW IF EXISTS vw_g4_churn_rate_by_customer_segment CASCADE;
DROP VIEW IF EXISTS vw_g5_high_value_churned_customers CASCADE;
DROP VIEW IF EXISTS vw_h1_product_performance CASCADE;
DROP VIEW IF EXISTS vw_h2_product_classification CASCADE;
DROP VIEW IF EXISTS vw_h3_category_level_summary CASCADE;
DROP VIEW IF EXISTS vw_h4_return_reasons_breakdown CASCADE;
DROP VIEW IF EXISTS vw_h5_basket_analysis_products_frequently_bought_together CASCADE;
DROP VIEW IF EXISTS vw_i1_conversion_rate_by_variant CASCADE;
DROP VIEW IF EXISTS vw_i2_uplift_calculation CASCADE;
DROP VIEW IF EXISTS vw_i3_estimated_annualized_business_impact CASCADE;


-- ================================================================
-- SECTION A: SALES ANALYTICS
-- ================================================================

-- A1. DAILY REVENUE
-- Business rule: only "Completed" orders count as real revenue.
-- Revenue = sum of line_total, minus discount%, plus shipping.
CREATE OR REPLACE VIEW vw_a1_daily_revenue AS
SELECT
    o.order_date::date AS order_day,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(oi.line_total) AS gross_revenue,
    SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS net_revenue_after_discount,
    SUM(oi.quantity) AS units_sold
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'Completed'
GROUP BY o.order_date::date
ORDER BY order_day;

-- A2. MONTHLY REVENUE
CREATE OR REPLACE VIEW vw_a2_monthly_revenue AS
SELECT
    DATE_TRUNC('month', o.order_date)::date AS order_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(oi.line_total) AS gross_revenue,
    SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS net_revenue,
    SUM(oi.quantity) AS units_sold
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status = 'Completed'
GROUP BY DATE_TRUNC('month', o.order_date)
ORDER BY order_month;

-- A3. MONTH-OVER-MONTH (MoM) GROWTH %
-- Uses window function LAG() to compare each month to the previous one.
CREATE OR REPLACE VIEW vw_a3_month_over_month AS
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS net_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY DATE_TRUNC('month', o.order_date)
)
SELECT
    order_month,
    net_revenue,
    LAG(net_revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
    ROUND(
        100.0 * (net_revenue - LAG(net_revenue) OVER (ORDER BY order_month))
        / NULLIF(LAG(net_revenue) OVER (ORDER BY order_month), 0)
    , 2) AS mom_growth_pct
FROM monthly_revenue
ORDER BY order_month;

-- A4. YEAR-OVER-YEAR (YoY) GROWTH %
-- Compares same month across different years using LAG with offset 12.
CREATE OR REPLACE VIEW vw_a4_year_over_year AS
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS net_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY DATE_TRUNC('month', o.order_date)
)
SELECT
    order_month,
    net_revenue,
    LAG(net_revenue, 12) OVER (ORDER BY order_month) AS same_month_last_year,
    ROUND(
        100.0 * (net_revenue - LAG(net_revenue, 12) OVER (ORDER BY order_month))
        / NULLIF(LAG(net_revenue, 12) OVER (ORDER BY order_month), 0)
    , 2) AS yoy_growth_pct
FROM monthly_revenue
ORDER BY order_month;

-- A5. AVERAGE ORDER VALUE (AOV) — overall and monthly
-- AOV = net revenue / number of orders
-- Exclude unit_price = 0 rows (flagged as promo/free items) from AOV calc.
CREATE OR REPLACE VIEW vw_a5_average_order_value AS
WITH order_totals AS (
    SELECT
        o.order_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS order_net_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
      AND oi.unit_price > 0
    GROUP BY o.order_id, DATE_TRUNC('month', o.order_date)
)
SELECT
    order_month,
    COUNT(order_id) AS total_orders,
    ROUND(AVG(order_net_value), 2) AS aov,
    ROUND(SUM(order_net_value), 2) AS total_revenue
FROM order_totals
GROUP BY order_month
ORDER BY order_month;

-- A6. UNITS SOLD BY CATEGORY (with CASE for size buckets, just for variety)
CREATE OR REPLACE VIEW vw_a6_units_sold_by_category AS
SELECT
    p.category,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.line_total) AS revenue,
    CASE
        WHEN SUM(oi.quantity) >= 5000 THEN 'High Volume'
        WHEN SUM(oi.quantity) >= 1000 THEN 'Medium Volume'
        ELSE 'Low Volume'
    END AS volume_tier
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- ================================================================
-- SECTION B: CUSTOMER GROWTH & BEHAVIOR
-- ================================================================

-- B1. NEW CUSTOMERS PER MONTH
-- "New" = their signup_date falls in that month.
CREATE OR REPLACE VIEW vw_b1_new_customers_per_month AS
SELECT
    DATE_TRUNC('month', signup_date)::date AS signup_month,
    COUNT(*) AS new_customers
FROM customers
GROUP BY DATE_TRUNC('month', signup_date)
ORDER BY signup_month;

-- B2. NEW VS RETURNING CUSTOMERS PER MONTH (based on orders)
-- A customer is "new" in a month if it's their FIRST EVER completed order month.
-- Uses window function to find each customer's first order date.
CREATE OR REPLACE VIEW vw_b2_new_vs_returning_customers_per_month AS
WITH customer_first_order AS (
    SELECT
        customer_id,
        MIN(order_date) AS first_order_date
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
orders_tagged AS (
    SELECT
        o.order_id,
        o.customer_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month,
        CASE
            WHEN DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', cfo.first_order_date)
            THEN 'New'
            ELSE 'Returning'
        END AS customer_type
    FROM orders o
    JOIN customer_first_order cfo ON cfo.customer_id = o.customer_id
    WHERE o.order_status = 'Completed'
)
SELECT
    order_month,
    customer_type,
    COUNT(DISTINCT customer_id) AS customers,
    COUNT(order_id) AS orders
FROM orders_tagged
GROUP BY order_month, customer_type
ORDER BY order_month, customer_type;

-- B3. REPEAT PURCHASE RATE (overall)
-- % of customers who placed MORE THAN ONE completed order.
CREATE OR REPLACE VIEW vw_b3_repeat_purchase_rate AS
WITH order_counts AS (
    SELECT
        customer_id,
        COUNT(*) AS num_orders
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
)
SELECT
    COUNT(*) AS total_customers_with_orders,
    COUNT(*) FILTER (WHERE num_orders > 1) AS repeat_customers,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE num_orders > 1) / COUNT(*)
    , 2) AS repeat_purchase_rate_pct
FROM order_counts;

-- B4. CUSTOMER PURCHASE FREQUENCY (orders per customer, distribution)
CREATE OR REPLACE VIEW vw_b4_customer_purchase_frequency AS
WITH order_counts AS (
    SELECT
        customer_id,
        COUNT(*) AS num_orders
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
)
SELECT
    num_orders AS orders_placed,
    COUNT(*) AS num_customers
FROM order_counts
GROUP BY num_orders
ORDER BY num_orders;

-- B5. CUSTOMER LIFETIME (days between first and last order)
CREATE OR REPLACE VIEW vw_b5_customer_lifetime AS
SELECT
    o.customer_id,
    MIN(o.order_date)::date AS first_order,
    MAX(o.order_date)::date AS last_order,
    (MAX(o.order_date)::date - MIN(o.order_date)::date) AS customer_lifetime_days,
    COUNT(*) AS total_orders
FROM orders o
WHERE o.order_status = 'Completed'
GROUP BY o.customer_id
HAVING COUNT(*) > 1   -- lifetime only makes sense for repeat customers
ORDER BY customer_lifetime_days DESC;

-- B6. AVERAGE CUSTOMER LIFETIME (single summary number)
CREATE OR REPLACE VIEW vw_b6_average_customer_lifetime AS
WITH cust_lifetime AS (
    SELECT
        customer_id,
        (MAX(order_date)::date - MIN(order_date)::date) AS lifetime_days
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
    HAVING COUNT(*) > 1
)
SELECT
    ROUND(AVG(lifetime_days), 1) AS avg_customer_lifetime_days,
    ROUND(AVG(lifetime_days) / 30.0, 1) AS avg_customer_lifetime_months
FROM cust_lifetime;

-- ================================================================
-- SECTION F: MARKETING: CAC, CLV & CHANNEL PERFORMANCE
-- ================================================================

-- F1. CAC PER CHANNEL
-- CAC = total spend on a channel / number of NEW customers acquired via that channel
CREATE OR REPLACE VIEW vw_f1_cac_per_channel AS
WITH channel_spend AS (
    SELECT
        channel,
        SUM(spend) AS total_spend
    FROM marketing_campaigns
    GROUP BY channel
),
channel_new_customers AS (
    SELECT
        acquisition_channel AS channel,
        COUNT(*) AS new_customers
    FROM customers
    GROUP BY acquisition_channel
)
SELECT
    cs.channel,
    cs.total_spend,
    cnc.new_customers,
    ROUND(cs.total_spend / NULLIF(cnc.new_customers,0), 2) AS cac
FROM channel_spend cs
JOIN channel_new_customers cnc ON cnc.channel = cs.channel
ORDER BY cac ASC NULLS LAST;

-- F2. CLV PER CUSTOMER (simple historical CLV = total net spend to date)
CREATE OR REPLACE VIEW vw_f2_clv_per_customer AS
WITH customer_spend AS (
    SELECT
        o.customer_id,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS total_spend,
        COUNT(DISTINCT o.order_id) AS total_orders,
        MIN(o.order_date)::date AS first_order,
        MAX(o.order_date)::date AS last_order
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id
)
SELECT
    customer_id,
    total_spend AS clv,
    total_orders,
    first_order,
    last_order,
    ROUND(total_spend / NULLIF(total_orders,0), 2) AS avg_order_value
FROM customer_spend
ORDER BY clv DESC;

-- F3. AVERAGE CLV PER ACQUISITION CHANNEL (+ CLV:CAC RATIO)
-- This is a KEY business insight query: which channel brings customers
-- who are both cheap to acquire AND spend a lot over their lifetime?
CREATE OR REPLACE VIEW vw_f3_average_clv_per_acquisition_channel AS
WITH customer_spend AS (
    SELECT
        o.customer_id,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS total_spend
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id
),
channel_clv AS (
    SELECT
        c.acquisition_channel AS channel,
        AVG(cs.total_spend) AS avg_clv,
        COUNT(*) AS num_customers
    FROM customers c
    JOIN customer_spend cs ON cs.customer_id = c.customer_id
    GROUP BY c.acquisition_channel
),
channel_cac AS (
    SELECT
        cs.channel,
        SUM(cs.spend) AS total_spend,
        cnc.new_customers,
        ROUND(SUM(cs.spend) / NULLIF(cnc.new_customers,0), 2) AS cac
    FROM marketing_campaigns cs
    JOIN (
        SELECT acquisition_channel AS channel, COUNT(*) AS new_customers
        FROM customers GROUP BY acquisition_channel
    ) cnc ON cnc.channel = cs.channel
    GROUP BY cs.channel, cnc.new_customers
)
SELECT
    cc.channel,
    ROUND(cclv.avg_clv, 2) AS avg_clv,
    cc.cac,
    ROUND(cclv.avg_clv / NULLIF(cc.cac,0), 2) AS clv_to_cac_ratio
FROM channel_cac cc
JOIN channel_clv cclv ON cclv.channel = cc.channel
ORDER BY clv_to_cac_ratio DESC NULLS LAST;

-- F4. MARKETING CHANNEL PERFORMANCE (CTR, CPC, CVR, ROAS)
CREATE OR REPLACE VIEW vw_f4_marketing_channel_performance AS
WITH channel_totals AS (
    SELECT
        channel,
        SUM(spend) AS total_spend,
        SUM(impressions) AS total_impressions,
        SUM(clicks) AS total_clicks,
        SUM(conversions) AS total_conversions
    FROM marketing_campaigns
    GROUP BY channel
),
channel_revenue AS (
    -- attribute revenue to channel via the customer's acquisition_channel
    -- (simple attribution model — first-touch / acquisition channel)
    SELECT
        c.acquisition_channel AS channel,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS attributed_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'Completed'
    GROUP BY c.acquisition_channel
)
SELECT
    ct.channel,
    ct.total_spend,
    ct.total_impressions,
    ct.total_clicks,
    ct.total_conversions,
    ROUND(100.0 * ct.total_clicks / NULLIF(ct.total_impressions,0), 3) AS ctr_pct,
    ROUND(ct.total_spend / NULLIF(ct.total_clicks,0), 2) AS cpc,
    ROUND(100.0 * ct.total_conversions / NULLIF(ct.total_clicks,0), 2) AS conversion_rate_pct,
    cr.attributed_revenue,
    ROUND(cr.attributed_revenue / NULLIF(ct.total_spend,0), 2) AS roas
FROM channel_totals ct
LEFT JOIN channel_revenue cr ON cr.channel = ct.channel
ORDER BY roas DESC NULLS LAST;

-- ================================================================
-- SECTION C: WEB FUNNEL & CONVERSION
-- ================================================================

-- C1. OVERALL FUNNEL — sessions reaching each stage
CREATE OR REPLACE VIEW vw_c1_overall_funnel_sessions_reaching_each_stage AS
WITH session_stages AS (
    SELECT
        session_id,
        MAX(CASE WHEN event_name = 'page_view'     THEN 1 ELSE 0 END) AS reached_page_view,
        MAX(CASE WHEN event_name = 'product_view'  THEN 1 ELSE 0 END) AS reached_product_view,
        MAX(CASE WHEN event_name = 'add_to_cart'   THEN 1 ELSE 0 END) AS reached_add_to_cart,
        MAX(CASE WHEN event_name = 'checkout'      THEN 1 ELSE 0 END) AS reached_checkout,
        MAX(CASE WHEN event_name = 'purchase'      THEN 1 ELSE 0 END) AS reached_purchase
    FROM web_events
    WHERE session_id != 'UNKNOWN_SESSION'
    GROUP BY session_id
)
SELECT
    SUM(reached_page_view)    AS step1_page_view,
    SUM(reached_product_view) AS step2_product_view,
    SUM(reached_add_to_cart)  AS step3_add_to_cart,
    SUM(reached_checkout)     AS step4_checkout,
    SUM(reached_purchase)     AS step5_purchase
FROM session_stages;

-- C2. CONVERSION RATE AT EACH FUNNEL STEP (step-to-step %)
CREATE OR REPLACE VIEW vw_c2_conversion_rate_at_each_funnel_step AS
WITH session_stages AS (
    SELECT
        session_id,
        MAX(CASE WHEN event_name = 'page_view'     THEN 1 ELSE 0 END) AS reached_page_view,
        MAX(CASE WHEN event_name = 'product_view'  THEN 1 ELSE 0 END) AS reached_product_view,
        MAX(CASE WHEN event_name = 'add_to_cart'   THEN 1 ELSE 0 END) AS reached_add_to_cart,
        MAX(CASE WHEN event_name = 'checkout'      THEN 1 ELSE 0 END) AS reached_checkout,
        MAX(CASE WHEN event_name = 'purchase'      THEN 1 ELSE 0 END) AS reached_purchase
    FROM web_events
    WHERE session_id != 'UNKNOWN_SESSION'
    GROUP BY session_id
),
totals AS (
    SELECT
        SUM(reached_page_view)    AS n_page_view,
        SUM(reached_product_view) AS n_product_view,
        SUM(reached_add_to_cart)  AS n_add_to_cart,
        SUM(reached_checkout)     AS n_checkout,
        SUM(reached_purchase)     AS n_purchase
    FROM session_stages
)
SELECT
    n_page_view,
    n_product_view,
    n_add_to_cart,
    n_checkout,
    n_purchase,
    ROUND(100.0 * n_product_view / NULLIF(n_page_view,0), 2)    AS pv_to_productview_pct,
    ROUND(100.0 * n_add_to_cart  / NULLIF(n_product_view,0), 2) AS productview_to_cart_pct,
    ROUND(100.0 * n_checkout     / NULLIF(n_add_to_cart,0), 2)  AS cart_to_checkout_pct,
    ROUND(100.0 * n_purchase     / NULLIF(n_checkout,0), 2)     AS checkout_to_purchase_pct,
    ROUND(100.0 * n_purchase     / NULLIF(n_page_view,0), 2)    AS overall_conversion_pct
FROM totals;

-- C3. DEVICE-WISE CONVERSION RATE (page_view -> purchase)
CREATE OR REPLACE VIEW vw_c3_device_wise_conversion_rate AS
WITH session_device AS (
    SELECT
        we.session_id,
        c.device,
        MAX(CASE WHEN we.event_name = 'page_view' THEN 1 ELSE 0 END) AS reached_page_view,
        MAX(CASE WHEN we.event_name = 'purchase'  THEN 1 ELSE 0 END) AS reached_purchase
    FROM web_events we
    JOIN customers c ON c.customer_id = we.customer_id
    WHERE we.session_id != 'UNKNOWN_SESSION'
    GROUP BY we.session_id, c.device
)
SELECT
    device,
    SUM(reached_page_view) AS sessions,
    SUM(reached_purchase) AS purchases,
    ROUND(100.0 * SUM(reached_purchase) / NULLIF(SUM(reached_page_view),0), 2) AS conversion_pct
FROM session_device
GROUP BY device
ORDER BY conversion_pct DESC;

-- C4. CHANNEL-WISE CONVERSION RATE (acquisition_channel -> purchase)
CREATE OR REPLACE VIEW vw_c4_channel_wise_conversion_rate AS
WITH session_channel AS (
    SELECT
        we.session_id,
        c.acquisition_channel,
        MAX(CASE WHEN we.event_name = 'page_view' THEN 1 ELSE 0 END) AS reached_page_view,
        MAX(CASE WHEN we.event_name = 'purchase'  THEN 1 ELSE 0 END) AS reached_purchase
    FROM web_events we
    JOIN customers c ON c.customer_id = we.customer_id
    WHERE we.session_id != 'UNKNOWN_SESSION'
    GROUP BY we.session_id, c.acquisition_channel
)
SELECT
    acquisition_channel,
    SUM(reached_page_view) AS sessions,
    SUM(reached_purchase) AS purchases,
    ROUND(100.0 * SUM(reached_purchase) / NULLIF(SUM(reached_page_view),0), 2) AS conversion_pct
FROM session_channel
GROUP BY acquisition_channel
ORDER BY conversion_pct DESC;

-- C5. BIGGEST DROP-OFF STAGE (which step loses the most sessions)
CREATE OR REPLACE VIEW vw_c5_biggest_drop_off_stage AS
WITH session_stages AS (
    SELECT
        session_id,
        MAX(CASE WHEN event_name = 'page_view'     THEN 1 ELSE 0 END) AS s1,
        MAX(CASE WHEN event_name = 'product_view'  THEN 1 ELSE 0 END) AS s2,
        MAX(CASE WHEN event_name = 'add_to_cart'   THEN 1 ELSE 0 END) AS s3,
        MAX(CASE WHEN event_name = 'checkout'      THEN 1 ELSE 0 END) AS s4,
        MAX(CASE WHEN event_name = 'purchase'      THEN 1 ELSE 0 END) AS s5
    FROM web_events
    WHERE session_id != 'UNKNOWN_SESSION'
    GROUP BY session_id
),
totals AS (
    SELECT SUM(s1) t1, SUM(s2) t2, SUM(s3) t3, SUM(s4) t4, SUM(s5) t5 FROM session_stages
)
SELECT stage, sessions_lost FROM (
    SELECT 'page_view -> product_view' AS stage, (t1 - t2) AS sessions_lost FROM totals
    UNION ALL
    SELECT 'product_view -> add_to_cart', (t2 - t3) FROM totals
    UNION ALL
    SELECT 'add_to_cart -> checkout', (t3 - t4) FROM totals
    UNION ALL
    SELECT 'checkout -> purchase', (t4 - t5) FROM totals
) drop_offs
ORDER BY sessions_lost DESC;

-- ================================================================
-- SECTION D: COHORT RETENTION
-- ================================================================

-- D1. COHORT RETENTION TABLE (signup month x months-since-signup)
CREATE OR REPLACE VIEW vw_d1_cohort_retention_table AS
WITH cohort AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers
),
customer_orders AS (
    SELECT
        o.customer_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month
    FROM orders o
    WHERE o.order_status = 'Completed'
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        co.customer_id,
        -- months between signup month and order month
        (EXTRACT(YEAR FROM co.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12
        + (EXTRACT(MONTH FROM co.order_month) - EXTRACT(MONTH FROM c.cohort_month)) AS month_number
    FROM cohort c
    JOIN customer_orders co ON co.customer_id = c.customer_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS num_customers
    FROM cohort
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.num_customers AS cohort_size,
    ca.month_number,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) / cs.num_customers, 2) AS retention_pct
FROM cohort_activity ca
JOIN cohort_size cs ON cs.cohort_month = ca.cohort_month
WHERE ca.month_number >= 0
GROUP BY ca.cohort_month, cs.num_customers, ca.month_number
ORDER BY ca.cohort_month, ca.month_number;

-- D2. RETENTION BY ACQUISITION CHANNEL (which channel retains best)
CREATE OR REPLACE VIEW vw_d2_retention_by_acquisition_channel AS
WITH cohort AS (
    SELECT
        customer_id,
        acquisition_channel,
        DATE_TRUNC('month', signup_date)::date AS cohort_month
    FROM customers
),
customer_orders AS (
    SELECT
        o.customer_id,
        DATE_TRUNC('month', o.order_date)::date AS order_month
    FROM orders o
    WHERE o.order_status = 'Completed'
),
cohort_activity AS (
    SELECT
        c.acquisition_channel,
        c.customer_id,
        (EXTRACT(YEAR FROM co.order_month) - EXTRACT(YEAR FROM c.cohort_month)) * 12
        + (EXTRACT(MONTH FROM co.order_month) - EXTRACT(MONTH FROM c.cohort_month)) AS month_number
    FROM cohort c
    JOIN customer_orders co ON co.customer_id = c.customer_id
),
channel_size AS (
    SELECT acquisition_channel, COUNT(DISTINCT customer_id) AS total_customers
    FROM cohort
    GROUP BY acquisition_channel
)
SELECT
    ca.acquisition_channel,
    cs.total_customers,
    -- retained at month 3 (i.e. still purchasing 3 months after signup)
    COUNT(DISTINCT ca.customer_id) FILTER (WHERE ca.month_number = 3) AS active_month_3,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_id) FILTER (WHERE ca.month_number = 3) / cs.total_customers, 2) AS retention_month3_pct
FROM cohort_activity ca
JOIN channel_size cs ON cs.acquisition_channel = ca.acquisition_channel
GROUP BY ca.acquisition_channel, cs.total_customers
ORDER BY retention_month3_pct DESC;

-- ================================================================
-- SECTION E: RFM CUSTOMER SEGMENTATION
-- ================================================================

-- E1. RAW RFM VALUES PER CUSTOMER
-- FIX: recency_days now measured from the dataset's own last order date
-- (analysis_date) instead of CURRENT_DATE, so the value is fixed and
-- reproducible no matter when this view is queried.
CREATE OR REPLACE VIEW vw_e1_raw_rfm_values_per_customer AS
WITH dataset_date AS (
    SELECT MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
),
rfm_raw AS (
    SELECT
        o.customer_id,
        (dd.analysis_date - MAX(o.order_date)::date) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    CROSS JOIN dataset_date dd
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, dd.analysis_date
)
SELECT * FROM rfm_raw
ORDER BY monetary DESC;

-- E2. RFM SCORES (1-5 scale) using NTILE
-- Note: recency is scored in REVERSE (lower days = higher score = 5)
-- FIX: analysis_date replaces CURRENT_DATE (see E1). Also added customer_id
-- as a secondary ORDER BY key inside each NTILE so ties (very common on
-- 'frequency', which only takes small integer values) are broken the same
-- way every time the view is run, instead of non-deterministically.
CREATE OR REPLACE VIEW vw_e2_rfm_scores AS
WITH dataset_date AS (
    SELECT MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
),
rfm_raw AS (
    SELECT
        o.customer_id,
        (dd.analysis_date - MAX(o.order_date)::date) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    CROSS JOIN dataset_date dd
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, dd.analysis_date
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- 5 = most recent (lowest days), 1 = least recent
        6 - NTILE(5) OVER (ORDER BY recency_days, customer_id) AS r_score,
        NTILE(5) OVER (ORDER BY frequency, customer_id)        AS f_score,
        NTILE(5) OVER (ORDER BY monetary, customer_id)         AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS rfm_total_score
FROM rfm_scored
ORDER BY rfm_total_score DESC;

-- E3. FULL RFM SEGMENTATION (business-labeled segments)
-- This is the main output table for BI / customer strategy.
-- FIX: same analysis_date + NTILE tiebreak fixes as E2.
CREATE OR REPLACE VIEW vw_e3_full_rfm_segmentation AS
WITH dataset_date AS (
    SELECT MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
),
rfm_raw AS (
    SELECT
        o.customer_id,
        (dd.analysis_date - MAX(o.order_date)::date) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    CROSS JOIN dataset_date dd
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, dd.analysis_date
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        6 - NTILE(5) OVER (ORDER BY recency_days, customer_id) AS r_score,
        NTILE(5) OVER (ORDER BY frequency, customer_id)        AS f_score,
        NTILE(5) OVER (ORDER BY monetary, customer_id)         AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score, f_score, m_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
        WHEN r_score >= 3 AND f_score <= 3 AND m_score >= 3 THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Cannot Lose Them'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
        WHEN r_score <= 3 AND f_score <= 2 THEN 'Hibernating'
        ELSE 'Others'
    END AS rfm_segment
FROM rfm_scored
ORDER BY monetary DESC;

-- E4. SEGMENT SUMMARY (count + avg spend per segment)
-- FIX: same analysis_date + NTILE tiebreak fixes as E2/E3.
CREATE OR REPLACE VIEW vw_e4_segment_summary AS
WITH dataset_date AS (
    SELECT MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
),
rfm_raw AS (
    SELECT
        o.customer_id,
        (dd.analysis_date - MAX(o.order_date)::date) AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS monetary
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    CROSS JOIN dataset_date dd
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, dd.analysis_date
),
rfm_scored AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        6 - NTILE(5) OVER (ORDER BY recency_days, customer_id) AS r_score,
        NTILE(5) OVER (ORDER BY frequency, customer_id)        AS f_score,
        NTILE(5) OVER (ORDER BY monetary, customer_id)         AS m_score
    FROM rfm_raw
),
rfm_segmented AS (
    SELECT
        customer_id,
        monetary,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
            WHEN r_score >= 3 AND f_score <= 3 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 4 AND m_score >= 4 THEN 'Cannot Lose Them'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
            WHEN r_score <= 3 AND f_score <= 2 THEN 'Hibernating'
            ELSE 'Others'
        END AS rfm_segment
    FROM rfm_scored
)
SELECT
    rfm_segment,
    COUNT(*) AS num_customers,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(SUM(monetary), 2) AS total_monetary
FROM rfm_segmented
GROUP BY rfm_segment
ORDER BY total_monetary DESC;

-- ================================================================
-- SECTION G: CHURN ANALYSIS
-- ================================================================

-- G1. MEDIAN REPURCHASE INTERVAL (use this to justify the 90-day rule)
-- Time gap between consecutive orders of the same customer, using LAG().
CREATE OR REPLACE VIEW vw_g1_median_repurchase_interval AS
WITH order_gaps AS (
    SELECT
        customer_id,
        order_date,
        order_date 
            - LAG(order_date) OVER (
                PARTITION BY customer_id 
                ORDER BY order_date
            ) AS days_since_prev_order
    FROM orders
    WHERE order_status = 'Completed'
)
SELECT
    ROUND(
        PERCENTILE_CONT(0.5) 
        WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM days_since_prev_order) / 86400
        )::numeric,
        1
    ) AS median_repurchase_days,

    ROUND(
        AVG(
            EXTRACT(EPOCH FROM days_since_prev_order) / 86400
        )::numeric,
        1
    ) AS avg_repurchase_days
FROM order_gaps
WHERE days_since_prev_order IS NOT NULL;

-- G2. CHURN STATUS PER CUSTOMER
-- FIX: was using CURRENT_DATE (the real, ever-advancing system date), which made
-- every customer show as "Churned" once enough real-world time had passed since
-- the dataset was captured. Now uses the dataset's own last order date as the
-- fixed analysis date (same approach as G3/G4), so results are reproducible and
-- consistent no matter when this view is queried.
CREATE OR REPLACE VIEW vw_g2_churn_status_per_customer AS
WITH customer_activity AS (
    SELECT
        customer_id,
        MAX(order_date)::date AS last_order_date,
        COUNT(*) AS total_orders
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
dataset_date AS (
    SELECT
        MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
)
SELECT
    ca.customer_id,
    ca.last_order_date,
    ca.total_orders,
    (dd.analysis_date - ca.last_order_date) AS days_since_last_order,
    CASE
        WHEN (dd.analysis_date - ca.last_order_date) > 90 THEN 'Churned'
        ELSE 'Active'
    END AS churn_status
FROM customer_activity ca
CROSS JOIN dataset_date dd
ORDER BY days_since_last_order DESC;

-- G3. OVERALL CHURN RATE
CREATE OR REPLACE VIEW vw_g3_overall_churn_rate AS
WITH customer_activity AS (
    SELECT
        customer_id,
        MAX(order_date)::date AS last_order_date
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),
dataset_date AS (
    SELECT
        MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
),
churn_tagged AS (
    SELECT
        ca.customer_id,
        ca.last_order_date,
        CASE
            WHEN (dd.analysis_date - ca.last_order_date) > 90
            THEN 1
            ELSE 0
        END AS is_churned
    FROM customer_activity ca
    CROSS JOIN dataset_date dd
)
SELECT
    COUNT(*) AS total_customers,
    SUM(is_churned) AS churned_customers,
    ROUND(
        100.0 * SUM(is_churned) / COUNT(*),
        2
    ) AS churn_rate_pct
FROM churn_tagged;

-- G4. CHURN RATE BY CUSTOMER SEGMENT (self-reported segment field)
CREATE OR REPLACE VIEW vw_g4_churn_rate_by_customer_segment AS
WITH customer_activity AS (
    SELECT
        o.customer_id,
        MAX(o.order_date)::date AS last_order_date
    FROM orders o
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id
),

analysis_date AS (
    SELECT
        MAX(order_date)::date AS max_order_date
    FROM orders
    WHERE order_status = 'Completed'
),

churn_tagged AS (
    SELECT
        ca.customer_id,
        c.customer_segment,
        ca.last_order_date,
        CASE
            WHEN (ad.max_order_date - ca.last_order_date) > 90
            THEN 1
            ELSE 0
        END AS is_churned
    FROM customer_activity ca
    JOIN customers c
        ON c.customer_id = ca.customer_id
    CROSS JOIN analysis_date ad
)

SELECT
    customer_segment,
    COUNT(*) AS total_customers,
    SUM(is_churned) AS churned_customers,
    ROUND(
        100.0 * SUM(is_churned) / COUNT(*),
        2
    ) AS churn_rate_pct
FROM churn_tagged
GROUP BY customer_segment
ORDER BY churn_rate_pct DESC;

-- G5. HIGH-VALUE CHURNED CUSTOMERS (priority list for retention team)
-- FIX: was using CURRENT_DATE, so this list would eventually include every
-- customer in the dataset regardless of true recency. Now uses the dataset's
-- own last order date as the fixed analysis date, same as G2/G3/G4.
CREATE OR REPLACE VIEW vw_g5_high_value_churned_customers AS
WITH customer_spend AS (
    SELECT
        o.customer_id,
        SUM(oi.line_total * (1 - COALESCE(o.discount,0))) AS total_spend,
        MAX(o.order_date)::date AS last_order_date,
        COUNT(DISTINCT o.order_id) AS total_orders
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id
),
dataset_date AS (
    SELECT
        MAX(order_date)::date AS analysis_date
    FROM orders
    WHERE order_status = 'Completed'
)
SELECT
    cs.customer_id,
    cs.total_spend,
    cs.total_orders,
    cs.last_order_date,
    (dd.analysis_date - cs.last_order_date) AS days_since_last_order
FROM customer_spend cs
CROSS JOIN dataset_date dd
WHERE (dd.analysis_date - cs.last_order_date) > 90   -- churned
ORDER BY total_spend DESC
LIMIT 100;

-- ================================================================
-- SECTION H: PRODUCT PERFORMANCE & BASKET ANALYSIS
-- ================================================================

-- H1. PRODUCT PERFORMANCE (revenue, margin, units, return rate)
CREATE OR REPLACE VIEW vw_h1_product_performance AS
WITH product_sales AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.cost,
        p.selling_price,
        SUM(oi.quantity) AS units_sold,
        SUM(oi.line_total) AS revenue,
        SUM(oi.quantity * COALESCE(p.cost,0)) AS total_cost
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.order_status = 'Completed'
      AND p.price_is_invalid = FALSE   -- exclude data-error priced products
    GROUP BY p.product_id, p.product_name, p.category, p.cost, p.selling_price
),
product_returns AS (
    SELECT
        product_id,
        COUNT(*) AS return_count
    FROM returns
    GROUP BY product_id
)
SELECT
    ps.product_id,
    ps.product_name,
    ps.category,
    ps.units_sold,
    ps.revenue,
    (ps.revenue - ps.total_cost) AS gross_margin,
    ROUND(100.0 * (ps.revenue - ps.total_cost) / NULLIF(ps.revenue,0), 2) AS margin_pct,
    COALESCE(pr.return_count, 0) AS return_count,
    ROUND(100.0 * COALESCE(pr.return_count,0) / NULLIF(ps.units_sold,0), 2) AS return_rate_pct
FROM product_sales ps
LEFT JOIN product_returns pr ON pr.product_id = ps.product_id
ORDER BY ps.revenue DESC;

-- H2. PRODUCT CLASSIFICATION (Stars / Problem / Hidden Gems / Dead Stock)
-- Uses median sales & margin as the split point (via CTE + window function).
CREATE OR REPLACE VIEW vw_h2_product_classification AS
WITH product_sales AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(oi.quantity) AS units_sold,
        SUM(oi.line_total) AS revenue,
        SUM(oi.line_total) - SUM(oi.quantity * COALESCE(p.cost,0)) AS gross_margin
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.order_status = 'Completed'
      AND p.price_is_invalid = FALSE
    GROUP BY p.product_id, p.product_name, p.category
),
medians AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY units_sold) AS median_units,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gross_margin) AS median_margin
    FROM product_sales
)
SELECT
    ps.product_id,
    ps.product_name,
    ps.category,
    ps.units_sold,
    ps.gross_margin,
    CASE
        WHEN ps.units_sold >= m.median_units AND ps.gross_margin >= m.median_margin THEN 'Star'
        WHEN ps.units_sold >= m.median_units AND ps.gross_margin <  m.median_margin THEN 'Problem Product'
        WHEN ps.units_sold <  m.median_units AND ps.gross_margin >= m.median_margin THEN 'Hidden Gem'
        ELSE 'Dead Stock'
    END AS product_classification
FROM product_sales ps
CROSS JOIN medians m
ORDER BY ps.gross_margin DESC;

-- H3. CATEGORY-LEVEL SUMMARY
CREATE OR REPLACE VIEW vw_h3_category_level_summary AS
SELECT
    p.category,
    COUNT(DISTINCT p.product_id) AS num_products,
    SUM(oi.quantity) AS units_sold,
    SUM(oi.line_total) AS revenue,
    ROUND(AVG(oi.unit_price), 2) AS avg_unit_price
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- H4. RETURN REASONS BREAKDOWN
CREATE OR REPLACE VIEW vw_h4_return_reasons_breakdown AS
SELECT
    return_reason,
    COUNT(*) AS num_returns,
    ROUND(SUM(refund_amount), 2) AS total_refunded
FROM returns
GROUP BY return_reason
ORDER BY num_returns DESC;

-- H5. BASKET ANALYSIS — products frequently bought together
-- Self-join order_items on order_id to find product pairs in the same order.
CREATE OR REPLACE VIEW vw_h5_basket_analysis_products_frequently_bought_together AS
WITH order_pairs AS (
    SELECT
        oi1.product_id AS product_a,
        oi2.product_id AS product_b,
        oi1.order_id
    FROM order_items oi1
    JOIN order_items oi2
        ON oi1.order_id = oi2.order_id
        AND oi1.product_id < oi2.product_id   -- avoid duplicate pairs & self-pairs
    JOIN orders o ON o.order_id = oi1.order_id
    WHERE o.order_status = 'Completed'
)
SELECT
    pa.product_name AS product_a_name,
    pb.product_name AS product_b_name,
    COUNT(*) AS times_bought_together
FROM order_pairs op
JOIN products pa ON pa.product_id = op.product_a
JOIN products pb ON pb.product_id = op.product_b
GROUP BY pa.product_name, pb.product_name
HAVING COUNT(*) >= 5   -- only meaningful pairs
ORDER BY times_bought_together DESC
LIMIT 50;

-- ================================================================
-- SECTION I: A/B EXPERIMENT RESULTS
-- ================================================================

-- I1. CONVERSION RATE BY VARIANT
CREATE OR REPLACE VIEW vw_i1_conversion_rate_by_variant AS
SELECT
    variant,
    COUNT(*) AS total_customers,
    SUM(converted) AS conversions,
    ROUND(100.0 * SUM(converted) / COUNT(*), 2) AS conversion_rate_pct,
    ROUND(SUM(revenue), 2) AS total_revenue,
    ROUND(AVG(revenue), 2) AS avg_revenue_per_customer
FROM experiments
GROUP BY variant
ORDER BY variant;

-- I2. UPLIFT CALCULATION (treatment vs control)
CREATE OR REPLACE VIEW vw_i2_uplift_calculation AS
WITH variant_stats AS (
    SELECT
        variant,
        COUNT(*) AS total_customers,
        SUM(converted) AS conversions,
        (100.0 * SUM(converted) / COUNT(*)) AS conversion_rate_pct,
        SUM(revenue) AS total_revenue
    FROM experiments
    GROUP BY variant
)
SELECT
    c.conversion_rate_pct AS control_conversion_pct,
    t.conversion_rate_pct AS treatment_conversion_pct,
    ROUND(t.conversion_rate_pct - c.conversion_rate_pct, 2) AS absolute_uplift_pct_points,
    ROUND(100.0 * (t.conversion_rate_pct - c.conversion_rate_pct) / c.conversion_rate_pct, 2) AS relative_uplift_pct,
    c.total_revenue AS control_revenue,
    t.total_revenue AS treatment_revenue,
    ROUND(t.total_revenue - c.total_revenue, 2) AS revenue_difference
FROM variant_stats c
CROSS JOIN variant_stats t
WHERE c.variant = 'control' AND t.variant = 'treatment';

-- I3. ESTIMATED ANNUALIZED BUSINESS IMPACT (if shipped to 100% of traffic)
-- Projects the uplift onto total historical completed-order customer base
-- as a rough "what if we shipped this" estimate. Treat as a directional
-- estimate, not a guarantee — real rollout should re-validate at scale.
CREATE OR REPLACE VIEW vw_i3_estimated_annualized_business_impact AS
WITH variant_stats AS (
    SELECT
        variant,
        (100.0 * SUM(converted) / COUNT(*)) AS conversion_rate_pct,
        AVG(revenue) FILTER (WHERE converted = 1) AS avg_revenue_per_conversion
    FROM experiments
    GROUP BY variant
),
uplift AS (
    SELECT
        (t.conversion_rate_pct - c.conversion_rate_pct) / 100.0 AS uplift_fraction,
        t.avg_revenue_per_conversion
    FROM variant_stats c
    CROSS JOIN variant_stats t
    WHERE c.variant = 'control' AND t.variant = 'treatment'
),
total_customer_base AS (
    SELECT COUNT(DISTINCT customer_id) AS n FROM orders WHERE order_status = 'Completed'
)
SELECT
    tcb.n AS total_customer_base,
    ROUND(u.uplift_fraction * 100, 2) AS uplift_pct_points,
    ROUND(tcb.n * u.uplift_fraction * u.avg_revenue_per_conversion, 2) AS estimated_additional_revenue
FROM uplift u
CROSS JOIN total_customer_base tcb;

-- ================================================================
-- HOW TO USE THIS FILE
-- ================================================================
-- 1. Run the main project script first (table creation + CSV import)
--    so that customers, products, orders, order_items, payments,
--    returns, marketing_campaigns, web_events, experiments all exist.
-- 2. Then run this file:
--        psql -U your_username -d your_database -f ecommerce_views.sql
-- 3. Every analysis is now a named view. Query any of them directly:
--        SELECT * FROM vw_a1_daily_revenue;
--        SELECT * FROM vw_e3_full_rfm_segmentation LIMIT 20;
-- 4. To see every view that now exists in the database:
--        SELECT table_name FROM information_schema.views
--        WHERE table_schema = 'public' AND table_name LIKE 'vw_%'
--        ORDER BY table_name;
-- ================================================================

SELECT table_name AS view_name
FROM information_schema.views
WHERE table_schema = 'public' AND table_name LIKE 'vw_%'
ORDER BY view_name;
