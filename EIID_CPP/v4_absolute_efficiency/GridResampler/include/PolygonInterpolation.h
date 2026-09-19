#ifndef EIID_V4_POLYGON_INTERPOLATION_H
#define EIID_V4_POLYGON_INTERPOLATION_H

#include "IInterpolationStrategy.h"

class PolygonInterpolation final : public IInterpolationStrategy
{
public:
    PolygonInterpolation(int subdivisionFactor, bool requireFullCoverage);
    std::string name() const override;
    AbsoluteEfficiencyMap resample(
        const IGrid& masterGrid,
        const IGrid& targetGrid,
        const AbsoluteEfficiencyMap& master
    ) const override;

private:
    int subdivisionFactor_{};
    bool requireFullCoverage_{};
};

#endif
