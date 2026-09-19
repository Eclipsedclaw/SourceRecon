#include "ReconConfig.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::filesystem::path resolvePath(
    const std::filesystem::path& directory,
    const std::string& configured
)
{
    const std::filesystem::path path{configured};
    return (path.is_absolute() ? path : directory / path).lexically_normal();
}

void requireNonEmpty(const std::string& value, const char* name)
{
    if (value.empty())
    {
        throw std::runtime_error{std::string{name} + " cannot be empty."};
    }
}
}

ReconConfig::ReconConfig(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open reconstruction configuration: " +
            absolutePath.string()
        };
    }

    try
    {
        nlohmann::json document;
        input >> document;
        const std::filesystem::path directory = absolutePath.parent_path();

        inputEventsFile_ = resolvePath(
            directory,
            document.at("input_events_file").get<std::string>()
        );
        inputEventsTree_ = document.at("input_events_tree").get<std::string>();
        outputResultFile_ = resolvePath(
            directory,
            document.at("output_result_file").get<std::string>()
        );
        outputResultTree_ = document.at("output_result_tree").get<std::string>();
        efficiencyFile_ = resolvePath(
            directory,
            document.at("absolute_efficiency_file").get<std::string>()
        );
        efficiencyTree_ =
            document.at("absolute_efficiency_tree").get<std::string>();

        healpixNside_ = document.at("healpix_nside").get<int>();
        healpixOrdering_ = document.at("healpix_ordering").get<std::string>();
        energyMinMeV_ = static_cast<Decimal>(
            document.at("energy_min_MeV").get<double>()
        );
        energyMaxMeV_ = static_cast<Decimal>(
            document.at("energy_max_MeV").get<double>()
        );
        energyPointCount_ = document.at("energy_point_count").get<int>();
        iterationCount_ = document.at("iteration_count").get<int>();
        responseSigmaDegree_ = static_cast<Decimal>(
            document.at("response_sigma_degree").get<double>()
        );
        denominatorFloor_ = static_cast<Decimal>(
            document.at("denominator_floor").get<double>()
        );

        const auto& event = document.at("event_branches");
        eventBranches_ = EventBranchNames{
            event.at("r1_x").get<std::string>(),
            event.at("r1_y").get<std::string>(),
            event.at("r1_z").get<std::string>(),
            event.at("r2_x").get<std::string>(),
            event.at("r2_y").get<std::string>(),
            event.at("r2_z").get<std::string>(),
            event.at("e1_MeV").get<std::string>()
        };

        const auto& result = document.at("result_branches");
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

        const auto& efficiency = document.at("absolute_efficiency_branches");
        efficiencyBranches_ = EfficiencyBranchNames{
            efficiency.at("cell_index").get<std::string>(),
            efficiency.at("efficiency").get<std::string>()
        };
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{
            "Missing or invalid reconstruction setting: " +
            std::string{error.what()}
        };
    }

    requireNonEmpty(inputEventsTree_, "input_events_tree");
    requireNonEmpty(outputResultTree_, "output_result_tree");
    requireNonEmpty(efficiencyTree_, "absolute_efficiency_tree");
    requireNonEmpty(efficiencyBranches_.cellIndex,
                    "absolute_efficiency_branches.cell_index");
    requireNonEmpty(efficiencyBranches_.efficiency,
                    "absolute_efficiency_branches.efficiency");

    if (healpixNside_ <= 0 || healpixOrdering_ != "RING")
    {
        throw std::runtime_error{"V7 requires positive RING-order HEALPix Nside."};
    }

    if (energyPointCount_ <= 0 || !std::isfinite(energyMinMeV_) ||
        !std::isfinite(energyMaxMeV_) || energyMaxMeV_ < energyMinMeV_ ||
        (energyPointCount_ == 1 && energyMinMeV_ != energyMaxMeV_))
    {
        throw std::runtime_error{"The reconstruction energy grid is invalid."};
    }

    if (iterationCount_ <= 0 || responseSigmaDegree_ <= 0.0 ||
        denominatorFloor_ <= 0.0)
    {
        throw std::runtime_error{"Iteration and numerical parameters must be positive."};
    }
}

const std::filesystem::path& ReconConfig::inputEventsFile() const { return inputEventsFile_; }
const std::string& ReconConfig::inputEventsTree() const { return inputEventsTree_; }
const std::filesystem::path& ReconConfig::outputResultFile() const { return outputResultFile_; }
const std::string& ReconConfig::outputResultTree() const { return outputResultTree_; }
const std::filesystem::path& ReconConfig::efficiencyFile() const { return efficiencyFile_; }
const std::string& ReconConfig::efficiencyTree() const { return efficiencyTree_; }
int ReconConfig::healpixNside() const { return healpixNside_; }
const std::string& ReconConfig::healpixOrdering() const { return healpixOrdering_; }
int ReconConfig::energyPointCount() const { return energyPointCount_; }
Decimal ReconConfig::energyMinMeV() const { return energyMinMeV_; }
Decimal ReconConfig::energyMaxMeV() const { return energyMaxMeV_; }
int ReconConfig::iterationCount() const { return iterationCount_; }
Decimal ReconConfig::responseSigmaDegree() const { return responseSigmaDegree_; }
Decimal ReconConfig::denominatorFloor() const { return denominatorFloor_; }
const EventBranchNames& ReconConfig::eventBranches() const { return eventBranches_; }
const ResultBranchNames& ReconConfig::resultBranches() const { return resultBranches_; }
const EfficiencyBranchNames& ReconConfig::efficiencyBranches() const { return efficiencyBranches_; }
