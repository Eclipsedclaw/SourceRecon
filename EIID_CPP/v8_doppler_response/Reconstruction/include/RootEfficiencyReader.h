#ifndef EIID_V7_ROOT_EFFICIENCY_READER_H
#define EIID_V7_ROOT_EFFICIENCY_READER_H

#include "AbsoluteEfficiencyMap.h"

class IGrid;
class ReconConfig;

class RootEfficiencyReader
{
public:
    static AbsoluteEfficiencyMap read(
        const ReconConfig& config,
        const IGrid& grid
    );
};

#endif
