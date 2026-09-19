#ifndef EIID_V10_PIXEL_CENTER_SAMPLER_H
#define EIID_V10_PIXEL_CENTER_SAMPLER_H

#include "IPixelDirectionSampler.h"

#include <vector>

// The V9-compatible control strategy: represent every reconstructed pixel by exactly
// one direction, namely its HEALPix centre.
class PixelCenterSampler final : public IPixelDirectionSampler
{
public:
    explicit PixelCenterSampler(int reconstructionNside);

    std::span<const Vec3> directions(
        std::size_t directionIndex
    ) const override;

    int reconstructionNside() const noexcept override;
    int integrationNside() const noexcept override;
    std::size_t directionCount() const noexcept override;
    std::size_t samplesPerPixel() const noexcept override;
    std::string_view name() const noexcept override;

private:
    int reconstructionNside_{};
    std::vector<Vec3> directions_;
};

#endif
