# Ecommerce Phase 2 — Analytics Views & Results

This document lists every analytical view created in PostgreSQL for this project, 
what business question it answers, and a sample of the actual output returned when the view was run 
against the loaded dataset (9 tables built from the provided CSV files: customers, products, orders, 
order_items, payments, returns, marketing_campaigns, web_events, experiments).

All views are defined in the companion file **`ecommerce_phase2_views.sql`**. 
Once that file is run, any view can be queried directly, e.g. `SELECT * FROM vw_a1_daily_revenue;`

---

## Section A: SALES ANALYTICS

### A1. DAILY REVENUE
**View name:** `vw_a1_daily_revenue`

> Business rule: only "Completed" orders count as real revenue.
> Revenue = sum of line_total, minus discount%, plus shipping.

**Query result (sample rows):**

```
order_day  | total_orders | gross_revenue | net_revenue_after_discount | units_sold 
------------+--------------+---------------+----------------------------+------------
 2023-01-13 |            1 |      45465.60 |               45465.600000 |          4
 2023-01-14 |            1 |      10137.18 |               10137.180000 |          2
 2023-01-17 |            1 |      29653.22 |               25205.237000 |          3
 2023-01-18 |            1 |      16943.01 |               16095.859500 |          3
 2023-01-19 |            1 |      35274.66 |               28219.728000 |          5
 2023-01-23 |            1 |      53321.44 |               45323.224000 |          4
(6 rows)
```

### A2. MONTHLY REVENUE
**View name:** `vw_a2_monthly_revenue`

**Query result (sample rows):**

```
order_month | total_orders | unique_customers | gross_revenue |  net_revenue   | units_sold 
-------------+--------------+------------------+---------------+----------------+------------
 2023-01-01  |           13 |               13 |     327416.13 |  301938.417000 |         34
 2023-02-01  |           31 |               29 |     703914.60 |  672523.917500 |         70
 2023-03-01  |           63 |               60 |    1267333.62 | 1194503.850500 |        136
 2023-04-01  |          112 |               97 |    2416056.38 | 2234760.622500 |        247
 2023-05-01  |          133 |              126 |    3151107.20 | 2936204.295000 |        328
 2023-06-01  |          164 |              153 |    3624715.21 | 3368275.389500 |        374
(6 rows)
```

### A3. MONTH-OVER-MONTH (MoM) GROWTH %
**View name:** `vw_a3_month_over_month`

> Uses window function LAG() to compare each month to the previous one.

**Query result (sample rows):**

```
order_month |  net_revenue   | prev_month_revenue | mom_growth_pct 
-------------+----------------+--------------------+----------------
 2023-01-01  |  301938.417000 |                    |               
 2023-02-01  |  672523.917500 |      301938.417000 |         122.74
 2023-03-01  | 1194503.850500 |      672523.917500 |          77.62
 2023-04-01  | 2234760.622500 |     1194503.850500 |          87.09
 2023-05-01  | 2936204.295000 |     2234760.622500 |          31.39
 2023-06-01  | 3368275.389500 |     2936204.295000 |          14.72
(6 rows)
```

### A4. YEAR-OVER-YEAR (YoY) GROWTH %
**View name:** `vw_a4_year_over_year`

> Compares same month across different years using LAG with offset 12.

**Query result (sample rows):**

```
order_month |  net_revenue   | same_month_last_year | yoy_growth_pct 
-------------+----------------+----------------------+----------------
 2023-01-01  |  301938.417000 |                      |               
 2023-02-01  |  672523.917500 |                      |               
 2023-03-01  | 1194503.850500 |                      |               
 2023-04-01  | 2234760.622500 |                      |               
 2023-05-01  | 2936204.295000 |                      |               
 2023-06-01  | 3368275.389500 |                      |               
(6 rows)
```

### A5. AVERAGE ORDER VALUE (AOV) — overall and monthly
**View name:** `vw_a5_average_order_value`

> AOV = net revenue / number of orders
> Exclude unit_price = 0 rows (flagged as promo/free items) from AOV calc.

**Query result (sample rows):**

