"""Build the self-contained HTML risk report. All text from the register is escaped."""

from __future__ import annotations

from collections import Counter
from html import escape

from . import charts
from .charts import BAND_VAR, money
from .model import CONTROL_STATUSES, CSF_FUNCTIONS, ISO_THEMES, Register
from .simulate import PortfolioResult
from .summary import decisions, findings, overdue_reviews

CSS = """
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --target: #52514e;
  --good: #0ca30c; --warning: #fab219; --serious: #ec835a; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --target: #c3c2b7;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --series-1: #3987e5; --series-2: #d95926; --target: #c3c2b7;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 28px 24px 56px; }
header h1 { margin: 0 0 4px; font-size: 26px; }
header p { margin: 0; color: var(--ink-2); }
h2 { font-size: 17px; margin: 0 0 12px; }
h3 { font-size: 15px; margin: 0; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 22px 0; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.tile .v { font-size: 28px; font-weight: 650; }
.tile .k { color: var(--ink-2); font-size: 13px; }
.tile .s { color: var(--muted); font-size: 12px; margin-top: 2px; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(440px, 100%), 1fr)); gap: 14px; margin-top: 14px; }
.grid2 > * { min-width: 0; }
section.card { margin-top: 14px; }
.narrative p { margin: 0 0 6px; }
.narrative ol { margin: 8px 0 0; padding-left: 20px; }
.note { color: var(--muted); font-size: 12px; margin: 8px 0 0; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: var(--ink-2); margin-bottom: 6px; }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -2px; }
.legend i.line { height: 3px; border-radius: 2px; vertical-align: 3px; }
svg.chart { width: 100%; height: auto; display: block; }
svg .grid { stroke: var(--grid); } svg .axis { stroke: var(--axis); }
svg .tick { fill: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
svg .cat { fill: var(--ink-2); font-size: 13px; }
svg .value { fill: var(--ink); font-size: 12px; font-weight: 600; }
svg .curve { fill: none; stroke-width: 2; stroke-linejoin: round; }
svg .curve.s1 { stroke: var(--series-1); } svg .curve.s2 { stroke: var(--series-2); }
svg .hit-dot { fill: transparent; } svg .hit-dot:hover { fill: var(--ink); fill-opacity: .25; }
svg .target { stroke: var(--target); stroke-width: 1.5; stroke-dasharray: 5 4; }
svg .bar { fill: var(--series-1); } svg .whisker { stroke: var(--ink-2); stroke-width: 2; }
svg g:hover .bar { opacity: .85; }
.heatmap { border-collapse: separate; border-spacing: 3px; margin: 0 auto; }
.hm-cell { width: 64px; height: 52px; text-align: center; vertical-align: middle; border-radius: 6px; font-size: 12px; font-weight: 600;
  background: color-mix(in srgb, var(--c) 30%, var(--surface)); border: 1px solid color-mix(in srgb, var(--c) 60%, transparent); }
.hm-axis { color: var(--muted); font-size: 12px; font-weight: 500; padding: 2px 6px; }
.hm-labels { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; max-width: 360px; margin: 4px auto 0; }
.table-wrap { overflow-x: auto; }
table.data { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
table.data th, table.data td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--grid); vertical-align: top; }
table.data th { color: var(--ink-2); font-weight: 600; white-space: nowrap; }
table.data td.num, table.data th.num { text-align: right; white-space: nowrap; }
table.data td:first-child { white-space: nowrap; }
table.data td.nw { white-space: nowrap; }
.band { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.band::before { content: ""; width: 9px; height: 9px; border-radius: 2px; background: var(--c); }
.flag { font-weight: 600; }
.risk { border-top: 1px solid var(--grid); padding: 14px 0; }
.risk:first-of-type { border-top: 0; }
.risk p { margin: 6px 0; color: var(--ink-2); }
.risk ul { margin: 6px 0; padding-left: 20px; font-size: 14px; }
code { font: 12px Consolas, monospace; background: color-mix(in srgb, var(--ink) 7%, transparent); padding: 1px 4px; border-radius: 4px; }
footer { margin-top: 28px; color: var(--muted); font-size: 12px; }
footer dt { font-weight: 600; color: var(--ink-2); margin-top: 6px; } footer dd { margin: 0; }
@media (max-width: 640px) { main { padding: 18px 16px 40px; } .hm-cell { width: 44px; height: 42px; font-size: 11px; } }
"""


def _band(name: str, text: str | None = None) -> str:
    return f'<span class="band" style="--c:var({BAND_VAR[name]})">{escape(text or name.title())}</span>'


