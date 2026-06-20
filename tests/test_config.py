from pathlib import Path

import pytest

from retainer_kit.config import ConfigError, init_client, load_config


def test_init_writes_a_starter_config_that_loads(tmp_path: Path) -> None:
    init_client(tmp_path / "acme", "Acme Goods")
    config = load_config(tmp_path / "acme")
    assert config.name == "Acme Goods"
    assert (tmp_path / "acme" / "exports").is_dir()


def test_init_never_overwrites(tmp_path: Path) -> None:
    init_client(tmp_path, "Acme")
    with pytest.raises(ConfigError, match="already exists"):
        init_client(tmp_path, "Acme")


def test_invalid_values_are_reported_with_the_file(tmp_path: Path) -> None:
    (tmp_path / "client.toml").write_text('name = "X"\nbrand_colour = "green"\n')
    with pytest.raises(ConfigError, match="client.toml"):
        load_config(tmp_path)


def test_test_emails_are_normalised(tmp_path: Path) -> None:
    (tmp_path / "client.toml").write_text('name = "X"\ntest_order_emails = [" QA@Shop.com "]\n')
    assert load_config(tmp_path).test_order_emails == ["qa@shop.com"]