```
order_month | total_orders |   aov    | total_revenue 
-------------+--------------+----------+---------------
 2023-01-01  |           13 | 23226.03 |     301938.42
 2023-02-01  |           31 | 21694.32 |     672523.92
 2023-03-01  |           63 | 18960.38 |    1194503.85
 2023-04-01  |          112 | 19953.22 |    2234760.62
 2023-05-01  |          132 | 22243.97 |    2936204.30
 2023-06-01  |          163 | 20664.27 |    3368275.39
(6 rows)
```

### A6. UNITS SOLD BY CATEGORY (with CASE for size buckets, just for variety)
**View name:** `vw_a6_units_sold_by_category`

**Query result (sample rows):**

```
category   | units_sold |   revenue    | volume_tier 
-------------+------------+--------------+-------------
 Beauty      |      11103 | 111143320.59 | High Volume
 Books       |      11131 | 102415647.53 | High Volume
 Electronics |      11118 | 117513404.10 | High Volume
 Fashion     |      11122 | 106280456.38 | High Volume
 Grocery     |      11021 | 112761541.05 | High Volume
 Home        |      11056 | 109156821.58 | High Volume
(6 rows)
```

## Section B: CUSTOMER GROWTH & BEHAVIOR

### B1. NEW CUSTOMERS PER MONTH
**View name:** `vw_b1_new_customers_per_month`

> "New" = their signup_date falls in that month.

**Query result (sample rows):**

```
signup_month | new_customers 
--------------+---------------
 2023-01-01   |           432
 2023-02-01   |           368
 2023-03-01   |           407
 2023-04-01   |           402
 2023-05-01   |           397
 2023-06-01   |           405
(6 rows)
```

### B2. NEW VS RETURNING CUSTOMERS PER MONTH (based on orders)
**View name:** `vw_b2_new_vs_returning_customers_per_month`

> A customer is "new" in a month if it's their FIRST EVER completed order month.
> Uses window function to find each customer's first order date.

**Query result (sample rows):**

```
order_month | customer_type | customers | orders 
-------------+---------------+-----------+--------
 2023-01-01  | New           |        13 |     13
 2023-02-01  | New           |        29 |     31
 2023-03-01  | New           |        57 |     60
 2023-03-01  | Returning     |         3 |      3
 2023-04-01  | New           |        84 |     97
 2023-04-01  | Returning     |        13 |     15
(6 rows)
```

### B3. REPEAT PURCHASE RATE (overall)
**View name:** `vw_b3_repeat_purchase_rate`

> % of customers who placed MORE THAN ONE completed order.

**Query result (sample rows):**

```
total_customers_with_orders | repeat_customers | repeat_purchase_rate_pct 
-----------------------------+------------------+--------------------------
                       10436 |             7210 |                    69.09
(1 row)
```

### B4. CUSTOMER PURCHASE FREQUENCY (orders per customer, distribution)
**View name:** `vw_b4_customer_purchase_frequency`

**Query result (sample rows):**

```
orders_placed | num_customers 
---------------+---------------
             1 |          3226
             2 |          2178
             3 |          1497
             4 |          1087
             5 |           748
             6 |           526
(6 rows)
```

### B5. CUSTOMER LIFETIME (days between first and last order)
**View name:** `vw_b5_customer_lifetime`

**Query result (sample rows):**

```
customer_id | first_order | last_order | customer_lifetime_days | total_orders 
-------------+-------------+------------+------------------------+--------------
 C100000     | 2024-03-23  | 2025-04-19 |                    392 |            3
 C100002     | 2024-09-03  | 2024-10-15 |                     42 |            2
 C100006     | 2023-05-25  | 2025-06-02 |                    739 |            2
 C100007     | 2024-06-24  | 2025-12-08 |                    532 |            2
 C100010     | 2024-11-30  | 2025-06-12 |                    194 |            2
 C100011     | 2025-05-16  | 2025-12-07 |                    205 |           13
(6 rows)
```

### B6. AVERAGE CUSTOMER LIFETIME (single summary number)
**View name:** `vw_b6_average_customer_lifetime`

**Query result (sample rows):**

