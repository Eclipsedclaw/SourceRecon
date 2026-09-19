#ifndef EIID_V10_SUBPIXEL_DIRECTION_CACHE_H
#define EIID_V10_SUBPIXEL_DIRECTION_CACHE_H

#include "PhysicsTypes.h"

#include <cstddef>
#include <span>
#include <vector>

// Builds the expensive RING-parent -> NESTED-child mapping once.  During MLEM,
// retrieving a pixel's samples is then only an O(1) span lookup with no heap
// allocation and no repeated HEALPix coordinate conversion.
class SubpixelDirectionCache
{
public:
    SubpixelDirectionCache(
        int reconstructionNside,
        int integrationNside
    );

    std::span<const Vec3> directions(
        std::size_t directionIndex
    ) const;

    int reconstructionNside() const noexcept;
    int integrationNside() const noexcept;
    std::size_t directionCount() const noexcept;
    std::size_t samplesPerPixel() const noexcept;

private:
    int reconstructionNside_{};
    int integrationNside_{};
    std::size_t directionCount_{};
    std::size_t samplesPerPixel_{};
    std::vector<Vec3> directions_;
};

#endif
