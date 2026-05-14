from __future__ import annotations

import sqlite3

import pandas as pd

from config import ANALYSIS_DATE, DATABASE_PATH, SQL_OUTPUT_DIR, ensure_directories


QUERIES = {
    "01_executive_kpis": f"""
        WITH valid_orders AS (
            SELECT *
            FROM orders
            WHERE order_status IN ('Completed', 'Shipped')
        ),
        repeat_customers AS (
            SELECT customer_id
            FROM valid_orders
            GROUP BY customer_id
            HAVING COUNT(DISTINCT order_id) > 1
        )
        SELECT
            ROUND(SUM(total_amount), 2) AS total_revenue,
            COUNT(DISTINCT order_id) AS total_orders,
            COUNT(DISTINCT customer_id) AS purchasing_customers,
            ROUND(SUM(total_amount) / COUNT(DISTINCT order_id), 2) AS average_order_value,
            ROUND(100.0 * (SELECT COUNT(*) FROM repeat_customers) / COUNT(DISTINCT customer_id), 2) AS repeat_customer_rate_pct,
            (SELECT COUNT(*) FROM returns) AS returned_orders
        FROM valid_orders;
    """,
    "02_monthly_revenue_growth": """
        WITH monthly AS (
            SELECT
                date(order_date, 'start of month') AS order_month,
                ROUND(SUM(total_amount), 2) AS revenue,
                COUNT(DISTINCT order_id) AS orders
            FROM orders
            WHERE order_status IN ('Completed', 'Shipped')
            GROUP BY date(order_date, 'start of month')
        )
        SELECT
            order_month,
            revenue,
            orders,
            ROUND(revenue / NULLIF(orders, 0), 2) AS aov,
            ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
                / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 2) AS month_over_month_growth_pct,
            ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (ORDER BY order_month))
                / NULLIF(LAG(revenue, 12) OVER (ORDER BY order_month), 0), 2) AS year_over_year_growth_pct,
            ROUND(SUM(revenue) OVER (ORDER BY order_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)
                AS running_revenue_total
        FROM monthly
        ORDER BY order_month;
    """,
    "03_revenue_by_category": """
        SELECT
            p.category,
            p.sub_category,
            ROUND(SUM(oi.quantity * oi.price_per_unit * (1 - oi.discount)), 2) AS revenue,
            ROUND(SUM(oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price)), 2) AS gross_profit,
            ROUND(100.0 * SUM(oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price))
                / NULLIF(SUM(oi.quantity * oi.price_per_unit * (1 - oi.discount)), 0), 2) AS profit_margin_pct,
            SUM(oi.quantity) AS units_sold
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.order_status IN ('Completed', 'Shipped')
        GROUP BY p.category, p.sub_category
        ORDER BY revenue DESC;
    """,
    "04_top_selling_products": """
        WITH product_sales AS (
            SELECT
                p.product_id,
                p.product_name,
                p.category,
                SUM(oi.quantity) AS units_sold,
                ROUND(SUM(oi.quantity * oi.price_per_unit * (1 - oi.discount)), 2) AS revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_status IN ('Completed', 'Shipped')
            GROUP BY p.product_id, p.product_name, p.category
        )
        SELECT
            *,
            RANK() OVER (ORDER BY revenue DESC) AS overall_revenue_rank,
            DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_revenue_dense_rank
        FROM product_sales
        ORDER BY revenue DESC
        LIMIT 50;
    """,
    "05_new_vs_returning_customers": """
        WITH valid_orders AS (
            SELECT
                order_id,
                customer_id,
                date(order_date, 'start of month') AS order_month,
                total_amount
            FROM orders
            WHERE order_status IN ('Completed', 'Shipped')
        ),
        first_order AS (
            SELECT customer_id, MIN(order_month) AS first_order_month
            FROM valid_orders
            GROUP BY customer_id
        )
        SELECT
            vo.order_month,
            CASE
                WHEN vo.order_month = fo.first_order_month THEN 'New Customer'
                ELSE 'Returning Customer'
            END AS customer_type,
            COUNT(DISTINCT vo.customer_id) AS customers,
            COUNT(DISTINCT vo.order_id) AS orders,
            ROUND(SUM(vo.total_amount), 2) AS revenue
        FROM valid_orders vo
        JOIN first_order fo ON vo.customer_id = fo.customer_id
        GROUP BY vo.order_month, customer_type
        ORDER BY vo.order_month, customer_type;
    """,
    "06_customer_lifetime_value": f"""
        WITH customer_orders AS (
            SELECT
                c.customer_id,
                c.customer_name,
                c.city,
                c.state,
                c.country,
                COUNT(DISTINCT o.order_id) AS order_count,
                ROUND(SUM(o.total_amount), 2) AS lifetime_revenue,
                MIN(o.order_date) AS first_purchase_date,
                MAX(o.order_date) AS last_purchase_date,
                CAST(julianday('{ANALYSIS_DATE}') - julianday(MAX(o.order_date)) AS INTEGER) AS days_since_last_purchase
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.order_status IN ('Completed', 'Shipped')
            GROUP BY c.customer_id, c.customer_name, c.city, c.state, c.country
        )
        SELECT
            *,
            ROUND(lifetime_revenue / NULLIF(order_count, 0), 2) AS customer_aov,
            CASE
                WHEN order_count >= 5 AND days_since_last_purchase <= 90 THEN 'Loyal Active'
                WHEN order_count >= 2 AND days_since_last_purchase <= 180 THEN 'Repeat Active'
                WHEN order_count >= 2 AND days_since_last_purchase > 180 THEN 'At Risk'
                ELSE 'One-Time'
            END AS lifecycle_status,
            RANK() OVER (ORDER BY lifetime_revenue DESC) AS customer_revenue_rank
        FROM customer_orders
        ORDER BY lifetime_revenue DESC
        LIMIT 1000;
    """,
    "07_churn_candidates": f"""
        WITH customer_history AS (
            SELECT
                c.customer_id,
                c.customer_name,
                COUNT(DISTINCT o.order_id) AS valid_orders,
                ROUND(SUM(o.total_amount), 2) AS revenue,
                MAX(o.order_date) AS last_purchase_date,
                CAST(julianday('{ANALYSIS_DATE}') - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.order_status IN ('Completed', 'Shipped')
            GROUP BY c.customer_id, c.customer_name
        )
        SELECT
            *,
            CASE
                WHEN recency_days > 365 THEN 'Lost'
                WHEN recency_days > 180 THEN 'At Risk'
                WHEN recency_days > 90 THEN 'Needs Attention'
                ELSE 'Active'
            END AS churn_status
        FROM customer_history
        WHERE valid_orders >= 2 AND recency_days > 180
        ORDER BY revenue DESC, recency_days DESC
        LIMIT 1000;
    """,
    "08_discount_impact": """
        WITH sales AS (
            SELECT
                CASE
                    WHEN oi.discount = 0 THEN 'No Discount'
                    WHEN oi.discount <= 0.10 THEN 'Low: 1-10%'
                    WHEN oi.discount <= 0.20 THEN 'Medium: 11-20%'
                    ELSE 'High: 21%+'
                END AS discount_bucket,
                oi.quantity,
                oi.price_per_unit,
                oi.discount,
                p.cost_price
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_status IN ('Completed', 'Shipped')
        )
        SELECT
            discount_bucket,
            SUM(quantity) AS units_sold,
            ROUND(SUM(quantity * price_per_unit * (1 - discount)), 2) AS revenue,
            ROUND(SUM(quantity * price_per_unit * discount), 2) AS discount_amount,
            ROUND(SUM(quantity * (price_per_unit * (1 - discount) - cost_price)), 2) AS gross_profit,
            ROUND(100.0 * SUM(quantity * (price_per_unit * (1 - discount) - cost_price))
                / NULLIF(SUM(quantity * price_per_unit * (1 - discount)), 0), 2) AS profit_margin_pct
        FROM sales
        GROUP BY discount_bucket
        ORDER BY revenue DESC;
    """,
    "09_geographic_revenue": """
        SELECT
            c.country,
            c.state,
            c.city,
            COUNT(DISTINCT c.customer_id) AS customers,
            COUNT(DISTINCT o.order_id) AS orders,
            ROUND(SUM(o.total_amount), 2) AS revenue,
            ROUND(SUM(o.total_amount) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS aov
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status IN ('Completed', 'Shipped')
        GROUP BY c.country, c.state, c.city
        ORDER BY revenue DESC;
    """,
    "10_product_rank_within_category": """
        WITH product_profit AS (
            SELECT
                p.category,
                p.product_id,
                p.product_name,
                ROUND(SUM(oi.quantity * oi.price_per_unit * (1 - oi.discount)), 2) AS revenue,
                ROUND(SUM(oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price)), 2) AS gross_profit
            FROM products p
            JOIN order_items oi ON p.product_id = oi.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_status IN ('Completed', 'Shipped')
            GROUP BY p.category, p.product_id, p.product_name
        )
        SELECT
            *,
            DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS revenue_rank_in_category,
            DENSE_RANK() OVER (PARTITION BY category ORDER BY gross_profit DESC) AS profit_rank_in_category
        FROM product_profit
        ORDER BY category, revenue_rank_in_category;
    """,
}


def run_queries() -> dict[str, pd.DataFrame]:
    ensure_directories()
    results = {}
    with sqlite3.connect(DATABASE_PATH) as conn:
        for name, query in QUERIES.items():
            df = pd.read_sql_query(query, conn)
            df.to_csv(SQL_OUTPUT_DIR / f"{name}.csv", index=False)
            results[name] = df
    return results


def main() -> None:
    results = run_queries()
    for name, df in results.items():
        print(f"{name}: {len(df):,} rows -> {SQL_OUTPUT_DIR / f'{name}.csv'}")


if __name__ == "__main__":
    main()

