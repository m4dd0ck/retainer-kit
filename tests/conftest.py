import csv
from pathlib import Path

from retainer_kit.shopify import REQUIRED_COLUMNS

EXTRA = ["Paid at", "Fulfillment Status", "Source"]


def write_export(path: Path, orders: list[dict[str, object]]) -> Path:
    """Shopify-style export: one row per line item, order fields only on the first row.

    Each order dict: name, email, created, subtotal, discount, refunded, country, cancelled,
    code, lines=[(sku, product, qty, price)].
    """
    header = REQUIRED_COLUMNS + EXTRA
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for order in orders:
            for index, (sku, product, qty, price) in enumerate(order["lines"]):  # type: ignore[arg-type]
                row = {c: "" for c in header}
                row.update(
                    {"Name": order["name"], "Lineitem sku": sku, "Lineitem name": product,
                     "Lineitem quantity": qty, "Lineitem price": price}
                )  # fmt: skip
                if index == 0:
                    subtotal = float(order["subtotal"])  # type: ignore[arg-type]
                    row.update(
                        {
                            "Email": order["email"],
                            "Financial Status": "refunded" if order.get("refunded") else "paid",
                            "Created at": f"{order['created']} 10:15:00 -0400",
                            "Currency": "USD",
                            "Subtotal": f"{subtotal:.2f}",
                            "Shipping": "5.00",
                            "Taxes": f"{subtotal * 0.08:.2f}",
                            "Total": f"{subtotal * 1.08 + 5:.2f}",
                            "Discount Code": order.get("code", ""),
                            "Discount Amount": order.get("discount", "0"),
                            "Refunded Amount": order.get("refunded", "0"),
                            "Billing Country": order.get("country", "US"),
                            "Cancelled at": order.get("cancelled", ""),
                        }
                    )
                writer.writerow(row)
    return path
