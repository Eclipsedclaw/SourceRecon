// D:\CodexForSR\EIID_CPP\io_translator_version\include\eiid.h

#ifndef EIID_CORE_H
#define EIID_CORE_H

#include "common.h"
#include "grid.h"
#include "parameter.h"

#include <vector>

// 重建核心接收的两次相互作用事件。
// r1/e1 是最前方 ch2 的位置和沉积能量；r2 是后方 ch1 的位置。
struct Event
{
    Vec3 r1;
    Vec3 r2;
    Decimal e1MeV;
};

Decimal calculateResponse(const Event& event, const Cell& cell, const Parameter& parameter);

std::vector<Decimal> runEiid(const std::vector<Event>& events, const Grid& grid, const Parameter& parameter);

#endif
