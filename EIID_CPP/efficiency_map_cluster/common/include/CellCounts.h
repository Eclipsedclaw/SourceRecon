#pragma once
#include "TaskSpec.h"
#include <map>

struct CellCounts
{
    std::uint64_t emitted{}, valid{}, hits{}, front{}, rear{};
    double coneFraction{};
};
// 只分配本块访问到的 cell；不为每个工作线程复制整个巨大天球数组。
using Counts = std::map<std::uint64_t, CellCounts>;
void addCounts(CellCounts& target, const CellCounts& source);
void validateCounts(const Counts& counts, const TaskSpec& task, const ConfigManager& config);
