#pragma once
#include "SimulationConfig.h"
#include <array>
#include <vector>

struct TaskSpec
{
    std::uint64_t id{};
    std::uint64_t firstEvent{};
    std::uint64_t eventCount{};
    std::uint64_t jobId{};
};

// 在两次 BeamOn 之间由主线程修改；BeamOn 期间所有工作线程只读。
struct RunContext
{
    TaskSpec task;
    std::uint64_t masterSeed{};
};

struct Campaign
{
    explicit Campaign(const std::filesystem::path& path);
    std::filesystem::path directory;
    nlohmann::json manifest;
    ConfigManager config;
    std::vector<TaskSpec> tasks;
    std::uint64_t seed{};
    int threads{};
    std::uint64_t jobs{};
    nlohmann::json identity(const TaskSpec& task) const;
    std::filesystem::path chunkPath(const TaskSpec& task) const;
};

std::array<long, 3> eventSeeds(std::uint64_t masterSeed, std::uint64_t globalEvent);
