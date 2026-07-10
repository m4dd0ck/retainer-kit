"""``retainer`` command line interface."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from retainer_kit.config import ConfigError, init_client
from retainer_kit.demo import build_demo_client
from retainer_kit.report import ReportError, build_report
from retainer_kit.shopify import ExportError
from retainer_kit.site import build_site

app = typer.Typer(help="Monthly retainer reports from Shopify exports.", no_args_is_help=True)
console = Console()


@app.command()
def init(
    client_dir: Annotated[Path, typer.Argument(help="New client folder, e.g. clients/acme")],
    name: Annotated[str, typer.Option(help="Client name on the report.")],
) -> None:
    """Set up a client: folder, exports/ and a starter client.toml."""
    try:
        path = init_client(client_dir, name)
    except ConfigError as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"Created {path}. Put Shopify order exports in {client_dir / 'exports'}.")


@app.command()
def report(
    client_dir: Annotated[Path, typer.Argument(help="Client folder.")],
    month: Annotated[str, typer.Option(help="Month to report, YYYY-MM.")],
) -> None:
    """Write reports/<month>.html for one client."""
    try:
        path = build_report(client_dir, month)
    except (ConfigError, ExportError, ReportError) as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"Report: {path}")


@app.command()
def demo(out: Annotated[Path, typer.Option()] = Path("demo_clients/fernway")) -> None:
    """Create a sample client with two years of exports."""
    console.print(f"Sample client: {build_demo_client(out)}")


@app.command()
def site(out: Annotated[Path, typer.Option()] = Path("site")) -> None:
    """Build the sample reports site."""
    console.print(f"Site: {build_site(out)}")
