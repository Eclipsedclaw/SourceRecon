#ifndef EIID_V7_ABSOLUTE_EFFICIENCY_MAP_H
#define EIID_V7_ABSOLUTE_EFFICIENCY_MAP_H

#include "Common.h"

#include <cstddef>
#include <cstdint>
#include <vector>

// 方向×能量的绝对探测效率采用连续一维内存，查询复杂度为 O(1)。
class AbsoluteEfficiencyMap
{
public:
    AbsoluteEfficiencyMap(
        std::size_t directionCount,
        std::size_t energyCount
    );

    std::size_t directionCount() const;
    std::size_t energyCount() const;
    std::size_t size() const;
    std::size_t flatIndex(
        std::size_t directionIndex,
        std::size_t energyIndex
    ) const;
    Decimal at(std::size_t directionIndex, std::size_t energyIndex) const;
    Decimal atFlat(std::size_t index) const;
    void set(
        std::size_t directionIndex,
        std::size_t energyIndex,
        Decimal value
    );
    void setFlat(std::size_t index, Decimal value);
    void requireComplete() const;

private:
    std::size_t directionCount_{};
    std::size_t energyCount_{};
    std::size_t assignedCount_{};
    std::vector<Decimal> values_;
    std::vector<std::uint8_t> assigned_;
};

#endif
