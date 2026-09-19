#ifndef EIID_V9_CALIBRATION_CONFIG_H
#define EIID_V9_CALIBRATION_CONFIG_H

#include <filesystem>
#include <string>
#include <vector>

struct CalibrationInput
{
    std::filesystem::path file;
    std::string tree;
    std::string level;
    std::string comptonModel;
};

class CalibrationConfig
{
public:
    explicit CalibrationConfig(const std::filesystem::path& path);

    const std::vector<CalibrationInput>& inputs() const noexcept;
    const std::filesystem::path& outputRootFile() const noexcept;
    const std::string& parameterTree() const noexcept;
    const std::string& histogramName() const noexcept;
    const std::filesystem::path& comparisonJson() const noexcept;
    const std::filesystem::path& modelStatusJson() const noexcept;
    const std::filesystem::path& figuresDirectory() const noexcept;
    const std::vector<double>& scatterAngleEdgesDegree() const noexcept;
    int armBinCount() const noexcept;
    double armMinimumDegree() const noexcept;
    double armMaximumDegree() const noexcept;
    std::size_t minimumEventsPerBin() const noexcept;
    std::size_t minimumTestEventsPerBin() const noexcept;
    double testFraction() const noexcept;

private:
    std::vector<CalibrationInput> inputs_;
    std::filesystem::path outputRootFile_;
    std::string parameterTree_;
    std::string histogramName_;
    std::filesystem::path comparisonJson_;
    std::filesystem::path modelStatusJson_;
    std::filesystem::path figuresDirectory_;
    std::vector<double> scatterAngleEdgesDegree_;
    int armBinCount_{};
    double armMinimumDegree_{};
    double armMaximumDegree_{};
    std::size_t minimumEventsPerBin_{};
    std::size_t minimumTestEventsPerBin_{};
    double testFraction_{};
};

#endif
