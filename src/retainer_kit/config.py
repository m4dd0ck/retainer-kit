"""Each client is described by one ``client.toml`` next to their exports."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

CONFIG_FILE = "client.toml"

TEMPLATE = """\
# Monthly report settings for this client.
name = "{name}"
currency = "USD"                    # shown on the report; exports are not converted
report_title = "Monthly performance"
brand_colour = "#2e5e4e"            # accent colour on the report
# monthly_sales_target = 50000      # optional; adds a target line to the report
exclude_test_orders = true
test_order_emails = []              # e.g. ["test@yourstore.com"]
"""


class ConfigError(ValueError):
    """Raised when a client folder or its client.toml is missing or invalid."""


class ClientConfig(BaseModel):
    """Settings that make one client's report theirs."""

    name: str = Field(min_length=1)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    report_title: str = "Monthly performance"
    brand_colour: str = Field(default="#2e5e4e", pattern=r"^#[0-9a-fA-F]{6}$")
    monthly_sales_target: float | None = Field(default=None, gt=0)
    exclude_test_orders: bool = True
    test_order_emails: list[str] = Field(default_factory=list)

    @field_validator("test_order_emails")
    @classmethod
    def lower_case(cls, emails: list[str]) -> list[str]:
        return [email.strip().lower() for email in emails]


def load_config(client_dir: Path) -> ClientConfig:
    """Read and validate ``client_dir/client.toml``."""
    path = client_dir / CONFIG_FILE
    if not path.is_file():
        raise ConfigError(f"No {CONFIG_FILE} in {client_dir}; run `retainer init {client_dir}`")
    try:
        return ClientConfig.model_validate(tomllib.loads(path.read_text()))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise ConfigError(f"{path}: {error}") from error


def init_client(client_dir: Path, name: str) -> Path:
    """Create the folder layout and a starter client.toml; refuse to overwrite one."""
    path = client_dir / CONFIG_FILE
    if path.exists():
        raise ConfigError(f"{path} already exists")
    (client_dir / "exports").mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(name=name.replace('"', "'")))
    return path
