#include "ReconConfig.h"

#include <nlohmann/json.hpp>

#include <cmath>
#include <fstream>
#include <stdexcept>

namespace
{
std::filesystem::path resolvePath(
    const std::filesystem::path& directory,
    const std::string& configured
)
{
    const std::filesystem::path path{configured};
    return (path.is_absolute() ? path : directory / path).lexically_normal();
}

void requireNonEmpty(const std::string& value, const char* name)
{
    if (value.empty())
    {
        throw std::runtime_error{std::string{name} + " cannot be empty."};
    }
}

bool isPowerOfTwo(int value)
{
    return value > 0 && (value & (value - 1)) == 0;
}
}

ReconConfig::ReconConfig(const std::filesystem::path& configPath)
{
    const std::filesystem::path absolutePath =
        std::filesystem::absolute(configPath).lexically_normal();
    std::ifstream input{absolutePath};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open reconstruction configuration: " +
            absolutePath.string()
        };
    }

    try
    {
        nlohmann::json document;
        input >> document;
        const std::filesystem::path directory = absolutePath.parent_path();

        inputEventsFile_ = resolvePath(
            directory,
            document.at("input_events_file").get<std::string>()
        );
        inputEventsTree_ = document.at("input_events_tree").get<std::string>();
        outputResultFile_ = resolvePath(
            directory,
            document.at("output_result_file").get<std::string>()
        );
        outputResultTree_ = document.at("output_result_tree").get<std::string>();
        efficiencyFile_ = resolvePath(
            directory,
            document.at("absolute_efficiency_file").get<std::string>()
        );
        efficiencyTree_ =
            document.at("absolute_efficiency_tree").get<std::string>();

        healpixNside_ = document.at("healpix_nside").get<int>();
        healpixOrdering_ = document.at("healpix_ordering").get<std::string>();
        energyMinMeV_ = static_cast<Decimal>(
            document.at("energy_min_MeV").get<double>()
        );
        energyMaxMeV_ = static_cast<Decimal>(
            document.at("energy_max_MeV").get<double>()
        );
        energyPointCount_ = document.at("energy_point_count").get<int>();
        iterationCount_ = document.at("iteration_count").get<int>();
        responseSigmaDegree_ = static_cast<Decimal>(
            document.value("response_sigma_degree", 6.0)
        );
        denominatorFloor_ = static_cast<Decimal>(
            document.at("denominator_floor").get<double>()
        );

        // V10 accepts a pluggable response model.  When this object is absent,
        // the old fixed Gaussian remains the default, so a V7 configuration
        // continues to run without modification.
        responseKernel_.type = "fixed_gaussian";
        responseKernel_.fixedSigmaDegree = responseSigmaDegree_;

        if (document.contains("response_kernel"))
        {
            const auto& kernel = document.at("response_kernel");
            responseKernel_.type = kernel.value("type", "fixed_gaussian");
            responseKernel_.parameterTree =
                kernel.value("parameter_tree", "ResponseParameters");
            responseKernel_.histogramName =
                kernel.value("histogram_name", "EmpiricalDetectorArmPdf");
            responseKernel_.fixedSigmaDegree = static_cast<Decimal>(
                kernel.value(
                    "fixed_sigma_degree",
                    static_cast<double>(responseSigmaDegree_)
                )
            );

            const std::string calibrationFile =
                kernel.value("calibration_file", "");

            if (!calibrationFile.empty())
            {
                responseKernel_.calibrationFile =
                    resolvePath(directory, calibrationFile);
            }
        }

        // A missing block intentionally means the old one-point evaluation.
        // This keeps historical configuration files readable by V10.
        pixelIntegration_.strategy = "pixel_center";
        pixelIntegration_.integrationNside = healpixNside_;

        if (document.contains("pixel_integration"))
        {
            const auto& integration = document.at("pixel_integration");
            pixelIntegration_.strategy =
                integration.value("strategy", "pixel_center");
            pixelIntegration_.integrationNside =
                integration.value("integration_nside", healpixNside_);
        }

        const auto& event = document.at("event_branches");
        eventBranches_ = EventBranchNames{
            event.at("r1_x").get<std::string>(),
            event.at("r1_y").get<std::string>(),
            event.at("r1_z").get<std::string>(),
            event.at("r2_x").get<std::string>(),
            event.at("r2_y").get<std::string>(),
            event.at("r2_z").get<std::string>(),
            event.at("e1_MeV").get<std::string>()
        };

        const auto& result = document.at("result_branches");
        resultBranches_ = ResultBranchNames{
            result.at("cell_index").get<std::string>(),
            result.at("weight").get<std::string>(),
            result.at("healpix_pixel_id").get<std::string>(),
            result.at("theta_degree").get<std::string>(),
            result.at("phi_degree").get<std::string>(),
            result.at("direction_x").get<std::string>(),
            result.at("direction_y").get<std::string>(),
            result.at("direction_z").get<std::string>(),
            result.at("energy_MeV").get<std::string>()
        };

        const auto& efficiency = document.at("absolute_efficiency_branches");
        efficiencyBranches_ = EfficiencyBranchNames{
            efficiency.at("cell_index").get<std::string>(),
            efficiency.at("efficiency").get<std::string>()
        };
    }
    catch (const nlohmann::json::exception& error)
    {
        throw std::runtime_error{
            "Missing or invalid reconstruction setting: " +
            std::string{error.what()}
        };
    }

    requireNonEmpty(inputEventsTree_, "input_events_tree");
    requireNonEmpty(outputResultTree_, "output_result_tree");
    requireNonEmpty(efficiencyTree_, "absolute_efficiency_tree");
    requireNonEmpty(efficiencyBranches_.cellIndex,
                    "absolute_efficiency_branches.cell_index");
    requireNonEmpty(efficiencyBranches_.efficiency,
                    "absolute_efficiency_branches.efficiency");

    if (!isPowerOfTwo(healpixNside_) || healpixOrdering_ != "RING")
    {
        throw std::runtime_error{
            "V10 requires power-of-two, RING-order HEALPix Nside."
        };
    }

    if (pixelIntegration_.strategy != "pixel_center" &&
        pixelIntegration_.strategy != "healpix_subpixel")
    {
        throw std::runtime_error{
            "pixel_integration.strategy must be pixel_center or healpix_subpixel."
        };
    }

    if (pixelIntegration_.strategy == "pixel_center")
    {
        if (pixelIntegration_.integrationNside != healpixNside_)
        {
            throw std::runtime_error{
                "pixel_center requires integration_nside equal to healpix_nside."
            };
        }
    }
    else
    {
        const int refinement =
            pixelIntegration_.integrationNside / healpixNside_;

        if (!isPowerOfTwo(pixelIntegration_.integrationNside) ||
            pixelIntegration_.integrationNside < healpixNside_ ||
            pixelIntegration_.integrationNside % healpixNside_ != 0 ||
            !isPowerOfTwo(refinement))
        {
            throw std::runtime_error{
                "healpix_subpixel requires a power-of-two integration Nside "
                "that is a HEALPix refinement of healpix_nside."
            };
        }
    }

    if (energyPointCount_ <= 0 || !std::isfinite(energyMinMeV_) ||
        !std::isfinite(energyMaxMeV_) || energyMaxMeV_ < energyMinMeV_ ||
        energyMinMeV_ <= static_cast<Decimal>(0.0) ||
        (energyPointCount_ == 1 && energyMinMeV_ != energyMaxMeV_))
    {
        throw std::runtime_error{"The reconstruction energy grid is invalid."};
    }

    if (iterationCount_ <= 0 || responseSigmaDegree_ <= 0.0 ||
        responseKernel_.fixedSigmaDegree <= 0.0 ||
        denominatorFloor_ <= 0.0)
    {
        throw std::runtime_error{"Iteration and numerical parameters must be positive."};
    }
}

