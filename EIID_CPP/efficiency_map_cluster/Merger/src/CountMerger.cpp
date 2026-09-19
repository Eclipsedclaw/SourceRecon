#include "CountMerger.h"
#include <iostream>
#include <set>
#include <stdexcept>

void CountMerger::run(const Campaign& campaign, bool checkOnly) const
{
    Counts merged;
    nlohmann::json software;
    std::set<std::filesystem::path> expected;
    for (const auto& task : campaign.tasks)
    {
        expected.insert(campaign.chunkPath(task).lexically_normal());
    }
    // 读取清单而不是 glob 后盲目相加；意外多出的 .root 也应明确报错。
    for (const auto& entry : std::filesystem::directory_iterator(campaign.directory / "chunks"))
    {
        if (entry.path().extension() == ".root" && expected.count(entry.path().lexically_normal()) == 0)
        {
            throw std::runtime_error{"Unexpected ROOT chunk: " + entry.path().string()};
        }
    }
    for (const auto& task : campaign.tasks)
    {
        const auto data = readChunk(campaign.chunkPath(task));
        if (data.metadata.at("identity") != campaign.identity(task))
        {
            throw std::runtime_error{"Chunk identity/config mismatch"};
        }
        if (software.is_null())
        {
            software = data.metadata.at("software");
        }
        if (software != data.metadata.at("software"))
        {
            throw std::runtime_error{"Mixed simulation builds or physics datasets"};
        }
        validateCounts(data.counts, task, campaign.config);
        for (const auto& [index, c] : data.counts)
        {
            addCounts(merged[index], c);
        }
    }
    validateCounts(merged, TaskSpec{0, 0, campaign.config.totalEvents(), 0}, campaign.config);
    std::uint64_t valid = 0;
    std::size_t positive = 0;
    for (const auto& [index, c] : merged)
    {
        (void)index;
        valid += c.valid;
        positive += c.valid > 0 ? 1 : 0;
    }
    std::cout << "Checked chunks: " << campaign.tasks.size() << "\nCompleted events: " << campaign.config.totalEvents()
              << "\nValid two-layer triggers: " << valid << "\nPositive cells: " << positive << std::endl;
    if (valid == 0)
    {
        std::cerr << "WARNING: all trigger counts are zero. Do not scale up before checking the log.\n";
    }
    const auto output = campaign.directory / "raw_efficiency_master.root";
    if (std::filesystem::exists(output))
    {
        verifyFinal(output, campaign, merged, software);
        std::cout << "Existing final ROOT verified: " << output << std::endl;
    }
    else if (!checkOnly)
    {
        writeFinal(output, campaign, merged, software);
        std::cout << "Final ROOT: " << output << std::endl;
    }
}
