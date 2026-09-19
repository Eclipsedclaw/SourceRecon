#include "ConfigManager.hh"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::filesystem::path resolvePath(
    const std::filesystem::path& configPath,
    const std::string& configuredPath
)
{
    const std::filesystem::path path{configuredPath};

    if (path.is_absolute())
    {
        return path.lexically_normal();
    }

    return (configPath.parent_path() / path).lexically_normal();
}

void requireFinitePositive(double value, const std::string& name)
{
    if (!std::isfinite(value) || value <= 0.0)
    {
        throw std::runtime_error{name + " must be finite and positive."};
    }
}
}

ConfigManager::ConfigManager(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open Geant4 simulation config: " + configPath.string()
        };
    }

    nlohmann::json json;
    input >> json;

    mode_ = json.at("mode").get<int>();
    randomSeed_ = json.at("random_seed").get<std::int64_t>();

    const auto& source = json.at("source");
    particleName_ = source.at("particle_name").get<std::string>();
    hemisphereRadiusMm_ = source.at("hemisphere_radius_mm").get<double>();
    frontHemisphereOnly_ = source.at("front_hemisphere_only").get<bool>();
    emissionConeHalfAngleDegree_ =
        source.at("emission_cone_half_angle_degree").get<double>();

    const auto& grid = json.at("grid");
    healpixNside_ = grid.at("healpix_nside").get<int>();
    energyPointCount_ = grid.at("energy_point_count").get<int>();
    energyMinMeV_ = grid.at("energy_min_MeV").get<double>();
    energyMaxMeV_ = grid.at("energy_max_MeV").get<double>();
    particlesPerCell_ = grid.at("particles_per_cell").get<int>();

    const auto& trigger = json.at("trigger");
    frontChamberId_ = trigger.at("front_chamber_id").get<int>();
    rearChamberId_ = trigger.at("rear_chamber_id").get<int>();
    minimumLayerEnergyMeV_ =
        trigger.at("minimum_layer_energy_MeV").get<double>();

    const auto& output = json.at("output");
    sensitivityRootFile_ = resolvePath(
        absolutePath,
        output.at("sensitivity_root_file").get<std::string>()
    );
    sensitivityTreeName_ =
        output.at("sensitivity_tree_name").get<std::string>();
    eventsRootFile_ = resolvePath(
        absolutePath,
        output.at("events_root_file").get<std::string>()
    );
    eventsTreeName_ = output.at("events_tree_name").get<std::string>();

    if (mode_ != 0 && mode_ != 1)
    {
        throw std::runtime_error{"Simulation mode must be 0 or 1."};
    }

    if (randomSeed_ <= 0)
    {
        throw std::runtime_error{"random_seed must be positive."};
    }

    if (particleName_.empty())
    {
        throw std::runtime_error{"source.particle_name cannot be empty."};
    }

    requireFinitePositive(hemisphereRadiusMm_, "hemisphere_radius_mm");

    if (!std::isfinite(emissionConeHalfAngleDegree_) ||
        emissionConeHalfAngleDegree_ <= 0.0 ||
        emissionConeHalfAngleDegree_ > 90.0)
    {
        throw std::runtime_error{
            "emission_cone_half_angle_degree must be in (0, 90]."
        };
    }

    if (healpixNside_ <= 0 || (healpixNside_ & (healpixNside_ - 1)) != 0)
    {
        throw std::runtime_error{
            "healpix_nside must be a positive power of two."
        };
    }

    if (energyPointCount_ <= 0 || particlesPerCell_ <= 0)
    {
        throw std::runtime_error{
            "energy_point_count and particles_per_cell must be positive."
        };
    }

    requireFinitePositive(energyMinMeV_, "energy_min_MeV");
    requireFinitePositive(energyMaxMeV_, "energy_max_MeV");

    if (energyMaxMeV_ < energyMinMeV_)
    {
        throw std::runtime_error{
            "energy_max_MeV must not be smaller than energy_min_MeV."
        };
    }

    if (frontChamberId_ == rearChamberId_)
    {
        throw std::runtime_error{
            "front_chamber_id and rear_chamber_id must be different."
        };
    }

    if (!std::isfinite(minimumLayerEnergyMeV_) || minimumLayerEnergyMeV_ < 0.0)
    {
        throw std::runtime_error{
            "minimum_layer_energy_MeV must be finite and non-negative."
        };
    }

    if (sensitivityTreeName_.empty() || eventsTreeName_.empty())
    {
        throw std::runtime_error{"ROOT tree names cannot be empty."};
    }
}

int ConfigManager::mode() const { return mode_; }
std::int64_t ConfigManager::randomSeed() const { return randomSeed_; }
const std::string& ConfigManager::particleName() const { return particleName_; }
double ConfigManager::hemisphereRadiusMm() const { return hemisphereRadiusMm_; }
bool ConfigManager::frontHemisphereOnly() const { return frontHemisphereOnly_; }
double ConfigManager::emissionConeHalfAngleDegree() const
{
    return emissionConeHalfAngleDegree_;
}
int ConfigManager::healpixNside() const { return healpixNside_; }
int ConfigManager::energyPointCount() const { return energyPointCount_; }
double ConfigManager::energyMinMeV() const { return energyMinMeV_; }
double ConfigManager::energyMaxMeV() const { return energyMaxMeV_; }
int ConfigManager::particlesPerCell() const { return particlesPerCell_; }
int ConfigManager::frontChamberId() const { return frontChamberId_; }
int ConfigManager::rearChamberId() const { return rearChamberId_; }
double ConfigManager::minimumLayerEnergyMeV() const
{
    return minimumLayerEnergyMeV_;
}
const std::filesystem::path& ConfigManager::sensitivityRootFile() const
{
    return sensitivityRootFile_;
}
const std::string& ConfigManager::sensitivityTreeName() const
{
    return sensitivityTreeName_;
}
const std::filesystem::path& ConfigManager::eventsRootFile() const
{
    return eventsRootFile_;
}
const std::string& ConfigManager::eventsTreeName() const
{
    return eventsTreeName_;
}
