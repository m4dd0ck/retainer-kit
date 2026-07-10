"""Assemble one client's monthly report from their exports and config."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from retainer_kit.charts import bars_svg, trend_svg
from retainer_kit.config import ClientConfig, load_config
from retainer_kit.drivers import product_movers, sales_change
from retainer_kit.metrics import (
    MonthSummary,
    cohorts,
    countries,
    customer_mix,
    month_summary,
    previous_month,
    top_discount_code,
    top_products,
    trend,
)
from retainer_kit.narrative import NarrativeInputs, money, month_name, write_narrative
from retainer_kit.shopify import Store, load_store

_env = Environment(
    loader=PackageLoader("retainer_kit", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


# Reason: half-width panels scale a 640-wide chart down until its labels are unreadable.
HALF_WIDTH = 380


class ReportError(ValueError):
    """Raised when a report cannot be produced for the requested month."""


@dataclass(frozen=True)
class Kpi:
    label: str
    value: str
    vs_month: float | None
    vs_year: float | None
    higher_is_better: bool = True
    is_share: bool = False  # changes shown in percentage points, not relative percent


def _change(now: float, before: float | None) -> float | None:
    return (now - before) / before if before else None


def _points(now: float, before: float | None) -> float | None:
    return None if before is None else now - before


def _kpis(
    current: MonthSummary,
    prior: MonthSummary | None,
    year: MonthSummary | None,
    currency: str,
    store: Store,
) -> list[Kpi]:
    mix = customer_mix(store, current.month)
    prior_mix = customer_mix(store, prior.month) if prior else None
    year_mix = customer_mix(store, year.month) if year else None

    def pair(getter: str) -> tuple[float | None, float | None]:
        now = getattr(current, getter)
        return (
            _change(now, getattr(prior, getter) if prior else None),
            _change(now, getattr(year, getter) if year else None),
        )

    return [
        Kpi("Net sales", money(current.net_sales, currency), *pair("net_sales")),
        Kpi("Orders", f"{current.orders:,}", *pair("orders")),
        Kpi("Average order", money(current.aov, currency), *pair("aov")),
        Kpi(
            "New customers",
            f"{mix.new_customers:,}",
            _change(mix.new_customers, prior_mix.new_customers if prior_mix else None),
            _change(mix.new_customers, year_mix.new_customers if year_mix else None),
        ),
        Kpi(
            "Orders from returning",
            f"{mix.repeat_order_share:.0%}",
            _points(mix.repeat_order_share, prior_mix.repeat_order_share if prior_mix else None),
            _points(mix.repeat_order_share, year_mix.repeat_order_share if year_mix else None),
            is_share=True,
        ),
        Kpi(
            "Discounts",
            f"{current.discount_share:.0%}",
            _points(current.discount_share, prior.discount_share if prior else None),
            _points(current.discount_share, year.discount_share if year else None),
            higher_is_better=False,
            is_share=True,
        ),
    ]


def render_report(store: Store, config: ClientConfig, month: str) -> str:
    """The report as one self-contained HTML page."""
    current = month_summary(store, month)
    if current is None:
        raise ReportError(f"No orders in {month} in the exports provided")
    prior = month_summary(store, previous_month(month))
    year = month_summary(store, previous_month(month, 12))
    currency = config.currency
    narrative = write_narrative(
        NarrativeInputs(
            current=current,
            currency=currency,
            prior=prior,
            vs_last_month=sales_change(current, prior) if prior else None,
            vs_last_year=sales_change(current, year) if year else None,
            customers=customer_mix(store, month),
            prior_customers=customer_mix(store, prior.month) if prior else None,
            movers=tuple(product_movers(store, month)),
            discount_code=top_discount_code(store, month),
            target=config.monthly_sales_target,
        )
    )
    products = top_products(store, month)
    first, last = store.query("select min(created_date), max(created_date) from orders")[0]
    return _env.get_template("report.html.j2").render(
        config=config,
        month_title=month_name(month),
        narrative=narrative,
        kpis=_kpis(current, prior, year, currency, store),
        trend=trend_svg(
            trend(store, month),
            config.brand_colour,
            config.monthly_sales_target,
            format_value=lambda value: money(value, currency),
        ),
        products=products,
        product_bars=bars_svg(
            [(p.product, p.sales, money(p.sales, currency)) for p in products],
            config.brand_colour,
            width=HALF_WIDTH,
        ),
        country_bars=bars_svg(
            [(c, v, money(v, currency)) for c, v in countries(store, month)],
            config.brand_colour,
            width=HALF_WIDTH,
        ),
        cohorts=cohorts(store, month),
        money=lambda value: money(value, currency),
        excluded=store.excluded,
        data_from=first,
        data_to=last,
    )


def build_report(client_dir: Path, month: str) -> Path:
    """Write ``client_dir/reports/<month>.html`` from the client's config and exports."""
    config = load_config(client_dir)
    exports = sorted((client_dir / "exports").glob("*.csv"))
    store = load_store(exports, config.test_order_emails if config.exclude_test_orders else [])
    path = client_dir / "reports" / f"{month}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(store, config, month), encoding="utf-8")
    return path
