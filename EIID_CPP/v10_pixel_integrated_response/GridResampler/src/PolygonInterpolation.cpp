#include "PolygonInterpolation.h"

#include "IGrid.h"

#include <healpix_base.h>

#include <numeric>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace
{
Decimal interpolateEnergy(
    const IGrid& grid,
    const AbsoluteEfficiencyMap& values,
    std::size_t direction,
    Decimal targetEnergy
)
{
    if (grid.energyCount() == 1 || targetEnergy <= grid.energy(0))
    {
        return values.at(direction, 0);
    }

    const std::size_t last = grid.energyCount() - 1;

    if (targetEnergy >= grid.energy(last))
    {
        return values.at(direction, last);
    }

    std::size_t upper = 1;

    while (grid.energy(upper) < targetEnergy)
    {
        ++upper;
    }

    const std::size_t lower = upper - 1;
    const Decimal fraction = (targetEnergy - grid.energy(lower)) /
        (grid.energy(upper) - grid.energy(lower));
    return (static_cast<Decimal>(1.0) - fraction) *
        values.at(direction, lower) +
        fraction * values.at(direction, upper);
}
}

PolygonInterpolation::PolygonInterpolation(
    int subdivisionFactor,
    bool requireFullCoverage
)
    : subdivisionFactor_{subdivisionFactor},
      requireFullCoverage_{requireFullCoverage}
{
    if (subdivisionFactor_ <= 0)
    {
        throw std::runtime_error{"Polygon subdivision factor must be positive."};
    }
}

std::string PolygonInterpolation::name() const { return "polygon"; }

AbsoluteEfficiencyMap PolygonInterpolation::resample(
    const IGrid& masterGrid,
    const IGrid& targetGrid,
    const AbsoluteEfficiencyMap& master
) const
{
    master.requireComplete();
    const int commonNside = std::lcm(
        masterGrid.healpixNside(),
        targetGrid.healpixNside()
    ) * subdivisionFactor_;

    if (commonNside <= 0 || commonNside > 4096)
    {
        throw std::runtime_error{"Polygon refinement Nside must be within 1..4096."};
    }

    const Healpix_Base commonBase{commonNside, RING, SET_NSIDE};
    const Healpix_Base masterBase{masterGrid.healpixNside(), RING, SET_NSIDE};
    const Healpix_Base targetBase{targetGrid.healpixNside(), RING, SET_NSIDE};
    using OverlapMap = std::unordered_map<std::size_t, std::size_t>;
    std::vector<OverlapMap> overlaps(targetGrid.directionCount());

    for (int pixel = 0; pixel < commonBase.Npix(); ++pixel)
    {
        const vec3 direction = commonBase.pix2vec(pixel);
        const std::size_t masterPixel = static_cast<std::size_t>(
            masterBase.vec2pix(direction)
        );
        const std::size_t targetPixel = static_cast<std::size_t>(
            targetBase.vec2pix(direction)
        );
        ++overlaps[targetPixel][masterPixel];
    }

    AbsoluteEfficiencyMap result{
        targetGrid.directionCount(),
        targetGrid.energyCount()
    };

    for (std::size_t targetDirection = 0;
         targetDirection < targetGrid.directionCount();
         ++targetDirection)
    {
        std::size_t totalMicroPixels{};

        for (const auto& entry : overlaps[targetDirection])
        {
            totalMicroPixels += entry.second;
        }

        if (totalMicroPixels == 0 && requireFullCoverage_)
        {
            throw std::runtime_error{"A Target pixel has no Master coverage."};
        }

        for (std::size_t targetEnergy = 0;
             targetEnergy < targetGrid.energyCount();
             ++targetEnergy)
        {
            Decimal weighted{};

            for (const auto& [masterDirection, count] :
                 overlaps[targetDirection])
            {
                weighted += static_cast<Decimal>(count) * interpolateEnergy(
                    masterGrid,
                    master,
                    masterDirection,
                    targetGrid.energy(targetEnergy)
                );
            }

            result.set(
                targetDirection,
                targetEnergy,
                totalMicroPixels == 0
                    ? static_cast<Decimal>(0.0)
                    : weighted / static_cast<Decimal>(totalMicroPixels)
            );
        }
    }

    return result;
}
