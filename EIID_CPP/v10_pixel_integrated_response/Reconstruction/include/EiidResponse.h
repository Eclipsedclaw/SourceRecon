#ifndef EIID_V7_EIID_RESPONSE_H
#define EIID_V7_EIID_RESPONSE_H

#include "PhysicsTypes.h"

class ReconConfig;
class IResponseKernel;

Decimal calculateResponse(
    const Event& event,
    const Cell& cell,
    const ReconConfig& config,
    const IResponseKernel& responseKernel
);

// Evaluate q_ij at an arbitrary source direction.  Separating direction from
// Cell is what lets V10 integrate the same physical response over several
// equal-area points without creating extra image unknowns.
Decimal calculateDirectionalResponse(
    const Event& event,
    Decimal candidateEnergyMeV,
    const Vec3& sourceDirection,
    const ReconConfig& config,
    const IResponseKernel& responseKernel
);

#endif
