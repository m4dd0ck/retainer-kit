import os
import subprocess
import sys
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


def test_names_with_quotes_and_backslashes_round_trip(tmp_path: Path) -> None:
    init_client(tmp_path, 'Acme "Goods" \\ Co\\')
    assert load_config(tmp_path).name == 'Acme "Goods" \\ Co\\'


def test_config_is_read_as_utf8_whatever_the_locale(tmp_path: Path) -> None:
    # Reason: Windows defaults text files to a legacy code page; TOML files are UTF-8.
    (tmp_path / "client.toml").write_text('name = "Café Ñandú"\n', encoding="utf-8")
    code = (
        "import sys, pathlib; from retainer_kit.config import load_config; "
        "sys.stdout.buffer.write(load_config(pathlib.Path(sys.argv[1])).name.encode('utf-8'))"
    )
    env = {**os.environ, "PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1", "LANG": "en_US.ISO8859-1"}
    done = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)], env=env, capture_output=True, check=True
    )
    assert done.stdout.decode("utf-8") == "Café Ñandú"
