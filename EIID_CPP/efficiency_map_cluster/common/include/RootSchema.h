#pragma once
#include "CellCounts.h"

struct ChunkData
{
    nlohmann::json metadata;
    Counts counts;
};

// 这些接口只在作业主线程、或独立合并进程里调用。没有工作线程共享 TFile。
ChunkData readChunk(const std::filesystem::path& path);
void writeChunk(const std::filesystem::path& path, const ChunkData& data);
void writeFinal(const std::filesystem::path& path, const Campaign& campaign, const Counts& counts,
                const nlohmann::json& software);
void verifyFinal(const std::filesystem::path& path, const Campaign& campaign, const Counts& counts,
                 const nlohmann::json& software);
