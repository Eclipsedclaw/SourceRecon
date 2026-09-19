#include "ReconConfig.h"

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
        throw std::runtime_error{"Cannot open reconstruction configuration: " + path.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;
        return document;
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid reconstruction JSON in " + path.string() + ": " + error.what()};
    }
}

std::filesystem::path resolvePath(
    const std::filesystem::path& configDirectory,
    const std::string& configuredPath
)
{
    const std::filesystem::path path{configuredPath};

    if (path.is_absolute())
    {
        return path.lexically_normal();
    }

    return (configDirectory / path).lexically_normal();
}

void requireNonEmpty(const std::string& value, const std::string& name)
{
    if (value.empty())
    {
        throw std::runtime_error{name + " must not be empty."};
    }
}
}

ReconConfig::ReconConfig(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();

    const std::filesystem::path configDirectory = absolutePath.parent_path();
    const nlohmann::json document = readJson(absolutePath);

    try
    {
        inputEventsFile_ = resolvePath(
            configDirectory,
            document.at("input_events_file").get<std::string>()
        );

        inputEventsTree_ = document.at("input_events_tree").get<std::string>();

        outputResultFile_ = resolvePath(
            configDirectory,
            document.at("output_result_file").get<std::string>()
        );

        outputResultTree_ = document.at("output_result_tree").get<std::string>();

        sensitivityFile_ = resolvePath(
            configDirectory,
            document.at("sensitivity_file").get<std::string>()
        );

        sensitivityTree_ = document.at("sensitivity_tree").get<std::string>();

        healpixNside_ = document.at("healpix_nside").get<int>();
        healpixOrdering_ = document.at("healpix_ordering").get<std::string>();
        energyMinMeV_ = static_cast<Decimal>(document.at("energy_min_MeV").get<double>());
        energyMaxMeV_ = static_cast<Decimal>(document.at("energy_max_MeV").get<double>());
        energyPointCount_ = document.at("energy_point_count").get<int>();

        iterationCount_ = document.at("iteration_count").get<int>();
        responseSigmaDegree_ = static_cast<Decimal>(document.at("response_sigma_degree").get<double>());
        denominatorFloor_ = static_cast<Decimal>(document.at("denominator_floor").get<double>());
        requireCompleteSensitivity_ = document.at("require_complete_sensitivity").get<bool>();

        const nlohmann::json& event = document.at("event_branches");
        eventBranches_ = EventBranchNames{
            event.at("r1_x").get<std::string>(),
            event.at("r1_y").get<std::string>(),
            event.at("r1_z").get<std::string>(),
            event.at("r2_x").get<std::string>(),
            event.at("r2_y").get<std::string>(),
            event.at("r2_z").get<std::string>(),
            event.at("e1_MeV").get<std::string>()
        };

        const nlohmann::json& result = document.at("result_branches");
        resultBranches_ = ResultBranchNames{
            result.at("cell_index").get<std::string>(),
            result.at("weight").get<std::string>(),
            result.at("healpix_pixel_id").get<std::string>(),
            result.at("theta_degree").get<std::string>(),
            result.at("phi_degree").get<std::string>(),
            result.at("direction_x").get<std::string>(),
            result.at("direction_y").get<std::string>(),
            result.at("direction_z").get<std::string>(),
            result.at("energy_MeV").get<std::string>()
        };

        const nlohmann::json& sensitivity = document.at("sensitivity_branches");
        sensitivityBranches_ = SensitivityBranchNames{
            sensitivity.at("direction_index").get<std::string>(),
            sensitivity.at("energy_index").get<std::string>(),
            sensitivity.at("healpix_pixel_id").get<std::string>(),
            sensitivity.at("energy_MeV").get<std::string>(),
            sensitivity.at("sensitivity").get<std::string>()
        };
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Missing or invalid reconstruction setting: " + std::string{error.what()}};
    }

    requireNonEmpty(inputEventsTree_, "input_events_tree");
    requireNonEmpty(outputResultTree_, "output_result_tree");
    requireNonEmpty(sensitivityTree_, "sensitivity_tree");
    requireNonEmpty(eventBranches_.r1X, "event_branches.r1_x");
    requireNonEmpty(eventBranches_.r1Y, "event_branches.r1_y");
    requireNonEmpty(eventBranches_.r1Z, "event_branches.r1_z");
    requireNonEmpty(eventBranches_.r2X, "event_branches.r2_x");
    requireNonEmpty(eventBranches_.r2Y, "event_branches.r2_y");
    requireNonEmpty(eventBranches_.r2Z, "event_branches.r2_z");
    requireNonEmpty(eventBranches_.e1MeV, "event_branches.e1_MeV");
    requireNonEmpty(sensitivityBranches_.directionIndex,
                    "sensitivity_branches.direction_index");
    requireNonEmpty(sensitivityBranches_.energyIndex,
                    "sensitivity_branches.energy_index");
    requireNonEmpty(sensitivityBranches_.healpixPixelId,
                    "sensitivity_branches.healpix_pixel_id");
    requireNonEmpty(sensitivityBranches_.energyMeV,
                    "sensitivity_branches.energy_MeV");
    requireNonEmpty(sensitivityBranches_.sensitivity,
                    "sensitivity_branches.sensitivity");

    if (healpixNside_ <= 0)
    {
        throw std::runtime_error{"healpix_nside must be positive."};
    }

    if (healpixOrdering_ != "RING")
    {
        throw std::runtime_error{"V3 currently requires healpix_ordering = RING."};
    }

    if (energyPointCount_ <= 0 || !std::isfinite(energyMinMeV_) ||
        !std::isfinite(energyMaxMeV_) || energyMaxMeV_ < energyMinMeV_)
    {
        throw std::runtime_error{"The configured energy grid is invalid."};
    }

    if (energyPointCount_ == 1 && energyMaxMeV_ != energyMinMeV_)
    {
        throw std::runtime_error{"A one-point energy grid requires equal minimum and maximum energy."};
    }

    if (iterationCount_ <= 0)
    {
        throw std::runtime_error{"iteration_count must be positive."};
    }

    if (!(responseSigmaDegree_ > static_cast<Decimal>(0.0L)) ||
        !(denominatorFloor_ > static_cast<Decimal>(0.0L)))
    {
        throw std::runtime_error{"response_sigma_degree and denominator_floor must be positive."};
    }
}

