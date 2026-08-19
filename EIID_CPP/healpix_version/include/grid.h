#ifndef EIID_GRID_H
#define EIID_GRID_H

#include "common.h"
#include "parameter.h"

#include <vector>

// 三维向量用来保存 HEALPix 像素中心方向和 hit 位置。
struct Vec3
{
    Decimal x;
    Decimal y;
    Decimal z;
};

// EIID 的一个 cell 同时代表一个 HEALPix 天空像素和一个候选入射能量。
struct Cell
{
    std::size_t directionIndex;
    std::size_t energyIndex;
    std::size_t healpixPixelId;

    // 为了让未修改的算法核心继续工作，保留 directionAngleDegree 这个原成员名。
    // 在 HEALPix 版本中，它保存像素中心的极角 theta；phi 单独保存在下一成员中。
    Decimal directionAngleDegree;
    Decimal directionPhiDegree;

    Vec3 sourceDirection;
    Decimal energyMeV;
    Decimal sensitivity;
};

// Grid 根据 Parameter 生成 HEALPix 全天球方向、能量以及二者组成的联合 cell。
// main() 和 EIID 核心都不需要知道 HEALPix 库的具体调用方式。
class Grid
{
public:
    explicit Grid(const Parameter& parameter);

    const std::vector<Cell>& cells() const;
    std::size_t directionCount() const;
    std::size_t energyCount() const;

private:
    const Parameter* parameter_;
    std::vector<Vec3> directions_;
    std::vector<std::size_t> healpixPixelIds_;
    std::vector<Decimal> directionAnglesDegree_;
    std::vector<Decimal> directionPhiDegree_;
    std::vector<Decimal> energiesMeV_;
    std::vector<Cell> cells_;

    void buildDirections();
    void buildEnergies();
    void buildCells();
};

#endif
