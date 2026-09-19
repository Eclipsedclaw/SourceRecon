#ifndef EIID_V7_CONFIG_MANAGER_HH
#define EIID_V7_CONFIG_MANAGER_HH

#include <cstdint>
#include <filesystem>
#include <string>

class ConfigManager
{
public:
    explicit ConfigManager(const std::filesystem::path& configPath);

    int mode() const;
    std::int64_t randomSeed() const;
    const std::string& particleName() const;
    double hemisphereRadiusMm() const;
    bool frontHemisphereOnly() const;
    double emissionConeSafetyMarginDegree() const;
    const std::string& worldMaterial() const;
    double worldMarginMm() const;
    int healpixNside() const;
    int energyPointCount() const;
    double energyMinMeV() const;
    double energyMaxMeV() const;
    int particlesPerCell() const;
    int frontChamberId() const;
    int rearChamberId() const;
    double minimumLayerEnergyMeV() const;
    const std::filesystem::path& efficiencyRootFile() const;
    const std::string& efficiencyTreeName() const;
    const std::filesystem::path& eventsRootFile() const;
    const std::string& eventsTreeName() const;

private:
    int mode_{};
    std::int64_t randomSeed_{};
    std::string particleName_;
    double hemisphereRadiusMm_{};
    bool frontHemisphereOnly_{};
    double coneSafetyMarginDegree_{};
    std::string worldMaterial_;
    double worldMarginMm_{};
    int healpixNside_{};
    int energyPointCount_{};
    double energyMinMeV_{};
    double energyMaxMeV_{};
    int particlesPerCell_{};
    int frontChamberId_{};
    int rearChamberId_{};
    double minimumLayerEnergyMeV_{};
    std::filesystem::path efficiencyRootFile_;
    std::string efficiencyTreeName_;
    std::filesystem::path eventsRootFile_;
    std::string eventsTreeName_;
};

#endif
