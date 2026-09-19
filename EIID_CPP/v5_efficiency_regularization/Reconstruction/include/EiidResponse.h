#ifndef EIID_V5_EIID_RESPONSE_H
#define EIID_V5_EIID_RESPONSE_H

#include "PhysicsTypes.h"

class ReconConfig;

Decimal calculateResponse(
    const Event& event,
    const Cell& cell,
    const ReconConfig& config
);

#endif
