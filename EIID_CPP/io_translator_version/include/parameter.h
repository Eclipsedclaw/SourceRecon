// D:\CodexForSR\EIID_CPP\io_translator_version\include\parameter.h

#ifndef EIID_PARAMETER_H
#define EIID_PARAMETER_H

#include "common.h"

// Parameter 只保存物理计算和网格划分需要的参数。
// 文件路径、树名和分支名全部由 IoConfig 管理。
class Parameter
{
public:
    // HEALPix 方向网格参数；方向像素数为 12 * Nside * Nside。
    int healpixNside;

    // 入射能量候选网格。
    int energyPointCount;
    Decimal energyMinMeV;
    Decimal energyMaxMeV;

    // EIID 迭代与响应参数。
    int iterationCount;
    Decimal responseSigmaDegree;
    Decimal defaultSensitivity;

    Parameter();
};

#endif
