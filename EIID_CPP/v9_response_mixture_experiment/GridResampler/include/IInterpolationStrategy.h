#ifndef EIID_V7_I_INTERPOLATION_STRATEGY_H
#define EIID_V7_I_INTERPOLATION_STRATEGY_H

#include "AbsoluteEfficiencyMap.h"

#include <string>

class IGrid;

class IInterpolationStrategy
{
public:
    virtual ~IInterpolationStrategy() = default;
    virtual std::string name() const = 0;
    virtual AbsoluteEfficiencyMap resample(
        const IGrid& masterGrid,
        const IGrid& targetGrid,
        const AbsoluteEfficiencyMap& master
    ) const = 0;
};

#endif
