// v3_json_architecture/include/grid.h

#ifndef EIID_GRID_H
#define EIID_GRID_H

#include "ReconConfig.h"
#include "common.h"

#include <vector>

// 三维向量用来保存 HEALPix 像素中心方向和事件中的 hit 位置。
struct Vec3
{
    Decimal x;
    Decimal y;
    Decimal z;
};

// 一个联合 cell 同时对应一个 HEALPix 天空像素和一个候选入射能量。
struct Cell
{
    std::size_t directionIndex;
    std::size_t energyIndex;
    std::size_t healpixPixelId;

    // directionAngleDegree 保存 HEALPix 像素中心的极角 theta。
    Decimal directionAngleDegree;
    Decimal directionPhiDegree;

    Vec3 sourceDirection;
    Decimal energyMeV;
};

// Grid 只负责生成全天球方向、能量以及二者组成的联合 cell。
class Grid
{
public:
    explicit Grid(const ReconConfig& config);
    Grid(int healpixNside, int energyPointCount, Decimal energyMinMeV, Decimal energyMaxMeV);

    const std::vector<Cell>& cells() const;
    const Cell& cell(std::size_t directionIndex, std::size_t energyIndex) const;
    const Vec3& direction(std::size_t directionIndex) const;
    Decimal energy(std::size_t energyIndex) const;

    int healpixNside() const;
    std::size_t directionCount() const;
    std::size_t energyCount() const;

private:
    int healpixNside_;
    int energyPointCount_;
    Decimal energyMinMeV_;
    Decimal energyMaxMeV_;

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
