#ifndef DOPPLER_V7_EXPERIMENT_CONFIG_MANAGER_HH
#define DOPPLER_V7_EXPERIMENT_CONFIG_MANAGER_HH

#include <cstdint>
#include <filesystem>
#include <string>

// 这个类只负责把 JSON 变成经过检查的 C++ 参数。
// 物理过程、事件筛选和 ROOT 输出都不在这里实现。
class ConfigManager
{
public:
    explicit ConfigManager(const std::filesystem::path& configPath);

    const std::string& experimentName() const;
    std::int64_t randomSeed() const;
    int numberOfEvents() const;

    const std::string& comptonModel() const;
    bool atomicRelaxation() const;

    const std::string& particleName() const;
    double sourceEnergyMeV() const;
    double sourceThetaDegree() const;
    double sourcePhiDegree() const;
    double hemisphereRadiusMm() const;
    double emissionConeSafetyMarginDegree() const;

    const std::string& worldMaterial() const;
    double worldMarginMm() const;

    int frontChamberId() const;
    int rearChamberId() const;
    double minimumLayerEnergyMeV() const;

    const std::filesystem::path& outputRootFile() const;
    const std::string& outputTreeName() const;
    const std::filesystem::path& summaryJsonFile() const;

private:
    std::string experimentName_;
    std::int64_t randomSeed_{};
    int numberOfEvents_{};

    std::string comptonModel_;
    bool atomicRelaxation_{};

    std::string particleName_;
    double sourceEnergyMeV_{};
    double sourceThetaDegree_{};
    double sourcePhiDegree_{};
    double hemisphereRadiusMm_{};
    double coneSafetyMarginDegree_{};

    std::string worldMaterial_;
    double worldMarginMm_{};

    int frontChamberId_{};
    int rearChamberId_{};
    double minimumLayerEnergyMeV_{};

    std::filesystem::path outputRootFile_;
    std::string outputTreeName_;
    std::filesystem::path summaryJsonFile_;
};

#endif
