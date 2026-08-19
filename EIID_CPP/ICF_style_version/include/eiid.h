#ifndef EIID_CORE_H
#define EIID_CORE_H

#include "common.h"
#include "grid.h"
#include "parameter.h"

#include <vector>

// 一个最小两次相互作用事件。
// r1/e1 是第一次 hit；r2 是第二次 hit。
struct Event
{
    Vec3 r1;
    Vec3 r2;
    Decimal e1MeV;
};

// 计算一个方向—能量 cell 对一个事件的解释能力。
Decimal calculateResponse(const Event& event, const Cell& cell, const Parameter& parameter);

// 在完整方向—能量联合网格上执行 EIID 的 LM-MLEM 迭代。
std::vector<Decimal> runEiid(const std::vector<Event>& events, const Grid& grid, const Parameter& parameter);

// 生成教学事件。真实数据接入后，这个函数会被 ROOT 读取函数替代。
std::vector<Event> makeToyEvents(const Parameter& parameter);

// 输出每个联合 cell 的结果，并指出峰值所在的方向和能量。
void printResult(const std::vector<Decimal>& image, const Grid& grid);

#endif
