#ifndef EIID_V4_ABSOLUTE_EFFICIENCY_ESTIMATOR_HH
#define EIID_V4_ABSOLUTE_EFFICIENCY_ESTIMATOR_HH

#include <cstdint>

class AbsoluteEfficiencyEstimator
{
public:
    static double solidAngleFraction(double coneHalfAngle);
    static double estimate(
        std::uint64_t validCount,
        std::uint64_t coneEmissionCount,
        double coneHalfAngle
    );
};

#endif
