from __future__ import annotations

from collections import Counter
from html import escape
from itertools import combinations
import json

import numpy as np
import pandas as pd

from config import (
    ANALYSIS_DATE,
    FIGURE_OUTPUT_DIR,
    POWERBI_IMPORT_DIR,
    PROCESSED_DIR,
    REPORT_OUTPUT_DIR,
    TABLE_OUTPUT_DIR,
    ensure_directories,
)


VALID_STATUSES = ["Completed", "Shipped"]


def round_numeric(df: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    rounded = df.copy()
    numeric_cols = rounded.select_dtypes(include=[np.number]).columns
    rounded[numeric_cols] = rounded[numeric_cols].round(decimals)
    return rounded


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def load_processed() -> dict[str, pd.DataFrame]:
    tables = {
        "customers": pd.read_csv(PROCESSED_DIR / "customers.csv", parse_dates=["signup_date"]),
        "products": pd.read_csv(PROCESSED_DIR / "products.csv"),
        "orders": pd.read_csv(PROCESSED_DIR / "orders.csv", parse_dates=["order_date", "shipment_date"]),
        "order_items": pd.read_csv(PROCESSED_DIR / "order_items.csv"),
        "returns": pd.read_csv(PROCESSED_DIR / "returns.csv", parse_dates=["return_date"]),
    }
    return tables


def score_quintile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    labels = [1, 2, 3, 4, 5] if higher_is_better else [5, 4, 3, 2, 1]
    ranked = series.rank(method="first")
    try:
        return pd.qcut(ranked, 5, labels=labels).astype(int)
    except ValueError:
        return pd.Series(np.repeat(3, len(series)), index=series.index)


def assign_rfm_segment(row: pd.Series) -> str:
    r, f, m = int(row["recency_score"]), int(row["frequency_score"]), int(row["monetary_score"])
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


def build_line_items(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    order_items = tables["order_items"]
    orders = tables["orders"]
    products = tables["products"]
    line_items = (
        order_items.merge(orders, on="order_id", how="left")
        .merge(products, on="product_id", how="left")
    )
    line_items["gross_line_amount"] = line_items["quantity"] * line_items["price_per_unit"]
    line_items["discount_amount"] = line_items["gross_line_amount"] * line_items["discount"]
    line_items["net_line_amount"] = line_items["gross_line_amount"] - line_items["discount_amount"]
    line_items["gross_profit"] = line_items["quantity"] * (
        line_items["price_per_unit"] * (1 - line_items["discount"]) - line_items["cost_price"]
    )
    line_items["order_month"] = line_items["order_date"].dt.to_period("M").dt.to_timestamp()
    return line_items


def executive_kpis(orders: pd.DataFrame, customers: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    customer_order_counts = valid_orders.groupby("customer_id")["order_id"].nunique()
    repeat_customers = int((customer_order_counts > 1).sum())
    purchasing_customers = int(customer_order_counts.count())
    kpis = {
        "total_revenue": valid_orders["total_amount"].sum(),
        "total_orders": valid_orders["order_id"].nunique(),
        "total_customers": customers["customer_id"].nunique(),
        "purchasing_customers": purchasing_customers,
        "average_order_value": valid_orders["total_amount"].sum() / valid_orders["order_id"].nunique(),
        "repeat_customer_rate_pct": 100 * repeat_customers / purchasing_customers,
        "return_rate_pct": 100 * returns["order_id"].nunique() / orders["order_id"].nunique(),
    }
    return pd.DataFrame([kpis]).round(2)


def monthly_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    valid_orders["order_month"] = valid_orders["order_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        valid_orders.groupby("order_month")
        .agg(revenue=("total_amount", "sum"), orders=("order_id", "nunique"), customers=("customer_id", "nunique"))
        .reset_index()
        .sort_values("order_month")
    )
    monthly["aov"] = monthly["revenue"] / monthly["orders"]
    monthly["mom_growth_pct"] = monthly["revenue"].pct_change() * 100
    monthly["yoy_growth_pct"] = monthly["revenue"].pct_change(12) * 100
    monthly["running_revenue"] = monthly["revenue"].cumsum()
    return round_numeric(monthly)


def product_and_category_performance(line_items: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid_lines = line_items[line_items["order_status"].isin(VALID_STATUSES)].copy()
    category = (
        valid_lines.groupby(["category", "sub_category"])
        .agg(
            revenue=("net_line_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
            discount_amount=("discount_amount", "sum"),
            units_sold=("quantity", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    category["profit_margin_pct"] = 100 * category["gross_profit"] / category["revenue"]
    category = category.sort_values("revenue", ascending=False).round(2)

    product = (
        valid_lines.groupby(["product_id", "product_name", "category", "sub_category", "brand"])
        .agg(
            revenue=("net_line_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
            units_sold=("quantity", "sum"),
            average_discount_pct=("discount", "mean"),
        )
        .reset_index()
    )
    product["profit_margin_pct"] = 100 * product["gross_profit"] / product["revenue"]
    product["revenue_rank"] = product["revenue"].rank(method="dense", ascending=False).astype(int)
    product["category_revenue_rank"] = product.groupby("category")["revenue"].rank(method="dense", ascending=False).astype(int)
    product = product.sort_values("revenue", ascending=False).round(2)
    return product, category


def rfm_analysis(orders: pd.DataFrame, customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    analysis_date = pd.Timestamp(ANALYSIS_DATE)
    rfm = (
        valid_orders.groupby("customer_id")
        .agg(
            last_purchase_date=("order_date", "max"),
            first_purchase_date=("order_date", "min"),
            frequency=("order_id", "nunique"),
            monetary=("total_amount", "sum"),
        )
        .reset_index()
    )
    rfm["recency"] = (analysis_date - rfm["last_purchase_date"]).dt.days
    rfm["recency_score"] = score_quintile(rfm["recency"], higher_is_better=False)
    rfm["frequency_score"] = score_quintile(rfm["frequency"], higher_is_better=True)
    rfm["monetary_score"] = score_quintile(rfm["monetary"], higher_is_better=True)
    rfm["rfm_score"] = (
        rfm["recency_score"].astype(str) + rfm["frequency_score"].astype(str) + rfm["monetary_score"].astype(str)
    )
    rfm["customer_segment"] = rfm.apply(assign_rfm_segment, axis=1)
    rfm = rfm.merge(
        customers[["customer_id", "customer_name", "gender", "age", "city", "state", "country", "signup_date"]],
        on="customer_id",
        how="left",
    )
    rfm["churn_status"] = np.select(
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
    ).round(1)
    summary = (
        rfm.groupby("customer_segment")
        .agg(
            customers=("customer_id", "nunique"),
            revenue=("monetary", "sum"),
            average_recency=("recency", "mean"),
            average_frequency=("frequency", "mean"),
            average_monetary=("monetary", "mean"),
            at_risk_customers=("churn_status", lambda s: int((s.isin(["At Risk", "Lost"])).sum())),
        )
        .reset_index()
    )
    summary["revenue_share_pct"] = 100 * summary["revenue"] / summary["revenue"].sum()
    return round_numeric(rfm), round_numeric(summary.sort_values("revenue", ascending=False))


def cohort_analysis(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    valid_orders["order_month"] = valid_orders["order_date"].dt.to_period("M").dt.to_timestamp()
    first_purchase = valid_orders.groupby("customer_id", as_index=False)["order_month"].min()
    first_purchase = first_purchase.rename(columns={"order_month": "cohort_month"})
    cohort = valid_orders[["customer_id", "order_id", "order_month"]].merge(first_purchase, on="customer_id", how="left")
    cohort["cohort_index"] = (
        (cohort["order_month"].dt.year - cohort["cohort_month"].dt.year) * 12
        + (cohort["order_month"].dt.month - cohort["cohort_month"].dt.month)
    )
    cohort_counts = (
        cohort.groupby(["cohort_month", "cohort_index"])["customer_id"]
        .nunique()
        .reset_index(name="customers")
        .sort_values(["cohort_month", "cohort_index"])
    )
    cohort_matrix = cohort_counts.pivot(index="cohort_month", columns="cohort_index", values="customers").fillna(0)
    cohort_sizes = cohort_matrix[0].replace(0, np.nan)
    retention = cohort_matrix.divide(cohort_sizes, axis=0) * 100
    retention = retention.round(2)
    cohort_counts["cohort_month"] = cohort_counts["cohort_month"].dt.strftime("%Y-%m-01")
    retention_export = retention.copy()
    retention_export.index = retention_export.index.strftime("%Y-%m-01")
    retention_export = retention_export.reset_index().rename(columns={"cohort_month": "cohort_month"})
    retention_export.columns = [str(col) if isinstance(col, int) else col for col in retention_export.columns]
    repeat_trend = (
        cohort[cohort["cohort_index"] > 0]
        .groupby("order_month")["customer_id"]
        .nunique()
        .reset_index(name="repeat_customers")
    )
    repeat_trend["order_month"] = repeat_trend["order_month"].dt.strftime("%Y-%m-01")
    return cohort_counts, retention_export, repeat_trend


def discount_analysis(line_items: pd.DataFrame) -> pd.DataFrame:
    valid_lines = line_items[line_items["order_status"].isin(VALID_STATUSES)].copy()
    valid_lines["discount_bucket"] = pd.cut(
        valid_lines["discount"],
        bins=[-0.01, 0, 0.10, 0.20, 1.0],
        labels=["No Discount", "Low: 1-10%", "Medium: 11-20%", "High: 21%+"],
    )
    analysis = (
        valid_lines.groupby("discount_bucket", observed=False)
        .agg(
            units_sold=("quantity", "sum"),
            revenue=("net_line_amount", "sum"),
            discount_amount=("discount_amount", "sum"),
            gross_profit=("gross_profit", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    analysis["profit_margin_pct"] = 100 * analysis["gross_profit"] / analysis["revenue"]
    analysis["revenue_per_unit"] = analysis["revenue"] / analysis["units_sold"]
    return analysis.round(2)


def geographic_analysis(orders: pd.DataFrame, customers: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    valid_orders = orders[orders["order_status"].isin(VALID_STATUSES)].copy()
    geo = (
        valid_orders.merge(customers[["customer_id", "city", "state", "country"]], on="customer_id", how="left")
        .groupby(["country", "state", "city"])
        .agg(revenue=("total_amount", "sum"), orders=("order_id", "nunique"), customers=("customer_id", "nunique"))
        .reset_index()
    )
    retention = (
        rfm.groupby(["country", "state", "city"])
        .agg(repeat_customer_rate_pct=("frequency", lambda s: 100 * (s > 1).sum() / len(s)))
        .reset_index()
    )
    geo = geo.merge(retention, on=["country", "state", "city"], how="left")
    geo["aov"] = geo["revenue"] / geo["orders"]
    return geo.sort_values("revenue", ascending=False).round(2)


def market_basket(line_items: pd.DataFrame) -> pd.DataFrame:
    valid = line_items[line_items["order_status"].isin(VALID_STATUSES)]
    order_products = valid.groupby("order_id")["product_name"].apply(lambda s: sorted(set(s))).reset_index()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for products in order_products["product_name"]:
        if len(products) < 2:
            continue
        for pair in combinations(products[:8], 2):
            pair_counts[pair] += 1
    rows = [
        {"product_a": a, "product_b": b, "orders_together": count}
        for (a, b), count in pair_counts.most_common(50)
    ]
    return pd.DataFrame(rows)


def sales_forecast(monthly: pd.DataFrame, periods: int = 6) -> pd.DataFrame:
    history = monthly.copy().sort_values("order_month")
    x = np.arange(len(history))
    y = history["revenue"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    history["month_number"] = history["order_month"].dt.month
    monthly_factor = history.groupby("month_number")["revenue"].mean() / history["revenue"].mean()

    future_months = pd.date_range(history["order_month"].max() + pd.offsets.MonthBegin(1), periods=periods, freq="MS")
    rows = []
    for i, month in enumerate(future_months, start=len(history)):
        trend_value = slope * i + intercept
        seasonal = float(monthly_factor.get(month.month, 1.0))
        rows.append(
            {
                "forecast_month": month.strftime("%Y-%m-01"),
                "forecast_revenue": round(max(trend_value * seasonal, 0), 2),
                "method": "Linear trend with monthly seasonal index",
            }
        )
    return pd.DataFrame(rows)


def calendar_table(orders: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(orders["order_date"].min(), orders["order_date"].max(), freq="D")
    calendar = pd.DataFrame({"date": dates})
    calendar["year"] = calendar["date"].dt.year
    calendar["quarter"] = "Q" + calendar["date"].dt.quarter.astype(str)
    calendar["month_number"] = calendar["date"].dt.month
    calendar["month_name"] = calendar["date"].dt.month_name()
    calendar["month_start"] = calendar["date"].dt.to_period("M").dt.to_timestamp()
    calendar["year_month"] = calendar["date"].dt.strftime("%Y-%m")
    calendar["day_name"] = calendar["date"].dt.day_name()
    calendar["is_weekend"] = calendar["date"].dt.dayofweek >= 5
    return calendar


def bar_svg(df: pd.DataFrame, label_col: str, value_col: str, title: str, color: str = "#2563eb") -> str:
    width, height = 900, 360
    left, right, top, bottom = 190, 35, 50, 45
    data = df[[label_col, value_col]].head(10).copy()
    data[value_col] = data[value_col].astype(float)
    max_value = max(float(data[value_col].max()), 1)
    bar_gap = 8
    bar_height = (height - top - bottom - bar_gap * (len(data) - 1)) / max(len(data), 1)
    rows = [
        f'<text x="{left}" y="28" text-anchor="middle" class="chart-title">{escape(title)}</text>'
    ]
    for idx, row in data.reset_index(drop=True).iterrows():
        y = top + idx * (bar_height + bar_gap)
        bar_width = (width - left - right) * float(row[value_col]) / max_value
        label = str(row[label_col])
        if len(label) > 28:
            label = label[:25] + "..."
        rows.append(f'<text x="{left - 12}" y="{y + bar_height * 0.68:.1f}" text-anchor="end" class="axis-label">{escape(label)}</text>')
        rows.append(f'<rect x="{left}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="4" fill="{color}"></rect>')
        rows.append(f'<text x="{left + bar_width + 8:.1f}" y="{y + bar_height * 0.68:.1f}" class="value-label">{float(row[value_col]):,.0f}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">{"".join(rows)}</svg>'


def line_svg(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> str:
    width, height = 900, 340
    left, right, top, bottom = 65, 30, 50, 55
    data = df[[x_col, y_col]].copy().sort_values(x_col)
    y_values = data[y_col].astype(float).to_numpy()
    y_min, y_max = float(y_values.min()), float(y_values.max())
    span = max(y_max - y_min, 1)
    points = []
    for idx, (_, row) in enumerate(data.iterrows()):
        x = left + idx * (width - left - right) / max(len(data) - 1, 1)
        y = top + (height - top - bottom) * (1 - (float(row[y_col]) - y_min) / span)
        points.append((x, y))
    point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    x_labels = []
    for idx in np.linspace(0, len(data) - 1, num=min(7, len(data)), dtype=int):
        label = pd.to_datetime(data.iloc[idx][x_col]).strftime("%b %Y")
        x = left + idx * (width - left - right) / max(len(data) - 1, 1)
        x_labels.append(f'<text x="{x:.1f}" y="{height - 20}" text-anchor="middle" class="axis-label">{label}</text>')
    circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#0f766e"></circle>' for x, y in points)
    return f"""
    <svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
        <text x="{width / 2}" y="28" text-anchor="middle" class="chart-title">{escape(title)}</text>
        <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#cbd5e1" />
        <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#cbd5e1" />
        <text x="{left - 8}" y="{top + 5}" text-anchor="end" class="axis-label">{money(y_max)}</text>
        <text x="{left - 8}" y="{height - bottom}" text-anchor="end" class="axis-label">{money(y_min)}</text>
        <polyline points="{point_string}" fill="none" stroke="#0f766e" stroke-width="4" />
        {circles}
        {''.join(x_labels)}
    </svg>
    """


def cohort_heatmap_html(retention: pd.DataFrame) -> str:
    display = retention.copy()
    display = display.head(18)
    month_cols = [c for c in display.columns if c != "cohort_month"][:13]
    rows = []
    header = "<th>Cohort</th>" + "".join(f"<th>M+{escape(str(c))}</th>" for c in month_cols)
    for _, row in display.iterrows():
        cells = [f"<th>{escape(str(row['cohort_month']))}</th>"]
        for col in month_cols:
            value = row[col]
            if pd.isna(value):
                cells.append("<td></td>")
                continue
            intensity = min(float(value) / 100, 1)
            background = f"rgba(15, 118, 110, {0.10 + intensity * 0.82:.2f})"
            text_color = "#ffffff" if intensity > 0.55 else "#0f172a"
            cells.append(f'<td style="background:{background};color:{text_color}">{float(value):.1f}%</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="heatmap"><thead><tr>{header}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def write_html_report(
    kpis: pd.DataFrame,
    monthly: pd.DataFrame,
    category: pd.DataFrame,
    product: pd.DataFrame,
    rfm_summary: pd.DataFrame,
    retention: pd.DataFrame,
    geo: pd.DataFrame,
    discount: pd.DataFrame,
) -> None:
    k = kpis.iloc[0]
    monthly_svg = line_svg(monthly, "order_month", "revenue", "Monthly Revenue Trend")
    category_svg = bar_svg(category.groupby("category", as_index=False)["gross_profit"].sum().sort_values("gross_profit", ascending=False), "category", "gross_profit", "Gross Profit by Category", "#1d4ed8")
    rfm_svg = bar_svg(rfm_summary.sort_values("revenue", ascending=False), "customer_segment", "revenue", "Revenue by RFM Segment", "#7c3aed")
    product_svg = bar_svg(product.head(10), "product_name", "revenue", "Top 10 Products by Revenue", "#dc2626")
    discount_svg = bar_svg(discount, "discount_bucket", "gross_profit", "Gross Profit by Discount Bucket", "#c2410c")

    (FIGURE_OUTPUT_DIR / "monthly_revenue.svg").write_text(monthly_svg, encoding="utf-8")
    (FIGURE_OUTPUT_DIR / "category_profit.svg").write_text(category_svg, encoding="utf-8")
    (FIGURE_OUTPUT_DIR / "rfm_revenue.svg").write_text(rfm_svg, encoding="utf-8")
    (FIGURE_OUTPUT_DIR / "top_products.svg").write_text(product_svg, encoding="utf-8")
    (FIGURE_OUTPUT_DIR / "discount_profit.svg").write_text(discount_svg, encoding="utf-8")

    top_geo = geo.head(8)[["country", "state", "city", "revenue", "repeat_customer_rate_pct"]]
    top_geo_rows = "".join(
        f"<tr><td>{escape(row.country)}</td><td>{escape(row.state)}</td><td>{escape(row.city)}</td><td>{money(row.revenue)}</td><td>{pct(row.repeat_customer_rate_pct)}</td></tr>"
        for row in top_geo.itertuples(index=False)
    )
    html = f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>E-commerce Customer Analytics Report</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; color: #0f172a; background: #f8fafc; }}
header {{ padding: 30px 42px; background: #111827; color: #f8fafc; }}
main {{ padding: 28px 42px 48px; max-width: 1220px; margin: auto; }}
h1 {{ margin: 0 0 8px; font-size: 30px; }}
h2 {{ margin: 36px 0 16px; font-size: 22px; }}
.subtitle {{ color: #cbd5e1; margin: 0; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 14px; }}
.card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, .04); }}
.metric {{ font-size: 25px; font-weight: 700; margin-top: 6px; }}
.label {{ color: #475569; font-size: 13px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
.wide {{ grid-column: 1 / -1; }}
svg {{ width: 100%; height: auto; display: block; }}
.chart-title {{ font-size: 18px; font-weight: 700; fill: #0f172a; }}
.axis-label {{ font-size: 12px; fill: #475569; }}
.value-label {{ font-size: 12px; fill: #334155; }}
table {{ border-collapse: collapse; width: 100%; background: white; }}
th, td {{ padding: 8px 10px; border: 1px solid #e2e8f0; text-align: right; font-size: 13px; }}
th:first-child, td:first-child {{ text-align: left; }}
thead th {{ background: #e5e7eb; color: #111827; }}
.heatmap td, .heatmap th {{ min-width: 54px; text-align: center; }}
.insights li {{ margin: 8px 0; }}
@media (max-width: 900px) {{ .kpis, .grid {{ grid-template-columns: 1fr; }} main, header {{ padding-left: 20px; padding-right: 20px; }} }}
</style>
</head>
<body>
<header>
  <h1>E-commerce Customer Analytics & Revenue Optimization</h1>
  <p class="subtitle">Generated analytics report from the normalized SQL/Pandas project pipeline.</p>
</header>
<main>
  <section class="kpis">
    <div class="card"><div class="label">Total Revenue</div><div class="metric">{money(k.total_revenue)}</div></div>
    <div class="card"><div class="label">Total Orders</div><div class="metric">{int(k.total_orders):,}</div></div>
    <div class="card"><div class="label">Average Order Value</div><div class="metric">{money(k.average_order_value)}</div></div>
    <div class="card"><div class="label">Repeat Customer Rate</div><div class="metric">{pct(k.repeat_customer_rate_pct)}</div></div>
  </section>
  <section class="grid">
    <div class="card wide">{monthly_svg}</div>
    <div class="card">{category_svg}</div>
    <div class="card">{rfm_svg}</div>
    <div class="card">{product_svg}</div>
    <div class="card">{discount_svg}</div>
  </section>
  <section>
    <h2>Cohort Retention Heatmap</h2>
    <div class="card">{cohort_heatmap_html(retention)}</div>
  </section>
  <section>
    <h2>Top Revenue Regions</h2>
    <div class="card">
      <table><thead><tr><th>Country</th><th>State</th><th>City</th><th>Revenue</th><th>Repeat Rate</th></tr></thead><tbody>{top_geo_rows}</tbody></table>
    </div>
  </section>
</main>
</body>
</html>
"""
    (REPORT_OUTPUT_DIR / "ecommerce_analytics_report.html").write_text(html, encoding="utf-8")


def export_powerbi_tables(
    tables: dict[str, pd.DataFrame],
    line_items: pd.DataFrame,
    calendar: pd.DataFrame,
    rfm: pd.DataFrame,
    retention: pd.DataFrame,
    monthly: pd.DataFrame,
    category: pd.DataFrame,
    product: pd.DataFrame,
    geo: pd.DataFrame,
    discount: pd.DataFrame,
) -> None:
    exports = {
        "dim_customers": tables["customers"],
        "dim_products": tables["products"],
        "fact_orders": tables["orders"],
        "fact_order_items": tables["order_items"],
        "fact_returns": tables["returns"],
        "fact_sales_lines": line_items,
        "dim_calendar": calendar,
        "rfm_segments": rfm,
        "cohort_retention": retention,
        "monthly_revenue": monthly,
        "category_performance": category,
        "product_performance": product,
        "geographic_performance": geo,
        "discount_analysis": discount,
    }
    for name, df in exports.items():
        out = df.copy()
        for col in out.select_dtypes(include=["datetime64[ns]"]).columns:
            out[col] = out[col].dt.strftime("%Y-%m-%d")
        out.to_csv(POWERBI_IMPORT_DIR / f"{name}.csv", index=False)


def save_outputs() -> dict[str, pd.DataFrame]:
    ensure_directories()
    tables = load_processed()
    customers, orders, returns = tables["customers"], tables["orders"], tables["returns"]
    line_items = build_line_items(tables)

    kpis = executive_kpis(orders, customers, returns)
    monthly = monthly_revenue(orders)
    product, category = product_and_category_performance(line_items)
    rfm, rfm_summary = rfm_analysis(orders, customers)
    cohort_counts, retention, repeat_trend = cohort_analysis(orders)
    discount = discount_analysis(line_items)
    geo = geographic_analysis(orders, customers, rfm)
    basket = market_basket(line_items)
    forecast = sales_forecast(monthly)
    calendar = calendar_table(orders)

    outputs = {
        "executive_kpis": kpis,
        "monthly_revenue": monthly,
        "product_performance": product,
        "category_performance": category,
        "rfm_customer_segments": rfm,
        "rfm_segment_summary": rfm_summary,
        "cohort_counts": cohort_counts,
        "cohort_retention": retention,
        "monthly_repeat_customers": repeat_trend,
        "discount_analysis": discount,
        "geographic_performance": geo,
        "market_basket_top_pairs": basket,
        "sales_forecast": forecast,
        "calendar": calendar,
    }

    for name, df in outputs.items():
        out = df.copy()
        for col in out.select_dtypes(include=["datetime64[ns]"]).columns:
            out[col] = out[col].dt.strftime("%Y-%m-%d")
        out.to_csv(TABLE_OUTPUT_DIR / f"{name}.csv", index=False)

    with pd.ExcelWriter(TABLE_OUTPUT_DIR / "analytics_export.xlsx") as writer:
        for name, df in outputs.items():
            sheet_name = name[:31]
            df.head(100_000).to_excel(writer, sheet_name=sheet_name, index=False)

    export_powerbi_tables(tables, line_items, calendar, rfm, retention, monthly, category, product, geo, discount)
    write_html_report(kpis, monthly, category, product, rfm_summary, retention, geo, discount)

    business_insights = build_business_insights(kpis, monthly, category, product, rfm_summary, discount, geo, retention)
    (TABLE_OUTPUT_DIR / "business_insights.json").write_text(json.dumps(business_insights, indent=2), encoding="utf-8")
    return outputs


def build_business_insights(
    kpis: pd.DataFrame,
    monthly: pd.DataFrame,
    category: pd.DataFrame,
    product: pd.DataFrame,
    rfm_summary: pd.DataFrame,
    discount: pd.DataFrame,
    geo: pd.DataFrame,
    retention: pd.DataFrame,
) -> list[dict[str, str]]:
    top_segment = rfm_summary.iloc[0]
    peak_month = monthly.loc[monthly["revenue"].idxmax()]
    top_category = category.groupby("category", as_index=False)["gross_profit"].sum().sort_values("gross_profit", ascending=False).iloc[0]
    low_margin_bucket = discount.sort_values("profit_margin_pct").iloc[0]
    top_region = geo.iloc[0]
    month_one_cols = [c for c in retention.columns if c == "1"]
    avg_m1 = float(retention[month_one_cols[0]].dropna().mean()) if month_one_cols else 0.0
    return [
        {
            "finding": "Highest revenue customer segment",
            "insight": f"{top_segment['customer_segment']} generated {money(float(top_segment['revenue']))}, representing {pct(float(top_segment['revenue_share_pct']))} of RFM revenue.",
            "recommendation": "Prioritize early access, loyalty benefits, and cross-sell journeys for this segment.",
        },
        {
            "finding": "Peak sales month",
            "insight": f"{pd.to_datetime(peak_month['order_month']).strftime('%B %Y')} was the peak month at {money(float(peak_month['revenue']))}.",
            "recommendation": "Use seasonal inventory planning and launch retention campaigns 4-6 weeks before this peak period.",
        },
        {
            "finding": "Most profitable category",
            "insight": f"{top_category['category']} produced the highest gross profit at {money(float(top_category['gross_profit']))}.",
            "recommendation": "Increase merchandising coverage and bundle this category with high-frequency add-ons.",
        },
        {
            "finding": "Discount margin pressure",
            "insight": f"{low_margin_bucket['discount_bucket']} has the lowest margin at {pct(float(low_margin_bucket['profit_margin_pct']))}.",
            "recommendation": "Replace broad promotions with targeted discounts for at-risk or high-propensity customers.",
        },
        {
            "finding": "Top revenue region",
            "insight": f"{top_region['city']}, {top_region['state']} leads regional revenue at {money(float(top_region['revenue']))}.",
            "recommendation": "Use this region as a benchmark for localized product mix and retention campaigns.",
        },
        {
            "finding": "Early retention",
            "insight": f"Average month-one cohort retention is {pct(avg_m1)}.",
            "recommendation": "Optimize onboarding, replenishment reminders, and second-purchase offers inside the first 30 days.",
        },
    ]


def main() -> None:
    outputs = save_outputs()
    for name, df in outputs.items():
        print(f"{name}: {len(df):,} rows -> {TABLE_OUTPUT_DIR / f'{name}.csv'}")
    print(f"HTML report -> {REPORT_OUTPUT_DIR / 'ecommerce_analytics_report.html'}")
    print(f"Power BI import tables -> {POWERBI_IMPORT_DIR}")


if __name__ == "__main__":
    main()