```
avg_customer_lifetime_days | avg_customer_lifetime_months 
----------------------------+------------------------------
                      303.3 |                         10.1
(1 row)
```

## Section F: MARKETING: CAC, CLV & CHANNEL PERFORMANCE

### F1. CAC PER CHANNEL
**View name:** `vw_f1_cac_per_channel`

> CAC = total spend on a channel / number of NEW customers acquired via that channel

**Query result (sample rows):**

```
channel     | total_spend | new_customers |   cac   
----------------+-------------+---------------+---------
 Affiliate      |  5643688.65 |          1220 | 4625.97
 Direct         |   191173.23 |           765 |  249.90
 Email          |  8281201.36 |          1475 | 5614.37
 Google Ads     | 10528604.58 |          3332 | 3159.85
 Meta Ads       |  8519537.24 |          3023 | 2818.24
 Organic Search |   369960.59 |          2667 |  138.72
(6 rows)
```

### F2. CLV PER CUSTOMER (simple historical CLV = total net spend to date)
**View name:** `vw_f2_clv_per_customer`

**Query result (sample rows):**

```
customer_id |     clv      | total_orders | first_order | last_order | avg_order_value 
-------------+--------------+--------------+-------------+------------+-----------------
 C100000     | 63278.090000 |            3 | 2024-03-23  | 2025-04-19 |        21092.70
 C100002     | 60762.612500 |            2 | 2024-09-03  | 2024-10-15 |        30381.31
 C100005     | 16546.360000 |            1 | 2025-06-06  | 2025-06-06 |        16546.36
 C100006     | 51078.005000 |            2 | 2023-05-25  | 2025-06-02 |        25539.00
 C100007     | 43114.613000 |            2 | 2024-06-24  | 2025-12-08 |        21557.31
 C100010     | 24133.830000 |            2 | 2024-11-30  | 2025-06-12 |        12066.92
(6 rows)
```

### F3. AVERAGE CLV PER ACQUISITION CHANNEL (+ CLV:CAC RATIO)
**View name:** `vw_f3_average_clv_per_acquisition_channel`

> This is a KEY business insight query: which channel brings customers
> who are both cheap to acquire AND spend a lot over their lifetime?

**Query result (sample rows):**

```
channel     | avg_clv  |   cac   | clv_to_cac_ratio 
----------------+----------+---------+------------------
 Affiliate      | 65785.32 | 4625.97 |            14.22
 Direct         | 68780.19 |  249.90 |           275.23
 Email          | 66154.44 | 5614.37 |            11.78
 Google Ads     | 69020.89 | 3159.85 |            21.84
 Meta Ads       | 66679.98 | 2818.24 |            23.66
 Organic Search | 71328.50 |  138.72 |           514.19
(6 rows)
```

### F4. MARKETING CHANNEL PERFORMANCE (CTR, CPC, CVR, ROAS)
**View name:** `vw_f4_marketing_channel_performance`

**Query result (sample rows):**

```
channel     | total_spend | total_impressions | total_clicks | total_conversions | ctr_pct |  cpc  | conversion_rate_pct | attributed_revenue |  roas  
----------------+-------------+-------------------+--------------+-------------------+---------+-------+---------------------+--------------------+--------
 Affiliate      |  5643688.65 |           9341051 |       235257 |              9808 |   2.519 | 23.99 |                4.17 |    57233232.713500 |  10.14
 Direct         |   191173.23 |           4779052 |       119201 |              4889 |   2.494 |  1.60 |                4.10 |    36659839.933000 | 191.76
 Email          |  8281201.36 |          13917221 |       347387 |             14155 |   2.496 | 23.84 |                4.07 |    68469850.268500 |   8.27
 Google Ads     | 10528604.58 |          18103132 |       448526 |             18825 |   2.478 | 23.47 |                4.20 |   160611604.721000 |  15.25
 Meta Ads       |  8519537.24 |          14243848 |       351226 |             14966 |   2.466 | 24.26 |                4.26 |   140494724.883000 |  16.49
 Organic Search |   369960.59 |           9604088 |       235384 |              9669 |   2.451 |  1.57 |                4.11 |   131957731.981500 | 356.68
(6 rows)
```

