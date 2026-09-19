#ifndef EIID_V4_RESAMPLER_IO_H
#define EIID_V4_RESAMPLER_IO_H

#include "AbsoluteEfficiencyMap.h"

#include <filesystem>
#include <string>

class IGrid;

struct EfficiencyDataset
{
    AbsoluteEfficiencyMap values;
    double sourceRadiusMm{};
};

class ResamplerIO
{
public:
    static EfficiencyDataset read(
        const std::filesystem::path& path,
        const std::string& treeName,
        const IGrid& grid
    );
    static void write(
        const std::filesystem::path& path,
        const std::string& treeName,
        const IGrid& grid,
        const AbsoluteEfficiencyMap& values,
        double sourceRadiusMm
    );
};

#endif
