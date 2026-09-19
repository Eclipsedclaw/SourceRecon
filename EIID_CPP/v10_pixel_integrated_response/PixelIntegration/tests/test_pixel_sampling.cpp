#include "HealpixSubpixelSampler.h"
#include "PixelCenterSampler.h"

#include <healpix_base.h>

#include <cassert>
#include <cmath>
#include <cstddef>

namespace
{
Decimal squaredDistance(const Vec3& left, const Vec3& right)
{
    const Decimal dx = left.x - right.x;
    const Decimal dy = left.y - right.y;
    const Decimal dz = left.z - right.z;
    return dx * dx + dy * dy + dz * dz;
}
}

int main()
{
    // With equal integration and reconstruction Nside, the subpixel path must
    // exactly reproduce the old pixel-centre path.  This is V10's principal
    // backward-compatibility check.
    const PixelCenterSampler centres{2};
    const HealpixSubpixelSampler equivalent{2, 2};

    assert(centres.directionCount() == equivalent.directionCount());
    assert(equivalent.samplesPerPixel() == 1);

    for (std::size_t pixel = 0; pixel < centres.directionCount(); ++pixel)
    {
        assert(
            squaredDistance(
                centres.directions(pixel).front(),
                equivalent.directions(pixel).front()
            ) < 1.0e-24
        );
    }

    // Nside 2 -> 4 gives four equal-area child centres per parent.  Mapping
    // each child centre back with the parent's RING map must recover that same
    // parent pixel.
    const HealpixSubpixelSampler refined{2, 4};
    const Healpix_Base parentRing{2, RING, SET_NSIDE};
    assert(refined.samplesPerPixel() == 4);

    Vec3 globalSum{};
    std::size_t sampleCount = 0;

    for (std::size_t parentPixel = 0;
         parentPixel < refined.directionCount();
         ++parentPixel)
    {
        const auto samples = refined.directions(parentPixel);
        assert(samples.size() == 4);

        for (const Vec3& sample : samples)
        {
            const vec3 healpixVector(
                static_cast<double>(sample.x),
                static_cast<double>(sample.y),
                static_cast<double>(sample.z)
            );
            assert(
                parentRing.vec2pix(healpixVector) ==
                static_cast<int>(parentPixel)
            );

            globalSum.x += sample.x;
            globalSum.y += sample.y;
            globalSum.z += sample.z;
            ++sampleCount;
        }
    }

    assert(sampleCount == static_cast<std::size_t>(12 * 4 * 4));

    // The equal-area child centres cover the complete sphere symmetrically.
    // Their global mean direction must therefore vanish up to round-off.
    assert(std::abs(globalSum.x) < 1.0e-12);
    assert(std::abs(globalSum.y) < 1.0e-12);
    assert(std::abs(globalSum.z) < 1.0e-12);
    return 0;
}
