#ifndef EIID_V10_RESPONSE_QUERY_H
#define EIID_V10_RESPONSE_QUERY_H

#include "Common.h"

// A response kernel receives only the three physical coordinates needed to
// evaluate q_ij.  Keeping this object independent of Event and Cell prevents
// the kernel library from depending on a particular reconstruction solver.
struct ResponseQuery
{
    Decimal deltaThetaDegree{};
    Decimal incidentEnergyMeV{};
    Decimal scatterAngleDegree{};
};

#endif
