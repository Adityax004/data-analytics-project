DROP VIEW IF EXISTS vw_order_item_enriched;
DROP VIEW IF EXISTS vw_customer_order_summary;
DROP VIEW IF EXISTS vw_monthly_revenue;
DROP VIEW IF EXISTS vw_product_performance;
DROP VIEW IF EXISTS vw_customer_rfm_base;

CREATE VIEW vw_order_item_enriched AS
SELECT
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    o.order_date,
    date(o.order_date, 'start of month') AS order_month,
    o.order_status,
    o.payment_method,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.brand,
    oi.quantity,
    oi.price_per_unit,
    oi.discount,
    p.cost_price,
    ROUND(oi.quantity * oi.price_per_unit, 2) AS gross_line_amount,
    ROUND(oi.quantity * oi.price_per_unit * oi.discount, 2) AS discount_amount,
    ROUND(oi.quantity * oi.price_per_unit * (1 - oi.discount), 2) AS net_line_amount,
    ROUND(oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price), 2) AS gross_profit
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id;

CREATE VIEW vw_customer_order_summary AS
SELECT
    c.customer_id,
    c.customer_name,
    c.gender,
    c.age,
    c.city,
    c.state,
    c.country,
    c.signup_date,
    COUNT(DISTINCT o.order_id) AS order_count,
    ROUND(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN o.total_amount ELSE 0 END), 2) AS valid_revenue,
    MIN(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN o.order_date END) AS first_purchase_date,
    MAX(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN o.order_date END) AS last_purchase_date,
    SUM(CASE WHEN o.order_status = 'Returned' THEN 1 ELSE 0 END) AS returned_orders,
    SUM(CASE WHEN o.order_status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_orders
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name, c.gender, c.age, c.city, c.state, c.country, c.signup_date;

CREATE VIEW vw_monthly_revenue AS
SELECT
    date(order_date, 'start of month') AS order_month,
    ROUND(SUM(total_amount), 2) AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS aov
FROM orders
WHERE order_status IN ('Completed', 'Shipped')
GROUP BY date(order_date, 'start of month');

CREATE VIEW vw_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.brand,
    SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity ELSE 0 END) AS units_sold,
    ROUND(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * oi.price_per_unit * (1 - oi.discount) ELSE 0 END), 2) AS revenue,
    ROUND(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price) ELSE 0 END), 2) AS gross_profit,
    ROUND(100.0 * SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price) ELSE 0 END)
        / NULLIF(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * oi.price_per_unit * (1 - oi.discount) ELSE 0 END), 0), 2) AS profit_margin_pct
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.product_name, p.category, p.sub_category, p.brand;

CREATE VIEW vw_customer_rfm_base AS
SELECT
    c.customer_id,
    c.customer_name,
    CAST(julianday('2026-01-01') - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency,
    ROUND(SUM(o.total_amount), 2) AS monetary
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_status IN ('Completed', 'Shipped')
GROUP BY c.customer_id, c.customer_name;

