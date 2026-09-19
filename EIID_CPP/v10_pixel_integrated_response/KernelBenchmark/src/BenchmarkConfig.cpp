#include "BenchmarkConfig.h"

#include <nlohmann/json.hpp>

#include <fstream>
#include <stdexcept>
#include <utility>

namespace
{
std::filesystem::path resolve(
    const std::filesystem::path& directory,
    const std::string& configured
)
{
    const std::filesystem::path path{configured};
    return (path.is_absolute() ? path : directory / path).lexically_normal();
}
}

BenchmarkConfig::BenchmarkConfig(const std::filesystem::path& path)
{
    const std::filesystem::path absolute =
        std::filesystem::absolute(path).lexically_normal();
    std::ifstream input{absolute};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open kernel-benchmark configuration: " + absolute.string()
        };
    }

    nlohmann::json document;
    input >> document;
    const std::filesystem::path directory = absolute.parent_path();

    const std::filesystem::path statusPath = resolve(
        directory,
        document.at("model_status_json").get<std::string>()
    );
    std::ifstream statusInput{statusPath};

    if (!statusInput)
    {
        throw std::runtime_error{
            "Cannot open response-model status: " + statusPath.string()
        };
    }

    nlohmann::json statusDocument;
    statusInput >> statusDocument;

    for (const auto& item : document.at("inputs"))
    {
        const std::string label = item.at("label").get<std::string>();
        const std::string kernelType =
            item.at("kernel_type").get<std::string>();
        const auto& status = statusDocument.at("models").at(kernelType);

        if (status.at("usable").get<bool>())
        {
            BenchmarkInput benchmarkInput{
                label,
                kernelType,
                resolve(directory, item.at("file").get<std::string>()),
                item.value("tree", "EiidImage"),
                item.at("pixel_integration_strategy").get<std::string>(),
                item.at("reconstruction_nside").get<int>(),
                item.at("integration_nside").get<int>(),
                item.at("samples_per_pixel").get<std::size_t>(),
                item.at("iteration_count").get<int>()
            };

            if ((benchmarkInput.pixelIntegrationStrategy != "pixel_center" &&
                 benchmarkInput.pixelIntegrationStrategy != "healpix_subpixel") ||
                benchmarkInput.reconstructionNside <= 0 ||
                benchmarkInput.integrationNside <= 0 ||
                benchmarkInput.samplesPerPixel == 0 ||
                benchmarkInput.iterationCount <= 0)
            {
                throw std::runtime_error{
                    "Benchmark input has invalid V10 metadata expectations: " +
                    label
                };
            }

            inputs_.push_back(std::move(benchmarkInput));
        }
        else
        {
            skippedInputs_.push_back(SkippedBenchmarkInput{
                label,
                kernelType,
                std::to_string(
                    status.at("converged_bins").get<std::size_t>()
                ) + "/" + std::to_string(
                    status.at("total_bins").get<std::size_t>()
                ) + " calibration bins converged"
            });
        }
    }

    const std::filesystem::path truthPath = resolve(
        directory,
        document.at("truth_info_file").get<std::string>()
    );
    std::ifstream truthInput{truthPath};

    if (!truthInput)
    {
        throw std::runtime_error{"Cannot open truth information: " + truthPath.string()};
    }

    nlohmann::json truthDocument;
    truthInput >> truthDocument;
    truth_ = BenchmarkTruth{
        truthDocument.at("theta_degree").get<double>(),
        truthDocument.at("phi_degree").get<double>(),
        truthDocument.at("energy_MeV").get<double>()
    };
    calibrationComparisonJson_ = resolve(
        directory,
        document.at("calibration_comparison_json").get<std::string>()
    );
    outputJson_ = resolve(
        directory,
        document.at("output_json").get<std::string>()
    );
    figuresDirectory_ = resolve(
        directory,
        document.at("figures_directory").get<std::string>()
    );

    if (inputs_.empty())
    {
        throw std::runtime_error{
            "Kernel benchmark has no usable response-model results."
        };
    }
}

const std::vector<BenchmarkInput>& BenchmarkConfig::inputs() const noexcept { return inputs_; }
const std::vector<SkippedBenchmarkInput>& BenchmarkConfig::skippedInputs() const noexcept { return skippedInputs_; }
const BenchmarkTruth& BenchmarkConfig::truth() const noexcept { return truth_; }
const std::filesystem::path& BenchmarkConfig::calibrationComparisonJson() const noexcept { return calibrationComparisonJson_; }
const std::filesystem::path& BenchmarkConfig::outputJson() const noexcept { return outputJson_; }
const std::filesystem::path& BenchmarkConfig::figuresDirectory() const noexcept { return figuresDirectory_; }
