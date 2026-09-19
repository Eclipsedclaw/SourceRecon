#include "TaskSpec.h"
#include <algorithm>
#include <climits>
#include <iomanip>
#include <sstream>
#include <stdexcept>

Campaign::Campaign(const std::filesystem::path& path)
    : directory{std::filesystem::absolute(path).parent_path()}, manifest(readJson(path)),
      config{manifest.at("sim_config")}
{
    if (manifest.at("schema_version") != 1 || manifest.at("campaign_id").get<std::string>().empty())
    {
        throw std::runtime_error{"Invalid manifest identity"};
    }
    const auto& run = manifest.at("run_config");
    seed = positiveInteger(run.at("master_seed"), "master_seed");
    const auto t = positiveInteger(run.at("threads"), "threads");
    jobs = positiveInteger(run.at("jobs"), "jobs");
    if (t > 18 || jobs > 1000000)
    {
        throw std::runtime_error{"Invalid thread/job count"};
    }
    threads = static_cast<int>(t);
    std::uint64_t next = 0;
    for (const auto& row : manifest.at("chunks"))
    {
        TaskSpec task{row.at("id").get<std::uint64_t>(), row.at("first_event").get<std::uint64_t>(),
                      positiveInteger(row.at("event_count"), "event_count"), row.at("job_id").get<std::uint64_t>()};
        if (task.id != tasks.size() || task.firstEvent != next || task.eventCount > INT_MAX || task.jobId >= jobs ||
            next > config.totalEvents() || task.eventCount > config.totalEvents() - next)
        {
            throw std::runtime_error{"Manifest has overlapping, missing or invalid event ranges"};
        }
        next += task.eventCount;
        tasks.push_back(task);
    }
    if (next != config.totalEvents() || next != manifest.at("total_events").get<std::uint64_t>())
    {
        throw std::runtime_error{"Manifest does not cover the requested event count"};
    }
}

nlohmann::json Campaign::identity(const TaskSpec& task) const
{
    return {{"schema_version", 1},
            {"campaign_id", manifest.at("campaign_id")},
            {"sim_config", config.document()},
            {"master_seed", seed},
            {"chunk_id", task.id},
            {"first_event", task.firstEvent},
            {"event_count", task.eventCount}};
}

std::filesystem::path Campaign::chunkPath(const TaskSpec& task) const
{
    std::ostringstream name;
    name << "chunk_" << std::setw(8) << std::setfill('0') << task.id << ".root";
    return directory / "chunks" / name.str();
}

std::array<long, 3> eventSeeds(std::uint64_t masterSeed, std::uint64_t globalEvent)
{
    // 每个全局事例对应一对 Ranecu 种子，不依赖线程编号或作业执行顺序。
    // SplitMix64 只混合整数；不是用它代替 Geant4 的物理随机数引擎。
    auto mix = [](std::uint64_t value)
    {
        value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
        return value ^ (value >> 31);
    };
    const auto state = mix(globalEvent + UINT64_C(0x9e3779b97f4a7c15)) ^ mix(masterSeed);
    return {static_cast<long>(mix(state) % 2147483562ULL + 1),
            static_cast<long>(mix(state + UINT64_C(0x9e3779b97f4a7c15)) % 2147483398ULL + 1), 0};
}
