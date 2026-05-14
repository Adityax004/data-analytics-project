from __future__ import annotations

import json

from config import NOTEBOOK_DIR, ensure_directories


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(keepends=True)}


def build_notebook() -> dict:
    cells = [
        markdown(
            """# E-commerce Customer Analytics & Revenue Optimization

This notebook demonstrates the Python/Pandas layer of the end-to-end analytics workflow:

- Load cleaned relational tables
- Validate data quality
- Explore sales, customer, product, and geographic patterns
- Build RFM customer segmentation
- Build acquisition cohort retention matrices
- Export analysis tables for Power BI

The project pipeline also creates SQL outputs and a local HTML report. Run the notebook from the repository root after executing `python src/run_pipeline.py`."""
        ),
        code(
            """from pathlib import Path
import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTS = True
except ImportError:
    HAS_PLOTS = False

ROOT = Path.cwd()
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs" / "tables"
ANALYSIS_DATE = pd.Timestamp("2026-01-01")
VALID_STATUSES = ["Completed", "Shipped"]

pd.set_option("display.max_columns", 120)
print("Plotting libraries available:", HAS_PLOTS)"""
        ),
        markdown("## 1. Load the Relational Tables"),
        code(
            """customers = pd.read_csv(PROCESSED / "customers.csv", parse_dates=["signup_date"])
orders = pd.read_csv(PROCESSED / "orders.csv", parse_dates=["order_date", "shipment_date"])
order_items = pd.read_csv(PROCESSED / "order_items.csv")
products = pd.read_csv(PROCESSED / "products.csv")
returns = pd.read_csv(PROCESSED / "returns.csv", parse_dates=["return_date"])

for name, df in {
    "customers": customers,
    "orders": orders,
    "order_items": order_items,
    "products": products,
    "returns": returns,
}.items():
    print(f"{name:12s} {df.shape[0]:,} rows x {df.shape[1]} columns")"""
        ),
        markdown("## 2. Data Quality Checks"),
        code(
            """quality = []
primary_keys = {
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "products": "product_id",
    "returns": "return_id",
}
tables = {
    "customers": customers,
    "orders": orders,
    "order_items": order_items,
    "products": products,
    "returns": returns,
}
for name, df in tables.items():
    quality.append({
        "table": name,
        "rows": len(df),
        "duplicate_pk": df[primary_keys[name]].duplicated().sum(),
        "null_values": int(df.isna().sum().sum()),
    })
pd.DataFrame(quality)"""
        ),
        markdown("## 3. Build the Analytical Sales Fact"),
        code(
            """line_items = (
    order_items
    .merge(orders, on="order_id", how="left")
    .merge(products, on="product_id", how="left")
)
line_items["gross_line_amount"] = line_items["quantity"] * line_items["price_per_unit"]
line_items["discount_amount"] = line_items["gross_line_amount"] * line_items["discount"]
line_items["net_line_amount"] = line_items["gross_line_amount"] - line_items["discount_amount"]
line_items["gross_profit"] = line_items["quantity"] * (
    line_items["price_per_unit"] * (1 - line_items["discount"]) - line_items["cost_price"]
)
line_items["order_month"] = line_items["order_date"].dt.to_period("M").dt.to_timestamp()

valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
valid_lines = line_items[line_items["order_status"].isin(VALID_STATUSES)].copy()
line_items.head()"""
        ),
        markdown("## 4. Executive KPIs"),
        code(
            """total_revenue = valid_orders["total_amount"].sum()
total_orders = valid_orders["order_id"].nunique()
total_customers = customers["customer_id"].nunique()
purchase_customers = valid_orders["customer_id"].nunique()
aov = total_revenue / total_orders
repeat_rate = (valid_orders.groupby("customer_id")["order_id"].nunique().gt(1).mean()) * 100
return_rate = returns["order_id"].nunique() / orders["order_id"].nunique() * 100

pd.DataFrame([{
    "total_revenue": total_revenue,
    "total_orders": total_orders,
    "total_customers": total_customers,
    "purchasing_customers": purchase_customers,
    "average_order_value": aov,
    "repeat_customer_rate_pct": repeat_rate,
    "return_rate_pct": return_rate,
}]).round(2)"""
        ),
        markdown("## 5. Revenue Trends"),
        code(
            """monthly = (
    valid_orders.assign(order_month=valid_orders["order_date"].dt.to_period("M").dt.to_timestamp())
    .groupby("order_month")
    .agg(revenue=("total_amount", "sum"), orders=("order_id", "nunique"), customers=("customer_id", "nunique"))
    .reset_index()
)
monthly["aov"] = monthly["revenue"] / monthly["orders"]
monthly["mom_growth_pct"] = monthly["revenue"].pct_change() * 100
monthly["yoy_growth_pct"] = monthly["revenue"].pct_change(12) * 100
monthly.tail(12).round(2)"""
        ),
        code(
            """if HAS_PLOTS:
    plt.figure(figsize=(13, 5))
    sns.lineplot(data=monthly, x="order_month", y="revenue", marker="o")
    plt.title("Monthly Revenue Trend")
    plt.xlabel("")
    plt.ylabel("Revenue")
    plt.xticks(rotation=45)
    plt.tight_layout()"""
        ),
        markdown("## 6. Product and Category Performance"),
        code(
            """category_perf = (
    valid_lines.groupby(["category", "sub_category"])
    .agg(
        revenue=("net_line_amount", "sum"),
        gross_profit=("gross_profit", "sum"),
        units_sold=("quantity", "sum"),
        orders=("order_id", "nunique"),
        avg_discount=("discount", "mean"),
    )
    .reset_index()
)
category_perf["profit_margin_pct"] = 100 * category_perf["gross_profit"] / category_perf["revenue"]
category_perf.sort_values("revenue", ascending=False).head(10).round(2)"""
        ),
        code(
            """product_perf = (
    valid_lines.groupby(["product_id", "product_name", "category", "sub_category", "brand"])
    .agg(revenue=("net_line_amount", "sum"), gross_profit=("gross_profit", "sum"), units_sold=("quantity", "sum"))
    .reset_index()
)
product_perf["profit_margin_pct"] = 100 * product_perf["gross_profit"] / product_perf["revenue"]
product_perf["category_revenue_rank"] = product_perf.groupby("category")["revenue"].rank(method="dense", ascending=False)
product_perf.sort_values("revenue", ascending=False).head(15).round(2)"""
        ),
        markdown("## 7. RFM Segmentation"),
        code(
            """def score_quintile(series, higher_is_better=True):
    labels = [1, 2, 3, 4, 5] if higher_is_better else [5, 4, 3, 2, 1]
    return pd.qcut(series.rank(method="first"), 5, labels=labels).astype(int)

def segment_customer(row):
    r, f, m = row["recency_score"], row["frequency_score"], row["monetary_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if f >= 4 and m >= 3:
        return "Loyal Customers"
    if r >= 4 and f >= 2:
        return "Potential Loyalists"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r == 1 and f <= 2:
        return "Lost Customers"
    if r >= 4 and f == 1:
        return "New Customers"
    return "Need Nurture"

rfm = (
    valid_orders.groupby("customer_id")
    .agg(
        last_purchase_date=("order_date", "max"),
        frequency=("order_id", "nunique"),
        monetary=("total_amount", "sum"),
    )
    .reset_index()
)
rfm["recency"] = (ANALYSIS_DATE - rfm["last_purchase_date"]).dt.days
rfm["recency_score"] = score_quintile(rfm["recency"], higher_is_better=False)
rfm["frequency_score"] = score_quintile(rfm["frequency"], higher_is_better=True)
rfm["monetary_score"] = score_quintile(rfm["monetary"], higher_is_better=True)
rfm["rfm_score"] = rfm["recency_score"].astype(str) + rfm["frequency_score"].astype(str) + rfm["monetary_score"].astype(str)
rfm["customer_segment"] = rfm.apply(segment_customer, axis=1)

rfm_summary = (
    rfm.groupby("customer_segment")
    .agg(customers=("customer_id", "nunique"), revenue=("monetary", "sum"), avg_recency=("recency", "mean"), avg_frequency=("frequency", "mean"))
    .reset_index()
    .sort_values("revenue", ascending=False)
)
rfm_summary.round(2)"""
        ),
        code(
            """if HAS_PLOTS:
    plt.figure(figsize=(11, 5))
    sns.barplot(data=rfm_summary, x="customer_segment", y="revenue")
    plt.title("Revenue by RFM Segment")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()"""
        ),
        markdown("## 8. Cohort Retention Analysis"),
        code(
            """cohort_orders = valid_orders.copy()
cohort_orders["order_month"] = cohort_orders["order_date"].dt.to_period("M").dt.to_timestamp()
first_order = cohort_orders.groupby("customer_id", as_index=False)["order_month"].min().rename(columns={"order_month": "cohort_month"})
cohort = cohort_orders[["customer_id", "order_id", "order_month"]].merge(first_order, on="customer_id", how="left")
cohort["cohort_index"] = (
    (cohort["order_month"].dt.year - cohort["cohort_month"].dt.year) * 12
    + (cohort["order_month"].dt.month - cohort["cohort_month"].dt.month)
)
cohort_counts = cohort.groupby(["cohort_month", "cohort_index"])["customer_id"].nunique().reset_index()
cohort_matrix = cohort_counts.pivot(index="cohort_month", columns="cohort_index", values="customer_id").fillna(0)
retention = cohort_matrix.divide(cohort_matrix[0].replace(0, np.nan), axis=0) * 100
retention.round(2).head()"""
        ),
        code(
            """if HAS_PLOTS:
    plt.figure(figsize=(14, 8))
    sns.heatmap(retention.iloc[:18, :13], annot=False, cmap="Blues", fmt=".1f")
    plt.title("Monthly Cohort Retention (%)")
    plt.xlabel("Months Since First Purchase")
    plt.ylabel("Acquisition Cohort")
    plt.tight_layout()"""
        ),
        markdown("## 9. Churn Indicators and Targeting"),
        code(
            """rfm["churn_status"] = np.select(
    [rfm["recency"] > 365, rfm["recency"] > 180, rfm["recency"] > 90],
    ["Lost", "At Risk", "Needs Attention"],
    default="Active",
)
rfm["churn_score"] = np.clip(
    (rfm["recency"] / 365 * 55)
    + ((5 - rfm["frequency_score"]) * 6)
    + ((5 - rfm["monetary_score"]) * 4),
    0,
    100,
)
rfm.sort_values(["churn_score", "monetary"], ascending=[False, False]).head(20).round(2)"""
        ),
        markdown("## 10. Export Outputs"),
        code(
            """OUTPUTS.mkdir(parents=True, exist_ok=True)
monthly.to_csv(OUTPUTS / "notebook_monthly_revenue.csv", index=False)
category_perf.to_csv(OUTPUTS / "notebook_category_performance.csv", index=False)
rfm.to_csv(OUTPUTS / "notebook_rfm_segments.csv", index=False)
retention.reset_index().to_csv(OUTPUTS / "notebook_cohort_retention.csv", index=False)
print("Notebook exports written to", OUTPUTS)"""
        ),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    ensure_directories()
    path = NOTEBOOK_DIR / "ecommerce_customer_analytics.ipynb"
    path.write_text(json.dumps(build_notebook(), indent=2), encoding="utf-8")
    print(f"Notebook created: {path}")


if __name__ == "__main__":
    main()

