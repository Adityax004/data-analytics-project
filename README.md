# E-commerce Customer Analytics & Revenue Optimization

This project simulates a complete analytics workflow for an e-commerce business using SQL, Python/Pandas, and Power BI-ready assets. It generates a realistic relational dataset, cleans and validates it, loads it into a normalized database, runs analytical SQL, builds RFM and cohort models in Python, and exports curated tables for a multi-page Power BI dashboard.

## Business Objective

Analyze large-scale e-commerce transaction data to uncover customer purchasing behavior, revenue trends, retention patterns, product performance, regional performance, and revenue optimization opportunities.

Stakeholders can use the outputs to answer questions such as:

- Which customer segments generate the most revenue?
- Which customers are likely to churn?
- Which categories and products drive profit?
- Which regions and months show the strongest growth?
- How do discounts affect revenue and margins?
- How does repeat purchase behavior change over time?

## Tech Stack

- SQL: PostgreSQL scripts plus a runnable local SQLite database
- Python: Pandas, NumPy, OpenPyXL
- Notebook: Jupyter `.ipynb`
- BI: Power BI-ready CSV model, DAX measures, dashboard build guide, and theme

## Project Structure

```text
.
├── data/
│   ├── raw/                  # generated source data with intentional quality issues
│   └── processed/            # cleaned relational tables
├── database/
│   └── ecommerce_analytics.sqlite
├── docs/
│   ├── data_dictionary.md
│   └── project_architecture.md
├── notebooks/
│   └── ecommerce_customer_analytics.ipynb
├── outputs/
│   ├── sql/                  # query result CSVs
│   ├── tables/               # Pandas analytics outputs
│   ├── figures/              # SVG chart assets
│   └── report/               # local HTML analytics report
├── powerbi/
│   ├── import_tables/        # tables to import into Power BI
│   ├── DAX_Measures.md
│   ├── Dashboard_Build_Guide.md
│   ├── Data_Model.md
│   └── powerbi_theme.json
├── sql/
│   ├── 01_schema_postgresql.sql
│   ├── 02_data_cleaning_postgresql.sql
│   ├── 03_analysis_queries_postgresql.sql
│   ├── 04_views_postgresql.sql
│   ├── sqlite_schema.sql
│   └── sqlite_views.sql
└── src/
    ├── generate_data.py
    ├── clean_data.py
    ├── build_database.py
    ├── run_sql_analysis.py
    ├── python_analysis.py
    ├── create_notebook.py
    └── run_pipeline.py
```

## Run the Project

Use a Python environment with Pandas and NumPy installed. In this Codex workspace, the bundled runtime was used to run the pipeline.

```powershell
python src/run_pipeline.py
```

If your default Python does not include the dependencies:

```powershell
pip install -r requirements.txt
python src/run_pipeline.py
```

## Generated Dataset

The pipeline creates a normalized e-commerce dataset with:

- Customers: customer demographics, geography, signup date
- Orders: order status, payment method, order and shipment dates, total amount
- Order Items: product-level line items, quantities, prices, discounts
- Products: category, sub-category, brand, cost and selling price
- Returns: returned order reasons and return dates

The default generation creates 50,000 customers, 800 products, more than 190,000 orders, and more than 400,000 order-item transaction records.

## Key Deliverables

1. SQL scripts for schema creation, data quality checks, views, CTEs, joins, window functions, ranking, date analysis, revenue analysis, customer behavior, product performance, and geography.
2. Python notebook for data cleaning review, EDA, RFM segmentation, cohort retention, churn indicators, and visualizations.
3. Power BI-ready import tables, DAX measures, model guide, dashboard build guide, and theme JSON.
4. Documentation covering architecture, data dictionary, business findings, and recommendations.

## Main Outputs

- `database/ecommerce_analytics.sqlite`
- `outputs/sql/*.csv`
- `outputs/tables/analytics_export.xlsx`
- `outputs/tables/business_insights.json`
- `outputs/report/ecommerce_analytics_report.html`
- `powerbi/import_tables/*.csv`

## Recommended Power BI Pages

- Executive Overview
- Sales Dashboard
- Customer Analytics
- Cohort Retention
- Product Performance
