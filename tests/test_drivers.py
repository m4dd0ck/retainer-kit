import pytest

from retainer_kit.drivers import customer_shift, product_movers, sales_change
from retainer_kit.metrics import CustomerMix, MonthSummary, customer_mix
from retainer_kit.shopify import Store


def summary(month: str, sales: float, orders: int) -> MonthSummary:
    return MonthSummary(month, sales, orders, units=0, discounts=0, refunds=0)


@pytest.mark.parametrize(
    ("base", "current"),
    [((1000.0, 10), (1500.0, 12)), ((1000.0, 10), (800.0, 16)), ((500.0, 5), (500.0, 5))],
)
def test_effects_add_up_to_the_change(base: tuple[float, int], current: tuple[float, int]) -> None:
    change = sales_change(summary("2025-05", *current), summary("2025-04", *base))
    parts = change.orders_effect + change.aov_effect + change.interaction
    assert parts == pytest.approx(change.change)


def test_more_orders_at_the_same_value_is_all_orders_effect() -> None:
    change = sales_change(summary("2025-05", 1200.0, 12), summary("2025-04", 1000.0, 10))
    assert change.orders_effect == pytest.approx(200.0)
    assert change.aov_effect == pytest.approx(0.0)
    assert change.percent == pytest.approx(0.2)


def test_customer_shift() -> None:
    before = CustomerMix(5, 5, 300.0, 700.0, 5, 10)
    after = CustomerMix(8, 4, 500.0, 650.0, 4, 12)
    shift = customer_shift(after, before)
    assert (shift.new_sales_change, shift.returning_sales_change) == (200.0, -50.0)


def test_product_movers(store: Store) -> None:
    assert product_movers(store, "2025-05") == [("Trail tent", 100.0), ("Camp mug", 40.0)]
    assert customer_mix(store, "2025-05").orders == 3
