"""Load Shopify "Export orders" CSVs into DuckDB as one row per order and one per line item.

Shopify writes one row per line item and fills the order-level fields (email, totals, status)
only on each order's first row. Taking each order's non-blank value per field restores them for
every order, whatever the row order in the file.

Net sales here are ``Subtotal - Refunded Amount``: after discounts, before shipping and tax,
less refunds. That is the figure most store owners mean by sales.
"""

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

REQUIRED_COLUMNS = [
    "Name", "Email", "Financial Status", "Created at", "Currency", "Subtotal", "Shipping",
    "Taxes", "Total", "Discount Code", "Discount Amount", "Lineitem quantity", "Lineitem name",
    "Lineitem price", "Lineitem sku", "Billing Country", "Refunded Amount", "Cancelled at",
]  # fmt: skip


class ExportError(ValueError):
    """Raised when the files are not Shopify order exports."""


@dataclass
class Store:
    """Orders and line items in an in-memory DuckDB database."""

    connection: duckdb.DuckDBPyConnection
    excluded: dict[str, int] = field(default_factory=dict)

    def query(self, sql: str, params: list[object] | None = None) -> list[tuple[object, ...]]:
        return self.connection.execute(sql, params or []).fetchall()


def _money(column: str) -> str:
    return f"""coalesce(try_cast(max(nullif(trim("{column}"), '')) as decimal(12, 2)), 0)"""


def _text(column: str) -> str:
    return f"""max(nullif(trim("{column}"), ''))"""


def load_store(export_paths: list[Path]) -> Store:
    """Load one or more order exports (overlapping periods are fine).

    Raises:
        ExportError: If no files are given or required Shopify columns are missing.
    """
    if not export_paths:
        raise ExportError("No order exports found")
    connection = duckdb.connect()
    connection.execute(
        """create table raw_rows as
        select *, filename as source_file
        from read_csv(?, all_varchar = true, header = true, filename = true,
                      union_by_name = true)""",
        [[str(p) for p in export_paths]],
    )
    columns = {row[0] for row in connection.execute("describe raw_rows").fetchall()}
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise ExportError(f"Not a Shopify orders export; missing columns: {', '.join(missing)}")

    # An order can appear in several monthly exports; the newest file has its latest state
    # (refunds, cancellations), so only that file's rows are kept for each order.
    connection.execute(
        """create table order_rows as
        select raw_rows.* from raw_rows
        inner join (select "Name", max(source_file) as source_file from raw_rows group by 1)
            as latest using ("Name", source_file)"""
    )
    connection.execute(
        f"""create table all_orders as
        select
            "Name" as order_name,
            lower({_text("Email")}) as email,
            cast(substr({_text("Created at")}, 1, 10) as date) as created_date,
            strftime(cast(substr({_text("Created at")}, 1, 10) as date), '%Y-%m') as month,
            {_text("Financial Status")} as financial_status,
            {_text("Currency")} as currency,
            {_money("Subtotal")} as subtotal,
            {_money("Shipping")} as shipping,
            {_money("Taxes")} as taxes,
            {_money("Total")} as total,
            {_text("Discount Code")} as discount_code,
            {_money("Discount Amount")} as discount_amount,
            {_money("Refunded Amount")} as refunded,
            {_money("Subtotal")} - {_money("Refunded Amount")} as net_sales,
            {_text("Billing Country")} as country,
            {_text("Cancelled at")} is not null as is_cancelled
        from order_rows
        group by "Name" """
    )
    connection.execute(
        """create table all_lines as
        select
            "Name" as order_name,
            nullif(trim("Lineitem sku"), '') as sku,
            trim("Lineitem name") as product,
            try_cast("Lineitem quantity" as integer) as qty,
            try_cast("Lineitem price" as decimal(12, 2)) as price
        from order_rows
        where nullif(trim("Lineitem name"), '') is not null"""
    )
    connection.execute("create view orders as select * from all_orders")
    connection.execute("create view order_lines as select * from all_lines")
    return Store(connection)
