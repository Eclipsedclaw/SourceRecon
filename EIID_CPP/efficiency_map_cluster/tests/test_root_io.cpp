#include "RootSchema.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

// 测试用的计数是人工构造的，不代表真实物理模拟。用于检查 ROOT 的实际读写。
int main(int argc, char** argv)
{
    try
    {
        if (argc != 2)
        {
            throw std::runtime_error{"Provide the test configuration"};
        }
        const auto sim = readJson(argv[1]);
        const ConfigManager config{sim};
        const auto stamp = std::chrono::high_resolution_clock::now().time_since_epoch().count();
        const auto directory = std::filesystem::current_path() / ("root_io_test_" + std::to_string(stamp));
        std::filesystem::create_directory(directory);
        const auto manifestPath = directory / "manifest.json";
        nlohmann::json manifest = {
            {"schema_version", 1},
            {"campaign_id", "root-io-regression"},
            {"sim_config", sim},
            {"run_config", {{"threads", 1}, {"jobs", 1}, {"master_seed", 1}}},
            {"total_events", config.totalEvents()},
            {"chunks", nlohmann::json::array(
                           {{{"id", 0}, {"job_id", 0}, {"first_event", 0}, {"event_count", config.totalEvents()}}})}};
        {
            std::ofstream output{manifestPath};
            output << manifest.dump();
        }
        const Campaign campaign{manifestPath};
        if (!campaign.manifest.is_object())
        {
            throw std::runtime_error{"Manifest became an array"};
        }
        ChunkData data;
        const nlohmann::json software = {{"test", true}};
        data.metadata = {
            {"identity", campaign.identity(campaign.tasks.front())}, {"software", software}, {"complete", true}};
        for (auto cell = config.firstActiveCell(); cell < config.fullCellCount(); ++cell)
        {
            // 偶数 cell 留下原始零值，奇数 cell 留下非零值，二者均须正确往返。
            const std::uint64_t k = cell % 2;
            data.counts[cell] = CellCounts{config.particlesPerCell(), k, k, k, k, 0.0002};
        }
        validateCounts(data.counts, campaign.tasks.front(), config);
        const auto chunk = campaign.chunkPath(campaign.tasks.front());
        writeChunk(chunk, data);
        const auto read = readChunk(chunk);
        validateCounts(read.counts, campaign.tasks.front(), config);
        const auto final = directory / "raw_efficiency_master.root";
        writeFinal(final, campaign, read.counts, software);
        verifyFinal(final, campaign, read.counts, software);
        bool rejected = false;
        try
        {
            writeChunk(chunk, data);
        }
        catch (const std::exception&)
        {
            rejected = true;
        }
        if (!rejected)
        {
            throw std::runtime_error{"Existing ROOT was overwritten"};
        }
        auto wrong = read.counts;
        ++wrong.begin()->second.valid;
        rejected = false;
        try
        {
            verifyFinal(final, campaign, wrong, software);
        }
        catch (const std::exception&)
        {
            rejected = true;
        }
        if (!rejected)
        {
            throw std::runtime_error{"Different counts were not detected"};
        }
        // 仅清除此函数刚刚创建的、唯一命名的测试目录，不清理用户 runs。
        std::filesystem::remove_all(directory);
        std::cout << "PASS: ROOT counts/zeros/metadata roundtrip, final readback, no overwrite\n";
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "ROOT I/O test failed: " << error.what() << '\n';
        return 1;
    }
}
