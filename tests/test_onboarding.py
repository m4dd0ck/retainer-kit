"""Taking on a second client is a config file and an export, never a code change."""

from pathlib import Path

from conftest import write_export
from typer.testing import CliRunner

from retainer_kit.cli import app


def test_second_client_end_to_end_through_the_cli(tmp_path: Path) -> None:
    client = tmp_path / "clients" / "hollow-tea"
    runner = CliRunner()
    assert runner.invoke(app, ["init", str(client), "--name", "Hollow Tea Co"]).exit_code == 0

    config = client / "client.toml"
    config.write_text(config.read_text().replace('currency = "USD"', 'currency = "GBP"'))
    orders = [
        {"name": f"#{n}", "email": f"c{n % 7}@tea.example",
         "created": f"2025-0{3 + n % 2}-1{n % 9}", "subtotal": "24.00", "country": "GB",
         "lines": [("TEA-EB", "Earl Grey tin", 2, "12.00")]}
        for n in range(40)
    ]  # fmt: skip
    write_export(client / "exports" / "orders_export.csv", orders)

    result = runner.invoke(app, ["report", str(client), "--month", "2025-04"])
    assert result.exit_code == 0, result.output
    html = (client / "reports" / "2025-04.html").read_text()
    assert "Hollow Tea Co" in html
    assert "£480" in html  # 20 April orders x £24, in the client's currency


def test_report_for_an_unknown_client_is_a_clear_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["report", str(tmp_path / "nobody"), "--month", "2025-04"])
    assert result.exit_code != 0
    assert "retainer init" in result.output
