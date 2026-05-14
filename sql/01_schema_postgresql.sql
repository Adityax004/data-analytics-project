DROP TABLE IF EXISTS returns CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    gender VARCHAR(30) NOT NULL,
    age INT NOT NULL CHECK (age BETWEEN 18 AND 90),
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL,
    signup_date DATE NOT NULL
);

CREATE TABLE products (
    product_id VARCHAR(20) PRIMARY KEY,
    product_name VARCHAR(160) NOT NULL,
    category VARCHAR(80) NOT NULL,
    sub_category VARCHAR(80) NOT NULL,
    brand VARCHAR(80) NOT NULL,
    cost_price NUMERIC(10, 2) NOT NULL CHECK (cost_price >= 0),
    selling_price NUMERIC(10, 2) NOT NULL CHECK (selling_price >= 0)
);

CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    shipment_date DATE,
    payment_method VARCHAR(40) NOT NULL,
    order_status VARCHAR(20) NOT NULL CHECK (order_status IN ('Completed', 'Shipped', 'Returned', 'Cancelled')),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0)
);

CREATE TABLE order_items (
    order_item_id VARCHAR(24) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id),
    product_id VARCHAR(20) NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    price_per_unit NUMERIC(10, 2) NOT NULL CHECK (price_per_unit >= 0),
    discount NUMERIC(5, 2) NOT NULL CHECK (discount BETWEEN 0 AND 1)
);

CREATE TABLE returns (
    return_id VARCHAR(20) PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id),
    return_reason VARCHAR(120) NOT NULL,
    return_date DATE NOT NULL
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_products_category ON products(category, sub_category);
CREATE INDEX idx_returns_order_id ON returns(order_id);

-- Example PostgreSQL load commands after generating data:
-- \copy customers FROM 'data/processed/customers.csv' WITH (FORMAT CSV, HEADER TRUE);
-- \copy products FROM 'data/processed/products.csv' WITH (FORMAT CSV, HEADER TRUE);
-- \copy orders FROM 'data/processed/orders.csv' WITH (FORMAT CSV, HEADER TRUE);
-- \copy order_items FROM 'data/processed/order_items.csv' WITH (FORMAT CSV, HEADER TRUE);
-- \copy returns FROM 'data/processed/returns.csv' WITH (FORMAT CSV, HEADER TRUE);

