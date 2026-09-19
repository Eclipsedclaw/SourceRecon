#include "SimulationConfig.h"
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>

using nlohmann::json;

json readJson(const std::filesystem::path& path)
{
    std::ifstream input{path};
    if (!input)
    {
        throw std::runtime_error{"Cannot open JSON: " + path.string()};
    }
    return json::parse(input);
}

std::uint64_t positiveInteger(const json& value, const char* name)
{
    if ((!value.is_number_unsigned() && !value.is_number_integer()) ||
        (value.is_number_integer() && !value.is_number_unsigned() && value.get<std::int64_t>() <= 0))
    {
        throw std::runtime_error{std::string{name} + " must be a positive integer"};
    }
    const auto result = value.get<std::uint64_t>();
    if (result == 0)
    {
        throw std::runtime_error{std::string{name} + " must be positive"};
    }
    return result;
}

// json{另一个 json} 可能优先走 initializer_list，产生“只有一个元素的数组”。
// 这里明确调用复制构造函数，保持原来的 JSON 对象结构。
ConfigManager::ConfigManager(const json& document) : document_(document)
{
    particle_ = document_.at("source").at("particle_name").get<std::string>();
    material_ = document_.at("environment").at("world_material").get<std::string>();
    if (particle_ != "gamma")
    {
        throw std::runtime_error{"This efficiency experiment requires gamma"};
    }
    if (material_ != "G4_Galactic" && material_ != "G4_AIR")
    {
        throw std::runtime_error{"world_material must be G4_Galactic or G4_AIR"};
    }
    const auto n = positiveInteger(document_["grid"].at("healpix_nside"), "healpix_nside");
    const auto e = positiveInteger(document_["grid"].at("energy_point_count"), "energy_point_count");
    // Healpix_Base 使用 int 像素编号。限制 Nside，防止其内部 12*Nside*Nside 溢出。
    if (n > 8192 || (n & (n - 1)) != 0 || e > 1000000)
    {
        throw std::runtime_error{"Invalid HEALPix or energy grid size"};
    }
    for (double value : {hemisphereRadiusMm(), worldMarginMm(), energyMinMeV(), energyMaxMeV()})
    {
        if (!std::isfinite(value) || value <= 0)
        {
            throw std::runtime_error{"Lengths and energies must be finite and positive"};
        }
    }
    if (energyMaxMeV() < energyMinMeV() || ((e == 1) != (energyMinMeV() == energyMaxMeV())))
    {
        throw std::runtime_error{"One energy point requires min=max; multiple points require max>min"};
    }
    const double margin = emissionConeSafetyMarginDegree();
    const double threshold = minimumLayerEnergyMeV();
    if (!std::isfinite(margin) || margin < 0 || margin >= 45 || !std::isfinite(threshold) || threshold < 0 ||
        frontChamberId() != 0 || rearChamberId() != 1)
    {
        throw std::runtime_error{"Invalid cone margin or ch2/ch1 trigger configuration"};
    }
    (void)frontHemisphereOnly();
    const auto cells = fullCellCount() - firstActiveCell();
    if (particlesPerCell() > std::numeric_limits<std::uint64_t>::max() / cells)
    {
        throw std::runtime_error{"Total event count overflows uint64"};
    }
}

double ConfigManager::hemisphereRadiusMm() const
{
    return document_["source"]["hemisphere_radius_mm"].get<double>();
}
bool ConfigManager::frontHemisphereOnly() const
{
    return document_["source"].at("front_hemisphere_only").get<bool>();
}
double ConfigManager::emissionConeSafetyMarginDegree() const
{
    return document_["source"].at("emission_cone_safety_margin_degree").get<double>();
}
double ConfigManager::worldMarginMm() const
{
    return document_["environment"].at("world_margin_mm").get<double>();
}
int ConfigManager::healpixNside() const
{
    return document_["grid"].at("healpix_nside").get<int>();
}
int ConfigManager::energyPointCount() const
{
    return document_["grid"].at("energy_point_count").get<int>();
}
double ConfigManager::energyMinMeV() const
{
    return document_["grid"].at("energy_min_MeV").get<double>();
}
double ConfigManager::energyMaxMeV() const
{
    return document_["grid"].at("energy_max_MeV").get<double>();
}
std::uint64_t ConfigManager::particlesPerCell() const
{
    return positiveInteger(document_["grid"].at("particles_per_cell"), "particles_per_cell");
}
int ConfigManager::frontChamberId() const
{
    return document_["trigger"].at("front_chamber_id").get<int>();
}
int ConfigManager::rearChamberId() const
{
    return document_["trigger"].at("rear_chamber_id").get<int>();
}
double ConfigManager::minimumLayerEnergyMeV() const
{
    return document_["trigger"].at("minimum_layer_energy_MeV").get<double>();
}
std::uint64_t ConfigManager::directionCount() const
{
    const auto n = std::uint64_t(healpixNside());
    return 12 * n * n;
}
std::uint64_t ConfigManager::fullCellCount() const
{
    return directionCount() * std::uint64_t(energyPointCount());
}
std::uint64_t ConfigManager::firstActiveCell() const
{
    // RING 从 +Z 向 -Z 排序。z<=0 含赤道，方向数为 6*Nside²+2*Nside。
    const auto n = std::uint64_t(healpixNside());
    return frontHemisphereOnly() ? (6 * n * n - 2 * n) * std::uint64_t(energyPointCount()) : 0;
}
std::uint64_t ConfigManager::totalEvents() const
{
    return (fullCellCount() - firstActiveCell()) * particlesPerCell();
}
