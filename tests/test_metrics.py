"""Metrics checked against numbers worked out by hand from a small fixture."""

from pathlib import Path

import pytest
from conftest import write_export

from retainer_kit.metrics import countries, month_summary, previous_month, top_products, trend
from retainer_kit.shopify import Store, load_store

TENT = ("TENT-1", "Trail tent", 1, "100.00")
MUG = ("MUG-1", "Camp mug", 2, "10.00")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    orders = [
        # April: one order, 100 in sales
        {"name": "#1", "email": "a@x.com", "created": "2025-04-10", "subtotal": "100",
         "lines": [TENT]},
        # May: three orders; one discounted by 20, one refunded 30, one from Canada
        {"name": "#2", "email": "a@x.com", "created": "2025-05-02", "subtotal": "120",
         "discount": "20", "code": "SPRING20", "lines": [TENT, MUG]},
        {"name": "#3", "email": "b@x.com", "created": "2025-05-09", "subtotal": "100",
         "refunded": "30", "lines": [TENT]},
        {"name": "#4", "email": "c@x.com", "created": "2025-05-20", "subtotal": "20",
         "country": "CA", "lines": [MUG]},
    ]  # fmt: skip
    return load_store([write_export(tmp_path / "orders.csv", orders)])


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
