"""Inline-SVG and HTML charts. Colors come from CSS variables so light and dark themes both apply.

Every mark has a <title> (hover tooltip) and every chart has a table elsewhere on the page.
"""

from __future__ import annotations

import math
from html import escape

from .model import Risk, rating
from .simulate import RiskResult, exceedance_curve

BAND_VAR = {"low": "--good", "medium": "--warning", "high": "--serious", "critical": "--critical"}


def nice_max(value: float) -> float:
    """Round up to 1, 2, 2.5 or 5 times a power of ten so axis ticks land on round amounts."""
    if value <= 0:
        return 1
    exp = 10 ** math.floor(math.log10(value))
    return next(step * exp for step in (1, 2, 2.5, 5, 10) if value <= step * exp)


def money(v: float, currency: str = "USD") -> str:
    symbol = "$" if currency == "USD" else ""
    suffix = "" if symbol else f" {currency}"
    if abs(v) >= 1_000_000:
        millions = v / 1_000_000
        text = f"{millions:.0f}" if millions == int(millions) else f"{millions:.2f}"
        return f"{symbol}{text}M{suffix}"
    if abs(v) >= 1_000:
        return f"{symbol}{v / 1_000:.0f}K{suffix}"
    return f"{symbol}{v:.0f}{suffix}"


def heatmap(risks: list[Risk], which: str) -> str:
    """5x5 likelihood x impact grid as an HTML table; cells list the risk IDs, so color is never the only cue."""
    cells: dict[tuple[int, int], list[str]] = {}
    for r in risks:
        s = getattr(r, which)
        cells.setdefault((s.likelihood, s.impact), []).append(r.id)
    rows = []
    for likelihood in range(5, 0, -1):
        tds = [f'<th scope="row" class="hm-axis">{likelihood}</th>']
        for impact in range(1, 6):
            band = rating(likelihood * impact)
            ids = cells.get((likelihood, impact), [])
            tip = f"Likelihood {likelihood} × impact {impact} = {likelihood * impact} ({band})"
            if ids:
                tip += ": " + ", ".join(ids)
            tds.append(
                f'<td class="hm-cell" style="--c:var({BAND_VAR[band]})" title="{escape(tip)}">'
                f"{'<br>'.join(escape(i) for i in ids)}</td>"
            )
        rows.append("<tr>" + "".join(tds) + "</tr>")
    head = "".join(f'<th scope="col" class="hm-axis">{i}</th>' for i in range(1, 6))
    return (
        f'<table class="heatmap" aria-label="{escape(which)} risk heat map">'
        f"<tbody>{''.join(rows)}</tbody><tfoot><tr><th></th>{head}</tr></tfoot></table>"
        '<div class="hm-labels"><span>↑ Likelihood</span><span>Impact →</span></div>'
    )


