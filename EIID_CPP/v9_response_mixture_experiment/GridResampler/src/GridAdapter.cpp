#include "GridAdapter.h"

#include "NearestInterpolation.h"
#include "PolygonInterpolation.h"

#include <stdexcept>

namespace
{
HealpixGrid makeGrid(const GridSpecification& specification)
{
    return HealpixGrid{
        specification.healpixNside,
        specification.energyPointCount,
        specification.energyMinMeV,
        specification.energyMaxMeV
    };
}
}

GridAdapter::GridAdapter(const ResamplerConfig& config)
    : masterGrid_{makeGrid(config.masterGrid())},
      targetGrid_{makeGrid(config.targetGrid())}
{
    if (config.interpolation() == "nearest")
    {
        strategy_ = std::make_unique<NearestInterpolation>();
    }
    else if (config.interpolation() == "polygon")
    {
        strategy_ = std::make_unique<PolygonInterpolation>(
            config.polygonSubdivisionFactor(),
            config.requireFullCoverage()
        );
    }
    else
    {
        throw std::runtime_error{"Unknown interpolation strategy."};
    }
}

const IGrid& GridAdapter::masterGrid() const { return masterGrid_; }
const IGrid& GridAdapter::targetGrid() const { return targetGrid_; }

AbsoluteEfficiencyMap GridAdapter::resample(
    const AbsoluteEfficiencyMap& master
) const
{
    return strategy_->resample(masterGrid_, targetGrid_, master);
}

std::string GridAdapter::strategyName() const
{
    return strategy_->name();
}
