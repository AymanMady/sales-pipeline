"""Step 2: clean the raw data.

Each function returns the clean rows plus a log of what it dropped and why,
so nothing disappears silently.

The functions are pure - DataFrame in, DataFrame out, no database - which is
what makes them easy to test.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

VALID_STATUSES = {"delivered", "shipped", "pending", "cancelled", "returned"}


# --- Helpers -------------------------------------------------------------

def log_drop(log, reason, dropped):
    if dropped:
        log.append((reason, dropped))
        logger.info("  dropped %4d rows: %s", dropped, reason)


def keep_rows(data, mask, reason, log):
    """Keep the rows matching mask, recording how many were dropped."""
    log_drop(log, reason, int((~mask).sum()))
    return data[mask]


def dedupe(data, reason, log, subset=None, keep="first"):
    before = len(data)
    data = data.drop_duplicates(subset=subset, keep=keep)
    log_drop(log, reason, before - len(data))
    return data


# --- Parsers -------------------------------------------------------------

def parse_dates(series):
    """Parse dates, trying each known format in turn.

    Real exports mix 2024-03-15, 15/03/2024 and 15-03-2024.
    Anything still unparsed becomes NaT.
    """
    text = series.astype(str).str.strip()
    result = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    for date_format in ("%d/%m/%Y", "%d-%m-%Y"):
        missing = result.isna()
        if not missing.any():
            break
        result[missing] = pd.to_datetime(text[missing], format=date_format, errors="coerce")
    return result


def parse_amounts(series):
    """Turn '89,90 EUR', '89.90' or '' into a number (or NaN)."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace("EUR", "", case=False, regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip(),
        errors="coerce",
    )


def parse_ids(series):
    """Parse ids into nullable integers, so missing ones stay visible."""
    return pd.to_numeric(series.astype(str).str.strip(), errors="coerce").astype("Int64")


def tidy_spaces(series):
    """Trim and collapse repeated spaces."""
    return series.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def titlecase(series):
    """Tidy spaces and capitalise each word.

    Proper nouns only: on a product name it would turn "SSD 1TB" into "Ssd 1Tb".
    """
    return tidy_spaces(series).str.title()


# --- Cleaning ------------------------------------------------------------

def clean_customers(raw):
    logger.info("Cleaning customers (%d rows)", len(raw))
    log, data = [], raw.copy()

    data = dedupe(data, "exact duplicate rows", log)

    data["customer_id"] = parse_ids(data["customer_id"])
    data = keep_rows(data, data["customer_id"].notna(), "missing or non-numeric customer_id", log)

    data["first_name"] = titlecase(data["first_name"])
    data["last_name"] = titlecase(data["last_name"])
    data["city"] = titlecase(data["city"])

    # Lowercase before comparing, otherwise "A@X.COM" and "a@x.com" look like
    # two different customers.
    data["email"] = data["email"].astype(str).str.strip().str.lower()
    valid = data["email"].str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", na=False)
    data = keep_rows(data, valid, "missing or invalid email", log)

    # A missing country is not worth dropping a customer over.
    country = titlecase(data["country"])
    data["country"] = country.where(country != "", "Unknown")

    data["signup_date"] = parse_dates(data["signup_date"])

    data = dedupe(data.sort_values("signup_date", na_position="first"),
                   "duplicate customer_id (keeping the most recent)", log,
                   subset=["customer_id"], keep="last")
    # email is UNIQUE in the database, so this has to be settled before loading
    data = dedupe(data, "duplicate email (keeping the first customer)", log, subset=["email"])

    columns = ["customer_id", "first_name", "last_name", "email",
               "city", "country", "signup_date"]
    data = data[columns].sort_values("customer_id").reset_index(drop=True)
    logger.info("Customers: %d clean rows", len(data))
    return data, log


def clean_products(raw):
    logger.info("Cleaning products (%d rows)", len(raw))
    log, data = [], raw.copy()

    data = dedupe(data, "exact duplicate rows", log)

    data["product_id"] = parse_ids(data["product_id"])
    data = keep_rows(data, data["product_id"].notna(), "missing or non-numeric product_id", log)

    # Spaces only, so acronyms like SSD or USB survive
    data["product_name"] = tidy_spaces(data["product_name"])
    category = titlecase(data["category"])
    data["category"] = category.where(category != "", "Unknown")

    # A negative or unreadable price would distort every revenue figure
    data["unit_price"] = parse_amounts(data["unit_price"])
    data = keep_rows(data, data["unit_price"].fillna(0) > 0, "missing, zero or negative price", log)

    data = dedupe(data, "duplicate product_id", log, subset=["product_id"], keep="last")

    columns = ["product_id", "product_name", "category", "unit_price"]
    data = data[columns].sort_values("product_id").reset_index(drop=True)
    logger.info("Products: %d clean rows", len(data))
    return data, log


def clean_orders(raw):
    logger.info("Cleaning orders (%d rows)", len(raw))
    log, data = [], raw.copy()

    data = dedupe(data, "exact duplicate rows", log)

    ids = ["order_id", "customer_id", "product_id"]
    for column in ids:
        data[column] = parse_ids(data[column])
    data = keep_rows(data, data[ids].notna().all(axis=1), "missing or non-numeric id", log)

    data["order_date"] = parse_dates(data["order_date"])
    data = keep_rows(data, data["order_date"].notna(), "unreadable date", log)

    data["status"] = data["status"].astype(str).str.strip().str.lower()
    unknown = ~data["status"].isin(VALID_STATUSES)
    if unknown.any():
        logger.warning("  %d unknown statuses set to 'pending'", int(unknown.sum()))
        data.loc[unknown, "status"] = "pending"

    # Zero or negative quantities are not sales
    data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    data = keep_rows(data, data["quantity"].fillna(0) > 0,
                 "zero, negative or unreadable quantity", log)
    data["quantity"] = data["quantity"].astype(int)

    # A missing price is not worth dropping the row: transform fills it in
    data["unit_price"] = parse_amounts(data["unit_price"])

    columns = ["order_id", "customer_id", "order_date", "status",
               "product_id", "quantity", "unit_price"]
    data = data[columns].reset_index(drop=True)
    logger.info("Orders: %d clean rows", len(data))
    return data, log
