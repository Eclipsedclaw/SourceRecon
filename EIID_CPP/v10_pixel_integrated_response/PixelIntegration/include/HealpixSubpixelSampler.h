#ifndef EIID_V10_HEALPIX_SUBPIXEL_SAMPLER_H
#define EIID_V10_HEALPIX_SUBPIXEL_SAMPLER_H

#include "IPixelDirectionSampler.h"
#include "SubpixelDirectionCache.h"

// Equal-area quadrature for one parent pixel.  If the reconstruction uses
// Nside=32 and integration uses Nside=64, every parent is represented by its
// four equal-area NESTED children, while the number of unknown image cells is
// still the Nside=32 count.
class HealpixSubpixelSampler final : public IPixelDirectionSampler
{
public:
    HealpixSubpixelSampler(
        int reconstructionNside,
        int integrationNside
    );

    std::span<const Vec3> directions(
        std::size_t directionIndex
    ) const override;

    int reconstructionNside() const noexcept override;
    int integrationNside() const noexcept override;
    std::size_t directionCount() const noexcept override;
    std::size_t samplesPerPixel() const noexcept override;
    std::string_view name() const noexcept override;

private:
    SubpixelDirectionCache cache_;
};

#endif
