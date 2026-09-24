"""Tests for the cleaning and transform steps.

No database involved: these work on DataFrames built by hand, which is
possible because clean.py and transform.py are pure functions.

    make test
"""

import pandas as pd
import pytest

from src import clean, transform

# --- Parsers -------------------------------------------------------------

def test_parse_dates_accepts_all_three_formats():
    dates = clean.parse_dates(pd.Series(["2024-03-15", "15/03/2024", "15-03-2024"]))
    assert (dates == pd.Timestamp("2024-03-15")).all()


def test_parse_dates_returns_nat_when_unreadable():
    assert clean.parse_dates(pd.Series(["unknown date", ""])).isna().all()


@pytest.mark.parametrize(("raw", "expected"), [
    ("89.90", 89.90),
    ("89,90", 89.90),
    ("89,90 EUR", 89.90),
    ("1 299,00 EUR", 1299.00),
])
def test_parse_amounts_handles_common_formats(raw, expected):
    assert clean.parse_amounts(pd.Series([raw])).iloc[0] == pytest.approx(expected)


def test_parse_amounts_returns_nan_when_empty():
    assert clean.parse_amounts(pd.Series([""])).isna().all()


def test_tidy_spaces_leaves_capitalisation_alone():
    result = clean.tidy_spaces(pd.Series(["  SSD 1TB ", "USB  hub"]))
    assert result.tolist() == ["SSD 1TB", "USB hub"]


def test_titlecase_capitalises_each_word():
    assert clean.titlecase(pd.Series(["  AMINA ", "amina"])).tolist() == ["Amina", "Amina"]


# --- Customers -----------------------------------------------------------

