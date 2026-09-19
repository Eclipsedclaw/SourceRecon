#ifndef EIID_V4_I_GRID_H
#define EIID_V4_I_GRID_H

#include "PhysicsTypes.h"

#include <cstddef>
#include <vector>

// 算法只依赖此接口。未来可加入其他球面像素化，而不修改重建器。
class IGrid
{
public:
    virtual ~IGrid() = default;

    virtual const std::vector<Cell>& cells() const = 0;
    virtual const Cell& cell(
        std::size_t directionIndex,
        std::size_t energyIndex
    ) const = 0;
    virtual const Vec3& direction(std::size_t directionIndex) const = 0;
    virtual Decimal energy(std::size_t energyIndex) const = 0;
    virtual int healpixNside() const = 0;
    virtual std::size_t directionCount() const = 0;
    virtual std::size_t energyCount() const = 0;
};

#endif
