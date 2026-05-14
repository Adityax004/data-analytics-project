# Power BI Dashboard Build Guide

## Page 1: Executive Overview

Purpose: give leadership a fast view of business health.

Visuals:

- KPI cards: Total Revenue, Total Orders, Total Customers, Average Order Value, Repeat Customer Rate, Return Rate
- Line chart: Total Revenue by Month
- Bar chart: Revenue by Category
- Map or filled map: Revenue by Country/State/City
- Waterfall or column chart: Gross Profit by Category
- Slicers: Date, Country, Category, Order Status

Interactions:

- Enable drill-down from country to state to city.
- Use tooltip pages for AOV, gross margin, and return rate.

## Page 2: Sales Dashboard

Purpose: monitor sales trends, growth, and performance drivers.

Visuals:

- Monthly Revenue and Running Revenue combo chart
- MoM and YoY Growth cards
- Revenue by Payment Method
- Revenue by Category/Sub-category matrix
- Discount Amount vs Revenue scatter chart
- Top 10 Products by Revenue

Recommended measures:

- Total Revenue
- Average Order Value
- MoM Revenue Growth %
- YoY Revenue Growth %
- Running Revenue
- Discount Amount

## Page 3: Customer Analytics

Purpose: understand customer value, retention, and churn risk.

Visuals:

- RFM Segment revenue bar chart
- Customer count by RFM Segment
- Churn Status donut or stacked bar
- At Risk Revenue KPI
- Top Customers table with Customer Revenue Rank
- Geographic repeat customer rate matrix

Slicers:

- Customer Segment
- Churn Status
- Country/State/City
- Signup Date

## Page 4: Cohort Dashboard

Purpose: measure acquisition cohort quality and repeat purchase behavior.

Visuals:

- Cohort retention matrix from `cohort_retention.csv`
- Monthly repeat customers trend
- Month-one retention KPI
- Segment filter to compare retention by customer segment

Build note:

Power BI matrices prefer long-form cohort data. The exported `cohort_retention.csv` is a heatmap-ready wide table. For more flexible visuals, import `cohort_counts.csv` from `outputs/tables/` and calculate retention by dividing each cohort month by month-zero customers.

## Page 5: Product Performance

Purpose: identify products and categories that drive or dilute profit.

Visuals:

- Top 10 Products by Revenue
- Bottom 10 Products by Gross Profit
- Revenue and Profit Margin by Category
- Units Sold by Sub-category
- Discount Bucket vs Gross Profit
- Product table with category rank and margin

Recommended conditional formatting:

- Profit Margin %: red below 10%, amber 10-25%, green above 25%
- Product Revenue Rank: top 10 highlighted
- Churn Score: red above 70

