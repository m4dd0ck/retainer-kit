from pathlib import Path

import pytest
from conftest import write_export

from retainer_kit.config import init_client
from retainer_kit.report import ReportError, build_report

ORDERS = [
    {"name": "#1", "email": "a@x.com", "created": "2025-04-10", "subtotal": "100",
     "lines": [("TENT-1", "Trail <tent>", 1, "100.00")]},
    {"name": "#2", "email": "a@x.com", "created": "2025-05-02", "subtotal": "150",
     "lines": [("TENT-1", "Trail <tent>", 1, "150.00")]},
    {"name": "#3", "email": "qa@x.com", "created": "2025-05-03", "subtotal": "999",
     "lines": [("TENT-1", "Trail <tent>", 1, "999.00")]},
]  # fmt: skip


@pytest.fixture
def client(tmp_path: Path) -> Path:
    client_dir = tmp_path / "acme"
    init_client(client_dir, "Acme & Sons")
    config = client_dir / "client.toml"
    config.write_text(
        config.read_text().replace("test_order_emails = []", 'test_order_emails = ["qa@x.com"]')
    )
    write_export(client_dir / "exports" / "orders.csv", ORDERS)
    return client_dir


def test_report_is_written_with_escaped_names_and_exclusions(client: Path) -> None:
    html = build_report(client, "2025-05").read_text()
    assert "Acme &amp; Sons" in html
    assert "Trail &lt;tent&gt;" in html and "Trail <tent>" not in html
    assert "Net sales were $150 in May 2025, up 50% on April 2025." in html
    assert "1 test order." in html


def test_month_without_orders_is_refused(client: Path) -> None:
    with pytest.raises(ReportError, match="No orders in 2025-08"):
        build_report(client, "2025-08")


@pytest.mark.parametrize("month", ["../../x", "2025-5", "2025-13", "2025-05/../../x"])
def test_month_must_be_year_and_month(client: Path, month: str) -> None:
    with pytest.raises(ReportError, match="Month must look like"):
        build_report(client, month)
