#ifndef EIID_V10_I_PIXEL_DIRECTION_SAMPLER_H
#define EIID_V10_I_PIXEL_DIRECTION_SAMPLER_H

#include "PhysicsTypes.h"

#include <cstddef>
#include <span>
#include <string_view>

// A sampler defines the physical directions used to average one reconstructed
// HEALPix pixel.  The reconstruction algorithm sees only this interface, so a
// new quadrature rule can be added without changing LM-MLEM.
class IPixelDirectionSampler
{
public:
    virtual ~IPixelDirectionSampler() = default;

    // directionIndex is always the RING pixel index used by HealpixGrid.
    virtual std::span<const Vec3> directions(
        std::size_t directionIndex
    ) const = 0;

    virtual int reconstructionNside() const noexcept = 0;
    virtual int integrationNside() const noexcept = 0;
    virtual std::size_t directionCount() const noexcept = 0;
    virtual std::size_t samplesPerPixel() const noexcept = 0;
    virtual std::string_view name() const noexcept = 0;
};

#endif
