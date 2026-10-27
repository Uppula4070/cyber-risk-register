"""Monte Carlo simulation of annual loss, in the style of FAIR (Factor Analysis of Information Risk).

For each simulated year and each risk:
  1. draw an event rate from the PERT distribution of the frequency estimate,
  2. draw how many loss events happen that year from a Poisson distribution with that rate,
  3. draw a loss amount for each event from the PERT distribution of the magnitude estimate.
The sum is that risk's loss for the year. Adding risks per simulated year gives the portfolio loss,
which keeps the shape of the tail (bad years) instead of adding up percentiles, which would be wrong.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .model import Estimate, Range3, Register, Risk

DEFAULT_YEARS = 10_000
DEFAULT_SEED = 27001


def pert(rng: random.Random, r: Range3, lam: float = 4.0) -> float:
    """Sample a PERT distribution: a beta distribution shaped by min, most likely and max."""
    if r.high == r.low:
        return r.low
    span = r.high - r.low
    alpha = 1 + lam * (r.mode - r.low) / span
    beta = 1 + lam * (r.high - r.mode) / span
    return r.low + rng.betavariate(alpha, beta) * span


def poisson(rng: random.Random, rate: float) -> int:
    """Knuth's method; fine for the small yearly rates used in risk registers."""
    if rate <= 0:
        return 0
    if rate > 30:  # normal approximation keeps large rates fast
        return max(0, round(rng.gauss(rate, math.sqrt(rate))))
    limit, k, p = math.exp(-rate), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def simulate_estimate(rng: random.Random, est: Estimate, years: int) -> list[float]:
    losses = []
    for _ in range(years):
        events = poisson(rng, pert(rng, est.frequency))
        losses.append(sum(pert(rng, est.magnitude) for _ in range(events)))
    return losses


def percentile(sorted_values: list[float], q: float) -> float:
    """Linear interpolation between closest ranks; q in [0, 1]."""
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


@dataclass
class LossStats:
    mean: float
    p10: float
    p50: float
    p90: float
    p99: float
    chance_of_any_loss: float

    @classmethod
    def from_losses(cls, losses: list[float]) -> LossStats:
        s = sorted(losses)
        return cls(
            mean=sum(s) / len(s),
            p10=percentile(s, 0.10),
            p50=percentile(s, 0.50),
            p90=percentile(s, 0.90),
            p99=percentile(s, 0.99),
            chance_of_any_loss=sum(v > 0 for v in s) / len(s),
        )


@dataclass
class RiskResult:
    risk: Risk
    current: LossStats
    after: LossStats | None  # with the planned treatment, if one is modelled
    above_appetite: bool
    appetite_reasons: list[str]

    @property
    def risk_reduction(self) -> float | None:
        """Expected annual loss avoided by the treatment."""
        return None if self.after is None else self.current.mean - self.after.mean

    @property
    def rosi(self) -> float | None:
        """Return on security investment: (loss avoided - cost) / cost."""
        t = self.risk.treatment
        if self.after is None or not t or t.cost <= 0:
            return None
        return (self.risk_reduction - t.cost) / t.cost


@dataclass
class PortfolioResult:
    years: int
    seed: int
    results: list[RiskResult]
    total_current: list[float]  # simulated annual portfolio loss per year
    total_after: list[float]
    current: LossStats
    after: LossStats


def run(register: Register, years: int = DEFAULT_YEARS, seed: int = DEFAULT_SEED) -> PortfolioResult:
    rng = random.Random(seed)
    total_current = [0.0] * years
    total_after = [0.0] * years
    results = []
    for risk in register.risks:
        current = simulate_estimate(rng, risk.estimate, years)
        t = risk.treatment
        # A risk with no modelled treatment keeps its current exposure in the "after" portfolio.
        after = simulate_estimate(rng, t.after, years) if t and t.after else current
        for i in range(years):
            total_current[i] += current[i]
            total_after[i] += after[i]
        current_stats = LossStats.from_losses(current)
        reasons = []
        if risk.residual.value > register.appetite.max_residual_score:
            reasons.append(f"residual score {risk.residual.value} > {register.appetite.max_residual_score}")
        cap = register.appetite.max_annual_loss_p90
        if cap is not None and current_stats.p90 > cap:
            reasons.append("90th percentile annual loss above the limit")
        results.append(
            RiskResult(
                risk=risk,
                current=current_stats,
                after=LossStats.from_losses(after) if t and t.after else None,
                above_appetite=bool(reasons),
                appetite_reasons=reasons,
            )
        )
    results.sort(key=lambda r: -r.current.mean)
    return PortfolioResult(
        years=years,
        seed=seed,
        results=results,
        total_current=total_current,
        total_after=total_after,
        current=LossStats.from_losses(total_current),
        after=LossStats.from_losses(total_after),
    )


def exceedance_curve(losses: list[float], points: list[float]) -> list[float]:
    """Probability that the annual loss is greater than each threshold (a loss exceedance curve)."""
    n = len(losses)
    s = sorted(losses)
    out = []
    j = 0
    for x in sorted(points):
        while j < n and s[j] <= x:
            j += 1
        out.append((n - j) / n)
    return out
