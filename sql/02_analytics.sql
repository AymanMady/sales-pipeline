-- Analysis views. Business logic lives here and nowhere else:
-- Python only formats what these views return.
--
-- Rule applied everywhere: cancelled and returned orders earn no revenue.

-- Base view: one row per product sold, with its customer and product details.
CREATE OR REPLACE VIEW core.v_sales AS
SELECT
    o.order_id,
    o.order_date,
    o.status,
    DATE_TRUNC('month', o.order_date)::date AS month,
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer,
    c.country,
    p.product_id,
    p.product_name,
    p.category,
    i.quantity,
    i.unit_price,
    i.line_total
FROM core.order_items i
JOIN core.orders    o ON o.order_id    = i.order_id
JOIN core.customers c ON c.customer_id = o.customer_id
JOIN core.products  p ON p.product_id  = i.product_id
WHERE o.status NOT IN ('cancelled', 'returned');

-- Revenue, order count, average order value.
-- Average order value is revenue / distinct orders, not AVG(line_total):
-- an order with three products is still one order.
CREATE OR REPLACE VIEW core.v_kpi AS
SELECT
    ROUND(SUM(line_total), 2)                            AS revenue,
    COUNT(DISTINCT order_id)                             AS orders,
    ROUND(SUM(line_total) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
    COUNT(DISTINCT customer_id)                          AS active_customers,
    SUM(quantity)                                        AS items_sold,
    MIN(order_date)                                      AS first_sale,
    MAX(order_date)                                      AS last_sale
FROM core.v_sales;

CREATE OR REPLACE VIEW core.v_sales_by_product AS
SELECT
    product_name,
    category,
    SUM(quantity)             AS quantity_sold,
    COUNT(DISTINCT order_id)  AS orders,
    ROUND(SUM(line_total), 2) AS revenue,
    ROUND(100 * SUM(line_total) / SUM(SUM(line_total)) OVER (), 2) AS revenue_share
FROM core.v_sales
GROUP BY product_name, category
ORDER BY revenue DESC;

CREATE OR REPLACE VIEW core.v_sales_by_month AS
WITH monthly AS (
    SELECT
        month,
        ROUND(SUM(line_total), 2) AS revenue,
        COUNT(DISTINCT order_id)  AS orders
    FROM core.v_sales
    GROUP BY month
)
SELECT
    TO_CHAR(month, 'YYYY-MM')                  AS month,
    revenue,
    orders,
    ROUND(revenue / orders, 2)                 AS avg_order_value,
    -- LAG reads the previous row, so we can compare month over month
    ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY month))
          / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS growth_pct
FROM monthly
ORDER BY month;

CREATE OR REPLACE VIEW core.v_top_customers AS
SELECT
    RANK() OVER (ORDER BY SUM(line_total) DESC)          AS rank,
    customer,
    country,
    COUNT(DISTINCT order_id)                             AS orders,
    ROUND(SUM(line_total), 2)                            AS total_spent,
    ROUND(SUM(line_total) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM core.v_sales
GROUP BY customer_id, customer, country
ORDER BY total_spent DESC;

CREATE OR REPLACE VIEW core.v_sales_by_category AS
SELECT
    category,
    COUNT(DISTINCT product_id) AS products,
    SUM(quantity)              AS quantity_sold,
    ROUND(SUM(line_total), 2)  AS revenue
FROM core.v_sales
GROUP BY category
ORDER BY revenue DESC;
