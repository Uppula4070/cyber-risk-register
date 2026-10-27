"""Board-level findings and the decisions the register asks leadership to make."""

from __future__ import annotations

from .charts import money
from .model import Register
from .simulate import PortfolioResult

LOW_ROSI = 0.5  # a treatment returning less than 50 cents per dollar deserves a second look


def overdue_reviews(reg: Register) -> list:
    return [r for r in reg.risks if r.review_date and r.review_date < reg.assessment_date]


def findings(reg: Register, p: PortfolioResult) -> list[str]:
    cur = reg.currency
    above = [r for r in p.results if r.above_appetite]
    lines = [
        f"Across {len(reg.risks)} risks, the expected annual loss is {money(p.current.mean, cur)}. "
        f"In a 1-in-10 bad year, losses would exceed {money(p.current.p90, cur)}.",
    ]
    funded = [r for r in p.results if r.after is not None]
    if funded:
        cost = sum(r.risk.treatment.cost for r in funded)
        avoided = p.current.mean - p.after.mean
        text = (
            f"The {len(funded)} modelled treatments reduce expected annual loss to {money(p.after.mean, cur)}, "
            f"avoiding about {money(avoided, cur)} a year"
        )
        text += f" for {money(cost, cur)} a year in cost ({avoided / cost:.1f}x return)." if cost else "."
        lines.append(text)
    if above:
        lines.append(f"{len(above)} risk(s) are above appetite: {', '.join(r.risk.id for r in above)}.")
    else:
        lines.append("All risks are within appetite.")
    top = p.results[0]
    lines.append(
        f"The largest exposure is {top.risk.id}, {top.risk.title.lower()}, at {money(top.current.mean, cur)} "
        f"expected per year."
    )
    return lines


def decisions(reg: Register, p: PortfolioResult) -> list[str]:
    cur = reg.currency
    out = []
    for r in p.results:
        t = r.risk.treatment
        if r.above_appetite and (t is None or t.strategy == "accept"):
            out.append(
                f"{r.risk.id} is above appetite ({'; '.join(r.appetite_reasons)}) with no treatment. "
                f"{r.risk.owner} must either fund a treatment or formally accept the risk."
            )
        elif r.above_appetite and t:
            out.append(
                f"Approve the {t.strategy} plan for {r.risk.id} ({money(t.cost, cur)} a year"
                + (f", owner {t.owner}, due {t.due}" if t.due else "")
                + ")."
            )
    for r in p.results:
        if r.rosi is not None and r.rosi < LOW_ROSI:
            out.append(
                f"Re-examine the treatment for {r.risk.id}: it avoids about {money(r.risk_reduction, cur)} a year "
                f"for {money(r.risk.treatment.cost, cur)}, a return of only {r.rosi:.2f} per dollar."
            )
    for risk in overdue_reviews(reg):
        out.append(f"{risk.id} was due for review on {risk.review_date} ({risk.owner}).")
    return out


def markdown(reg: Register, p: PortfolioResult) -> str:
    cur = reg.currency
    out = [f"# Cyber risk summary: {reg.organization}", "", f"Assessment date {reg.assessment_date}.", ""]
    out += [" ".join(findings(reg, p)), "", "## Decisions needed", ""]
    out += [f"{i}. {d}" for i, d in enumerate(decisions(reg, p), 1)] or ["None."]
    out += [
        "",
        "## Risks by expected annual loss",
        "",
        "| ID | Risk | Residual | Expected loss / year | 1-in-10 year | Chance of any loss | Appetite |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in p.results:
        s = r.risk.residual
        out.append(
            f"| {r.risk.id} | {r.risk.title} | {s.value} ({s.rating}) | {money(r.current.mean, cur)} | "
            f"{money(r.current.p90, cur)} | {r.current.chance_of_any_loss:.0%} | "
            f"{'**Above**' if r.above_appetite else 'Within'} |"
        )
    out += [
        "",
        f"Simulated with {p.years:,} years per risk (seed {p.seed}). Estimates are calibrated ranges, "
        "so results are directional and should be read as orders of magnitude.",
    ]
    return "\n".join(out) + "\n"
