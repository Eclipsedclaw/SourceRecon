#include "parameter.h"

Parameter::Parameter()
{
    // 极简角分辨率，先保证能出图（12 * 4 * 4 = 192 个像素）
    healpixNside = 4;

    // 针对 0.662 MeV 的专属小区间
    energyPointCount = 10; 
    energyMinMeV = static_cast<Decimal>(0.4L);
    energyMaxMeV = static_cast<Decimal>(0.9L);

    // 少量迭代，足够看出图像收敛趋势
    iterationCount = 20;
    responseSigmaDegree = static_cast<Decimal>(6.0L);

    defaultSensitivity = static_cast<Decimal>(1.0L);
}
// // D:\CodexForSR\EIID_CPP\io_translator_version\core\parameter.cpp

// #include "parameter.h"

// Parameter::Parameter()
// {
//     // Nside = 8 时，全天球包含 12 * 8 * 8 = 768 个等面积方向像素。
//     healpixNside = 16;

//     // 三个能量候选点分别为 0.8 MeV、1.0 MeV 和 1.2 MeV。
//     energyPointCount = 50;
//     energyMinMeV = static_cast<Decimal>(0.1L);
//     energyMaxMeV = static_cast<Decimal>(3.0L);

//     iterationCount = 100;
//     responseSigmaDegree = static_cast<Decimal>(6.0L);

//     // 当前基础框架暂时认为每个 cell 的灵敏度相同。
//     defaultSensitivity = static_cast<Decimal>(1.0L);
// }
