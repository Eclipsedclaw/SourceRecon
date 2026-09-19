#include "BenchmarkConfig.h"

#include <nlohmann/json.hpp>

#include <fstream>
#include <stdexcept>

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

    for (const auto& item : document.at("inputs"))
    {
        inputs_.push_back(BenchmarkInput{
            item.at("label").get<std::string>(),
            item.at("kernel_type").get<std::string>(),
            resolve(directory, item.at("file").get<std::string>()),
            item.value("tree", "EiidImage")
        });
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
    outputJson_ = resolve(
        directory,
        document.at("output_json").get<std::string>()
    );
    figuresDirectory_ = resolve(
        directory,
        document.at("figures_directory").get<std::string>()
    );

    if (inputs_.size() < 2)
    {
        throw std::runtime_error{"Kernel benchmark requires at least two results."};
    }
}

const std::vector<BenchmarkInput>& BenchmarkConfig::inputs() const noexcept { return inputs_; }
const BenchmarkTruth& BenchmarkConfig::truth() const noexcept { return truth_; }
const std::filesystem::path& BenchmarkConfig::outputJson() const noexcept { return outputJson_; }
const std::filesystem::path& BenchmarkConfig::figuresDirectory() const noexcept { return figuresDirectory_; }
