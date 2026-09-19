#include "ResamplerConfig.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::filesystem::path resolve(
    const std::filesystem::path& directory,
    const std::string& configured
)
{
    const std::filesystem::path path{configured};
    return (path.is_absolute() ? path : directory / path).lexically_normal();
}

GridSpecification readGrid(const nlohmann::json& value)
{
    return GridSpecification{
        value.at("healpix_nside").get<int>(),
        value.at("energy_point_count").get<int>(),
        value.at("energy_min_MeV").get<double>(),
        value.at("energy_max_MeV").get<double>()
    };
}

void validateGrid(const GridSpecification& grid, const char* name)
{
    if (grid.healpixNside <= 0 || grid.energyPointCount <= 0 ||
        !std::isfinite(grid.energyMinMeV) ||
        !std::isfinite(grid.energyMaxMeV) ||
        grid.energyMaxMeV < grid.energyMinMeV ||
        (grid.energyPointCount == 1 &&
         grid.energyMinMeV != grid.energyMaxMeV))
    {
        throw std::runtime_error{std::string{name} + " grid is invalid."};
    }
}
}

ResamplerConfig::ResamplerConfig(const std::filesystem::path& path)
{
    const auto absolutePath = std::filesystem::absolute(path).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{"Cannot open resampler configuration: " + absolutePath.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;
        const auto directory = absolutePath.parent_path();
        inputFile_ = resolve(
            directory,
            document.at("input_absolute_efficiency_file").get<std::string>()
        );
        inputTree_ =
            document.at("input_absolute_efficiency_tree").get<std::string>();
        outputFile_ = resolve(
            directory,
            document.at("output_absolute_efficiency_file").get<std::string>()
        );
        outputTree_ =
            document.at("output_absolute_efficiency_tree").get<std::string>();
        masterGrid_ = readGrid(document.at("master_grid"));
        targetGrid_ = readGrid(document.at("target_grid"));
        interpolation_ = document.at("interpolation").get<std::string>();
        polygonSubdivisionFactor_ =
            document.at("polygon_subdivision_factor").get<int>();
        requireFullCoverage_ = document.at("require_full_coverage").get<bool>();
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid resampler setting: " + std::string{error.what()}};
    }

    validateGrid(masterGrid_, "Master");
    validateGrid(targetGrid_, "Target");

    if (inputTree_.empty() || outputTree_.empty() ||
        (interpolation_ != "nearest" && interpolation_ != "polygon") ||
        polygonSubdivisionFactor_ <= 0)
    {
        throw std::runtime_error{"Resampler tree or interpolation settings are invalid."};
    }

    if (targetGrid_.energyMinMeV < masterGrid_.energyMinMeV ||
        targetGrid_.energyMaxMeV > masterGrid_.energyMaxMeV)
    {
        throw std::runtime_error{"Target energy range must be inside the Master range."};
    }
}

const std::filesystem::path& ResamplerConfig::inputFile() const { return inputFile_; }
const std::string& ResamplerConfig::inputTree() const { return inputTree_; }
const std::filesystem::path& ResamplerConfig::outputFile() const { return outputFile_; }
const std::string& ResamplerConfig::outputTree() const { return outputTree_; }
const GridSpecification& ResamplerConfig::masterGrid() const { return masterGrid_; }
const GridSpecification& ResamplerConfig::targetGrid() const { return targetGrid_; }
const std::string& ResamplerConfig::interpolation() const { return interpolation_; }
int ResamplerConfig::polygonSubdivisionFactor() const { return polygonSubdivisionFactor_; }
bool ResamplerConfig::requireFullCoverage() const { return requireFullCoverage_; }
