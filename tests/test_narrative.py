from retainer_kit.drivers import sales_change
from retainer_kit.metrics import CustomerMix, MonthSummary
from retainer_kit.narrative import NarrativeInputs, money, write_narrative

APRIL = MonthSummary("2025-04", 10_000.0, 100, 300, discounts=200.0, refunds=0.0)


def test_more_orders_at_lower_value_is_described_as_an_orders_story() -> None:
    may = MonthSummary("2025-05", 12_600.0, 140, 400, discounts=2_400.0, refunds=0.0)
    paragraphs = write_narrative(
        NarrativeInputs(
            current=may,
            currency="USD",
            prior=APRIL,
            vs_last_month=sales_change(may, APRIL),
            discount_code=("SPRING20", 95),
            customers=CustomerMix(60, 40, 5_000.0, 7_600.0, 55, 140),
            movers=(("Trail tent", 1_500.0), ("Camp mug", -200.0)),
            target=12_000.0,
        )
    )
    assert paragraphs[0] == (
        "Net sales were $12,600 in May 2025, up 26% on April 2025. "
        "That is 105% of the $12,000 target."
    )
    assert paragraphs[1].startswith("More orders (+40, about $4,000) outweighed smaller orders")
    assert "SPRING20 was used on 95 orders" in paragraphs[2]
    assert "39% of orders came from returning customers" in paragraphs[3]
    assert (
        paragraphs[4]
        == "By product: biggest gain Trail tent (+$1,500); biggest drop Camp mug (-$200)."
    )


def test_first_month_has_no_comparisons() -> None:
    assert write_narrative(NarrativeInputs(current=APRIL, currency="GBP")) == [
        "Net sales were £10,000 in April 2025."
    ]


def test_money_formats() -> None:
    assert money(-1234.4, "EUR") == "-€1,234"
    assert money(50, "SEK") == "SEK 50"


def test_opposite_effects_say_which_one_won() -> None:
    # More orders, but much smaller baskets: sales fell.
    may = MonthSummary("2025-05", 9_000.0, 150, 400, discounts=0.0, refunds=0.0)
    text = write_narrative(
        NarrativeInputs(
            current=may, currency="USD", prior=APRIL, vs_last_month=sales_change(may, APRIL)
        )
    )[1]
    assert text.startswith("Smaller orders (average $100 to $60, about -$6,000) outweighed")
    assert "more orders (+50, about $5,000)" in text


def test_same_direction_effects_are_both_named() -> None:
    may = MonthSummary("2025-05", 13_200.0, 110, 400, discounts=0.0, refunds=0.0)
    text = write_narrative(
        NarrativeInputs(
            current=may, currency="USD", prior=APRIL, vs_last_month=sales_change(may, APRIL)
        )
    )[1]
    assert text.startswith("Both more orders (+10") and text.endswith("added to sales.")
