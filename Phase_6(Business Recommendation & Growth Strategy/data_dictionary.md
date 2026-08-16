# Data Dictionary — AI-Powered E-commerce Intelligence Platform

Generated synthetic dataset simulating 3 years (2023–2025) of e-commerce activity.
All tables below reflect the **cleaned** schema (`data/processed/`).

---

## customers (15,000 rows)
| Column | Type | Notes |
|---|---|---|
| customer_id | VARCHAR PK | e.g. C100001 |
| customer_name | VARCHAR | |
| signup_date | DATE | |
| country | VARCHAR | standardized casing |
| city | VARCHAR | missing → `'Unknown'` |
| device | VARCHAR | Mobile/Desktop/Tablet/Unknown |
| acquisition_channel | VARCHAR | Google Ads, Meta Ads, YouTube Ads, Email, Organic Search, Affiliate, Referral, Direct |
| customer_segment | VARCHAR | New/Regular/VIP/Budget/Unclassified (self-reported label, **not** the RFM segment you'll compute later) |

## products (798 rows)
| Column | Type | Notes |
|---|---|---|
| product_id | VARCHAR PK | e.g. P2001 |
| product_name | VARCHAR | |
| category | VARCHAR | Electronics, Fashion, Home, Beauty, Sports, Books, Grocery |
| subcategory | VARCHAR | |
| brand | VARCHAR | |
| cost | NUMERIC | product cost; **~4% originally missing**, imputed as category-median — see `cost_is_estimated` |
| selling_price | NUMERIC | catalog price |
| cost_is_estimated | BOOLEAN | TRUE = cost was imputed, treat margin as approximate |
| price_is_invalid | BOOLEAN | TRUE = selling_price was ≤0 in source data (data error); exclude from price/margin analysis |

## orders (59,985 rows)
| Column | Type | Notes |
|---|---|---|
| order_id | VARCHAR PK | |
| customer_id | VARCHAR FK → customers | |
| order_date | TIMESTAMP | |
| order_status | VARCHAR | Completed / Cancelled / Returned / Pending |
| payment_method | VARCHAR | Credit Card, Debit Card, UPI, Net Banking, COD, Wallet |
| discount | NUMERIC | as a fraction, e.g. 0.10 = 10% off |
| shipping_cost | NUMERIC | |

## order_items (119,091 rows)
| Column | Type | Notes |
|---|---|---|
| order_item_id | VARCHAR PK | |
| order_id | VARCHAR FK → orders | |
| product_id | VARCHAR FK → products | |
| quantity | INTEGER | always > 0 after cleaning |
| unit_price | NUMERIC | actual price paid (may differ slightly from catalog `selling_price` due to promo pricing); **~0.7% are 0** (flagged as possible free/promo items — exclude from AOV calcs) |
| line_total | NUMERIC | = quantity × unit_price (computed at load time) |

## web_events (292,069 rows)
| Column | Type | Notes |
|---|---|---|
| event_id | VARCHAR PK | |
| customer_id | VARCHAR FK → customers | |
| event_timestamp | TIMESTAMP | |
| event_name | VARCHAR | page_view, product_view, add_to_cart, checkout, purchase, login, wishlist |
| session_id | VARCHAR | ~1% were missing → filled `'UNKNOWN_SESSION'`; **exclude these from funnel/session analysis** |
| product_id | VARCHAR FK → products | NULL for login/page_view-only events |

## marketing_campaigns (13,834 rows)
| Column | Type | Notes |
|---|---|---|
| date | DATE | |
| channel | VARCHAR | |
| campaign | VARCHAR | |
| spend | NUMERIC | missing → filled 0 |
| impressions | INTEGER | |
| clicks | INTEGER | always ≤ impressions after cleaning |
| conversions | INTEGER | always ≤ clicks after cleaning |

## payments (34,357 rows)
| Column | Type | Notes |
|---|---|---|
| payment_id | VARCHAR PK | |
| order_id | VARCHAR FK → orders | only exists for "Completed" orders |
| amount | NUMERIC | gross − discount + shipping |
| payment_status | VARCHAR | Success/Failed/Refunded |
| payment_date | TIMESTAMP | |

## returns (5,454 rows)
| Column | Type | Notes |
|---|---|---|
| return_id | VARCHAR PK | |
| order_id | VARCHAR FK → orders | |
| customer_id | VARCHAR FK → customers | |
| product_id | VARCHAR FK → products | |
| return_date | DATE | |
| return_reason | VARCHAR | missing → filled `'Not Specified'` |
| refund_amount | NUMERIC | |

## experiments (8,000 rows)
Simulated **checkout redesign A/B test**, June 2025.
| Column | Type | Notes |
|---|---|---|
| experiment_id | VARCHAR | constant: `EXP001_checkout_redesign` |
| customer_id | VARCHAR FK → customers | |
| variant | VARCHAR | control / treatment |
| experiment_date | DATE | |
| converted | INTEGER | 0/1 |
| revenue | NUMERIC | 0 if not converted |

**Ground truth built into the simulation** (for your own validation later — don't reveal this in your portfolio writeup, discover it via the analysis): control ≈ 11.8% conversion, treatment ≈ 14.1% conversion (~2.3pp uplift). Your A/B test analysis in Phase 6 should independently detect this.

---

## Known data-quality issues (by design) and how they were resolved
See `logs/data_quality_report.txt` for exact counts from the actual run. Summary of business rules applied:

| Issue | Rule Applied |
|---|---|
| Duplicate customer/order rows | Dropped, kept first occurrence |
| Orphan orders (customer_id not in customers) | Removed — can't attribute to any customer |
| Missing city/device/segment | Filled with `'Unknown'` / `'Unclassified'` |
| Missing product cost | Imputed with category median, flagged `cost_is_estimated` |
| selling_price ≤ 0 | Flagged `price_is_invalid`, NOT dropped (keeps order history joins intact) |
| Negative/zero quantity in order_items | Dropped — data entry error |
| unit_price = 0 in order_items | Kept, flagged for exclusion from AOV/revenue-per-unit metrics |
| Missing session_id | Filled `'UNKNOWN_SESSION'`, exclude from funnel analysis |
| clicks > impressions or conversions > clicks | Dropped — tracking pipeline error |
| Missing discount/shipping_cost | Filled 0 |

These are **documented assumptions**, not silent fixes — cite them explicitly if asked in an interview.
