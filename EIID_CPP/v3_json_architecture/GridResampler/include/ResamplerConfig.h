#ifndef EIID_RESAMPLER_CONFIG_H
#define EIID_RESAMPLER_CONFIG_H

#include "common.h"

#include <filesystem>
#include <string>

struct GridSpecification
{
    int healpixNside;
    int energyPointCount;
    Decimal energyMinMeV;
    Decimal energyMaxMeV;
};

class ResamplerConfig
{
public:
    explicit ResamplerConfig(const std::filesystem::path& configPath);

    const std::filesystem::path& inputSensitivityFile() const;
    const std::string& inputSensitivityTree() const;
    const std::filesystem::path& outputSensitivityFile() const;
    const std::string& outputSensitivityTree() const;

    const GridSpecification& masterGrid() const;
    const GridSpecification& targetGrid() const;
    const std::string& interpolation() const;
    int polygonSubdivisionFactor() const;
    bool requireFullCoverage() const;

private:
    std::filesystem::path inputSensitivityFile_;
    std::string inputSensitivityTree_;
    std::filesystem::path outputSensitivityFile_;
    std::string outputSensitivityTree_;
    GridSpecification masterGrid_{};
    GridSpecification targetGrid_{};
    std::string interpolation_;
    int polygonSubdivisionFactor_ = 1;
    bool requireFullCoverage_ = true;
};

#endif
