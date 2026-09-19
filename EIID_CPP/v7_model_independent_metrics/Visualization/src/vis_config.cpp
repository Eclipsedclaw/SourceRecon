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
        // V7 使用 metrics 命名；第二个 value() 让 V7 配置仍可直接使用。
        drawEnergyMetrics_ = plotConfig.value(
            "draw_energy_metrics",
            plotConfig.value("draw_energy_fit", false)
        );
        drawDirectionMetrics_ = plotConfig.value(
            "draw_direction_metrics",
            plotConfig.value("draw_direction_fit", false)
        );
        drawEnergyAngleMap_ =
            plotConfig.value("draw_energy_angle_map", false);
        writeQualitySummary_ = plotConfig.value(
            "write_quality_summary",
            plotConfig.value("write_fit_summary", false)
        );
        showTruthMarkers_ = plotConfig.at("show_truth_markers").get<bool>();

        if (plotConfig.contains("analysis"))
        {
            const nlohmann::json& analysisConfig =
                plotConfig.at("analysis");
            analysis_.energyIntervalFraction = analysisConfig.value(
                "energy_interval_fraction",
                analysis_.energyIntervalFraction
            );
            analysis_.gaussianFitEnabled = analysisConfig.value(
                "gaussian_fit_enabled",
                analysis_.gaussianFitEnabled
            );
            analysis_.gaussianFitHalfWidthMeV = analysisConfig.value(
                "gaussian_fit_half_width_MeV",
                analysis_.gaussianFitHalfWidthMeV
            );
            analysis_.directionLocalRadiusDegree = analysisConfig.value(
                "direction_local_radius_degree",
                analysis_.directionLocalRadiusDegree
            );
            analysis_.directionSpectrumRadiusDegree = analysisConfig.value(
                "direction_spectrum_radius_degree",
                analysis_.directionSpectrumRadiusDegree
            );
        }
        else if (plotConfig.contains("fit"))
        {
            // 兼容 V7：保留其 Gaussian 窗口和两个方向半径。
            const nlohmann::json& oldFitConfig = plotConfig.at("fit");
            analysis_.gaussianFitHalfWidthMeV = oldFitConfig.value(
                "energy_fit_half_width_MeV",
                analysis_.gaussianFitHalfWidthMeV
            );
            analysis_.directionLocalRadiusDegree = oldFitConfig.value(
                "direction_fit_radius_degree",
                analysis_.directionLocalRadiusDegree
            );
            analysis_.directionSpectrumRadiusDegree = oldFitConfig.value(
                "direction_spectrum_radius_degree",
                analysis_.directionSpectrumRadiusDegree
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

    if (!std::isfinite(analysis_.energyIntervalFraction) ||
        analysis_.energyIntervalFraction <= 0.0 ||
        analysis_.energyIntervalFraction >= 1.0 ||
        !std::isfinite(analysis_.gaussianFitHalfWidthMeV) ||
        analysis_.gaussianFitHalfWidthMeV <= 0.0 ||
        !std::isfinite(analysis_.directionLocalRadiusDegree) ||
        analysis_.directionLocalRadiusDegree <= 0.0 ||
        analysis_.directionLocalRadiusDegree >= 90.0 ||
        !std::isfinite(analysis_.directionSpectrumRadiusDegree) ||
        analysis_.directionSpectrumRadiusDegree <= 0.0 ||
        analysis_.directionSpectrumRadiusDegree >
            analysis_.directionLocalRadiusDegree)
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

const AnalysisConfig& VisConfig::analysis() const
{
    return analysis_;
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

bool VisConfig::drawEnergyMetrics() const
{
    return drawEnergyMetrics_;
}

bool VisConfig::drawDirectionMetrics() const
{
    return drawDirectionMetrics_;
}

bool VisConfig::drawEnergyAngleMap() const
{
    return drawEnergyAngleMap_;
}

bool VisConfig::writeQualitySummary() const
{
    return writeQualitySummary_;
}

bool VisConfig::showTruthMarkers() const
{
    return showTruthMarkers_;
}
