#ifndef EIID_V10_BENCHMARK_CONFIG_H
#define EIID_V10_BENCHMARK_CONFIG_H

#include <filesystem>
#include <cstddef>
#include <string>
#include <vector>

struct BenchmarkInput
{
    std::string label;
    std::string kernelType;
    std::filesystem::path file;
    std::string tree;
    std::string pixelIntegrationStrategy;
    int reconstructionNside{};
    int integrationNside{};
    std::size_t samplesPerPixel{};
    int iterationCount{};
};

struct BenchmarkTruth
{
    double thetaDegree{};
    double phiDegree{};
    double energyMeV{};
};

struct SkippedBenchmarkInput
{
    std::string label;
    std::string kernelType;
    std::string reason;
};

class BenchmarkConfig
{
public:
    explicit BenchmarkConfig(const std::filesystem::path& path);

    const std::vector<BenchmarkInput>& inputs() const noexcept;
    const std::vector<SkippedBenchmarkInput>& skippedInputs() const noexcept;
    const BenchmarkTruth& truth() const noexcept;
    const std::filesystem::path& calibrationComparisonJson() const noexcept;
    const std::filesystem::path& outputJson() const noexcept;
    const std::filesystem::path& figuresDirectory() const noexcept;

private:
    std::vector<BenchmarkInput> inputs_;
    std::vector<SkippedBenchmarkInput> skippedInputs_;
    BenchmarkTruth truth_;
    std::filesystem::path calibrationComparisonJson_;
    std::filesystem::path outputJson_;
    std::filesystem::path figuresDirectory_;
};

#endif
