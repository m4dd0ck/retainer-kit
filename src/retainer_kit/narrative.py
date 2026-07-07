"""The "what changed" section, written from the numbers by plain rules.

Every sentence is traceable to a figure elsewhere in the report; nothing here is judgement the
analyst hasn't checked. The analyst adds context the data can't know (a stockout, a campaign).
"""

from dataclasses import dataclass
from datetime import date

from retainer_kit.drivers import SalesChange
from retainer_kit.metrics import CustomerMix, MonthSummary

SYMBOLS = {"USD": "$", "CAD": "$", "AUD": "$", "GBP": "£", "EUR": "€"}
DISCOUNT_SHIFT = 0.03  # mention discounts when their share moves by 3 points or more


def money(value: float, currency: str) -> str:
    symbol = SYMBOLS.get(currency, f"{currency} ")
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.0f}"


def month_name(month: str) -> str:
    return date.fromisoformat(f"{month}-01").strftime("%B %Y")


def _versus(change: SalesChange | None, label: str) -> str | None:
    if change is None or change.percent is None:
        return None
    direction = "up" if change.change >= 0 else "down"
    return f"{direction} {abs(change.percent):.0%} on {label}"


@dataclass(frozen=True)
class NarrativeInputs:
    current: MonthSummary
    currency: str
    vs_last_month: SalesChange | None = None
    vs_last_year: SalesChange | None = None
    prior: MonthSummary | None = None
    customers: CustomerMix | None = None
    prior_customers: CustomerMix | None = None
    movers: tuple[tuple[str, float], ...] = ()
    discount_code: tuple[str, int] | None = None
    target: float | None = None


def write_narrative(facts: NarrativeInputs) -> list[str]:
    """Short paragraphs, most important first."""
    now, cur = facts.current, facts.currency
    paragraphs = []

    comparisons = [
        text
        for text in (
            _versus(facts.vs_last_month, month_name(facts.prior.month) if facts.prior else ""),
            _versus(facts.vs_last_year, "the same month last year"),
        )
        if text
    ]
    headline = f"Net sales were {money(now.net_sales, cur)} in {month_name(now.month)}"
    headline += f", {' and '.join(comparisons)}." if comparisons else "."
    if facts.target:
        headline += (
            f" That is {now.net_sales / facts.target:.0%} of the {money(facts.target, cur)} target."
        )
    paragraphs.append(headline)

    change = facts.vs_last_month
    if change and facts.prior and abs(change.change) >= 0.01:
        paragraphs.append(_driver_sentence(now, facts.prior, change, cur))

    if facts.prior and abs(now.discount_share - facts.prior.discount_share) >= DISCOUNT_SHIFT:
        text = (
            f"Discounts were {now.discount_share:.0%} of sales before discounts, "
            f"{'up' if now.discount_share > facts.prior.discount_share else 'down'} from "
            f"{facts.prior.discount_share:.0%}"
        )
        if facts.discount_code:
            code, orders = facts.discount_code
            text += f"; {code} was used on {orders:,} orders"
        paragraphs.append(text + ".")

    if facts.customers:
        mix = facts.customers
        text = (
            f"New customers spent {money(mix.new_sales, cur)} ({mix.new_customers:,} people) and "
            f"returning customers {money(mix.returning_sales, cur)}"
        )
        if facts.prior_customers:
            delta = mix.returning_sales - facts.prior_customers.returning_sales
            text += f" ({'+' if delta >= 0 else '-'}{money(abs(delta), cur)} on last month)"
        text += f". {mix.repeat_order_share:.0%} of orders came from returning customers."
        paragraphs.append(text)

    gains = [m for m in facts.movers if m[1] > 0]
    drops = [m for m in facts.movers if m[1] < 0]
    if gains or drops:
        parts = []
        if gains:
            parts.append(f"biggest gain {gains[0][0]} (+{money(gains[0][1], cur)})")
        if drops:
            parts.append(f"biggest drop {drops[0][0]} ({money(drops[0][1], cur)})")
        paragraphs.append(f"By product: {'; '.join(parts)}.")
    return paragraphs


def _driver_sentence(now: MonthSummary, prior: MonthSummary, change: SalesChange, cur: str) -> str:
    """Name the bigger effect, and say so plainly when the two pulled in opposite directions.

    The order-value part includes the interaction term, so the two parts still add up exactly
    to the change quoted in the headline.
    """
    orders_part = change.orders_effect
    value_part = change.aov_effect + change.interaction
    order_delta = now.orders - prior.orders
    orders_text = (
        f"{'more' if order_delta > 0 else 'fewer'} orders ({order_delta:+,}, about "
        f"{money(orders_part, cur)})"
    )
    value_text = (
        f"{'larger' if now.aov > prior.aov else 'smaller'} orders (average "
        f"{money(prior.aov, cur)} to {money(now.aov, cur)}, about {money(value_part, cur)})"
    )
    if (orders_part >= 0) == (value_part >= 0):
        both = f"{orders_text} and {value_text}"
        return f"Both {both} {'added to' if change.change >= 0 else 'took away from'} sales."
    main, other = (
        (orders_text, value_text)
        if abs(orders_part) >= abs(value_part)
        else (value_text, orders_text)
    )
    return f"{main[0].upper()}{main[1:]} outweighed {other}."
