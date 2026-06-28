"""Metrics checked against numbers worked out by hand from a small fixture."""

import pytest

from retainer_kit.metrics import (
    cohorts,
    countries,
    customer_mix,
    month_summary,
    previous_month,
    top_products,
    trend,
)
from retainer_kit.shopify import Store


def test_previous_month_crosses_years() -> None:
    assert previous_month("2025-01") == "2024-12"
    assert previous_month("2025-05", back=12) == "2024-05"


def test_month_summary(store: Store) -> None:
    may = month_summary(store, "2025-05")
    assert may is not None
    assert (may.net_sales, may.orders, may.units) == (210.0, 3, 6)  # 120 + 70 + 20
    assert may.aov == pytest.approx(70.0)
    assert may.discount_share == pytest.approx(20 / 260)  # 20 of 210 + 30 + 20
    assert month_summary(store, "2025-06") is None


def test_trend_fills_empty_months(store: Store) -> None:
    assert trend(store, "2025-06", months=3) == [
        ("2025-04", 100.0, 1),
        ("2025-05", 210.0, 3),
        ("2025-06", 0.0, 0),
    ]


def test_top_products_with_prior_month(store: Store) -> None:
    rows = top_products(store, "2025-05")
    assert [(r.product, r.units, r.sales, r.prior_sales) for r in rows] == [
        ("Trail tent", 2, 200.0, 100.0),
        ("Camp mug", 4, 40.0, 0.0),
    ]


def test_countries(store: Store) -> None:
    assert countries(store, "2025-05") == [("US", 190.0), ("CA", 20.0)]


def test_customer_mix(store: Store) -> None:
    mix = customer_mix(store, "2025-05")
    assert (mix.new_customers, mix.returning_customers) == (2, 1)  # a@ first ordered in April
    assert (mix.new_sales, mix.returning_sales) == (90.0, 120.0)
    assert mix.repeat_order_share == pytest.approx(1 / 3)


def test_cohorts_mark_future_months_as_unknown(store: Store) -> None:
    rows = cohorts(store, "2025-05", count=2, horizon=2)
    april = next(r for r in rows if r.cohort == "2025-04")
    assert april.customers == 1
    assert april.retention == [1.0, None]  # came back in May; June has not happened