def exceedance_chart(current: list[float], after: list[float], cap: float | None, currency: str) -> str:
    """Loss exceedance curve on a log x-axis: chance that annual loss exceeds each amount."""
    w, h, pl, pr, pt, pb = 560, 280, 48, 30, 14, 40
    # Stop the axis at the 1-in-1000 year loss; the extreme tail would squash everything else.
    hi = max(sorted(current)[int(len(current) * 0.999) - 1], 1.0)
    lo_exp, hi_exp = 4, max(5, math.ceil(math.log10(hi)))  # from $10K
    xs_val = [10 ** (lo_exp + (hi_exp - lo_exp) * i / 59) for i in range(60)]
    plot_w, plot_h = w - pl - pr, h - pt - pb

    def x(v: float) -> float:
        return pl + plot_w * (math.log10(v) - lo_exp) / (hi_exp - lo_exp)

    def y(p: float) -> float:
        return pt + plot_h * (1 - p)

    parts = []
    for i in range(5):
        p = i / 4
        cls = "axis" if i == 0 else "grid"
        parts.append(f'<line class="{cls}" x1="{pl}" x2="{w - pr}" y1="{y(p):.1f}" y2="{y(p):.1f}"/>')
        parts.append(f'<text class="tick" x="{pl - 6}" y="{y(p) + 4:.1f}" text-anchor="end">{p:.0%}</text>')
    for e in range(lo_exp, hi_exp + 1):
        parts.append(f'<line class="grid" x1="{x(10**e):.1f}" x2="{x(10**e):.1f}" y1="{pt}" y2="{h - pb}"/>')
        parts.append(
            f'<text class="tick" x="{x(10**e):.1f}" y="{h - pb + 18}" text-anchor="middle">'
            f"{money(10**e, currency)}</text>"
        )
    if cap:
        parts.append(f'<line class="target" x1="{x(cap):.1f}" x2="{x(cap):.1f}" y1="{pt}" y2="{h - pb}"/>')
    for name, losses, cls in (("Current", current, "s1"), ("After planned treatments", after, "s2")):
        probs = exceedance_curve(losses, xs_val)
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{x(v):.1f},{y(p):.1f}" for i, (v, p) in enumerate(zip(xs_val, probs, strict=True))
        )
        parts.append(f'<path class="curve {cls}" d="{d}"/>')
        for v, p in list(zip(xs_val, probs, strict=True))[::3]:
            tip = f"{name}: {p:.0%} chance annual loss exceeds {money(v, currency)}"
            parts.append(
                f'<circle class="hit-dot" cx="{x(v):.1f}" cy="{y(p):.1f}" r="7"><title>{escape(tip)}</title></circle>'
            )
    return (
        f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Loss exceedance curve, current and after planned treatments">{"".join(parts)}</svg>'
    )


def exposure_bars(results: list[RiskResult], cap: float | None, currency: str) -> str:
    """Per risk: bar to the expected annual loss, whisker to the 90th percentile."""
    w, left, right, row_h = 560, 56, 160, 30
    h = row_h * len(results) + 34
    top = nice_max(max([r.current.p90 for r in results] + [cap or 0]))
    plot_w = w - left - right

    def x(v: float) -> float:
        return left + plot_w * v / top

    parts = []
    for i in range(5):
        v = top * i / 4
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="4" y2="{h - 28}"/>')
        parts.append(f'<text class="tick" x="{x(v):.1f}" y="{h - 10}" text-anchor="middle">{money(v, currency)}</text>')
    if cap:
        parts.append(f'<line class="target" x1="{x(cap):.1f}" x2="{x(cap):.1f}" y1="4" y2="{h - 28}"/>')
    for i, r in enumerate(results):
        yc = 8 + i * row_h + 10
        parts.append(f'<text class="cat" x="{left - 8}" y="{yc + 5}" text-anchor="end">{escape(r.risk.id)}</text>')
        tip = (
            f"{r.risk.id} {r.risk.title}: expected {money(r.current.mean, currency)} a year, "
            f"1-in-10 year {money(r.current.p90, currency)}"
        )
        bw = max(x(r.current.mean) - left, 2)
        parts.append(
            f"<g><title>{escape(tip)}</title>"
            f'<rect class="bar" x="{left}" y="{yc - 7}" width="{bw:.1f}" height="14" rx="4"/>'
            f'<line class="whisker" x1="{left + bw:.1f}" x2="{x(r.current.p90):.1f}" y1="{yc}" y2="{yc}"/>'
            f'<line class="whisker" x1="{x(r.current.p90):.1f}" x2="{x(r.current.p90):.1f}" '
            f'y1="{yc - 6}" y2="{yc + 6}"/></g>'
        )
        label = money(r.current.mean, currency) + (" · above appetite" if r.above_appetite else "")
        parts.append(
            f'<text class="value" x="{max(x(r.current.p90), left + bw) + 8:.1f}" y="{yc + 5}">{escape(label)}</text>'
        )
    return (
        f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Expected annual loss per risk with 90th percentile">{"".join(parts)}</svg>'
    )
