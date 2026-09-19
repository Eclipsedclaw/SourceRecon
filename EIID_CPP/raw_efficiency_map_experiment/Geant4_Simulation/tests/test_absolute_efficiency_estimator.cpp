#include "AbsoluteEfficiencyEstimator.hh"

#include <cassert>
#include <cmath>
#include <stdexcept>

int main()
{
    constexpr double pi = 3.14159265358979323846;
    assert(std::abs(
        AbsoluteEfficiencyEstimator::solidAngleFraction(pi / 2.0) - 0.5
    ) < 1.0e-14);
    assert(std::abs(
        AbsoluteEfficiencyEstimator::estimate(25, 100, pi / 2.0) -
        (25.5 / 101.0) * 0.5
    ) < 1.0e-14);

    // Raw mode contains no pseudo-count and is exactly k / N times the
    // directed-cone solid-angle fraction.
    assert(std::abs(
        AbsoluteEfficiencyEstimator::estimateRaw(25, 100, pi / 2.0) -
        0.25 * 0.5
    ) < 1.0e-14);
    assert(AbsoluteEfficiencyEstimator::estimateRaw(0, 100, pi / 2.0) == 0.0);
    assert(AbsoluteEfficiencyEstimator::estimateRaw(0, 0, pi / 2.0) == 0.0);

    // A simulated cell with zero observed triggers receives a small positive
    // efficiency estimate instead of being misclassified as impossible.
    assert(std::abs(
        AbsoluteEfficiencyEstimator::estimate(0, 100, pi / 2.0) -
        (0.5 / 101.0) * 0.5
    ) < 1.0e-14);

    // A cell outside the simulated domain emitted no photons and remains a
    // strict zero, so it can still act as an intentional reconstruction mask.
    assert(AbsoluteEfficiencyEstimator::estimate(0, 0, 0.1) == 0.0);

    // At high statistics the half-count correction becomes negligible and
    // approaches the original k/N estimator.
    const double regularized = AbsoluteEfficiencyEstimator::estimate(
        250000,
        1000000,
        pi / 2.0
    );
    assert(std::abs(regularized - 0.125) < 3.0e-7);

    bool rejectedInvalidCounts = false;

    try
    {
        static_cast<void>(AbsoluteEfficiencyEstimator::estimate(2, 1, 0.1));
    }
    catch (const std::runtime_error&)
    {
        rejectedInvalidCounts = true;
    }

    assert(rejectedInvalidCounts);
    return 0;
}
