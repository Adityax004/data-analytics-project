# Power BI Data Model

Import CSV files from `powerbi/import_tables/`.

## Core Tables

| Power BI Table | Source File | Role |
|---|---|---|
| Dim Customers | `dim_customers.csv` | Customer demographics and geography |
| Dim Products | `dim_products.csv` | Product category, brand, cost, selling price |
| Fact Orders | `fact_orders.csv` | Order header facts |
| Fact Order Items | `fact_order_items.csv` | Transaction line facts |
| Fact Returns | `fact_returns.csv` | Return events |
| Fact Sales Lines | `fact_sales_lines.csv` | Denormalized sales line table for faster visuals |
| Dim Calendar | `dim_calendar.csv` | Date dimension |
| RFM Segments | `rfm_segments.csv` | Customer segmentation and churn indicators |
| Cohort Retention | `cohort_retention.csv` | Cohort heatmap matrix |

## Relationships

Create these relationships:

| From | To | Cardinality | Filter Direction |
|---|---|---|---|
| Dim Customers[customer_id] | Fact Orders[customer_id] | One-to-many | Single |
| Fact Orders[order_id] | Fact Order Items[order_id] | One-to-many | Single |
| Dim Products[product_id] | Fact Order Items[product_id] | One-to-many | Single |
| Fact Orders[order_id] | Fact Returns[order_id] | One-to-many | Single |
| Dim Calendar[date] | Fact Orders[order_date] | One-to-many | Single |
| Dim Customers[customer_id] | RFM Segments[customer_id] | One-to-one or one-to-many | Single |

Optional: use `Fact Sales Lines` as the main visual fact table and keep `Fact Orders`/`Fact Order Items` for drill-through validation. If using `Fact Sales Lines`, relate:

| From | To |
|---|---|
| Dim Customers[customer_id] | Fact Sales Lines[customer_id] |
| Dim Products[product_id] | Fact Sales Lines[product_id] |
| Dim Calendar[date] | Fact Sales Lines[order_date] |

## Date Table

Mark `Dim Calendar` as the date table using `Dim Calendar[date]`.

## Recommended Slicers

- Date range
- Country, state, city
- Category, sub-category, brand
- Payment method
- Order status
- Customer segment
- Churn status

