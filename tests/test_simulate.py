import random

import pytest

from riskreg.model import Estimate, Range3, load
from riskreg.simulate import LossStats, exceedance_curve, percentile, pert, poisson, run, simulate_estimate


def test_pert_stays_in_range_and_centres_on_pert_mean():
    rng = random.Random(1)
    r = Range3(10, 20, 60)
    draws = [pert(rng, r) for _ in range(20_000)]
    assert min(draws) >= 10 and max(draws) <= 60
    assert sum(draws) / len(draws) == pytest.approx((10 + 4 * 20 + 60) / 6, rel=0.02)  # PERT mean


def test_pert_degenerate_range():
    assert pert(random.Random(1), Range3(5, 5, 5)) == 5


@pytest.mark.parametrize("rate", [0.1, 2.0, 50.0])
def test_poisson_mean(rate):
    rng = random.Random(2)
    draws = [poisson(rng, rate) for _ in range(20_000)]
    assert sum(draws) / len(draws) == pytest.approx(rate, rel=0.05)


def test_percentile_interpolates():
    assert percentile([0, 10, 20, 30, 40], 0.5) == 20
    assert percentile([0, 10], 0.25) == 2.5


def test_zero_frequency_means_no_loss():
    est = Estimate(Range3(0, 0, 0), Range3(100, 200, 300))
    stats = LossStats.from_losses(simulate_estimate(random.Random(3), est, 1000))
    assert stats.mean == 0 and stats.chance_of_any_loss == 0


def test_expected_loss_matches_frequency_times_magnitude():
    est = Estimate(Range3(1, 1, 1), Range3(1000, 1000, 1000))
    stats = LossStats.from_losses(simulate_estimate(random.Random(4), est, 20_000))
    assert stats.mean == pytest.approx(1000, rel=0.03)  # 1 event a year x $1,000


def test_exceedance_curve():
    losses = [0, 0, 100, 200, 1000]
    assert exceedance_curve(losses, [0, 150, 1000]) == [0.6, 0.4, 0.0]


def test_run_is_reproducible(sample):
    reg = load(sample)
    a, b = run(reg, years=2000, seed=7), run(reg, years=2000, seed=7)
    assert a.current.mean == b.current.mean
    assert run(reg, years=2000, seed=8).current.mean != a.current.mean


def test_sample_results(sample):
    p = run(load(sample), years=5000)
    ids = {r.risk.id for r in p.results if r.above_appetite}
    assert {"R-04", "R-06"} <= ids  # residual score 12 is above the appetite of 9
    assert p.after.mean < p.current.mean
    assert p.current.p90 > p.current.p50
    by_id = {r.risk.id: r for r in p.results}
    assert by_id["R-05"].rosi is None  # no treatment modelled
    assert by_id["R-01"].rosi > 1
    assert by_id["R-10"].rosi < 0.5
