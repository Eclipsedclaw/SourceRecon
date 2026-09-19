#ifndef EIID_V7_NEAREST_INTERPOLATION_H
#define EIID_V7_NEAREST_INTERPOLATION_H

#include "IInterpolationStrategy.h"

class NearestInterpolation final : public IInterpolationStrategy
{
public:
    std::string name() const override;
    AbsoluteEfficiencyMap resample(
        const IGrid& masterGrid,
        const IGrid& targetGrid,
        const AbsoluteEfficiencyMap& master
    ) const override;
};

#endif
