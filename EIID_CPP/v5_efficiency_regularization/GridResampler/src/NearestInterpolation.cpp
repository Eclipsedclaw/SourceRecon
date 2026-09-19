#include "NearestInterpolation.h"

#include "IGrid.h"

#include <healpix_base.h>

#include <cmath>
#include <limits>

std::string NearestInterpolation::name() const { return "nearest"; }

AbsoluteEfficiencyMap NearestInterpolation::resample(
    const IGrid& masterGrid,
    const IGrid& targetGrid,
    const AbsoluteEfficiencyMap& master
) const
{
    master.requireComplete();
    AbsoluteEfficiencyMap result{
        targetGrid.directionCount(),
        targetGrid.energyCount()
    };
    const Healpix_Base masterBase{
        masterGrid.healpixNside(),
        RING,
        SET_NSIDE
    };

    for (std::size_t direction = 0;
         direction < targetGrid.directionCount();
         ++direction)
    {
        const Vec3& targetDirection = targetGrid.direction(direction);
        const std::size_t masterDirection = static_cast<std::size_t>(
            masterBase.vec2pix(
                vec3(targetDirection.x, targetDirection.y, targetDirection.z)
            )
        );

        for (std::size_t energy = 0;
             energy < targetGrid.energyCount();
             ++energy)
        {
            std::size_t nearestEnergy{};
            Decimal nearestDistance = std::numeric_limits<Decimal>::max();

            for (std::size_t candidate = 0;
                 candidate < masterGrid.energyCount();
                 ++candidate)
            {
                const Decimal distance = std::abs(
                    masterGrid.energy(candidate) - targetGrid.energy(energy)
                );

                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestEnergy = candidate;
                }
            }

            result.set(
                direction,
                energy,
                master.at(masterDirection, nearestEnergy)
            );
        }
    }

    return result;
}
