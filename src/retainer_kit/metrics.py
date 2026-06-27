"""The numbers in a monthly report, computed from a loaded Store."""

from dataclasses import dataclass
from decimal import Decimal

from retainer_kit.shopify import Store


def as_float(value: object) -> float:
    """DuckDB number (int, float or Decimal) as float; NULL and anything else as 0."""
    return float(value) if isinstance(value, (int, float, Decimal)) else 0.0


def as_int(value: object) -> int:
    return int(value) if isinstance(value, (int, float, Decimal)) else 0


def previous_month(month: str, back: int = 1) -> str:
    """``2025-03`` minus ``back`` months, as YYYY-MM."""
    year, number = (int(part) for part in month.split("-"))
    index = year * 12 + number - 1 - back
    return f"{index // 12}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class MonthSummary:
    month: str
    net_sales: float
    orders: int
    units: int
    discounts: float
    refunds: float

    @property
    def aov(self) -> float:
        """Average order value: net sales per order."""
        return self.net_sales / self.orders if self.orders else 0.0

    @property
    def discount_share(self) -> float:
        """Discounts as a share of sales before discounts."""
        gross = self.net_sales + self.refunds + self.discounts
        return self.discounts / gross if gross else 0.0


@dataclass(frozen=True)
class ProductRow:
    product: str
    units: int
    sales: float
    prior_sales: float


def month_summary(store: Store, month: str) -> MonthSummary | None:
    """Headline numbers for one month, or None if the month has no orders."""
    row = store.query(
        """select sum(net_sales), count(*), sum(discount_amount), sum(refunded)
        from orders where month = ?""",
        [month],
    )[0]
    if not row[1]:
        return None
    units = store.query(
        """select coalesce(sum(qty), 0) from order_lines
        where order_name in (select order_name from orders where month = ?)""",
        [month],
    )[0][0]
    return MonthSummary(
        month=month,
        net_sales=as_float(row[0]),
        orders=as_int(row[1]),
        units=as_int(units),
        discounts=as_float(row[2]),
        refunds=as_float(row[3]),
    )


def trend(store: Store, end_month: str, months: int = 12) -> list[tuple[str, float, int]]:
    """(month, net sales, orders) for the ``months`` months ending at ``end_month``."""
    wanted = [previous_month(end_month, back) for back in range(months - 1, -1, -1)]
    rows = {
        str(m): (as_float(s), as_int(o))
        for m, s, o in store.query("select month, sum(net_sales), count(*) from orders group by 1")
    }
    return [(m, *rows.get(m, (0.0, 0))) for m in wanted]


def top_products(store: Store, month: str, limit: int = 5) -> list[ProductRow]:
    """Best sellers by line value this month, with last month's sales alongside."""
    rows = store.query(
        """with sales as (
            select orders.month, lines.product, sum(lines.qty) as units,
                   sum(lines.qty * lines.price) as value
            from order_lines as lines join orders using (order_name)
            group by all
        )
        select now.product, now.units, now.value, coalesce(prior.value, 0)
        from sales as now
        left join sales as prior on prior.product = now.product and prior.month = ?
        where now.month = ?
        order by now.value desc, now.product
        limit ?""",
        [previous_month(month), month, limit],
    )
    return [ProductRow(str(p), as_int(u), as_float(v), as_float(pv)) for p, u, v, pv in rows]


def countries(store: Store, month: str, limit: int = 5) -> list[tuple[str, float]]:
    """Net sales by billing country this month, largest first."""
    rows = store.query(
        """select coalesce(country, 'Unknown'), sum(net_sales) from orders
        where month = ? group by 1 order by 2 desc limit ?""",
        [month, limit],
    )
    return [(str(c), as_float(s)) for c, s in rows]


@dataclass(frozen=True)
class CustomerMix:
    """New vs returning, where "new" means first order in the exports provided."""

    new_customers: int
    returning_customers: int
    new_sales: float
    returning_sales: float
    returning_orders: int
    orders: int

    @property
    def repeat_order_share(self) -> float:
        """Share of this month's orders placed by returning customers."""
        return self.returning_orders / self.orders if self.orders else 0.0


FIRST_ORDERS = """
    select email, min(month) as first_month from orders where email is not null group by email
"""


def customer_mix(store: Store, month: str) -> CustomerMix:
    row = store.query(
        f"""with first as ({FIRST_ORDERS})
        select
            count(distinct email) filter (where first.first_month = orders.month),
            count(distinct email) filter (where first.first_month < orders.month),
            sum(net_sales) filter (where first.first_month = orders.month),
            sum(net_sales) filter (where first.first_month < orders.month),
            count(*) filter (where first.first_month < orders.month),
            count(*)
        from orders left join first using (email)
        where orders.month = ?""",
        [month],
    )[0]
    return CustomerMix(
        new_customers=as_int(row[0]),
        returning_customers=as_int(row[1]),
        new_sales=as_float(row[2]),
        returning_sales=as_float(row[3]),
        returning_orders=as_int(row[4]),
        orders=as_int(row[5]),
    )


@dataclass(frozen=True)
class CohortRow:
    cohort: str
    customers: int
    retention: list[float | None]  # share ordering again k months later; None = not yet happened


def cohorts(store: Store, end_month: str, count: int = 6, horizon: int = 6) -> list[CohortRow]:
    """Customers grouped by first-order month; who ordered again 1..horizon months later."""
    # The latest ``count`` cohorts that have at least one later month to look at.
    wanted = [previous_month(end_month, back) for back in range(count, 0, -1)]
    rows = store.query(
        f"""with first as ({FIRST_ORDERS}),
        activity as (select distinct email, month from orders where email is not null)
        select first.first_month, activity.month, count(distinct activity.email)
        from first join activity using (email)
        group by all""",
    )
    active: dict[tuple[str, str], int] = {(str(c), str(m)): as_int(n) for c, m, n in rows}
    result = []
    for cohort in wanted:
        size = active.get((cohort, cohort), 0)
        if not size:
            continue
        retention: list[float | None] = []
        for k in range(1, horizon + 1):
            later = _add_months(cohort, k)
            retention.append(None if later > end_month else active.get((cohort, later), 0) / size)
        result.append(CohortRow(cohort, size, retention))
    return result


def _add_months(month: str, forward: int) -> str:
    return previous_month(month, back=-forward)
