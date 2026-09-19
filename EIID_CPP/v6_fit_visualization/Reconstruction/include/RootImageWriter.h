#ifndef EIID_V6_ROOT_IMAGE_WRITER_H
#define EIID_V6_ROOT_IMAGE_WRITER_H

#include "Common.h"

#include <vector>

class IGrid;
class ReconConfig;

class RootImageWriter
{
public:
    static void write(
        const std::vector<Decimal>& image,
        const IGrid& grid,
        const ReconConfig& config
    );
};

#endif
