from pathlib import Path

import pytest
from conftest import write_export

from retainer_kit.shopify import ExportError, load_store

ORDER = {
    "name": "#1001",
    "email": "Ana@Mail.com",
    "created": "2025-05-03",
    "subtotal": "50.00",
    "lines": [("TENT-1", "Trail tent", 1, "40.00"), ("MUG-1", "Camp mug", 2, "5.00")],
}


def test_order_fields_are_restored_for_every_line(tmp_path: Path) -> None:
    store = load_store([write_export(tmp_path / "may.csv", [ORDER])])
    assert store.query("select order_name, email, month, net_sales from orders") == [
        ("#1001", "ana@mail.com", "2025-05", 50)
    ]
    assert store.query("select sku, qty from order_lines order by sku") == [
        ("MUG-1", 2),
        ("TENT-1", 1),
    ]


def test_newest_export_wins_for_an_order_in_two_files(tmp_path: Path) -> None:
    first = write_export(tmp_path / "a_may.csv", [ORDER])
    later = write_export(tmp_path / "b_june.csv", [{**ORDER, "refunded": "10.00"}])
    store = load_store([first, later])
    assert store.query("select count(*), max(net_sales) from orders") == [(1, 40)]


def test_non_shopify_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "x.csv").write_text("order,amount\n1,5\n")
    with pytest.raises(ExportError, match="missing columns"):
        load_store([tmp_path / "x.csv"])
