#include "CalibrationConfig.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <functional>
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

CalibrationConfig::CalibrationConfig(const std::filesystem::path& path)
{
    const std::filesystem::path absolute =
        std::filesystem::absolute(path).lexically_normal();
    std::ifstream input{absolute};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open response-calibration configuration: " +
            absolute.string()
        };
    }

    nlohmann::json document;
    input >> document;
    const std::filesystem::path directory = absolute.parent_path();

    for (const auto& item : document.at("inputs"))
    {
        inputs_.push_back(CalibrationInput{
            resolve(directory, item.at("file").get<std::string>()),
            item.value("tree", "SelectedEvents"),
            item.value("level", "detector"),
            item.value("compton_model", "livermore")
        });
    }

    outputRootFile_ = resolve(
        directory,
        document.at("output_root_file").get<std::string>()
    );
    parameterTree_ = document.value(
        "output_parameter_tree",
        "ResponseParameters"
    );
    histogramName_ = document.value(
        "output_histogram_name",
        "EmpiricalDetectorArmPdf"
    );
    comparisonJson_ = resolve(
        directory,
        document.at("output_comparison_json").get<std::string>()
    );
    modelStatusJson_ = resolve(
        directory,
        document.at("output_model_status_json").get<std::string>()
    );
    figuresDirectory_ = resolve(
        directory,
        document.at("figures_directory").get<std::string>()
    );
    scatterAngleEdgesDegree_ =
        document.at("scatter_angle_edges_degree").get<std::vector<double>>();
    armBinCount_ = document.value("arm_bin_count", 400);
    armMinimumDegree_ = document.value("arm_min_degree", -25.0);
    armMaximumDegree_ = document.value("arm_max_degree", 25.0);
    minimumEventsPerBin_ = document.value(
        "minimum_events_per_bin",
        static_cast<std::size_t>(30)
    );
    minimumTestEventsPerBin_ = document.value(
        "minimum_test_events_per_bin",
        static_cast<std::size_t>(5)
    );
    testFraction_ = document.value("test_fraction", 0.2);

    if (inputs_.empty())
    {
        throw std::runtime_error{"At least one calibration input is required."};
    }

    for (const CalibrationInput& item : inputs_)
    {
        if (item.level != "truth" && item.level != "detector")
        {
            throw std::runtime_error{
                "Calibration input level must be truth or detector."
            };
        }

        if (item.comptonModel.empty())
        {
            throw std::runtime_error{"Calibration Compton model cannot be empty."};
        }
    }

    const std::string& commonLevel = inputs_.front().level;

    if (std::any_of(
            inputs_.begin(),
            inputs_.end(),
            [&commonLevel](const CalibrationInput& item)
            {
                return item.level != commonLevel;
            }
        ))
    {
        throw std::runtime_error{
            "Do not mix truth- and detector-level samples in one calibration."
        };
    }

    if (scatterAngleEdgesDegree_.size() < 2 ||
        !std::is_sorted(
            scatterAngleEdgesDegree_.begin(),
            scatterAngleEdgesDegree_.end()
        ) ||
        std::adjacent_find(
            scatterAngleEdgesDegree_.begin(),
            scatterAngleEdgesDegree_.end(),
            std::greater_equal<double>{}
        ) != scatterAngleEdgesDegree_.end())
    {
        throw std::runtime_error{
            "scatter_angle_edges_degree must be strictly increasing."
        };
    }

    if (armBinCount_ <= 0 || armMaximumDegree_ <= armMinimumDegree_ ||
        minimumEventsPerBin_ < 5 || minimumTestEventsPerBin_ < 1 ||
        testFraction_ <= 0.0 ||
        testFraction_ >= 0.5)
    {
        throw std::runtime_error{"Response-calibration binning is invalid."};
    }
}

const std::vector<CalibrationInput>& CalibrationConfig::inputs() const noexcept { return inputs_; }
const std::filesystem::path& CalibrationConfig::outputRootFile() const noexcept { return outputRootFile_; }
const std::string& CalibrationConfig::parameterTree() const noexcept { return parameterTree_; }
const std::string& CalibrationConfig::histogramName() const noexcept { return histogramName_; }
const std::filesystem::path& CalibrationConfig::comparisonJson() const noexcept { return comparisonJson_; }
const std::filesystem::path& CalibrationConfig::modelStatusJson() const noexcept { return modelStatusJson_; }
const std::filesystem::path& CalibrationConfig::figuresDirectory() const noexcept { return figuresDirectory_; }
const std::vector<double>& CalibrationConfig::scatterAngleEdgesDegree() const noexcept { return scatterAngleEdgesDegree_; }
int CalibrationConfig::armBinCount() const noexcept { return armBinCount_; }
double CalibrationConfig::armMinimumDegree() const noexcept { return armMinimumDegree_; }
double CalibrationConfig::armMaximumDegree() const noexcept { return armMaximumDegree_; }
std::size_t CalibrationConfig::minimumEventsPerBin() const noexcept { return minimumEventsPerBin_; }
std::size_t CalibrationConfig::minimumTestEventsPerBin() const noexcept { return minimumTestEventsPerBin_; }
double CalibrationConfig::testFraction() const noexcept { return testFraction_; }
