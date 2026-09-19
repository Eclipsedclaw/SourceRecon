#include "AbsoluteEfficiencyEstimator.hh"

#include <cassert>
#include <cmath>

int main()
{
    constexpr double pi = 3.14159265358979323846;
    assert(std::abs(
        AbsoluteEfficiencyEstimator::solidAngleFraction(pi / 2.0) - 0.5
    ) < 1.0e-14);
    assert(std::abs(
        AbsoluteEfficiencyEstimator::estimate(25, 100, pi / 2.0) - 0.125
    ) < 1.0e-14);
    assert(AbsoluteEfficiencyEstimator::estimate(0, 0, 0.1) == 0.0);
    return 0;
}
