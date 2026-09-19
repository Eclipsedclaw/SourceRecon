#ifndef EIID_V7_I_RECONSTRUCTION_SOLVER_H
#define EIID_V7_I_RECONSTRUCTION_SOLVER_H

#include "Common.h"
#include "PhysicsTypes.h"

#include <vector>

class IReconstructionSolver
{
public:
    virtual ~IReconstructionSolver() = default;
    virtual std::vector<Decimal> solve(
        const std::vector<Event>& events
    ) const = 0;
};

#endif
