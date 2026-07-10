from xml.etree import ElementTree

from retainer_kit.charts import bars_svg, trend_svg


def test_trend_is_valid_svg_with_every_month_labelled() -> None:
    points = [(f"2025-{m:02d}", 1000.0 * m, m) for m in range(1, 13)]
    svg = trend_svg(points, "#2e5e4e", target=9000.0)
    root = ElementTree.fromstring(svg)
    labels = [el.text for el in root.iter("{http://www.w3.org/2000/svg}text")] or [
        el.text for el in root.iter("text")
    ]
    assert {"Jan", "Dec", "target 9,000", "12,000"} <= set(labels)
    assert 'class="target"' in svg


def test_bar_labels_are_escaped() -> None:
    svg = bars_svg([("<script>", 5.0, "$5"), ("Mug", 2.0, "$2")], "#000000")
    assert "<script>" not in svg
    ElementTree.fromstring(svg)


def test_all_zero_months_do_not_divide_by_zero() -> None:
    ElementTree.fromstring(trend_svg([("2025-01", 0.0, 0), ("2025-02", 0.0, 0)], "#000000"))