def _table(headers: list[str], rows: list[list[str]], numeric: set[int] = frozenset()) -> str:
    head = "".join(f'<th class="{"num" if i in numeric else ""}">{escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return (
        f'<div class="table-wrap"><table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    )


def _coverage(reg: Register) -> tuple[str, str]:
    csf: Counter = Counter()
    iso: Counter = Counter()
    for risk in reg.risks:
        for c in risk.controls:
            for fn in {ref[:2] for ref in c.nist_csf}:
                csf[(fn, c.status)] += 1
            for theme in {int(ref.split(".")[1]) for ref in c.iso27001}:
                iso[(theme, c.status)] += 1
    headers = ["", *[s.title() for s in CONTROL_STATUSES]]
    csf_rows = [
        [f"{escape(name)} <code>{code}</code>", *[str(csf[(code, s)]) for s in CONTROL_STATUSES]]
        for code, name in CSF_FUNCTIONS.items()
    ]
    iso_rows = [
        [f"{escape(name)} <code>A.{n}</code>", *[str(iso[(n, s)]) for s in CONTROL_STATUSES]]
        for n, name in ISO_THEMES.items()
    ]
    return _table(["NIST CSF 2.0 function", *headers[1:]], csf_rows, {1, 2, 3}), _table(
        ["ISO 27001:2022 theme", *headers[1:]], iso_rows, {1, 2, 3}
    )


def build(reg: Register, p: PortfolioResult) -> str:
    cur = reg.currency
    above = [r for r in p.results if r.above_appetite]
    funded = [r for r in p.results if r.after is not None]
    cost = sum(r.risk.treatment.cost for r in funded)
    cap = reg.appetite.max_annual_loss_p90

    tiles = [
        (str(len(reg.risks)), "Risks in the register", f"{len(above)} above appetite"),
        (money(p.current.mean, cur), "Expected annual loss", f"{money(p.after.mean, cur)} after planned treatments"),
        (money(p.current.p90, cur), "1-in-10 year loss", "90th percentile of simulated years"),
        (money(cost, cur), "Annual cost of treatments", f"avoids ~{money(p.current.mean - p.after.mean, cur)} a year"),
    ]
    tiles_html = "".join(
        f'<div class="card tile"><div class="v">{escape(v)}</div><div class="k">{escape(k)}</div>'
        f'<div class="s">{escape(s)}</div></div>'
        for v, k, s in tiles
    )
    find_html = "".join(f"<p>{escape(t)}</p>" for t in findings(reg, p))
    dec_html = "".join(f"<li>{escape(d)}</li>" for d in decisions(reg, p)) or "<li>None.</li>"

    exposure_rows = [
        [
            escape(r.risk.id),
            escape(r.risk.title),
            _band(r.risk.residual.rating, f"{r.risk.residual.value} {r.risk.residual.rating}"),
            money(r.current.mean, cur),
            money(r.current.p90, cur),
            f"{r.current.chance_of_any_loss:.0%}",
            '<span class="flag">Above</span>' if r.above_appetite else "Within",
        ]
        for r in p.results
    ]
    exposure_table = _table(
        ["ID", "Risk", "Residual", "Expected / yr", "1-in-10 yr", "Chance of any loss in a year", "Appetite"],
        exposure_rows,
        {3, 4, 5},
    )
    treat_rows = []
    for r in p.results:
        t = r.risk.treatment
        if not t:
            continue
        treat_rows.append(
            [
                escape(r.risk.id),
                escape(t.strategy.title()),
                escape(t.plan),
                escape(t.owner),
                f'<span style="white-space:nowrap">{escape(str(t.due or "–"))}</span>',
                money(t.cost, cur) if t.cost else "–",
                money(r.risk_reduction, cur) if r.risk_reduction is not None else "–",
                f"{r.rosi:.2f}" if r.rosi is not None else "–",
            ]
        )
    treat_table = _table(
        ["ID", "Strategy", "Plan", "Owner", "Due", "Cost / yr", "Loss avoided / yr", "ROSI"], treat_rows, {5, 6, 7}
    )
    csf_table, iso_table = _coverage(reg)
    overdue = {r.id for r in overdue_reviews(reg)}

    detail = []
    for r in sorted(p.results, key=lambda x: x.risk.id):
        risk = r.risk
        ctrl = "".join(
            f"<li>{escape(c.name)} – <em>{escape(c.status)}</em>"
            + "".join(f" <code>{escape(x)}</code>" for x in c.nist_csf + c.iso27001)
            + "</li>"
            for c in risk.controls
        )
        est = risk.estimate
        review = escape(str(risk.review_date or "–")) + (" <strong>(overdue)</strong>" if risk.id in overdue else "")
        detail.append(
            f'<div class="risk" id="{escape(risk.id)}"><h3>{escape(risk.id)}: {escape(risk.title)}</h3>'
            f"<p>{escape(risk.category)} · owner {escape(risk.owner)} · inherent "
            f"{_band(risk.inherent.rating, str(risk.inherent.value))} → residual "
            f"{_band(risk.residual.rating, str(risk.residual.value))} · next review {review}</p>"
            + (f"<p>{escape(risk.description)}</p>" if risk.description else "")
            + f"<p>Estimate: {est.frequency.low:g}–{est.frequency.high:g} loss events a year "
            f"(most likely {est.frequency.mode:g}), {money(est.magnitude.low, cur)}–{money(est.magnitude.high, cur)} "
            f"per event (most likely {money(est.magnitude.mode, cur)}).</p>"
            f"<ul>{ctrl}</ul></div>"
        )

    curve = charts.exceedance_chart(p.total_current, p.total_after, None, cur)
    bars = charts.exposure_bars(p.results, cap, cur)
    band_legend = "".join(
        f'<span><i style="background:var({BAND_VAR[b]})"></i>{b.title()} ({rng})</span>'
        for b, rng in (("low", "1–5"), ("medium", "6–11"), ("high", "12–19"), ("critical", "20–25"))
    )
    appetite_txt = f"Appetite: residual score ≤ {reg.appetite.max_residual_score}" + (
        f" and 1-in-10 year loss ≤ {money(cap, cur)} per risk" if cap else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cyber risk register – {escape(reg.organization)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
  <h1>Cyber risk register</h1>
  <p>{escape(reg.organization)} · assessed {reg.assessment_date} · {escape(appetite_txt)}</p>
</header>

<section class="tiles">{tiles_html}</section>

<section class="card narrative">
  <h2>Summary</h2>
  {find_html}
  <h2 style="margin-top:14px">Decisions needed</h2>
  <ol>{dec_html}</ol>
</section>

<section class="grid2">
  <div class="card"><h2>Inherent risk (before controls)</h2>{charts.heatmap(reg.risks, "inherent")}</div>
  <div class="card"><h2>Residual risk (with current controls)</h2>{charts.heatmap(reg.risks, "residual")}</div>
</section>
<div class="legend" style="margin-top:10px;justify-content:center">{band_legend}</div>

<section class="grid2">
  <div class="card"><h2>Loss exceedance curve, whole register</h2>
    <div class="legend"><span><i class="line" style="background:var(--series-1)"></i>Current</span>
      <span><i class="line" style="background:var(--series-2)"></i>After planned treatments</span></div>
    {curve}
    <p class="note">Chance that total losses in a year exceed the amount on the x-axis (log scale).
      At 10%, the curve shows the 1-in-10 bad year.</p></div>
  <div class="card"><h2>Expected annual loss by risk</h2>
    {bars}
    <p class="note">Bar: expected (mean) annual loss. Whisker: 1-in-10 year loss. Dashed line: per-risk appetite limit.</p></div>
</section>

<section class="card"><h2>Exposure by risk</h2>{exposure_table}</section>
<section class="card"><h2>Treatment plan</h2>{treat_table}
  <p class="note">ROSI (return on security investment) = (expected loss avoided − cost) ÷ cost. Above 0 means the treatment pays for itself.</p></section>
<section class="grid2">
  <div class="card"><h2>Control coverage: NIST CSF 2.0</h2>{csf_table}</div>
  <div class="card"><h2>Control coverage: ISO/IEC 27001:2022 Annex A</h2>{iso_table}</div>
</section>
<section class="card"><h2>Risk details</h2>{"".join(detail)}</section>

<footer>
  <dl>
    <dt>Qualitative score</dt><dd>Likelihood (1–5) × impact (1–5). Inherent is before controls, residual is with controls as they operate today.</dd>
    <dt>Quantitative model</dt><dd>FAIR-style Monte Carlo: {p.years:,} simulated years (seed {p.seed}). Each year draws an event rate and per-event losses from PERT distributions of the min / most likely / max estimates, with Poisson event counts. Portfolio figures add the risks year by year, so they keep the shape of the tail.</dd>
    <dt>Reading the numbers</dt><dd>Estimates are calibrated ranges, not measurements. Use the results to compare risks and treatments, not as accounting forecasts.</dd>
  </dl>
  <p>Generated by riskreg.</p>
</footer>
</main>
</body>
</html>
"""
