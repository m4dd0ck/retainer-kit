"""Small charts as inline SVG: no JavaScript, so the report prints and emails cleanly."""

from datetime import date
from html import escape

WIDTH = 640


def _label(month: str) -> str:
    return date.fromisoformat(f"{month}-01").strftime("%b")


def trend_svg(
    points: list[tuple[str, float, int]], colour: str, target: float | None = None
) -> str:
    """Net sales per month as a line with the latest month marked, plus an optional target."""
    height, left, bottom, top = 200, 8, 26, 16
    values = [sales for _, sales, _ in points]
    ceiling = max([*values, target or 0.0, 1.0]) * 1.1
    step = (WIDTH - 2 * left) / max(len(points) - 1, 1)

    def xy(index: int, value: float) -> tuple[float, float]:
        return left + index * step, top + (1 - value / ceiling) * (height - top - bottom)

    coords = [xy(i, v) for i, v in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    base = height - bottom
    area = f"{coords[0][0]:.1f},{base} {line} {coords[-1][0]:.1f},{base}"
    parts = [
        f'<svg viewBox="0 0 {WIDTH} {height}" role="img" class="chart">',
        "<title>Net sales by month, last 12 months</title>",
        f'<polygon points="{area}" fill="{colour}" opacity="0.12"/>',
        f'<polyline points="{line}" fill="none" stroke="{colour}" stroke-width="2.5"/>',
        f'<line x1="{left}" x2="{WIDTH - left}" y1="{base}" y2="{base}" class="axis"/>',
    ]
    if target:
        y = xy(0, target)[1]
        parts.append(
            f'<line x1="{left}" x2="{WIDTH - left}" y1="{y:.1f}" y2="{y:.1f}" class="target"/>'
        )
    last_x, last_y = coords[-1]
    parts.append(f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="4.5" fill="{colour}"/>')
    for index, (month, _, _) in enumerate(points):
        x = coords[index][0]
        anchor = "start" if index == 0 else "end" if index == len(points) - 1 else "middle"
        parts.append(
            f'<text x="{x:.1f}" y="{height - 8}" text-anchor="{anchor}">'
            f"{escape(_label(month))}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def bars_svg(rows: list[tuple[str, float, str]], colour: str) -> str:
    """Horizontal bars: (label, value, formatted value) per row, largest scale from the data."""
    row_height, label_width, value_width = 30, 190, 90
    height = row_height * len(rows) + 4
    largest = max((value for _, value, _ in rows), default=1.0) or 1.0
    span = WIDTH - label_width - value_width
    parts = [
        f'<svg viewBox="0 0 {WIDTH} {height}" role="img" class="chart"><title>Bar chart</title>'
    ]
    for index, (label, value, shown) in enumerate(rows):
        y = index * row_height + 4
        width = max(value, 0) / largest * span
        short = label if len(label) <= 28 else label[:26] + "…"
        parts += [
            f'<text x="0" y="{y + 17}">{escape(short)}</text>',
            f'<rect x="{label_width}" y="{y + 4}" width="{width:.1f}" height="18" rx="3" '
            f'fill="{colour}"/>',
            f'<text x="{WIDTH}" y="{y + 17}" text-anchor="end" class="value">'
            f"{escape(shown)}</text>",
        ]
    parts.append("</svg>")
    return "".join(parts)
