#include "ResamplerConfig.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
nlohmann::json readJson(const std::filesystem::path& path)
{
    std::ifstream input{path};

    if (!input)
    {
        throw std::runtime_error{"Cannot open resampler configuration: " + path.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;
        return document;
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid resampler JSON: " + std::string{error.what()}};
    }
}

std::filesystem::path resolvePath(
    const std::filesystem::path& base,
    const std::string& configuredPath
)
{
    const std::filesystem::path path{configuredPath};
    return path.is_absolute() ? path.lexically_normal() : (base / path).lexically_normal();
}

GridSpecification readGridSpecification(const nlohmann::json& grid)
{
    return GridSpecification{
        grid.at("healpix_nside").get<int>(),
        grid.at("energy_point_count").get<int>(),
        static_cast<Decimal>(grid.at("energy_min_MeV").get<double>()),
        static_cast<Decimal>(grid.at("energy_max_MeV").get<double>())
    };
}

void validateGrid(const GridSpecification& grid, const std::string& name)
{
    if (grid.healpixNside <= 0 || grid.energyPointCount <= 0 ||
        !std::isfinite(grid.energyMinMeV) ||
        !std::isfinite(grid.energyMaxMeV) ||
        grid.energyMaxMeV < grid.energyMinMeV)
    {
        throw std::runtime_error{name + " grid is invalid."};
    }

    if (grid.energyPointCount == 1 && grid.energyMinMeV != grid.energyMaxMeV)
    {
        throw std::runtime_error{name + " one-point energy grid requires equal bounds."};
    }
}
}

ResamplerConfig::ResamplerConfig(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();

    const std::filesystem::path base = absolutePath.parent_path();
    const nlohmann::json document = readJson(absolutePath);

    try
    {
        inputSensitivityFile_ = resolvePath(
            base,
            document.at("input_sensitivity_file").get<std::string>()
        );

        inputSensitivityTree_ = document.at("input_sensitivity_tree").get<std::string>();

        outputSensitivityFile_ = resolvePath(
            base,
            document.at("output_sensitivity_file").get<std::string>()
        );

        outputSensitivityTree_ = document.at("output_sensitivity_tree").get<std::string>();
        masterGrid_ = readGridSpecification(document.at("master_grid"));
        targetGrid_ = readGridSpecification(document.at("target_grid"));
        interpolation_ = document.at("interpolation").get<std::string>();
        polygonSubdivisionFactor_ = document.at("polygon_subdivision_factor").get<int>();
        requireFullCoverage_ = document.at("require_full_coverage").get<bool>();
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Missing or invalid resampler setting: " + std::string{error.what()}};
    }

    validateGrid(masterGrid_, "Master");
    validateGrid(targetGrid_, "Target");

    if (inputSensitivityTree_.empty() || outputSensitivityTree_.empty())
    {
        throw std::runtime_error{"Sensitivity tree names must not be empty."};
    }

    if (interpolation_ != "nearest" && interpolation_ != "polygon")
    {
        throw std::runtime_error{"interpolation must be nearest or polygon."};
    }

    if (polygonSubdivisionFactor_ <= 0)
    {
        throw std::runtime_error{"polygon_subdivision_factor must be positive."};
    }

    if (targetGrid_.energyMinMeV < masterGrid_.energyMinMeV ||
        targetGrid_.energyMaxMeV > masterGrid_.energyMaxMeV)
    {
        throw std::runtime_error{"Target energy range must lie inside the Master energy range."};
    }
}

const std::filesystem::path& ResamplerConfig::inputSensitivityFile() const { return inputSensitivityFile_; }
const std::string& ResamplerConfig::inputSensitivityTree() const { return inputSensitivityTree_; }
const std::filesystem::path& ResamplerConfig::outputSensitivityFile() const { return outputSensitivityFile_; }
const std::string& ResamplerConfig::outputSensitivityTree() const { return outputSensitivityTree_; }
const GridSpecification& ResamplerConfig::masterGrid() const { return masterGrid_; }
const GridSpecification& ResamplerConfig::targetGrid() const { return targetGrid_; }
const std::string& ResamplerConfig::interpolation() const { return interpolation_; }
int ResamplerConfig::polygonSubdivisionFactor() const { return polygonSubdivisionFactor_; }
bool ResamplerConfig::requireFullCoverage() const { return requireFullCoverage_; }
