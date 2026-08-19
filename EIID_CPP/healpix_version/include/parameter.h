#ifndef EIID_PARAMETER_H
#define EIID_PARAMETER_H

#include "common.h"

// Parameter 只负责保存参数，不负责生成网格，也不执行 EIID 迭代。
// 以后想修改 HEALPix 分辨率、能量范围或迭代次数，只改这个对象即可。
class Parameter
{
public:
    // HEALPix 的方向分辨率参数。
    // 全天球方向像素总数固定为 12 * healpixNside * healpixNside。
    int healpixNside;

    // 能量网格：从最小能量均匀划分到最大能量。
    int energyPointCount;
    Decimal energyMinMeV;
    Decimal energyMaxMeV;

    // EIID 迭代参数。
    int iterationCount;
    Decimal responseSigmaDegree;
    Decimal defaultSensitivity;

    // 以下参数只用来生成教学事件，不会传给 EIID 重建器作为答案。
    int toyEventCount;
    Decimal toyTrueEnergyMeV;
    Decimal toyScatterAngleDegree;

    Parameter();
};

#endif
