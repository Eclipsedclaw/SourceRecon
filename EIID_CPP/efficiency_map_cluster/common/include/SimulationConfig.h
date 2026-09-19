#pragma once

#include "json.hpp"
#include <cstdint>
#include <filesystem>
#include <string>

// 只读配置；沿用 ConfigManager 名称，使已验证的几何和源代码无需改物理逻辑。
class ConfigManager
{
  public:
    explicit ConfigManager(const nlohmann::json& document);
    const nlohmann::json& document() const
    {
        return document_;
    }
    const std::string& particleName() const
    {
        return particle_;
    }
    double hemisphereRadiusMm() const;
    bool frontHemisphereOnly() const;
    double emissionConeSafetyMarginDegree() const;
    const std::string& worldMaterial() const
    {
        return material_;
    }
    double worldMarginMm() const;
    int healpixNside() const;
    int energyPointCount() const;
    double energyMinMeV() const;
    double energyMaxMeV() const;
    std::uint64_t particlesPerCell() const;
    int frontChamberId() const;
    int rearChamberId() const;
    double minimumLayerEnergyMeV() const;
    std::uint64_t directionCount() const;
    std::uint64_t firstActiveCell() const;
    std::uint64_t fullCellCount() const;
    std::uint64_t totalEvents() const;

  private:
    nlohmann::json document_;
    std::string particle_;
    std::string material_;
};

nlohmann::json readJson(const std::filesystem::path& path);
// JSON 的 get<unsigned>() 会把负数转换为很大的正数，因此先检查符号与类型。
std::uint64_t positiveInteger(const nlohmann::json& value, const char* name);
