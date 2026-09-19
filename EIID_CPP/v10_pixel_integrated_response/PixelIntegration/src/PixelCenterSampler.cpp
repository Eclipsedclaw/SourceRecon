#include "PixelCenterSampler.h"

#include <healpix_base.h>

#include <stdexcept>

PixelCenterSampler::PixelCenterSampler(int reconstructionNside)
    : reconstructionNside_{reconstructionNside}
{
    if (reconstructionNside_ <= 0)
    {
        throw std::runtime_error{"Pixel-centre Nside must be positive."};
    }

    const Healpix_Base healpix{reconstructionNside_, RING, SET_NSIDE};
    directions_.reserve(static_cast<std::size_t>(healpix.Npix()));

    for (int pixel = 0; pixel < healpix.Npix(); ++pixel)
    {
        const vec3 direction = healpix.pix2vec(pixel);
        directions_.push_back(
            Vec3{
                static_cast<Decimal>(direction.x),
                static_cast<Decimal>(direction.y),
                static_cast<Decimal>(direction.z)
            }
        );
    }
}

std::span<const Vec3> PixelCenterSampler::directions(
    std::size_t directionIndex
) const
{
    if (directionIndex >= directions_.size())
    {
        throw std::out_of_range{"Pixel-centre direction index is out of range."};
    }

    return std::span<const Vec3>{directions_.data() + directionIndex, 1};
}

int PixelCenterSampler::reconstructionNside() const noexcept
{
    return reconstructionNside_;
}

int PixelCenterSampler::integrationNside() const noexcept
{
    return reconstructionNside_;
}

std::size_t PixelCenterSampler::directionCount() const noexcept
{
    return directions_.size();
}

std::size_t PixelCenterSampler::samplesPerPixel() const noexcept
{
    return 1;
}

std::string_view PixelCenterSampler::name() const noexcept
{
    return "pixel_center";
}
