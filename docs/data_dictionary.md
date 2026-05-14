# Data Dictionary

## customers

| Field | Description |
|---|---|
| customer_id | Unique customer key |
| customer_name | Customer full name |
| gender | Customer gender |
| age | Customer age |
| city | Customer city |
| state | Customer state/province |
| country | Customer country |
| signup_date | Date the customer signed up |

## orders

| Field | Description |
|---|---|
| order_id | Unique order key |
| customer_id | Foreign key to customers |
| order_date | Date the order was placed |
| shipment_date | Date the order shipped; blank for cancelled orders |
| payment_method | Payment method used |
| order_status | Completed, Shipped, Returned, or Cancelled |
| total_amount | Recalculated order value after item discounts |

## order_items

| Field | Description |
|---|---|
| order_item_id | Unique order line key |
| order_id | Foreign key to orders |
| product_id | Foreign key to products |
| quantity | Units purchased |
| price_per_unit | Sale price before discount |
| discount | Discount rate as a decimal, e.g. 0.10 means 10% |

## products

| Field | Description |
|---|---|
| product_id | Unique product key |
| product_name | Product display name |
| category | Product category |
| sub_category | Product sub-category |
| brand | Product brand |
| cost_price | Unit cost |
| selling_price | Standard listed selling price |

## returns

| Field | Description |
|---|---|
| return_id | Unique return key |
| order_id | Foreign key to returned order |
| return_reason | Reason for return |
| return_date | Date return was recorded |

## Analytical Tables

| Table | Description |
|---|---|
| executive_kpis | Revenue, orders, AOV, customers, repeat rate, return rate |
| monthly_revenue | Monthly revenue, orders, customers, MoM growth, YoY growth, running revenue |
| product_performance | Revenue, units, profit, margin, category rank |
| category_performance | Category/sub-category revenue and margin |
| rfm_customer_segments | Customer-level RFM scores, segment, churn score |
| rfm_segment_summary | Segment-level revenue and retention targeting summary |
| cohort_retention | Monthly retention matrix by acquisition cohort |
| geographic_performance | Revenue, AOV, and repeat rate by city/state/country |
| discount_analysis | Revenue and margin by discount bucket |
| market_basket_top_pairs | Frequently co-purchased product pairs |
| sales_forecast | Six-month simple seasonal revenue forecast |

