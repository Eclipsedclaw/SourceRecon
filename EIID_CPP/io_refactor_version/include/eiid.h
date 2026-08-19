#ifndef EIID_CORE_H
#define EIID_CORE_H

#include "common.h"
#include "grid.h"
#include "parameter.h"

#include <vector>

// 算法核心接收的最小两次相互作用事件。
// r1/e1 是第一次 hit；r2 是第二次 hit。
struct Event
{
    Vec3 r1;
    Vec3 r2;
    Decimal e1MeV;
};

Decimal calculateResponse(const Event& event, const Cell& cell, const Parameter& parameter);

std::vector<Decimal> runEiid(const std::vector<Event>& events, const Grid& grid, const Parameter& parameter);

#endif