## Section C: WEB FUNNEL & CONVERSION

### C1. OVERALL FUNNEL — sessions reaching each stage
**View name:** `vw_c1_overall_funnel_sessions_reaching_each_stage`

**Query result (sample rows):**

```
step1_page_view | step2_product_view | step3_add_to_cart | step4_checkout | step5_purchase 
-----------------+--------------------+-------------------+----------------+----------------
          123738 |              80272 |             43187 |          20878 |           8640
(1 row)
```

### C2. CONVERSION RATE AT EACH FUNNEL STEP (step-to-step %)
**View name:** `vw_c2_conversion_rate_at_each_funnel_step`

**Query result (sample rows):**

```
n_page_view | n_product_view | n_add_to_cart | n_checkout | n_purchase | pv_to_productview_pct | productview_to_cart_pct | cart_to_checkout_pct | checkout_to_purchase_pct | overall_conversion_pct 
-------------+----------------+---------------+------------+------------+-----------------------+-------------------------+----------------------+--------------------------+------------------------
      123738 |          80272 |         43187 |      20878 |       8640 |                 64.87 |                   53.80 |                48.34 |                    41.38 |                   6.98
(1 row)
```

### C3. DEVICE-WISE CONVERSION RATE (page_view -> purchase)
**View name:** `vw_c3_device_wise_conversion_rate`

**Query result (sample rows):**

```
device  | sessions | purchases | conversion_pct 
---------+----------+-----------+----------------
 Desktop |    40970 |      2961 |           7.23
 Mobile  |    68346 |      4738 |           6.93
 Tablet  |     8318 |       550 |           6.61
 Unknown |     6104 |       391 |           6.41
(4 rows)
```

### C4. CHANNEL-WISE CONVERSION RATE (acquisition_channel -> purchase)
**View name:** `vw_c4_channel_wise_conversion_rate`

**Query result (sample rows):**

```
acquisition_channel | sessions | purchases | conversion_pct 
---------------------+----------+-----------+----------------
 Affiliate           |    10223 |       707 |           6.92
 Direct              |     6235 |       402 |           6.45
 Email               |    12237 |       824 |           6.73
 Google Ads          |    27297 |      1894 |           6.94
 Meta Ads            |    24922 |      1799 |           7.22
 Organic Search      |    21791 |      1527 |           7.01
(6 rows)
```

### C5. BIGGEST DROP-OFF STAGE (which step loses the most sessions)
**View name:** `vw_c5_biggest_drop_off_stage`

**Query result (sample rows):**

```
stage            | sessions_lost 
-----------------------------+---------------
 add_to_cart -> checkout     |         22309
 checkout -> purchase        |         12238
 page_view -> product_view   |         43466
 product_view -> add_to_cart |         37085
(4 rows)
```

## Section D: COHORT RETENTION

### D1. COHORT RETENTION TABLE (signup month x months-since-signup)
**View name:** `vw_d1_cohort_retention_table`

**Query result (sample rows):**

```
cohort_month | cohort_size | month_number | active_customers | retention_pct 
--------------+-------------+--------------+------------------+---------------
 2023-01-01   |         432 |            0 |               13 |          3.01
 2023-01-01   |         432 |            1 |               16 |          3.70
 2023-01-01   |         432 |            2 |               27 |          6.25
 2023-01-01   |         432 |            3 |               23 |          5.32
 2023-01-01   |         432 |            4 |               25 |          5.79
 2023-01-01   |         432 |            5 |               28 |          6.48
(6 rows)
```

### D2. RETENTION BY ACQUISITION CHANNEL (which channel retains best)
**View name:** `vw_d2_retention_by_acquisition_channel`

**Query result (sample rows):**

```
acquisition_channel | total_customers | active_month_3 | retention_month3_pct 
---------------------+-----------------+----------------+----------------------
 Affiliate           |            1220 |            152 |                12.46
 Direct              |             765 |             97 |                12.68
 Email               |            1475 |            186 |                12.61
 Google Ads          |            3332 |            420 |                12.61
 Meta Ads            |            3023 |            385 |                12.74
 Organic Search      |            2667 |            326 |                12.22
(6 rows)
```

