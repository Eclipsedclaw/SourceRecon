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

#endif
