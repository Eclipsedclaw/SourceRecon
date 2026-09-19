#include "vis_config.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
nlohmann::json readJsonFile(const std::filesystem::path& path)
{
    std::ifstream input{path};

    if (!input)
    {
        throw std::runtime_error{"Cannot open JSON configuration file: " + path.string()};
    }

    try
    {
        nlohmann::json document;
        input >> document;
        return document;
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Invalid JSON in " + path.string() + ": " + error.what()};
    }
}

std::filesystem::path resolvePath(
    const std::filesystem::path& baseDirectory,
    const std::string& configuredPath
)
{
    const std::filesystem::path path{configuredPath};

    if (path.is_absolute())
    {
        return path.lexically_normal();
    }

    return (baseDirectory / path).lexically_normal();
}
}

VisConfig::VisConfig(const std::filesystem::path& plotConfigPath)
{
    const std::filesystem::path absoluteConfigPath =
        std::filesystem::absolute(plotConfigPath).lexically_normal();

    const std::filesystem::path configDirectory = absoluteConfigPath.parent_path();
    const nlohmann::json plotConfig = readJsonFile(absoluteConfigPath);

    try
    {
        inputRootFilePath_ = resolvePath(
            configDirectory,
            plotConfig.at("input_root_file").get<std::string>()
        );

        outputDirectory_ = resolvePath(
            configDirectory,
            plotConfig.at("output_directory").get<std::string>()
        );

        inputTreeName_ = plotConfig.at("input_tree_name").get<std::string>();
        drawSkymap_ = plotConfig.at("draw_skymap").get<bool>();
        drawSpectrum_ = plotConfig.at("draw_spectrum").get<bool>();
        drawContainment_ = plotConfig.at("draw_containment").get<bool>();
        // 新增开关使用 value() 读取，使 V5 的旧绘图配置仍可直接使用。
        // 缺失时只是不生成 V6 新图，不影响原来的三张图。
        drawEnergyFit_ = plotConfig.value("draw_energy_fit", false);
        drawDirectionFit_ = plotConfig.value("draw_direction_fit", false);
        drawEnergyAngleMap_ =
            plotConfig.value("draw_energy_angle_map", false);
        writeFitSummary_ = plotConfig.value("write_fit_summary", false);
        showTruthMarkers_ = plotConfig.at("show_truth_markers").get<bool>();

        if (plotConfig.contains("fit"))
        {
            const nlohmann::json& fitConfig = plotConfig.at("fit");
            fit_.energyFitHalfWidthMeV = fitConfig.value(
                "energy_fit_half_width_MeV",
                fit_.energyFitHalfWidthMeV
            );
            fit_.directionEnergyGateSigma = fitConfig.value(
                "direction_energy_gate_sigma",
                fit_.directionEnergyGateSigma
            );
            fit_.directionFitRadiusDegree = fitConfig.value(
                "direction_fit_radius_degree",
                fit_.directionFitRadiusDegree
            );
            fit_.directionSpectrumRadiusDegree = fitConfig.value(
                "direction_spectrum_radius_degree",
                fit_.directionSpectrumRadiusDegree
            );
        }

        const std::filesystem::path truthInfoPath = resolvePath(
            configDirectory,
            plotConfig.at("truth_info_file").get<std::string>()
        );

        const nlohmann::json truthConfig = readJsonFile(truthInfoPath);
        truth_.thetaDegree = truthConfig.at("theta_degree").get<double>();
        truth_.phiDegree = truthConfig.at("phi_degree").get<double>();
        truth_.energyMeV = truthConfig.at("energy_MeV").get<double>();
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{"Missing or invalid visualization configuration value: " + std::string{error.what()}};
    }

    if (inputTreeName_.empty())
    {
        throw std::runtime_error{"input_tree_name must not be empty."};
    }

    if (!std::isfinite(truth_.thetaDegree) || truth_.thetaDegree < 0.0 || truth_.thetaDegree > 180.0)
    {
        throw std::runtime_error{"Truth theta_degree must be between 0 and 180 degrees."};
    }

    if (!std::isfinite(truth_.phiDegree))
    {
        throw std::runtime_error{"Truth phi_degree must be finite."};
    }

    if (!std::isfinite(truth_.energyMeV) || truth_.energyMeV <= 0.0)
    {
        throw std::runtime_error{"Truth energy_MeV must be positive and finite."};
    }

    if (!std::isfinite(fit_.energyFitHalfWidthMeV) ||
        fit_.energyFitHalfWidthMeV <= 0.0 ||
        !std::isfinite(fit_.directionEnergyGateSigma) ||
        fit_.directionEnergyGateSigma <= 0.0 ||
        !std::isfinite(fit_.directionFitRadiusDegree) ||
        fit_.directionFitRadiusDegree <= 0.0 ||
        fit_.directionFitRadiusDegree >= 90.0 ||
        !std::isfinite(fit_.directionSpectrumRadiusDegree) ||
        fit_.directionSpectrumRadiusDegree <= 0.0 ||
        fit_.directionSpectrumRadiusDegree > fit_.directionFitRadiusDegree)
    {
        throw std::runtime_error{
            "Visualization fit windows are invalid."
        };
    }
}

const std::filesystem::path& VisConfig::inputRootFilePath() const
{
    return inputRootFilePath_;
}

const std::filesystem::path& VisConfig::outputDirectory() const
{
    return outputDirectory_;
}

const std::string& VisConfig::inputTreeName() const
{
    return inputTreeName_;
}

const TruthInfo& VisConfig::truth() const
{
    return truth_;
}

const FitConfig& VisConfig::fit() const
{
    return fit_;
}

bool VisConfig::drawSkymap() const
{
    return drawSkymap_;
}

bool VisConfig::drawSpectrum() const
{
    return drawSpectrum_;
}

bool VisConfig::drawContainment() const
{
    return drawContainment_;
}

bool VisConfig::drawEnergyFit() const
{
    return drawEnergyFit_;
}

bool VisConfig::drawDirectionFit() const
{
    return drawDirectionFit_;
}

bool VisConfig::drawEnergyAngleMap() const
{
    return drawEnergyAngleMap_;
}

bool VisConfig::writeFitSummary() const
{
    return writeFitSummary_;
}

bool VisConfig::showTruthMarkers() const
{
    return showTruthMarkers_;
}
