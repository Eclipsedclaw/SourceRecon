#include "HealpixSubpixelSampler.h"

HealpixSubpixelSampler::HealpixSubpixelSampler(
    int reconstructionNside,
    int integrationNside
)
    : cache_{reconstructionNside, integrationNside}
{
}

std::span<const Vec3> HealpixSubpixelSampler::directions(
    std::size_t directionIndex
) const
{
    return cache_.directions(directionIndex);
}

int HealpixSubpixelSampler::reconstructionNside() const noexcept
{
    return cache_.reconstructionNside();
}

int HealpixSubpixelSampler::integrationNside() const noexcept
{
    return cache_.integrationNside();
}

std::size_t HealpixSubpixelSampler::directionCount() const noexcept
{
    return cache_.directionCount();
}

std::size_t HealpixSubpixelSampler::samplesPerPixel() const noexcept
{
    return cache_.samplesPerPixel();
}

std::string_view HealpixSubpixelSampler::name() const noexcept
{
    return "healpix_subpixel";
}
