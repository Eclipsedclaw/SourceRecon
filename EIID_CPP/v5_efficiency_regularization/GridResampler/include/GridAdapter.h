#ifndef EIID_V5_GRID_ADAPTER_H
#define EIID_V5_GRID_ADAPTER_H

#include "HealpixGrid.h"
#include "IInterpolationStrategy.h"
#include "ResamplerConfig.h"

#include <memory>

class GridAdapter
{
public:
    explicit GridAdapter(const ResamplerConfig& config);
    const IGrid& masterGrid() const;
    const IGrid& targetGrid() const;
    AbsoluteEfficiencyMap resample(
        const AbsoluteEfficiencyMap& master
    ) const;
    std::string strategyName() const;

private:
    HealpixGrid masterGrid_;
    HealpixGrid targetGrid_;
    std::unique_ptr<IInterpolationStrategy> strategy_;
};

#endif
