#ifndef EIID_V8_BENCHMARK_CONFIG_H
#define EIID_V8_BENCHMARK_CONFIG_H

#include <filesystem>
#include <string>
#include <vector>

struct BenchmarkInput
{
    std::string label;
    std::string kernelType;
    std::filesystem::path file;
    std::string tree;
};

struct BenchmarkTruth
{
    double thetaDegree{};
    double phiDegree{};
    double energyMeV{};
};

class BenchmarkConfig
{
public:
    explicit BenchmarkConfig(const std::filesystem::path& path);

    const std::vector<BenchmarkInput>& inputs() const noexcept;
    const BenchmarkTruth& truth() const noexcept;
    const std::filesystem::path& outputJson() const noexcept;
    const std::filesystem::path& figuresDirectory() const noexcept;

private:
    std::vector<BenchmarkInput> inputs_;
    BenchmarkTruth truth_;
    std::filesystem::path outputJson_;
    std::filesystem::path figuresDirectory_;
};

#endif
