#include "include/parameter.h"

Parameter::Parameter()
{
    // Nside = 8 时，全天球共有 12 * 8 * 8 = 768 个等面积方向像素。
    healpixNside = 8;

    // 三个能量点分别是 0.8 MeV、1.0 MeV、1.2 MeV。
    energyPointCount = 3;
    energyMinMeV = static_cast<Decimal>(0.8L);
    energyMaxMeV = static_cast<Decimal>(1.2L);

    // 当前教学例子执行 10 次迭代，响应宽度暂设为 6 度。
    iterationCount = 10;
    responseSigmaDegree = static_cast<Decimal>(6.0L);

    // 教学例子暂时认为所有方向—能量 cell 的探测效率相同。
    defaultSensitivity = static_cast<Decimal>(1.0L);

    // 教学数据包含四个来自正前方、能量为 1 MeV 的事件。
    toyEventCount = 4;
    toyTrueEnergyMeV = static_cast<Decimal>(1.0L);
    toyScatterAngleDegree = static_cast<Decimal>(45.0L);
}