## Section E: RFM CUSTOMER SEGMENTATION

### E1. RAW RFM VALUES PER CUSTOMER
**View name:** `vw_e1_raw_rfm_values_per_customer`

**Query result (sample rows):**

```
customer_id | recency_days | frequency |   monetary   
-------------+--------------+-----------+--------------
 C100000     |          478 |         3 | 63278.090000
 C100002     |          664 |         2 | 60762.612500
 C100005     |          430 |         1 | 16546.360000
 C100006     |          434 |         2 | 51078.005000
 C100007     |          245 |         2 | 43114.613000
 C100010     |          424 |         2 | 24133.830000
(6 rows)
```

### E2. RFM SCORES (1-5 scale) using NTILE
**View name:** `vw_e2_rfm_scores`

> Note: recency is scored in REVERSE (lower days = higher score = 5)

**Query result (sample rows):**

```
customer_id | recency_days | frequency |   monetary   | r_score | f_score | m_score | rfm_total_score 
-------------+--------------+-----------+--------------+---------+---------+---------+-----------------
 C100000     |          478 |         3 | 63278.090000 |       2 |       4 |       4 |              10
 C100002     |          664 |         2 | 60762.612500 |       1 |       3 |       3 |               7
 C100005     |          430 |         1 | 16546.360000 |       2 |       1 |       1 |               4
 C100006     |          434 |         2 | 51078.005000 |       2 |       3 |       3 |               8
 C100007     |          245 |         2 | 43114.613000 |       4 |       3 |       3 |              10
 C100010     |          424 |         2 | 24133.830000 |       2 |       2 |       2 |               6
(6 rows)
```

### E3. FULL RFM SEGMENTATION (business-labeled segments)
**View name:** `vw_e3_full_rfm_segmentation`

> This is the main output table for BI / customer strategy.

**Query result (sample rows):**

```
customer_id | recency_days | frequency | monetary | r_score | f_score | m_score |   rfm_segment    
-------------+--------------+-----------+----------+---------+---------+---------+------------------
 C100000     |          478 |         3 | 63278.09 |       2 |       4 |       4 | Cannot Lose Them
 C100002     |          664 |         2 | 60762.61 |       1 |       3 |       3 | At Risk
 C100005     |          430 |         1 | 16546.36 |       2 |       1 |       1 | Lost
 C100006     |          434 |         2 | 51078.01 |       2 |       3 |       3 | At Risk
 C100007     |          245 |         2 | 43114.61 |       4 |       3 |       3 | Loyal Customers
 C100010     |          424 |         2 | 24133.83 |       2 |       2 |       2 | Lost
(6 rows)
```

### E4. SEGMENT SUMMARY (count + avg spend per segment)
**View name:** `vw_e4_segment_summary`

**Query result (sample rows):**

```
rfm_segment    | num_customers | avg_monetary | total_monetary 
------------------+---------------+--------------+----------------
 At Risk          |          1067 |     54116.66 |    57742474.61
 Cannot Lose Them |           682 |    114077.18 |    77800635.56
 Champions        |          2024 |    146948.34 |   297423438.42
 Hibernating      |           916 |     29043.50 |    26603842.87
 Lost             |          2130 |     16826.91 |    35841314.64
 Loyal Customers  |          2488 |     77234.72 |   192159977.45
(6 rows)
```

## Section G: CHURN ANALYSIS

### G1. MEDIAN REPURCHASE INTERVAL (use this to justify the 90-day rule)
**View name:** `vw_g1_median_repurchase_interval`

> Time gap between consecutive orders of the same customer, using LAG().

**Query result (sample rows):**

```
median_repurchase_days | avg_repurchase_days 
------------------------+---------------------
                   47.8 |                91.8
(1 row)
```

### G2. CHURN STATUS PER CUSTOMER
**View name:** `vw_g2_churn_status_per_customer`

**Query result (sample rows):**

