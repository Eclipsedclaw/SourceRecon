#ifndef EIID_MLEM_CORE_H
#define EIID_MLEM_CORE_H

#include "ReconConfig.h"
#include "SensitivityMatrix.h"
#include "common.h"
#include "eiid_core.h"
#include "grid.h"

#include <vector>

// LmMlemSolver 只负责迭代。
// Grid、配置和真实敏感度均由 main.cpp 显式注入，内部没有隐藏全局参数。
class LmMlemSolver
{
public:
    LmMlemSolver(
        const Grid& grid,
        const SensitivityMatrix& sensitivity,
        const ReconConfig& config
    );

    std::vector<Decimal> solve(const std::vector<Event>& events) const;

private:
    const Grid* grid_;
    const SensitivityMatrix* sensitivity_;
    const ReconConfig* config_;
};

#endif
