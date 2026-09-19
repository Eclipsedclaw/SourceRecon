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
        showTruthMarkers_ = plotConfig.at("show_truth_markers").get<bool>();

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

bool VisConfig::showTruthMarkers() const
{
    return showTruthMarkers_;
}
