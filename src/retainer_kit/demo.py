"""A sample client: two years of Shopify exports for an outdoor gear store.

Planted so the report has real stories to tell: seasonal categories (tents in summer, jackets in
winter), a SPRING20 promotion in May 2025 (more orders, smaller baskets), and a
returning-customer program from March 2025. Also refunds, cancellations and test orders, as a
real store has. One export file per month, the way a client sends them.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from retainer_kit.config import CONFIG_FILE
from retainer_kit.shopify import REQUIRED_COLUMNS

FIRST_MONTH = date(2023, 7, 1)
LAST_MONTH = date(2025, 6, 1)
TEST_EMAIL = "test@fernway.example"
PROMO_MONTH = "2025-05"
LOYALTY_FROM = "2025-03"
HEADER = REQUIRED_COLUMNS + ["Paid at", "Fulfillment Status", "Source"]

# (sku, name, price, category)
PRODUCTS = [
    ("TNT-2P", "Ridge 2P tent", 289.00, "summer"),
    ("TNT-4P", "Basecamp 4P tent", 459.00, "summer"),
    ("BAG-3S", "Three-season sleeping bag", 139.00, "summer"),
    ("PAD-UL", "Ultralight sleeping pad", 89.00, "summer"),
    ("STV-CN", "Canister stove", 64.00, "summer"),
    ("JKT-DN", "Down jacket", 219.00, "winter"),
    ("JKT-SH", "Rain shell", 169.00, "winter"),
    ("GLV-WM", "Wool gloves", 34.00, "winter"),
    ("BNE-MR", "Merino beanie", 29.00, "winter"),
    ("MUG-TI", "Titanium mug", 32.00, "all"),
    ("LMP-HD", "Rechargeable headlamp", 49.00, "all"),
    ("BTL-1L", "Insulated bottle 1L", 38.00, "all"),
    ("SCK-HK", "Hiking socks (3 pack)", 27.00, "all"),
    ("PCK-30", "Daypack 30L", 119.00, "all"),
]
SEASON = {
    "summer": [0.5, 0.5, 0.8, 1.2, 1.6, 1.9, 2.0, 1.7, 1.1, 0.7, 0.5, 0.6],
    "winter": [1.2, 0.9, 0.7, 0.5, 0.3, 0.2, 0.2, 0.3, 0.7, 1.4, 1.9, 2.1],
    "all": [0.9, 0.9, 1.0, 1.0, 1.1, 1.1, 1.1, 1.1, 1.0, 1.0, 1.3, 1.5],
}
DEMAND = [0.8, 0.7, 0.85, 0.95, 1.05, 1.1, 1.1, 1.05, 0.95, 1.0, 1.35, 1.5]
COUNTRIES = {"US": 0.72, "CA": 0.14, "GB": 0.06, "AU": 0.04, "DE": 0.04}
CLIENT_TOML = f"""\
name = "Fernway Outdoor"
currency = "USD"
report_title = "Monthly performance"
brand_colour = "#2e5e4e"
monthly_sales_target = 110000
exclude_test_orders = true
test_order_emails = ["{TEST_EMAIL}"]
"""


def _months() -> list[date]:
    months, current = [], FIRST_MONTH
    while current <= LAST_MONTH:
        months.append(current)
        current = (current + timedelta(days=32)).replace(day=1)
    return months


def build_demo_client(client_dir: Path, seed: int = 21) -> Path:
    """Write client.toml and one export per month under ``client_dir``."""
    rng = random.Random(seed)
    (client_dir / "exports").mkdir(parents=True, exist_ok=True)
    (client_dir / CONFIG_FILE).write_text(CLIENT_TOML)
    customers: list[tuple[str, str]] = []  # (email, country)
    number = 1000
    for index, month_start in enumerate(_months()):
        month = month_start.strftime("%Y-%m")
        promo = month == PROMO_MONTH
        loyalty = month >= LOYALTY_FROM
        orders = round(310 * 1.018**index * DEMAND[month_start.month - 1] * (1.3 if promo else 1))
        returning_chance = 0.34 if loyalty else 0.24
        days = ((month_start + timedelta(days=32)).replace(day=1) - month_start).days
        rows: list[dict[str, object]] = []
        for _ in range(orders):
            number += 1
            if customers and rng.random() < returning_chance:
                # Reason: recent buyers are far likelier to come back than ones from a year ago;
                # an exponential pick over customer age gives a smooth retention curve.
                age = min(int(rng.expovariate(1 / 1200)), len(customers) - 1)
                email, country = customers[-1 - age]
            else:
                country = rng.choices(list(COUNTRIES), weights=list(COUNTRIES.values()))[0]
                email = f"customer{len(customers) + 1}@mail.example"
                customers.append((email, country))
            created = month_start + timedelta(days=rng.randrange(days))
            rows += _order_rows(
                rng, f"#{number}", email, country, created, month_start.month, promo
            )
        for extra in range(2):  # the store owner testing checkout
            number += 1
            test_day = month_start + timedelta(days=extra + 3)
            rows += _order_rows(rng, f"#{number}", TEST_EMAIL, "US", test_day, 1, False)
        _write(client_dir / "exports" / f"orders_export_{month}.csv", rows)
    return client_dir


def _order_rows(
    rng: random.Random,
    name: str,
    email: str,
    country: str,
    created: date,
    calendar_month: int,
    promo: bool,
) -> list[dict[str, object]]:
    weights = [SEASON[category][calendar_month - 1] for *_, category in PRODUCTS]
    count = rng.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]
    picked = rng.choices(PRODUCTS, weights=weights, k=count)
    lines = [(sku, product, rng.choice([1, 1, 1, 2]), price) for sku, product, price, _ in picked]
    if promo:  # promotion shoppers buy fewer big-ticket items
        lines = [line for line in lines if line[3] < 200] or lines[:1]
    gross = sum(qty * price for _, _, qty, price in lines)
    discount = round(gross * 0.2, 2) if promo and rng.random() < 0.75 else 0.0
    subtotal = gross - discount
    refunded = round(subtotal * rng.choice([1.0, 0.5]), 2) if rng.random() < 0.03 else 0.0
    cancelled = rng.random() < 0.01
    stamp = f"{created.isoformat()} {rng.randint(7, 22):02d}:{rng.randint(0, 59):02d}:00 -0400"
    rows = []
    for index, (sku, product, qty, price) in enumerate(lines):
        row: dict[str, object] = {column: "" for column in HEADER}
        row.update(
            {"Name": name, "Lineitem sku": sku, "Lineitem name": product,
             "Lineitem quantity": qty, "Lineitem price": f"{price:.2f}"}
        )  # fmt: skip
        if index == 0:  # Shopify fills order fields on the first line only
            row.update(
                {
                    "Email": email,
                    "Financial Status": "refunded" if refunded else "paid",
                    "Paid at": stamp,
                    "Created at": stamp,
                    "Currency": "USD",
                    "Subtotal": f"{subtotal:.2f}",
                    "Shipping": "0.00" if subtotal >= 100 else "8.00",
                    "Taxes": f"{subtotal * 0.07:.2f}",
                    "Total": f"{subtotal * 1.07 + (0 if subtotal >= 100 else 8):.2f}",
                    "Discount Code": "SPRING20" if discount else "",
                    "Discount Amount": f"{discount:.2f}",
                    "Billing Country": country,
                    "Refunded Amount": f"{refunded:.2f}",
                    "Cancelled at": stamp if cancelled else "",
                    "Fulfillment Status": "fulfilled",
                    "Source": "web",
                }
            )
        rows.append(row)
    return rows


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)
