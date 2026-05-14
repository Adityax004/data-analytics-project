-- Staging-table cleaning examples for PostgreSQL.
-- The Python pipeline performs cleaning and writes data/processed/*.csv.
-- These SQL snippets show how equivalent checks can be handled in-database.

-- 1. Duplicate primary-key checks
SELECT 'customers' AS table_name, customer_id AS duplicated_key, COUNT(*) AS row_count
FROM customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

SELECT 'orders' AS table_name, order_id AS duplicated_key, COUNT(*) AS row_count
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1;

SELECT 'order_items' AS table_name, order_item_id AS duplicated_key, COUNT(*) AS row_count
FROM order_items
GROUP BY order_item_id
HAVING COUNT(*) > 1;

-- 2. Referential integrity checks
SELECT COUNT(*) AS orders_without_customer
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

SELECT COUNT(*) AS items_without_product
FROM order_items oi
LEFT JOIN products p ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;

-- 3. Data consistency checks
SELECT COUNT(*) AS negative_order_amounts
FROM orders
WHERE total_amount < 0;

SELECT COUNT(*) AS invalid_discounts
FROM order_items
WHERE discount < 0 OR discount > 1;

SELECT COUNT(*) AS shipments_before_order
FROM orders
WHERE shipment_date IS NOT NULL
  AND shipment_date < order_date;

-- 4. Recalculate order totals from line items
WITH recalculated AS (
    SELECT
        order_id,
        ROUND(SUM(quantity * price_per_unit * (1 - discount)), 2) AS recalculated_total
    FROM order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.total_amount,
    r.recalculated_total,
    ABS(o.total_amount - r.recalculated_total) AS difference
FROM orders o
JOIN recalculated r ON o.order_id = r.order_id
WHERE ABS(o.total_amount - r.recalculated_total) > 0.01
ORDER BY difference DESC;