const std::filesystem::path& ReconConfig::inputEventsFile() const { return inputEventsFile_; }
const std::string& ReconConfig::inputEventsTree() const { return inputEventsTree_; }
const std::filesystem::path& ReconConfig::outputResultFile() const { return outputResultFile_; }
const std::string& ReconConfig::outputResultTree() const { return outputResultTree_; }
const std::filesystem::path& ReconConfig::sensitivityFile() const { return sensitivityFile_; }
const std::string& ReconConfig::sensitivityTree() const { return sensitivityTree_; }
int ReconConfig::healpixNside() const { return healpixNside_; }
const std::string& ReconConfig::healpixOrdering() const { return healpixOrdering_; }
int ReconConfig::energyPointCount() const { return energyPointCount_; }
Decimal ReconConfig::energyMinMeV() const { return energyMinMeV_; }
Decimal ReconConfig::energyMaxMeV() const { return energyMaxMeV_; }
int ReconConfig::iterationCount() const { return iterationCount_; }
Decimal ReconConfig::responseSigmaDegree() const { return responseSigmaDegree_; }
Decimal ReconConfig::denominatorFloor() const { return denominatorFloor_; }
bool ReconConfig::requireCompleteSensitivity() const { return requireCompleteSensitivity_; }
const EventBranchNames& ReconConfig::eventBranches() const { return eventBranches_; }
const ResultBranchNames& ReconConfig::resultBranches() const { return resultBranches_; }
const SensitivityBranchNames& ReconConfig::sensitivityBranches() const { return sensitivityBranches_; }
