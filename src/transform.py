"""Step 3: reshape the orders into proper tables.

orders.csv is flat - one row per product, with the customer and date repeated
on every row. That is not a valid relational model: if two rows of the same
order carry different dates, which one is true?

So it is split into:
    orders      - what describes the order (customer, date, status)
    order_items - what describes the lines (product, quantity, price)

Referential integrity is enforced here rather than left to PostgreSQL,
because the database would reject the whole batch over a single orphan row
and take the thousand valid rows down with it.
"""

import logging

from src.clean import keep_rows, log_drop

logger = logging.getLogger(__name__)


def transform(customers, products, orders):
    logger.info("Transforming %d order rows", len(orders))
    log = []

    # Fill missing prices from the product catalogue
    catalogue = products[["product_id", "unit_price"]].rename(
        columns={"unit_price": "catalogue_price"}
    )
    orders = orders.merge(catalogue, on="product_id", how="left")
    filled = orders["unit_price"].isna() & orders["catalogue_price"].notna()
    orders["unit_price"] = orders["unit_price"].fillna(orders["catalogue_price"])
    orders = orders.drop(columns="catalogue_price")
    if filled.any():
        logger.info("  filled %d missing prices from the catalogue", int(filled.sum()))
    orders = keep_rows(orders, orders["unit_price"].fillna(0) > 0,
                       "price missing from the catalogue too", log)

    orders = keep_rows(orders, orders["customer_id"].isin(customers["customer_id"]),
                       "orphan order (customer does not exist)", log)
    orders = keep_rows(orders, orders["product_id"].isin(products["product_id"]),
                       "orphan line (product does not exist)", log)

    # An order has one customer, date and status. If rows disagree, keep the first.
    headers = (
        orders.sort_values(["order_id", "order_date"])
        .drop_duplicates("order_id")[["order_id", "customer_id", "order_date", "status"]]
        .reset_index(drop=True)
    )

    # UNIQUE (order_id, product_id) forbids the same product twice in one order,
    # so those rows are merged by summing their quantities.
    before = len(orders)
    items = orders.groupby(["order_id", "product_id"], as_index=False).agg(
        quantity=("quantity", "sum"), unit_price=("unit_price", "first")
    )
    log_drop(log, "same product repeated in an order (quantities merged)", before - len(items))

    tables = {
        "customers": customers,
        "products": products,
        "orders": headers,
        "order_items": items,
    }
    for name, table in tables.items():
        logger.info("  %-12s %5d rows", name, len(table))
    return tables, log
