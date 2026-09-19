#ifndef EIID_V6_RESAMPLER_CONFIG_H
#define EIID_V6_RESAMPLER_CONFIG_H

#include "Common.h"

#include <filesystem>
#include <string>

struct GridSpecification
{
    int healpixNside{};
    int energyPointCount{};
    Decimal energyMinMeV{};
    Decimal energyMaxMeV{};
};

class ResamplerConfig
{
public:
    explicit ResamplerConfig(const std::filesystem::path& path);
    const std::filesystem::path& inputFile() const;
    const std::string& inputTree() const;
    const std::filesystem::path& outputFile() const;
    const std::string& outputTree() const;
    const GridSpecification& masterGrid() const;
    const GridSpecification& targetGrid() const;
    const std::string& interpolation() const;
    int polygonSubdivisionFactor() const;
    bool requireFullCoverage() const;

private:
    std::filesystem::path inputFile_;
    std::string inputTree_;
    std::filesystem::path outputFile_;
    std::string outputTree_;
    GridSpecification masterGrid_;
    GridSpecification targetGrid_;
    std::string interpolation_;
    int polygonSubdivisionFactor_{};
    bool requireFullCoverage_{};
};

#endif
