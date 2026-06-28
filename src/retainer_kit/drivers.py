"""Why sales moved: split a change into more orders vs bigger orders, and find what shifted.

    sales = orders x average order value
    change = (Δorders x old AOV) + (ΔAOV x old orders) + (Δorders x ΔAOV)

The three parts add up to the actual change exactly, so the report never shows effects that
don't sum to the headline number.
"""

from dataclasses import dataclass

from retainer_kit.metrics import CustomerMix, MonthSummary, as_float, previous_month
from retainer_kit.shopify import Store


@dataclass(frozen=True)
class SalesChange:
    """How sales moved from ``base`` to ``current``."""

    base_month: str
    base_sales: float
    change: float
    orders_effect: float
    aov_effect: float
    interaction: float

    @property
    def percent(self) -> float | None:
        return self.change / self.base_sales if self.base_sales else None


def sales_change(current: MonthSummary, base: MonthSummary) -> SalesChange:
    orders_delta = current.orders - base.orders
    aov_delta = current.aov - base.aov
    return SalesChange(
        base_month=base.month,
        base_sales=base.net_sales,
        change=current.net_sales - base.net_sales,
        orders_effect=orders_delta * base.aov,
        aov_effect=aov_delta * base.orders,
        interaction=orders_delta * aov_delta,
    )


@dataclass(frozen=True)
class CustomerShift:
    new_sales_change: float
    returning_sales_change: float


def customer_shift(current: CustomerMix, base: CustomerMix) -> CustomerShift:
    return CustomerShift(
        new_sales_change=current.new_sales - base.new_sales,
        returning_sales_change=current.returning_sales - base.returning_sales,
    )


def product_movers(store: Store, month: str, limit: int = 3) -> list[tuple[str, float]]:
    """Products with the largest change in line sales vs the previous month, either way."""
    rows = store.query(
        """with sales as (
            select orders.month, lines.product, sum(lines.qty * lines.price) as value
            from order_lines as lines join orders using (order_name)
            where orders.month in (?, ?)
            group by all
        )
        select product,
               coalesce(sum(value) filter (where month = ?), 0)
               - coalesce(sum(value) filter (where month = ?), 0) as change
        from sales group by product
        having change != 0
        order by abs(change) desc, product
        limit ?""",
        [month, previous_month(month), month, previous_month(month), limit],
    )
    return [(str(product), as_float(change)) for product, change in rows]
