#include "ConfigManager.hh"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::filesystem::path resolve(
    const std::filesystem::path& configPath,
    const std::string& configured
)
{
    const std::filesystem::path path{configured};
    return (path.is_absolute() ? path : configPath.parent_path() / path)
        .lexically_normal();
}

void requirePositive(double value, const char* name)
{
    if (!std::isfinite(value) || value <= 0.0)
    {
        throw std::runtime_error{std::string{name} + " must be finite and positive."};
    }
}
}

ConfigManager::ConfigManager(const std::filesystem::path& configPath)
{
    const auto absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{"Cannot open simulation config: " + absolutePath.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;
        mode_ = document.at("mode").get<int>();
        randomSeed_ = document.at("random_seed").get<std::int64_t>();

        const auto& source = document.at("source");
        particleName_ = source.at("particle_name").get<std::string>();
        hemisphereRadiusMm_ = source.at("hemisphere_radius_mm").get<double>();
        frontHemisphereOnly_ = source.at("front_hemisphere_only").get<bool>();
        coneSafetyMarginDegree_ =
            source.at("emission_cone_safety_margin_degree").get<double>();

        const auto& environment = document.at("environment");
        worldMaterial_ = environment.at("world_material").get<std::string>();
        worldMarginMm_ = environment.at("world_margin_mm").get<double>();

        const auto& grid = document.at("grid");
        healpixNside_ = grid.at("healpix_nside").get<int>();
        energyPointCount_ = grid.at("energy_point_count").get<int>();
        energyMinMeV_ = grid.at("energy_min_MeV").get<double>();
        energyMaxMeV_ = grid.at("energy_max_MeV").get<double>();
        particlesPerCell_ = grid.at("particles_per_cell").get<int>();

        const auto& trigger = document.at("trigger");
        frontChamberId_ = trigger.at("front_chamber_id").get<int>();
        rearChamberId_ = trigger.at("rear_chamber_id").get<int>();
        minimumLayerEnergyMeV_ =
            trigger.at("minimum_layer_energy_MeV").get<double>();

        const auto& output = document.at("output");
        efficiencyRootFile_ = resolve(
            absolutePath,
            output.at("absolute_efficiency_root_file").get<std::string>()
        );
        efficiencyTreeName_ =
            output.at("absolute_efficiency_tree_name").get<std::string>();
        eventsRootFile_ = resolve(
            absolutePath,
            output.at("events_root_file").get<std::string>()
        );
        eventsTreeName_ = output.at("events_tree_name").get<std::string>();
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid simulation setting: " + std::string{error.what()}};
    }

    if ((mode_ != 0 && mode_ != 1) || randomSeed_ <= 0 ||
        particleName_.empty())
    {
        throw std::runtime_error{"Simulation mode, seed, or particle name is invalid."};
    }

    requirePositive(hemisphereRadiusMm_, "hemisphere_radius_mm");
    requirePositive(worldMarginMm_, "world_margin_mm");

    if (!std::isfinite(coneSafetyMarginDegree_) ||
        coneSafetyMarginDegree_ < 0.0 || coneSafetyMarginDegree_ >= 45.0)
    {
        throw std::runtime_error{
            "emission_cone_safety_margin_degree must be within [0, 45)."
        };
    }

    if (worldMaterial_ != "G4_Galactic" && worldMaterial_ != "G4_AIR")
    {
        throw std::runtime_error{"world_material must be G4_Galactic or G4_AIR."};
    }

    if (healpixNside_ <= 0 || (healpixNside_ & (healpixNside_ - 1)) != 0 ||
        energyPointCount_ <= 0 || particlesPerCell_ <= 0)
    {
        throw std::runtime_error{"Simulation grid dimensions are invalid."};
    }

    requirePositive(energyMinMeV_, "energy_min_MeV");
    requirePositive(energyMaxMeV_, "energy_max_MeV");

    if (energyMaxMeV_ < energyMinMeV_ ||
        (energyPointCount_ == 1 && energyMinMeV_ != energyMaxMeV_))
    {
        throw std::runtime_error{"Simulation energy grid is invalid."};
    }

    if (frontChamberId_ != 0 || rearChamberId_ != 1)
    {
        throw std::runtime_error{"V7 detector geometry requires ch2=0 and ch1=1."};
    }

    if (!std::isfinite(minimumLayerEnergyMeV_) ||
        minimumLayerEnergyMeV_ < 0.0 || efficiencyTreeName_.empty() ||
        eventsTreeName_.empty())
    {
        throw std::runtime_error{"Trigger threshold or ROOT tree names are invalid."};
    }
}

int ConfigManager::mode() const { return mode_; }
std::int64_t ConfigManager::randomSeed() const { return randomSeed_; }
const std::string& ConfigManager::particleName() const { return particleName_; }
double ConfigManager::hemisphereRadiusMm() const { return hemisphereRadiusMm_; }
bool ConfigManager::frontHemisphereOnly() const { return frontHemisphereOnly_; }
double ConfigManager::emissionConeSafetyMarginDegree() const { return coneSafetyMarginDegree_; }
const std::string& ConfigManager::worldMaterial() const { return worldMaterial_; }
double ConfigManager::worldMarginMm() const { return worldMarginMm_; }
int ConfigManager::healpixNside() const { return healpixNside_; }
int ConfigManager::energyPointCount() const { return energyPointCount_; }
double ConfigManager::energyMinMeV() const { return energyMinMeV_; }
double ConfigManager::energyMaxMeV() const { return energyMaxMeV_; }
int ConfigManager::particlesPerCell() const { return particlesPerCell_; }
int ConfigManager::frontChamberId() const { return frontChamberId_; }
int ConfigManager::rearChamberId() const { return rearChamberId_; }
double ConfigManager::minimumLayerEnergyMeV() const { return minimumLayerEnergyMeV_; }
const std::filesystem::path& ConfigManager::efficiencyRootFile() const { return efficiencyRootFile_; }
const std::string& ConfigManager::efficiencyTreeName() const { return efficiencyTreeName_; }
const std::filesystem::path& ConfigManager::eventsRootFile() const { return eventsRootFile_; }
const std::string& ConfigManager::eventsTreeName() const { return eventsTreeName_; }
