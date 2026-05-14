CREATE OR REPLACE VIEW vw_order_item_enriched AS
SELECT
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    o.order_date,
    DATE_TRUNC('month', o.order_date)::date AS order_month,
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

CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    DATE_TRUNC('month', order_date)::date AS order_month,
    ROUND(SUM(total_amount), 2) AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(total_amount) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS aov
FROM orders
WHERE order_status IN ('Completed', 'Shipped')
GROUP BY DATE_TRUNC('month', order_date)::date;

CREATE OR REPLACE VIEW vw_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    p.brand,
    SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity ELSE 0 END) AS units_sold,
    ROUND(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * oi.price_per_unit * (1 - oi.discount) ELSE 0 END), 2) AS revenue,
    ROUND(SUM(CASE WHEN o.order_status IN ('Completed', 'Shipped') THEN oi.quantity * (oi.price_per_unit * (1 - oi.discount) - p.cost_price) ELSE 0 END), 2) AS gross_profit
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.product_name, p.category, p.sub_category, p.brand;

