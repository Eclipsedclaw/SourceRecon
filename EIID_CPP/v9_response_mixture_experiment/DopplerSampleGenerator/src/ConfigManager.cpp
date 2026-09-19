#include "ConfigManager.hh"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>
#include <string>

namespace
{
std::filesystem::path resolvePath(
    const std::filesystem::path& configPath,
    const std::string& configuredPath
)
{
    const std::filesystem::path value{configuredPath};
    return (value.is_absolute() ? value : configPath.parent_path() / value)
        .lexically_normal();
}

void requireFinitePositive(double value, const char* name)
{
    if (!std::isfinite(value) || value <= 0.0)
    {
        throw std::runtime_error{std::string{name} + " must be finite and positive."};
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
        throw std::runtime_error{"Cannot open experiment config: " + absolutePath.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;

        experimentName_ = document.at("experiment_name").get<std::string>();
        randomSeed_ = document.at("random_seed").get<std::int64_t>();
        numberOfEvents_ = document.at("number_of_events").get<int>();

        const auto& physics = document.at("physics");
        comptonModel_ = physics.at("compton_model").get<std::string>();
        atomicRelaxation_ = physics.at("atomic_relaxation").get<bool>();

        const auto& source = document.at("source");
        particleName_ = source.at("particle_name").get<std::string>();
        sourceEnergyMeV_ = source.at("energy_MeV").get<double>();
        sourceThetaDegree_ = source.at("theta_degree").get<double>();
        sourcePhiDegree_ = source.at("phi_degree").get<double>();
        hemisphereRadiusMm_ = source.at("hemisphere_radius_mm").get<double>();
        coneSafetyMarginDegree_ =
            source.at("emission_cone_safety_margin_degree").get<double>();

        const auto& environment = document.at("environment");
        worldMaterial_ = environment.at("world_material").get<std::string>();
        worldMarginMm_ = environment.at("world_margin_mm").get<double>();

        const auto& selection = document.at("selection");
        frontChamberId_ = selection.at("front_chamber_id").get<int>();
        rearChamberId_ = selection.at("rear_chamber_id").get<int>();
        minimumLayerEnergyMeV_ =
            selection.at("minimum_layer_energy_MeV").get<double>();

        const auto& output = document.at("output");
        outputRootFile_ = resolvePath(
            absolutePath,
            output.at("root_file").get<std::string>()
        );
        outputTreeName_ = output.at("tree_name").get<std::string>();
        summaryJsonFile_ = resolvePath(
            absolutePath,
            output.at("summary_json").get<std::string>()
        );
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid experiment config: " + std::string{error.what()}};
    }

    if (experimentName_.empty() || randomSeed_ <= 0 || numberOfEvents_ <= 0)
    {
        throw std::runtime_error{"Experiment name, seed, or event count is invalid."};
    }

    if (comptonModel_ != "free" && comptonModel_ != "livermore" &&
        comptonModel_ != "lowep")
    {
        throw std::runtime_error{
            "physics.compton_model must be free, livermore, or lowep."
        };
    }

    if (particleName_ != "gamma")
    {
        throw std::runtime_error{"This experiment currently requires particle_name=gamma."};
    }

    requireFinitePositive(sourceEnergyMeV_, "source.energy_MeV");
    requireFinitePositive(hemisphereRadiusMm_, "source.hemisphere_radius_mm");
    requireFinitePositive(worldMarginMm_, "environment.world_margin_mm");
    if (!std::isfinite(sourceThetaDegree_) || sourceThetaDegree_ < 0.0 ||
        sourceThetaDegree_ > 180.0 || !std::isfinite(sourcePhiDegree_))
    {
        throw std::runtime_error{"Source theta/phi is invalid."};
    }

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

    if (frontChamberId_ != 0 || rearChamberId_ != 1)
    {
        throw std::runtime_error{"This detector geometry requires ch2=0 and ch1=1."};
    }

    if (!std::isfinite(minimumLayerEnergyMeV_) || minimumLayerEnergyMeV_ < 0.0 ||
        outputTreeName_.empty())
    {
        throw std::runtime_error{"Selection threshold or output tree name is invalid."};
    }
}

const std::string& ConfigManager::experimentName() const { return experimentName_; }
std::int64_t ConfigManager::randomSeed() const { return randomSeed_; }
int ConfigManager::numberOfEvents() const { return numberOfEvents_; }
const std::string& ConfigManager::comptonModel() const { return comptonModel_; }
bool ConfigManager::atomicRelaxation() const { return atomicRelaxation_; }
const std::string& ConfigManager::particleName() const { return particleName_; }
double ConfigManager::sourceEnergyMeV() const { return sourceEnergyMeV_; }
double ConfigManager::sourceThetaDegree() const { return sourceThetaDegree_; }
double ConfigManager::sourcePhiDegree() const { return sourcePhiDegree_; }
double ConfigManager::hemisphereRadiusMm() const { return hemisphereRadiusMm_; }
double ConfigManager::emissionConeSafetyMarginDegree() const
{
    return coneSafetyMarginDegree_;
}
const std::string& ConfigManager::worldMaterial() const { return worldMaterial_; }
double ConfigManager::worldMarginMm() const { return worldMarginMm_; }
int ConfigManager::frontChamberId() const { return frontChamberId_; }
int ConfigManager::rearChamberId() const { return rearChamberId_; }
double ConfigManager::minimumLayerEnergyMeV() const { return minimumLayerEnergyMeV_; }
const std::filesystem::path& ConfigManager::outputRootFile() const
{
    return outputRootFile_;
}
const std::string& ConfigManager::outputTreeName() const { return outputTreeName_; }
const std::filesystem::path& ConfigManager::summaryJsonFile() const
{
    return summaryJsonFile_;
}
