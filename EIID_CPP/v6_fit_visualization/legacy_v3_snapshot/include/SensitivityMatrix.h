#ifndef EIID_SENSITIVITY_MATRIX_H
#define EIID_SENSITIVITY_MATRIX_H

#include "common.h"

#include <cstddef>
#include <cstdint>
#include <vector>

// 二维的“方向 × 能量”敏感度在内存中保存为连续一维数组。
// flatIndex = directionIndex * energyCount + energyIndex，因此查询为 O(1)。
class SensitivityMatrix
{
public:
    SensitivityMatrix(std::size_t directionCount, std::size_t energyCount);

    std::size_t directionCount() const;
    std::size_t energyCount() const;
    std::size_t size() const;
    std::size_t assignedCount() const;

    std::size_t flatIndex(std::size_t directionIndex, std::size_t energyIndex) const;
    bool has(std::size_t directionIndex, std::size_t energyIndex) const;

    Decimal at(std::size_t directionIndex, std::size_t energyIndex) const;
    Decimal atFlat(std::size_t flatIndex) const;

    void set(std::size_t directionIndex, std::size_t energyIndex, Decimal value);
    void requireComplete() const;

private:
    std::size_t directionCount_;
    std::size_t energyCount_;
    std::size_t assignedCount_ = 0;
    std::vector<Decimal> values_;
    std::vector<std::uint8_t> assigned_;
};

#endif
