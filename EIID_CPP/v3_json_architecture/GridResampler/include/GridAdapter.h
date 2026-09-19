#ifndef EIID_GRID_ADAPTER_H
#define EIID_GRID_ADAPTER_H

#include "ResamplerConfig.h"
#include "SensitivityMatrix.h"
#include "grid.h"

#include <string>

// GridAdapter 持有 Master 与 Target 两套网格，并只负责数值重采样。
// ROOT 文件格式由 ResamplerIO 独立处理。
class GridAdapter
{
public:
    GridAdapter(
        const GridSpecification& masterSpecification,
        const GridSpecification& targetSpecification,
        int polygonSubdivisionFactor,
        bool requireFullCoverage
    );

    const Grid& masterGrid() const;
    const Grid& targetGrid() const;

    SensitivityMatrix resample(
        const SensitivityMatrix& masterSensitivity,
        const std::string& interpolation
    ) const;

private:
    Grid masterGrid_;
    Grid targetGrid_;
    int polygonSubdivisionFactor_;
    bool requireFullCoverage_;

    SensitivityMatrix resampleNearest(
        const SensitivityMatrix& masterSensitivity
    ) const;

    SensitivityMatrix resamplePolygon(
        const SensitivityMatrix& masterSensitivity
    ) const;

    Decimal interpolateMasterEnergy(
        const SensitivityMatrix& masterSensitivity,
        std::size_t masterDirectionIndex,
        Decimal targetEnergy
    ) const;
};

#endif
