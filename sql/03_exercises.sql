-- SQL practice, easiest first.
-- Open a console with `make psql`, or use Adminer at http://localhost:8081
-- Write your own query before reading the solution below it.


-- LEVEL 1 - select and filter

-- 1.1 The 10 most expensive products.
SELECT product_name, category, unit_price
FROM core.products
ORDER BY unit_price DESC
LIMIT 10;

-- 1.2 How many customers per country?
SELECT country, COUNT(*) AS customers
FROM core.customers
GROUP BY country
ORDER BY customers DESC;

-- 1.3 Which orders were cancelled or returned?
SELECT order_id, order_date, status
FROM core.orders
WHERE status IN ('cancelled', 'returned')
ORDER BY order_date;


-- LEVEL 2 - joins

-- 2.1 The 20 latest order lines, with customer and product names.
SELECT o.order_date, v.customer, v.product_name, v.quantity, v.line_total
FROM core.v_sales v
JOIN core.orders o ON o.order_id = v.order_id
ORDER BY o.order_date DESC
LIMIT 20;

-- 2.2 Which products were never sold?
-- LEFT JOIN + IS NULL is how you find what does NOT exist.
SELECT p.product_id, p.product_name
FROM core.products p
LEFT JOIN core.order_items i ON i.product_id = p.product_id
WHERE i.product_id IS NULL;

-- 2.3 Which customers never ordered?
SELECT c.customer_id, c.first_name, c.last_name
FROM core.customers c
LEFT JOIN core.orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL;


-- LEVEL 3 - aggregation

-- 3.1 Revenue per country.
SELECT country, ROUND(SUM(line_total), 2) AS revenue
FROM core.v_sales
GROUP BY country
ORDER BY revenue DESC;

-- 3.2 Average number of different products per order.
SELECT ROUND(AVG(products), 2) AS products_per_order
FROM (
    SELECT order_id, COUNT(*) AS products
    FROM core.order_items
    GROUP BY order_id
) t;

-- 3.3 Which weekday sells the most?
SELECT TRIM(TO_CHAR(order_date, 'Day')) AS weekday,
       ROUND(SUM(line_total), 2)        AS revenue
FROM core.v_sales
GROUP BY weekday
ORDER BY revenue DESC;


-- LEVEL 4 - window functions

-- 4.1 Top 3 products within each category.
WITH ranked AS (
    SELECT category,
           product_name,
           SUM(line_total) AS revenue,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY SUM(line_total) DESC) AS rank
    FROM core.v_sales
    GROUP BY category, product_name
)
SELECT category, rank, product_name, ROUND(revenue, 2) AS revenue
FROM ranked
WHERE rank <= 3
ORDER BY category, rank;

-- 4.2 Running revenue total, month by month.
SELECT month,
       revenue,
       ROUND(SUM(revenue) OVER (ORDER BY month), 2) AS running_total
FROM core.v_sales_by_month;

-- 4.3 Days between each customer's consecutive orders.
WITH customer_orders AS (
    SELECT DISTINCT customer, order_date FROM core.v_sales
)
SELECT customer,
       order_date,
       order_date - LAG(order_date) OVER (PARTITION BY customer ORDER BY order_date) AS days_since_last
FROM customer_orders
ORDER BY days_since_last DESC NULLS LAST
LIMIT 15;


-- LEVEL 5 - going further

-- 5.1 Which products are bought together?
SELECT p1.product_name AS product_a,
       p2.product_name AS product_b,
       COUNT(*)        AS bought_together
FROM core.order_items i1
JOIN core.order_items i2
      ON i1.order_id = i2.order_id
     AND i1.product_id < i2.product_id  -- avoids counting (A,B) and (B,A) twice
JOIN core.products p1 ON p1.product_id = i1.product_id
JOIN core.products p2 ON p2.product_id = i2.product_id
GROUP BY product_a, product_b
ORDER BY bought_together DESC
LIMIT 10;

-- 5.2 See the index being used.
EXPLAIN ANALYZE
SELECT * FROM core.order_items WHERE order_id = 1042;

-- 5.3 Prove the constraints work. All three must FAIL - that is the point.
--
-- INSERT INTO core.orders (order_id, customer_id, order_date)
-- VALUES (99999, 123456, '2025-01-01');   -- foreign key violation
--
-- INSERT INTO core.products (product_id, product_name, category, unit_price)
-- VALUES (500, 'Free', 'Test', -5);       -- CHECK violation: price must be > 0
--
-- INSERT INTO core.order_items (order_id, product_id, quantity, unit_price)
-- VALUES (1042, 1, 0, 10);                -- CHECK violation: quantity must be > 0
