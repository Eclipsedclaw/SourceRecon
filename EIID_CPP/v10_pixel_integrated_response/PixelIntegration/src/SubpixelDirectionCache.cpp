#include "SubpixelDirectionCache.h"

#include <healpix_base.h>

#include <limits>
#include <stdexcept>

namespace
{
bool isPowerOfTwo(int value)
{
    return value > 0 && (value & (value - 1)) == 0;
}
}

SubpixelDirectionCache::SubpixelDirectionCache(
    int reconstructionNside,
    int integrationNside
)
    : reconstructionNside_{reconstructionNside},
      integrationNside_{integrationNside}
{
    if (!isPowerOfTwo(reconstructionNside_) ||
        !isPowerOfTwo(integrationNside_))
    {
        throw std::runtime_error{
            "HEALPix reconstruction and integration Nside must be powers of two."
        };
    }

    if (integrationNside_ < reconstructionNside_ ||
        integrationNside_ % reconstructionNside_ != 0)
    {
        throw std::runtime_error{
            "Integration Nside must be an integer refinement of reconstruction Nside."
        };
    }

    const int refinement = integrationNside_ / reconstructionNside_;

    if (!isPowerOfTwo(refinement))
    {
        throw std::runtime_error{
            "The HEALPix Nside refinement ratio must be a power of two."
        };
    }

    samplesPerPixel_ = static_cast<std::size_t>(refinement) *
                       static_cast<std::size_t>(refinement);

    const Healpix_Base parent{reconstructionNside_, NEST, SET_NSIDE};
    const Healpix_Base child{integrationNside_, NEST, SET_NSIDE};
    directionCount_ = static_cast<std::size_t>(parent.Npix());

    if (directionCount_ >
        std::numeric_limits<std::size_t>::max() / samplesPerPixel_)
    {
        throw std::overflow_error{"Subpixel cache size overflow."};
    }

    directions_.reserve(directionCount_ * samplesPerPixel_);

    // HealpixGrid exposes parent pixels in RING order.  NESTED ordering is used
    // only internally because all descendants of one NESTED parent are a
    // contiguous block: parentNest * samplesPerPixel + localChild.
    for (int parentRing = 0; parentRing < parent.Npix(); ++parentRing)
    {
        const int parentNest = parent.ring2nest(parentRing);
        const std::size_t firstChild =
            static_cast<std::size_t>(parentNest) * samplesPerPixel_;

        for (std::size_t localChild = 0;
             localChild < samplesPerPixel_;
             ++localChild)
        {
            const std::size_t childIndex = firstChild + localChild;

            if (childIndex >= static_cast<std::size_t>(child.Npix()))
            {
                throw std::logic_error{"Computed HEALPix child index is invalid."};
            }

            const vec3 direction = child.pix2vec(
                static_cast<int>(childIndex)
            );
            directions_.push_back(
                Vec3{
                    static_cast<Decimal>(direction.x),
                    static_cast<Decimal>(direction.y),
                    static_cast<Decimal>(direction.z)
                }
            );
        }
    }
}

std::span<const Vec3> SubpixelDirectionCache::directions(
    std::size_t directionIndex
) const
{
    if (directionIndex >= directionCount_)
    {
        throw std::out_of_range{"Subpixel direction index is out of range."};
    }

    const std::size_t first = directionIndex * samplesPerPixel_;
    return std::span<const Vec3>{
        directions_.data() + first,
        samplesPerPixel_
    };
}

int SubpixelDirectionCache::reconstructionNside() const noexcept
{
    return reconstructionNside_;
}

int SubpixelDirectionCache::integrationNside() const noexcept
{
    return integrationNside_;
}

std::size_t SubpixelDirectionCache::directionCount() const noexcept
{
    return directionCount_;
}

std::size_t SubpixelDirectionCache::samplesPerPixel() const noexcept
{
    return samplesPerPixel_;
}
