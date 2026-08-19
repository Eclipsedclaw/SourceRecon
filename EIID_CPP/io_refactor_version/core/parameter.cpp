#include "parameter.h"

Parameter::Parameter()
{
    // Nside = 8 时，全天球包含 12 * 8 * 8 = 768 个等面积方向像素。
    healpixNside = 16;

    // 三个能量候选点分别为 0.8 MeV、1.0 MeV 和 1.2 MeV。
    energyPointCount = 10;
    energyMinMeV = static_cast<Decimal>(0.3L);
    energyMaxMeV = static_cast<Decimal>(2.0L);

    iterationCount = 10;
    responseSigmaDegree = static_cast<Decimal>(6.0L);

    // 当前基础框架暂时认为每个 cell 的灵敏度相同。
    defaultSensitivity = static_cast<Decimal>(1.0L);
}