```
customer_id | last_order_date | total_orders | days_since_last_order | churn_status 
-------------+-----------------+--------------+-----------------------+--------------
 C100000     | 2025-04-19      |            3 |                   478 | Churned
 C100002     | 2024-10-15      |            2 |                   664 | Churned
 C100005     | 2025-06-06      |            1 |                   430 | Churned
 C100006     | 2025-06-02      |            2 |                   434 | Churned
 C100007     | 2025-12-08      |            2 |                   245 | Churned
 C100010     | 2025-06-12      |            2 |                   424 | Churned
(6 rows)
```

### G3. OVERALL CHURN RATE
**View name:** `vw_g3_overall_churn_rate`

**Query result (sample rows):**

```
total_customers | churned_customers | churn_rate_pct 
-----------------+-------------------+----------------
           10436 |              5384 |          51.59
(1 row)
```

### G4. CHURN RATE BY CUSTOMER SEGMENT (self-reported segment field)
**View name:** `vw_g4_churn_rate_by_customer_segment`

**Query result (sample rows):**

```
customer_segment | total_customers | churned_customers | churn_rate_pct 
------------------+-----------------+-------------------+----------------
 Budget           |            2334 |              1192 |          51.07
 New              |            2405 |              1278 |          53.14
 Regular          |            2338 |              1200 |          51.33
 Unclassified     |            1048 |               534 |          50.95
 VIP              |            2311 |              1180 |          51.06
(5 rows)
```

### G5. HIGH-VALUE CHURNED CUSTOMERS (priority list for retention team)
**View name:** `vw_g5_high_value_churned_customers`

**Query result (sample rows):**

```
customer_id |  total_spend  | total_orders | last_order_date | days_since_last_order 
-------------+---------------+--------------+-----------------+-----------------------
 C100029     | 356861.953500 |           13 | 2025-12-02      |                   251
 C100815     | 326254.969000 |           11 | 2025-12-16      |                   237
 C100873     | 327421.539500 |           12 | 2025-11-21      |                   262
 C100925     | 362840.940000 |           14 | 2025-12-26      |                   227
 C101164     | 349171.381000 |           17 | 2025-12-17      |                   236
 C101278     | 315707.555000 |           10 | 2025-12-20      |                   233
(6 rows)
```

## Section H: PRODUCT PERFORMANCE & BASKET ANALYSIS

### H1. PRODUCT PERFORMANCE (revenue, margin, units, return rate)
**View name:** `vw_h1_product_performance`

**Query result (sample rows):**

```
product_id |      product_name      |  category   | units_sold |  revenue   | gross_margin | margin_pct | return_count | return_rate_pct 
------------+------------------------+-------------+------------+------------+--------------+------------+--------------+-----------------
 P2001      | Orenda Mobiles Classic | Electronics |        111 | 1353722.33 |    289203.47 |      21.36 |            8 |            7.21
 P2002      | Nimbus Headphones      | Electronics |         97 | 1653881.73 |    250364.48 |      15.14 |            5 |            5.15
 P2003      | Petal Laptops Air      | Electronics |        121 | 1453043.75 |    383591.30 |      26.40 |            5 |            4.13
 P2004      | Solace Headphones Pro  | Electronics |         99 | 1523497.94 |    296671.13 |      19.47 |           10 |           10.10
 P2005      | Orenda Mobiles Classic | Electronics |        108 | 1340437.84 |    225934.00 |      16.86 |            7 |            6.48
 P2006      | Trekko Mobiles Classic | Electronics |         95 |  896460.81 |    273225.66 |      30.48 |            9 |            9.47
(6 rows)
```

### H2. PRODUCT CLASSIFICATION (Stars / Problem / Hidden Gems / Dead Stock)
**View name:** `vw_h2_product_classification`

> Uses median sales & margin as the split point (via CTE + window function).

**Query result (sample rows):**

```
product_id |      product_name      |  category   | units_sold | gross_margin | product_classification 
------------+------------------------+-------------+------------+--------------+------------------------
 P2001      | Orenda Mobiles Classic | Electronics |        111 |    289203.47 | Star
 P2002      | Nimbus Headphones      | Electronics |         97 |    250364.48 | Star
 P2003      | Petal Laptops Air      | Electronics |        121 |    383591.30 | Star
 P2004      | Solace Headphones Pro  | Electronics |         99 |    296671.13 | Star
 P2005      | Orenda Mobiles Classic | Electronics |        108 |    225934.00 | Star
 P2006      | Trekko Mobiles Classic | Electronics |         95 |    273225.66 | Hidden Gem
(6 rows)
```

