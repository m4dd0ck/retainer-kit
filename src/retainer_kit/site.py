"""Sample reports for GitHub Pages: three months for the demo store, plus an index."""

import shutil
import tempfile
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from retainer_kit.demo import build_demo_client
from retainer_kit.narrative import month_name
from retainer_kit.report import build_report

SITE_MARKER = ".retainer-site"
SAMPLE_MONTHS = ["2025-04", "2025-05", "2025-06"]
_env = Environment(
    loader=PackageLoader("retainer_kit", "templates"), autoescape=select_autoescape(["j2"])
)


class UnsafeOutputError(ValueError):
    """Raised instead of deleting a folder this tool did not create."""


def build_site(out_dir: Path) -> Path:
    if out_dir.exists():
        if any(out_dir.iterdir()) and not (out_dir / SITE_MARKER).exists():
            raise UnsafeOutputError(f"{out_dir} is not empty and was not built by retainer site")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        client = build_demo_client(Path(tmp) / "fernway")
        for month in SAMPLE_MONTHS:
            shutil.copy(build_report(client, month), out_dir / f"{month}.html")
    reports = [(f"{m}.html", month_name(m)) for m in SAMPLE_MONTHS]
    index = out_dir / "index.html"
    index.write_text(_env.get_template("site_index.html.j2").render(reports=reports))
    (out_dir / SITE_MARKER).write_text("Built by retainer site; safe to delete.\n")
    return index
