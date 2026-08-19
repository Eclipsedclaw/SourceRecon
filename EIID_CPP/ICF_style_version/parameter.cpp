#include "include/parameter.h"

Parameter::Parameter()
{
    // 三个方向点分别是 -20 度、0 度、20 度。
    directionPointCount = 3;
    directionMinDegree = static_cast<Decimal>(-20.0L);
    directionMaxDegree = static_cast<Decimal>(20.0L);

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
