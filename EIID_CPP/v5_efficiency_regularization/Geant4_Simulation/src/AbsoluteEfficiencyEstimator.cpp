#include "AbsoluteEfficiencyEstimator.hh"

#include <cmath>
#include <stdexcept>

namespace
{
constexpr double pi = 3.14159265358979323846;
}

double AbsoluteEfficiencyEstimator::solidAngleFraction(double halfAngle)
{
    if (!std::isfinite(halfAngle) || halfAngle < 0.0 || halfAngle > pi)
    {
        throw std::runtime_error{"Cone half-angle is outside [0, pi]."};
    }

    // Omega_cone / 4pi = 2pi(1-cos(alpha)) / 4pi.
    return (1.0 - std::cos(halfAngle)) / 2.0;
}

double AbsoluteEfficiencyEstimator::estimate(
    std::uint64_t validCount,
    std::uint64_t coneEmissionCount,
    double halfAngle
)
{
    if (validCount > coneEmissionCount)
    {
        throw std::runtime_error{"Valid count cannot exceed emitted count."};
    }

    if (coneEmissionCount == 0)
    {
        // No photon was assigned to this cell.  In the current simulation
        // layout this identifies a cell outside the active source domain,
        // such as the unused rear hemisphere.  It must remain a hard zero.
        return 0.0;
    }

    // Jeffreys smoothing is applied to every active cell, not only to cells
    // whose validCount happens to be zero.  The added half count matters for
    // small Monte Carlo samples and vanishes automatically for large N.
    const double conditionalEfficiency =
        (static_cast<double>(validCount) + 0.5) /
        (static_cast<double>(coneEmissionCount) + 1.0);
    return conditionalEfficiency * solidAngleFraction(halfAngle);
}
