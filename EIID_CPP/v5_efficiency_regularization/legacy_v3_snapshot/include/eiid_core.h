#ifndef EIID_CORE_V3_H
#define EIID_CORE_V3_H

#include "ReconConfig.h"
#include "common.h"
#include "grid.h"

struct Event
{
    Vec3 r1;
    Vec3 r2;
    Decimal e1MeV;
};

// 单事件响应核沿用上一版 EIID 的康普顿几何与能量一致性模型。
Decimal calculateResponse(
    const Event& event,
    const Cell& cell,
    const ReconConfig& config
);

#endif
