#ifndef EIID_V7_ABSOLUTE_EFFICIENCY_ESTIMATOR_HH
#define EIID_V7_ABSOLUTE_EFFICIENCY_ESTIMATOR_HH

#include <cstdint>

class AbsoluteEfficiencyEstimator
{
public:
    static double solidAngleFraction(double coneHalfAngle);

    // Frequentist Monte-Carlo estimate without any pseudo-count:
    //
    //     efficiency_raw = (k / N) * Omega_cone / (4 pi)
    //
    // A simulated cell with k == 0 therefore remains exactly zero.  This is
    // the quantity used by the raw-efficiency experiment and its quick-look
    // figures.  It is intentionally not suitable as a hard production veto
    // until the Monte-Carlo statistics have been checked.
    static double estimateRaw(
        std::uint64_t validCount,
        std::uint64_t coneEmissionCount,
        double coneHalfAngle
    );

    // Estimate the absolute detection efficiency of an isotropic point source.
    //
    // A zero emitted count means that the cell was outside the configured
    // simulation domain, so its efficiency remains exactly zero.  Every
    // simulated cell uses the Jeffreys posterior mean (k + 1/2) / (N + 1).
    // This prevents a finite-statistics zero count from becoming a hard
    // physical veto, while converging to k / N as N grows.
    static double estimate(
        std::uint64_t validCount,
        std::uint64_t coneEmissionCount,
        double coneHalfAngle
    );
};

#endif
