"""Generate the raw CSV files in data/raw/.

Realistic defects are injected on purpose - duplicates, mixed date formats,
missing values, negative quantities, orphan rows. Without them the cleaning
step would have nothing to do.

Standard library only, so it runs before `pip install`.

    python scripts/generate_raw_data.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Fixed seed: two runs produce identical files
random.seed(42)

FIRST_NAMES = ["Amina", "Lucas", "Fatou", "Hugo", "Sofia", "Karim", "Lea", "Yanis",
               "Chloe", "Mehdi", "Ines", "Noah", "Sarah", "Adam", "Nour", "Gabriel",
               "Lina", "Rayan", "Emma", "Ilyes", "Jade", "Samir", "Alice", "Omar"]
LAST_NAMES = ["Diallo", "Martin", "Ben Ali", "Dubois", "Rossi", "Haddad", "Bernard",
              "Moreau", "Silva", "Traore", "Lefevre", "Nakamura", "Garcia", "Petit"]
PLACES = [("Paris", "France"), ("Lyon", "France"), ("Tunis", "Tunisia"),
          ("Casablanca", "Morocco"), ("Dakar", "Senegal"), ("Brussels", "Belgium"),
          ("Geneva", "Switzerland"), ("Montreal", "Canada")]

PRODUCTS = [
    ("Mechanical keyboard", "Peripherals", 89.90),
    ("Wireless mouse", "Peripherals", 34.50),
    ("Headphones", "Audio", 129.00),
    ("Bluetooth speaker", "Audio", 74.99),
    ("27-inch monitor", "Monitors", 249.00),
    ("34-inch monitor", "Monitors", 519.00),
    ("HD webcam", "Peripherals", 59.90),
    ("USB microphone", "Audio", 99.00),
    ("SSD 1TB", "Storage", 109.00),
    ("SSD 2TB", "Storage", 189.00),
    ("USB stick 128GB", "Storage", 19.90),
    ("USB-C hub", "Accessories", 39.90),
    ("Laptop stand", "Accessories", 44.00),
    ("XL mouse pad", "Accessories", 24.90),
    ("65W charger", "Accessories", 49.90),
    ("Docking station", "Peripherals", 179.00),
    ("Desk lamp", "Accessories", 54.90),
    ("Ergonomic chair", "Furniture", 329.00),
    ("Standing desk", "Furniture", 599.00),
    ("Footrest", "Furniture", 39.00),
]

STATUSES = ["delivered"] * 14 + ["shipped"] * 3 + ["pending"] * 2 + ["cancelled", "returned"]


def messy_case(value):
    """Make capitalisation and spacing inconsistent, like a sloppy export."""
    roll = random.random()
    if roll < 0.10:
        return value.upper()
    if roll < 0.18:
        return f"  {value} "
    if roll < 0.24:
        return value.lower()
    return value


def messy_date(day):
    """Mix three date formats, which is what real exports do."""
    roll = random.random()
    if roll < 0.70:
        return day.isoformat()           # 2024-03-15
    if roll < 0.90:
        return day.strftime("%d/%m/%Y")  # 15/03/2024
    return day.strftime("%d-%m-%Y")      # 15-03-2024


def make_customers(count=45):
    customers = []
    for customer_id in range(1, count + 1):
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        city, country = random.choice(PLACES)
        email = f"{first}.{last}@example.com".replace(" ", "").lower()
        customers.append({
            "customer_id": customer_id,
            "first_name": messy_case(first),
            "last_name": messy_case(last),
            # uppercase emails become duplicates you cannot spot by eye
            "email": email.upper() if random.random() < 0.12 else email,
            "city": city,
            "country": "" if random.random() < 0.08 else country,
            "signup_date": messy_date(date(2023, 1, 1) + timedelta(days=random.randint(0, 700))),
        })

    customers += [dict(c) for c in random.sample(customers, 3)]   # duplicate rows
    customers.append({                                            # unusable: no email
        "customer_id": 999, "first_name": "Test", "last_name": "Anonymous",
        "email": "", "city": "Paris", "country": "France", "signup_date": "2024-01-01",
    })
    repeated = dict(customers[0])                                 # same id, newer row
    repeated["city"], repeated["signup_date"] = "Lille", "2024-06-01"
    customers.append(repeated)
    return customers


def make_products():
    products = []
    for product_id, (name, category, price) in enumerate(PRODUCTS, start=1):
        roll = random.random()
        if roll < 0.15:
            price_text = f"{price:.2f} EUR".replace(".", ",")
        elif roll < 0.30:
            price_text = f"{price:.2f}".replace(".", ",")
        else:
            price_text = f"{price:.2f}"
        products.append({
            "product_id": product_id,
            "product_name": name,
            "category": messy_case(category),
            "unit_price": price_text,
        })

    products.append({                                             # invalid price
        "product_id": 99, "product_name": "Ghost product",
        "category": "Unknown", "unit_price": "-10.00",
    })
    products.append(dict(products[2]))                            # duplicate row
    return products


def make_orders(customers, products, count=520):
    customer_ids = sorted({int(c["customer_id"]) for c in customers if c["customer_id"] != 999})
    catalogue = {
        int(p["product_id"]): float(p["unit_price"].replace(" EUR", "").replace(",", "."))
        for p in products
        if not p["unit_price"].startswith("-")
    }
    product_ids = sorted(catalogue)

    rows = []
    start = date(2024, 1, 1)
    for order_id in range(1000, 1000 + count):
        customer = random.choice(customer_ids)
        day = start + timedelta(days=random.randint(0, 640))
        status = random.choice(STATUSES)
        status = status.upper() if random.random() < 0.10 else status

        # More items per order in November and December
        max_items = 4 if day.month in (11, 12) else 3
        for product in random.sample(product_ids, random.randint(1, max_items)):
            quantity = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 13, 7, 5])[0]
            if random.random() < 0.02:
                quantity = random.choice([0, -1, -2])             # impossible quantity
            rows.append({
                "order_id": order_id,
                "customer_id": customer,
                "order_date": messy_date(day),
                "status": status,
                "product_id": product,
                "quantity": quantity,
                # missing prices have to be recovered from the catalogue
                "unit_price": "" if random.random() < 0.03 else f"{catalogue[product]:.2f}",
            })

    rows += [dict(row) for row in random.sample(rows, 15)]         # duplicate rows
    for order_id in (9001, 9002):                                 # customer 7777 does not exist
        rows.append({
            "order_id": order_id, "customer_id": 7777, "order_date": "2025-02-14",
            "status": "delivered", "product_id": random.choice(product_ids),
            "quantity": 1, "unit_price": "",
        })
    rows.append({                                                 # product 8888 does not exist
        "order_id": 9003, "customer_id": random.choice(customer_ids),
        "order_date": "2025-03-03", "status": "delivered",
        "product_id": 8888, "quantity": 1, "unit_price": "29.90",
    })
    rows.append({                                                 # unreadable date
        "order_id": 9004, "customer_id": random.choice(customer_ids),
        "order_date": "unknown date", "status": "delivered",
        "product_id": random.choice(product_ids), "quantity": 2, "unit_price": "",
    })

    random.shuffle(rows)
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {path.name}: {len(rows)} rows")


def main():
    print("Generating raw CSV files (with deliberate defects)...")
    customers = make_customers()
    products = make_products()
    write_csv(RAW_DIR / "customers.csv", customers)
    write_csv(RAW_DIR / "products.csv", products)
    write_csv(RAW_DIR / "orders.csv", make_orders(customers, products))


if __name__ == "__main__":
    main()
