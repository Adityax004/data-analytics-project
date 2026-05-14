-- Advanced analytical SQL for the e-commerce customer analytics project.
-- Dialect: PostgreSQL.

-- 1. Executive KPIs: revenue, orders, customers, AOV, repeat rate
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
    ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS average_order_value,
    ROUND(100.0 * (SELECT COUNT(*) FROM repeat_customers) / NULLIF(COUNT(DISTINCT customer_id), 0), 2) AS repeat_customer_rate_pct
FROM valid_orders;

-- 2. Monthly revenue, MoM growth, YoY growth, and running revenue
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date)::date AS order_month,
        ROUND(SUM(total_amount), 2) AS revenue,
        COUNT(DISTINCT order_id) AS orders
    FROM orders
    WHERE order_status IN ('Completed', 'Shipped')
    GROUP BY DATE_TRUNC('month', order_date)::date
)
SELECT
    order_month,
    revenue,
    orders,
    ROUND(revenue / NULLIF(orders, 0), 2) AS aov,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
        / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0), 2) AS mom_growth_pct,
    ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (ORDER BY order_month))
        / NULLIF(LAG(revenue, 12) OVER (ORDER BY order_month), 0), 2) AS yoy_growth_pct,
    ROUND(SUM(revenue) OVER (ORDER BY order_month), 2) AS running_revenue_total
FROM monthly
ORDER BY order_month;

-- 3. Revenue and profit by category/sub-category
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

-- 4. Top customers by revenue with ranking
WITH customer_revenue AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.city,
        c.state,
        c.country,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(SUM(o.total_amount), 2) AS revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status IN ('Completed', 'Shipped')
    GROUP BY c.customer_id, c.customer_name, c.city, c.state, c.country
)
SELECT
    *,
    RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
    NTILE(10) OVER (ORDER BY revenue DESC) AS revenue_decile
FROM customer_revenue
ORDER BY revenue DESC
LIMIT 100;

-- 5. Product ranking within category using dense rank
WITH product_sales AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(oi.quantity) AS units_sold,
        ROUND(SUM(oi.quantity * oi.price_per_unit * (1 - oi.discount)), 2) AS revenue
    FROM products p
    JOIN order_items oi ON p.product_id = oi.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status IN ('Completed', 'Shipped')
    GROUP BY p.product_id, p.product_name, p.category
)
SELECT
    *,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_revenue_rank
FROM product_sales
ORDER BY category, category_revenue_rank;

-- 6. New vs returning customer trend
WITH valid_orders AS (
    SELECT
        order_id,
        customer_id,
        DATE_TRUNC('month', order_date)::date AS order_month,
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
    CASE WHEN vo.order_month = fo.first_order_month THEN 'New Customer' ELSE 'Returning Customer' END AS customer_type,
    COUNT(DISTINCT vo.customer_id) AS customers,
    COUNT(DISTINCT vo.order_id) AS orders,
    ROUND(SUM(vo.total_amount), 2) AS revenue
FROM valid_orders vo
JOIN first_order fo ON vo.customer_id = fo.customer_id
GROUP BY vo.order_month, customer_type
ORDER BY vo.order_month, customer_type;

-- 7. Churn identification
WITH customer_history AS (
    SELECT
        c.customer_id,
        c.customer_name,
        COUNT(DISTINCT o.order_id) AS valid_orders,
        ROUND(SUM(o.total_amount), 2) AS revenue,
        MAX(o.order_date) AS last_purchase_date,
        DATE '2026-01-01' - MAX(o.order_date) AS recency_days
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
WHERE valid_orders >= 2
ORDER BY recency_days DESC, revenue DESC;

-- 8. Geographic performance
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

-- 9. Discount impact on revenue and margin
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

