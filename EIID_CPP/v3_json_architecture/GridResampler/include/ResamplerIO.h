#ifndef EIID_RESAMPLER_IO_H
#define EIID_RESAMPLER_IO_H

#include "SensitivityMatrix.h"
#include "grid.h"

#include <filesystem>
#include <string>

class ResamplerIO
{
public:
    static SensitivityMatrix read(
        const std::filesystem::path& filePath,
        const std::string& treeName,
        const Grid& grid
    );

    static void write(
        const std::filesystem::path& filePath,
        const std::string& treeName,
        const Grid& grid,
        const SensitivityMatrix& sensitivity
    );
};

#endif
