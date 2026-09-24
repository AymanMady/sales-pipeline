-- Database schema.
--   staging = raw CSV copy, everything TEXT, no constraints
--   core    = clean, typed data with primary and foreign keys
-- Safe to re-run.

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

-- Staging: accept the data exactly as it arrives, clean it later in Python.

DROP TABLE IF EXISTS staging.customers;
CREATE TABLE staging.customers (
    customer_id TEXT,
    first_name  TEXT,
    last_name   TEXT,
    email       TEXT,
    city        TEXT,
    country     TEXT,
    signup_date TEXT
);

DROP TABLE IF EXISTS staging.products;
CREATE TABLE staging.products (
    product_id   TEXT,
    product_name TEXT,
    category     TEXT,
    unit_price   TEXT
);

DROP TABLE IF EXISTS staging.orders;
CREATE TABLE staging.orders (
    order_id    TEXT,
    customer_id TEXT,
    order_date  TEXT,
    status      TEXT,
    product_id  TEXT,
    quantity    TEXT,
    unit_price  TEXT
);

-- Core. CASCADE is needed because the analysis views depend on these tables;
-- the pipeline recreates the views right after.

DROP TABLE IF EXISTS core.order_items CASCADE;
DROP TABLE IF EXISTS core.orders      CASCADE;
DROP TABLE IF EXISTS core.products    CASCADE;
DROP TABLE IF EXISTS core.customers   CASCADE;

CREATE TABLE core.customers (
    customer_id INTEGER PRIMARY KEY,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    city        TEXT,
    country     TEXT NOT NULL DEFAULT 'Unknown',
    signup_date DATE
);

CREATE TABLE core.products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT           NOT NULL,
    category     TEXT           NOT NULL DEFAULT 'Unknown',
    unit_price   NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0)
);

CREATE TABLE core.orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES core.customers (customer_id),
    order_date  DATE    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'delivered'
                CHECK (status IN ('delivered', 'shipped', 'pending', 'cancelled', 'returned'))
);

CREATE TABLE core.order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id      INTEGER        NOT NULL REFERENCES core.orders (order_id) ON DELETE CASCADE,
    product_id    INTEGER        NOT NULL REFERENCES core.products (product_id),
    quantity      INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10, 2) NOT NULL CHECK (unit_price > 0),
    -- Computed by PostgreSQL, so it can never drift from quantity * unit_price
    line_total    NUMERIC(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    -- One row per product per order; repeated products get their quantities merged
    UNIQUE (order_id, product_id)
);

-- PostgreSQL does not index foreign keys automatically, and these are the
-- columns every analysis joins on.
CREATE INDEX idx_orders_customer_id     ON core.orders (customer_id);
CREATE INDEX idx_orders_order_date      ON core.orders (order_date);
CREATE INDEX idx_order_items_order_id   ON core.order_items (order_id);
CREATE INDEX idx_order_items_product_id ON core.order_items (product_id);