### H3. CATEGORY-LEVEL SUMMARY
**View name:** `vw_h3_category_level_summary`

**Query result (sample rows):**

```
category   | num_products | units_sold |   revenue    | avg_unit_price 
-------------+--------------+------------+--------------+----------------
 Beauty      |          114 |      11103 | 111143320.59 |        9997.88
 Books       |          114 |      11131 | 102415647.53 |        9204.83
 Electronics |          114 |      11118 | 117513404.10 |       10553.94
 Fashion     |          114 |      11122 | 106280456.38 |        9524.87
 Grocery     |          114 |      11021 | 112761541.05 |       10227.42
 Home        |          114 |      11056 | 109156821.58 |        9890.37
(6 rows)
```

### H4. RETURN REASONS BREAKDOWN
**View name:** `vw_h4_return_reasons_breakdown`

**Query result (sample rows):**

```
return_reason         | num_returns | total_refunded 
------------------------------+-------------+----------------
 Better price found elsewhere |         645 |     6644159.15
 Changed my mind              |         605 |     6618063.23
 Damaged in transit           |         604 |     6526379.04
 Defective product            |         585 |     5825329.96
 Late delivery                |         606 |     6249302.98
 Not Specified                |         621 |     6086190.14
(6 rows)
```

### H5. BASKET ANALYSIS — products frequently bought together
**View name:** `vw_h5_basket_analysis_products_frequently_bought_together`

> Self-join order_items on order_id to find product pairs in the same order.

**Query result (sample rows):**

```
product_a_name    |     product_b_name      | times_bought_together 
----------------------+-------------------------+-----------------------
 Bexley Footwear Pro  | Urbana Non-Fiction Air  |                     5
 Bexley Footwear Pro  | Zylo Snacks Air         |                     5
 Bexley Footwear Pro  | Marvo Furniture Classic |                     5
 Forgeon Footwear Pro | Bexley Footwear Pro     |                     5
 Lumex Makeup Pro     | Trekko Academic Classic |                     5
 Nordik Laptops       | Bexley Footwear Pro     |                     5
(6 rows)
```

## Section I: A/B EXPERIMENT RESULTS

### I1. CONVERSION RATE BY VARIANT
**View name:** `vw_i1_conversion_rate_by_variant`

**Query result (sample rows):**

```
variant  | total_customers | conversions | conversion_rate_pct | total_revenue | avg_revenue_per_customer 
-----------+-----------------+-------------+---------------------+---------------+--------------------------
 control   |            3981 |         467 |               11.73 |    1581271.17 |                   397.20
 treatment |            4019 |         563 |               14.01 |    1889530.55 |                   470.15
(2 rows)
```

### I2. UPLIFT CALCULATION (treatment vs control)
**View name:** `vw_i2_uplift_calculation`

**Query result (sample rows):**

```
control_conversion_pct | treatment_conversion_pct | absolute_uplift_pct_points | relative_uplift_pct | control_revenue | treatment_revenue | revenue_difference 
------------------------+--------------------------+----------------------------+---------------------+-----------------+-------------------+--------------------
    11.7307209243908566 |      14.0084598158745957 |                       2.28 |               19.42 |      1581271.17 |        1889530.55 |          308259.38
(1 row)
```

### I3. ESTIMATED ANNUALIZED BUSINESS IMPACT (if shipped to 100% of traffic)
**View name:** `vw_i3_estimated_annualized_business_impact`

> Projects the uplift onto total historical completed-order customer base
> as a rough "what if we shipped this" estimate. Treat as a directional
> estimate, not a guarantee — real rollout should re-validate at scale.

**Query result (sample rows):**

```
total_customer_base | uplift_pct_points | estimated_additional_revenue 
---------------------+-------------------+------------------------------
               10436 |              2.28 |                    797780.71
(1 row)
```