const std::filesystem::path& ReconConfig::inputEventsFile() const { return inputEventsFile_; }
const std::string& ReconConfig::inputEventsTree() const { return inputEventsTree_; }
const std::filesystem::path& ReconConfig::outputResultFile() const { return outputResultFile_; }
const std::string& ReconConfig::outputResultTree() const { return outputResultTree_; }
const std::filesystem::path& ReconConfig::efficiencyFile() const { return efficiencyFile_; }
const std::string& ReconConfig::efficiencyTree() const { return efficiencyTree_; }
int ReconConfig::healpixNside() const { return healpixNside_; }
const std::string& ReconConfig::healpixOrdering() const { return healpixOrdering_; }
int ReconConfig::energyPointCount() const { return energyPointCount_; }
Decimal ReconConfig::energyMinMeV() const { return energyMinMeV_; }
Decimal ReconConfig::energyMaxMeV() const { return energyMaxMeV_; }
int ReconConfig::iterationCount() const { return iterationCount_; }
Decimal ReconConfig::responseSigmaDegree() const { return responseSigmaDegree_; }
const ResponseKernelConfig& ReconConfig::responseKernel() const { return responseKernel_; }
const PixelIntegrationConfig& ReconConfig::pixelIntegration() const { return pixelIntegration_; }
Decimal ReconConfig::denominatorFloor() const { return denominatorFloor_; }
const EventBranchNames& ReconConfig::eventBranches() const { return eventBranches_; }
const ResultBranchNames& ReconConfig::resultBranches() const { return resultBranches_; }
const EfficiencyBranchNames& ReconConfig::efficiencyBranches() const { return efficiencyBranches_; }
