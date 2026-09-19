#ifndef EIID_V6_LM_MLEM_SOLVER_H
#define EIID_V6_LM_MLEM_SOLVER_H

#include "AbsoluteEfficiencyMap.h"
#include "IGrid.h"
#include "IReconstructionSolver.h"

class ReconConfig;

class LmMlemSolver final : public IReconstructionSolver
{
public:
    LmMlemSolver(
        const IGrid& grid,
        const AbsoluteEfficiencyMap& efficiency,
        const ReconConfig& config
    );

    std::vector<Decimal> solve(
        const std::vector<Event>& events
    ) const override;

private:
    const IGrid* grid_{};
    const AbsoluteEfficiencyMap* efficiency_{};
    const ReconConfig* config_{};
};

#endif
