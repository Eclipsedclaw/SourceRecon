#include "io_config.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::string resolvePath(
    const std::filesystem::path& configPath,
    const std::string& configuredPath
)
{
    const std::filesystem::path path{configuredPath};

    return (
        path.is_absolute() ? path : configPath.parent_path() / path
    ).lexically_normal().string();
}

void requireNonEmpty(const std::string& value, const std::string& name)
{
    if (value.empty())
    {
        throw std::runtime_error{name + " cannot be empty."};
    }
}
}

IoConfig::IoConfig(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open Translator configuration: " + absolutePath.string()
        };
    }

    nlohmann::json json;

    try
    {
        input >> json;

        rawGeant4FilePath = resolvePath(
            absolutePath,
            json.at("raw_input_file").get<std::string>()
        );
        rawGeant4TreeName = json.at("raw_input_tree").get<std::string>();
        inputRootFilePath = resolvePath(
            absolutePath,
            json.at("output_events_file").get<std::string>()
        );
        inputTreeName = json.at("output_events_tree").get<std::string>();

        frontChamberId = json.at("front_chamber_id").get<int>();
        rearChamberId = json.at("rear_chamber_id").get<int>();
        minimumLayerEnergyMeV =
            json.at("minimum_layer_energy_MeV").get<double>();

        const auto& raw = json.at("raw_branches");
        rawEventIdBranchName = raw.at("event_id").get<std::string>();
        rawChamberIdBranchName = raw.at("chamber_id").get<std::string>();
        rawXBranchName = raw.at("x").get<std::string>();
        rawYBranchName = raw.at("y").get<std::string>();
        rawZBranchName = raw.at("z").get<std::string>();
        rawEnergyDepositBranchName =
            raw.at("energy_deposit_MeV").get<std::string>();

        const auto& output = json.at("output_branches");
        r1XBranchName = output.at("r1_x").get<std::string>();
        r1YBranchName = output.at("r1_y").get<std::string>();
        r1ZBranchName = output.at("r1_z").get<std::string>();
        r2XBranchName = output.at("r2_x").get<std::string>();
        r2YBranchName = output.at("r2_y").get<std::string>();
        r2ZBranchName = output.at("r2_z").get<std::string>();
        e1MeVBranchName = output.at("e1_MeV").get<std::string>();
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{
            "Missing or invalid Translator setting: " +
            std::string{error.what()}
        };
    }

    outputResultPath.clear();
    outputTreeName.clear();
    outputCellIndexBranchName.clear();
    outputWeightBranchName.clear();

    requireNonEmpty(rawGeant4TreeName, "raw_input_tree");
    requireNonEmpty(inputTreeName, "output_events_tree");
    requireNonEmpty(rawEventIdBranchName, "raw_branches.event_id");
    requireNonEmpty(rawChamberIdBranchName, "raw_branches.chamber_id");
    requireNonEmpty(rawXBranchName, "raw_branches.x");
    requireNonEmpty(rawYBranchName, "raw_branches.y");
    requireNonEmpty(rawZBranchName, "raw_branches.z");
    requireNonEmpty(
        rawEnergyDepositBranchName,
        "raw_branches.energy_deposit_MeV"
    );
    requireNonEmpty(r1XBranchName, "output_branches.r1_x");
    requireNonEmpty(r1YBranchName, "output_branches.r1_y");
    requireNonEmpty(r1ZBranchName, "output_branches.r1_z");
    requireNonEmpty(r2XBranchName, "output_branches.r2_x");
    requireNonEmpty(r2YBranchName, "output_branches.r2_y");
    requireNonEmpty(r2ZBranchName, "output_branches.r2_z");
    requireNonEmpty(e1MeVBranchName, "output_branches.e1_MeV");

    if (frontChamberId == rearChamberId)
    {
        throw std::runtime_error{
            "Translator front and rear chamber IDs must differ."
        };
    }

    if (!std::isfinite(minimumLayerEnergyMeV) ||
        minimumLayerEnergyMeV < 0.0)
    {
        throw std::runtime_error{
            "minimum_layer_energy_MeV must be finite and non-negative."
        };
    }
}