def raw_customers(**overrides):
    data = {
        "customer_id": ["1", "2", "3"],
        "first_name": ["  amina ", "Lucas", "Fatou"],
        "last_name": ["Diallo", "Martin", "Ben Ali"],
        "email": ["AMINA@EXAMPLE.COM", "lucas@example.com", "fatou@example.com"],
        "city": ["Paris", "Lyon", "Tunis"],
        "country": ["France", "", "Tunisia"],
        "signup_date": ["2024-01-01", "01/02/2024", "2024-03-01"],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_customer_email_is_lowercased():
    data, _ = clean.clean_customers(raw_customers())
    assert data.loc[0, "email"] == "amina@example.com"


def test_customer_name_is_normalised():
    data, _ = clean.clean_customers(raw_customers())
    assert data.loc[0, "first_name"] == "Amina"


def test_missing_country_becomes_unknown():
    data, _ = clean.clean_customers(raw_customers())
    assert data.loc[1, "country"] == "Unknown"


def test_invalid_email_is_dropped():
    data, log = clean.clean_customers(
        raw_customers(email=["not-an-email", "lucas@example.com", "fatou@example.com"])
    )
    assert len(data) == 2
    assert ("missing or invalid email", 1) in log


def test_exact_duplicate_customer_rows_are_dropped():
    raw = pd.concat([raw_customers(), raw_customers().head(1)], ignore_index=True)
    data, _ = clean.clean_customers(raw)
    assert len(data) == 3


def test_same_email_in_different_case_is_one_customer():
    raw = raw_customers(email=["amina@example.com", "AMINA@EXAMPLE.COM", "fatou@example.com"])
    data, _ = clean.clean_customers(raw)
    assert len(data) == 2


# --- Products ------------------------------------------------------------

def raw_products(**overrides):
    data = {
        "product_id": ["1", "2", "3"],
        "product_name": ["SSD 1TB", "Wireless  mouse", "Monitor"],
        "category": ["STORAGE", " storage ", "Monitors"],
        "unit_price": ["89.90", "34,50 EUR", "249.00"],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_product_name_keeps_its_acronyms():
    """Title-casing would turn 'SSD 1TB' into 'Ssd 1Tb'."""
    data, _ = clean.clean_products(raw_products())
    assert data["product_name"].tolist() == ["SSD 1TB", "Wireless mouse", "Monitor"]


def test_categories_are_harmonised():
    data, _ = clean.clean_products(raw_products())
    assert data.loc[0, "category"] == data.loc[1, "category"] == "Storage"


@pytest.mark.parametrize("price", ["-34.50", "0", ""])
def test_invalid_price_rejects_the_product(price):
    data, log = clean.clean_products(raw_products(unit_price=["89.90", price, "249.00"]))
    assert len(data) == 2
    assert ("missing, zero or negative price", 1) in log


# --- Orders --------------------------------------------------------------

def raw_orders(**overrides):
    data = {
        "order_id": ["1000", "1000", "1001"],
        "customer_id": ["1", "1", "2"],
        "order_date": ["2024-01-15", "2024-01-15", "16/01/2024"],
        "status": ["DELIVERED", "delivered", "shipped"],
        "product_id": ["1", "2", "1"],
        "quantity": ["2", "1", "3"],
        "unit_price": ["89.90", "", "89.90"],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_status_is_lowercased():
    data, _ = clean.clean_orders(raw_orders())
    assert set(data["status"]) == {"delivered", "shipped"}


def test_unknown_status_becomes_pending():
    data, _ = clean.clean_orders(raw_orders(status=["completed", "delivered", "shipped"]))
    assert data.loc[0, "status"] == "pending"


@pytest.mark.parametrize("quantity", ["-1", "0"])
def test_impossible_quantity_is_dropped(quantity):
    data, log = clean.clean_orders(raw_orders(quantity=["2", quantity, "3"]))
    assert len(data) == 2
    assert ("zero, negative or unreadable quantity", 1) in log


def test_unreadable_date_is_dropped():
    data, _ = clean.clean_orders(raw_orders(order_date=["2024-01-15", "???", "16/01/2024"]))
    assert len(data) == 2


def test_missing_price_is_kept_for_transform_to_fill():
    data, _ = clean.clean_orders(raw_orders())
    assert len(data) == 3
    assert data["unit_price"].isna().sum() == 1


# --- Transform -----------------------------------------------------------

@pytest.fixture
def clean_tables():
    customers, _ = clean.clean_customers(raw_customers())
    products, _ = clean.clean_products(raw_products())
    orders, _ = clean.clean_orders(raw_orders())
    return customers, products, orders


def test_missing_price_is_filled_from_the_catalogue(clean_tables):
    tables, _ = transform.transform(*clean_tables)
    items = tables["order_items"]
    assert items["unit_price"].notna().all()
    assert items.loc[items["product_id"] == 2, "unit_price"].iloc[0] == pytest.approx(34.50)


def test_orders_are_split_from_their_lines(clean_tables):
    tables, _ = transform.transform(*clean_tables)
    assert len(tables["orders"]) == 2       # three lines across two orders
    assert len(tables["order_items"]) == 3
    assert tables["orders"]["order_id"].is_unique


def test_orphan_order_is_dropped(clean_tables):
    customers, products, orders = clean_tables
    orders.loc[len(orders)] = {
        "order_id": 9999, "customer_id": 7777, "order_date": pd.Timestamp("2024-05-01"),
        "status": "delivered", "product_id": 1, "quantity": 1, "unit_price": 89.90,
    }
    tables, log = transform.transform(customers, products, orders)
    assert 9999 not in tables["orders"]["order_id"].values
    assert ("orphan order (customer does not exist)", 1) in log


def test_line_with_unknown_product_is_dropped(clean_tables):
    customers, products, orders = clean_tables
    orders.loc[len(orders)] = {
        "order_id": 1001, "customer_id": 2, "order_date": pd.Timestamp("2024-01-16"),
        "status": "shipped", "product_id": 8888, "quantity": 1, "unit_price": 10.0,
    }
    tables, log = transform.transform(customers, products, orders)
    assert 8888 not in tables["order_items"]["product_id"].values
    assert ("orphan line (product does not exist)", 1) in log


def test_product_repeated_in_one_order_has_its_quantities_merged(clean_tables):
    customers, products, orders = clean_tables
    orders.loc[len(orders)] = {
        "order_id": 1000, "customer_id": 1, "order_date": pd.Timestamp("2024-01-15"),
        "status": "delivered", "product_id": 1, "quantity": 5, "unit_price": 89.90,
    }
    tables, _ = transform.transform(customers, products, orders)
    items = tables["order_items"]
    line = items[(items["order_id"] == 1000) & (items["product_id"] == 1)]
    assert len(line) == 1
    assert line["quantity"].iloc[0] == 7  # 2 + 5
