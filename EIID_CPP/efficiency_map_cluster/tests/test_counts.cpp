#include "CellCounts.h"
#include <functional>
#include <iostream>
#include <set>
#include <stdexcept>

namespace
{
    void require(bool condition, const char* message)
    {
        if (!condition)
        {
            throw std::runtime_error{message};
        }
    }
    void mustReject(const std::function<void()>& operation)
    {
        try
        {
            operation();
        }
        catch (const std::exception&)
        {
            return;
        }
        throw std::runtime_error{"Invalid input was accepted"};
    }
} // namespace

int main(int argc, char** argv)
{
    try
    {
        require(argc == 2, "Provide sim_config.json");
        auto doc = readJson(argv[1]);
        ConfigManager config{doc};
        const Campaign campaign{std::filesystem::path{argv[1]}.parent_path() / "manifest.json"};
        require(campaign.manifest.is_object() && campaign.tasks.size() == 2, "Manifest parsing failed");
        require(campaign.identity(campaign.tasks.front()).at("sim_config") == doc,
                "Frozen configuration changed shape");
        require(config.directionCount() == 48, "Nside2 must have 48 pixels");
        require(config.firstActiveCell() == 20, "RING front hemisphere mapping wrong");
        require(config.totalEvents() == 280000, "Smoke total must be 280000");
        // 故意把块切在 cell 中间，防止“整 cell 分块”测试漏掉边界 bug。
        TaskSpec task{0, 9990, 30, 0};
        Counts c{{20, CellCounts{10, 0, 0, 0, 0, 0.0002}}, {21, CellCounts{20, 2, 4, 3, 2, 0.0002}}};
        validateCounts(c, task, config);
        auto missing = c;
        missing.erase(20);
        mustReject(
            [&]
            {
                validateCounts(missing, task, config);
            });
        auto wrong = c;
        ++wrong[21].emitted;
        mustReject(
            [&]
            {
                validateCounts(wrong, task, config);
            });
        wrong = c;
        wrong[21].valid = 5;
        mustReject(
            [&]
            {
                validateCounts(wrong, task, config);
            });
        CellCounts sum;
        addCounts(sum, c.at(20));
        addCounts(sum, c.at(21));
        require(sum.emitted == 30 && sum.valid == 2, "Integer count merge failed");
        auto differentCone = c.at(20);
        differentCone.coneFraction *= 2;
        mustReject(
            [&]
            {
                addCounts(sum, differentCone);
            });
        doc["grid"]["particles_per_cell"] = UINT64_C(10000000000);
        ConfigManager large{doc};
        require(large.totalEvents() == UINT64_C(280000000000), "64-bit event count lost");
        doc["grid"]["particles_per_cell"] = -1;
        mustReject(
            [&]
            {
                ConfigManager bad{doc};
            });
        doc["grid"]["particles_per_cell"] = UINT64_MAX;
        mustReject(
            [&]
            {
                ConfigManager bad{doc};
            });
        std::set<std::array<long, 3>> streams;
        for (std::uint64_t i = 0; i < 10000; ++i)
        {
            const auto seeds = eventSeeds(20260913, i);
            require(seeds == eventSeeds(20260913, i), "Seed reproducibility failed");
            require(seeds[0] > 0 && seeds[0] < 2147483563L && seeds[1] > 0 && seeds[1] < 2147483399L,
                    "Ranecu seed range");
            require(streams.insert(seeds).second, "Repeated seed pair in test sample");
        }
        std::cout << "PASS: boundary counts, raw zeros, merge, uint64, invalid configs, deterministic event seeds\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
