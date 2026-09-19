#ifndef EIID_V3_CONFIG_MANAGER_HH
#define EIID_V3_CONFIG_MANAGER_HH

#include <cstdint>
#include <filesystem>
#include <string>

// mode = 0：逐个网格 cell 统计发射数和有效触发数，生成敏感度表。
// mode = 1：按相同的源分布模拟，并把通过触发的事件直接写成精简 ROOT 文件。
class ConfigManager
{
public:
    explicit ConfigManager(const std::filesystem::path& configPath);

    int mode() const;
    std::int64_t randomSeed() const;

    const std::string& particleName() const;
    double hemisphereRadiusMm() const;
    bool frontHemisphereOnly() const;
    double emissionConeHalfAngleDegree() const;

    int healpixNside() const;
    int energyPointCount() const;
    double energyMinMeV() const;
    double energyMaxMeV() const;
    int particlesPerCell() const;

    int frontChamberId() const;
    int rearChamberId() const;
    double minimumLayerEnergyMeV() const;

    const std::filesystem::path& sensitivityRootFile() const;
    const std::string& sensitivityTreeName() const;
    const std::filesystem::path& eventsRootFile() const;
    const std::string& eventsTreeName() const;

private:
    int mode_{};
    std::int64_t randomSeed_{};

    std::string particleName_;
    double hemisphereRadiusMm_{};
    bool frontHemisphereOnly_{};
    double emissionConeHalfAngleDegree_{};

    int healpixNside_{};
    int energyPointCount_{};
    double energyMinMeV_{};
    double energyMaxMeV_{};
    int particlesPerCell_{};

    int frontChamberId_{};
    int rearChamberId_{};
    double minimumLayerEnergyMeV_{};

    std::filesystem::path sensitivityRootFile_;
    std::string sensitivityTreeName_;
    std::filesystem::path eventsRootFile_;
    std::string eventsTreeName_;
};

#endif
