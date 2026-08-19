#ifndef EIID_GRID_H
#define EIID_GRID_H

#include "common.h"
#include "parameter.h"

#include <vector>

// 三维向量用来保存天空方向和 hit 位置。
struct Vec3
{
    Decimal x;
    Decimal y;
    Decimal z;
};

// EIID 的一个 cell 同时代表一个天空方向和一个候选入射能量。
struct Cell
{
    std::size_t directionIndex;
    std::size_t energyIndex;
    Decimal directionAngleDegree;
    Vec3 sourceDirection;
    Decimal energyMeV;
    Decimal sensitivity;
};

// Grid 根据 Parameter 生成全部方向、能量和联合 cell。
// main() 不再亲自编写双重循环，也不再负责索引展开。
class Grid
{
public:
    explicit Grid(const Parameter& parameter);

    const std::vector<Cell>& cells() const;//末尾带有const的，代表这是一个只读函数；常量对象只能调用只读（常量）成员函数
    std::size_t directionCount() const;
    std::size_t energyCount() const;

private:
    const Parameter* parameter_;
    std::vector<Vec3> directions_;
    std::vector<Decimal> directionAnglesDegree_;
    std::vector<Decimal> energiesMeV_;
    std::vector<Cell> cells_;

    void buildDirections();
    void buildEnergies();
    void buildCells();
};

#endif
