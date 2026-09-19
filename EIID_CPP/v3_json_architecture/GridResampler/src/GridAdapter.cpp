#include "GridAdapter.h"

#include <healpix_base.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <unordered_map>
#include <vector>

GridAdapter::GridAdapter(
    const GridSpecification& masterSpecification,
    const GridSpecification& targetSpecification,
    int polygonSubdivisionFactor,
    bool requireFullCoverage
)
    : masterGrid_{
          masterSpecification.healpixNside,
          masterSpecification.energyPointCount,
          masterSpecification.energyMinMeV,
          masterSpecification.energyMaxMeV
      },
      targetGrid_{
          targetSpecification.healpixNside,
          targetSpecification.energyPointCount,
          targetSpecification.energyMinMeV,
          targetSpecification.energyMaxMeV
      },
      polygonSubdivisionFactor_{polygonSubdivisionFactor},
      requireFullCoverage_{requireFullCoverage}
{
    if (polygonSubdivisionFactor_ <= 0)
    {
        throw std::runtime_error{"Polygon subdivision factor must be positive."};
    }
}

const Grid& GridAdapter::masterGrid() const { return masterGrid_; }
const Grid& GridAdapter::targetGrid() const { return targetGrid_; }

SensitivityMatrix GridAdapter::resample(
    const SensitivityMatrix& masterSensitivity,
    const std::string& interpolation
) const
{
    if (masterSensitivity.directionCount() != masterGrid_.directionCount() ||
        masterSensitivity.energyCount() != masterGrid_.energyCount())
    {
        throw std::runtime_error{"Input sensitivity dimensions do not match the Master grid."};
    }

    masterSensitivity.requireComplete();

    if (interpolation == "nearest")
    {
        return resampleNearest(masterSensitivity);
    }

    if (interpolation == "polygon")
    {
        return resamplePolygon(masterSensitivity);
    }

    throw std::runtime_error{"Unknown interpolation method: " + interpolation};
}

SensitivityMatrix GridAdapter::resampleNearest(
    const SensitivityMatrix& masterSensitivity
) const
{
    SensitivityMatrix result{
        targetGrid_.directionCount(),
        targetGrid_.energyCount()
    };

    const Healpix_Base masterBase{
        masterGrid_.healpixNside(),
        RING,
        SET_NSIDE
    };

    for (std::size_t targetDirection = 0;
         targetDirection < targetGrid_.directionCount();
         ++targetDirection)
    {
        const Vec3& direction = targetGrid_.direction(targetDirection);
        const int masterDirection = masterBase.vec2pix(
            vec3(
                static_cast<double>(direction.x),
                static_cast<double>(direction.y),
                static_cast<double>(direction.z)
            )
        );

        for (std::size_t targetEnergyIndex = 0;
             targetEnergyIndex < targetGrid_.energyCount();
             ++targetEnergyIndex)
        {
            const Decimal targetEnergy = targetGrid_.energy(targetEnergyIndex);
            std::size_t nearestEnergyIndex = 0;
            Decimal nearestDistance = std::numeric_limits<Decimal>::max();

            for (std::size_t masterEnergyIndex = 0;
                 masterEnergyIndex < masterGrid_.energyCount();
                 ++masterEnergyIndex)
            {
                const Decimal distance = std::abs(
                    masterGrid_.energy(masterEnergyIndex) - targetEnergy
                );

                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestEnergyIndex = masterEnergyIndex;
                }
            }

            result.set(
                targetDirection,
                targetEnergyIndex,
                masterSensitivity.at(
                    static_cast<std::size_t>(masterDirection),
                    nearestEnergyIndex
                )
            );
        }
    }

    return result;
}

SensitivityMatrix GridAdapter::resamplePolygon(
    const SensitivityMatrix& masterSensitivity
) const
{
    // HEALPix 微像素全部等面积。把 Master 与 Target 同时投影到共同细分网格后，
    // 落入同一对像素的微像素数量正比于两个球面像素的交叠面积。
    // 对常见的 2^k Nside 网格，commonNside 是二者的共同层级细分。
    const int commonNside = std::lcm(
        masterGrid_.healpixNside(),
        targetGrid_.healpixNside()
    ) * polygonSubdivisionFactor_;

    if (commonNside <= 0 || commonNside > 4096)
    {
        throw std::runtime_error{"Polygon common-refinement Nside is outside the safe range 1..4096."};
    }

    const Healpix_Base commonBase{commonNside, RING, SET_NSIDE};
    const Healpix_Base masterBase{masterGrid_.healpixNside(), RING, SET_NSIDE};
    const Healpix_Base targetBase{targetGrid_.healpixNside(), RING, SET_NSIDE};

    using OverlapMap = std::unordered_map<std::size_t, std::size_t>;
    std::vector<OverlapMap> overlapCounts(targetGrid_.directionCount());

    for (int commonPixel = 0; commonPixel < commonBase.Npix(); ++commonPixel)
    {
        const vec3 direction = commonBase.pix2vec(commonPixel);
        const std::size_t masterPixel = static_cast<std::size_t>(
            masterBase.vec2pix(direction)
        );

        const std::size_t targetPixel = static_cast<std::size_t>(
            targetBase.vec2pix(direction)
        );

        ++overlapCounts[targetPixel][masterPixel];
    }

    SensitivityMatrix result{
        targetGrid_.directionCount(),
        targetGrid_.energyCount()
    };

    for (std::size_t targetDirection = 0;
         targetDirection < targetGrid_.directionCount();
         ++targetDirection)
    {
        const OverlapMap& overlaps = overlapCounts[targetDirection];

        std::size_t totalMicroPixels = 0;

        for (const auto& [masterDirection, count] : overlaps)
        {
            static_cast<void>(masterDirection);
            totalMicroPixels += count;
        }

        if (totalMicroPixels == 0 && requireFullCoverage_)
        {
            throw std::runtime_error{"A Target HEALPix pixel has no Master polygon coverage."};
        }

        for (std::size_t targetEnergyIndex = 0;
             targetEnergyIndex < targetGrid_.energyCount();
             ++targetEnergyIndex)
        {
            Decimal weightedSum = static_cast<Decimal>(0.0L);
            const Decimal targetEnergy = targetGrid_.energy(targetEnergyIndex);

            for (const auto& [masterDirection, count] : overlaps)
            {
                weightedSum += static_cast<Decimal>(count) *
                    interpolateMasterEnergy(
                        masterSensitivity,
                        masterDirection,
                        targetEnergy
                    );
            }

            const Decimal value = totalMicroPixels == 0
                ? static_cast<Decimal>(0.0L)
                : weightedSum / static_cast<Decimal>(totalMicroPixels);

            result.set(targetDirection, targetEnergyIndex, value);
        }
    }

    return result;
}

Decimal GridAdapter::interpolateMasterEnergy(
    const SensitivityMatrix& masterSensitivity,
    std::size_t masterDirectionIndex,
    Decimal targetEnergy
) const
{
    if (masterGrid_.energyCount() == 1)
    {
        return masterSensitivity.at(masterDirectionIndex, 0);
    }

    if (targetEnergy <= masterGrid_.energy(0))
    {
        return masterSensitivity.at(masterDirectionIndex, 0);
    }

    const std::size_t lastIndex = masterGrid_.energyCount() - 1;

    if (targetEnergy >= masterGrid_.energy(lastIndex))
    {
        return masterSensitivity.at(masterDirectionIndex, lastIndex);
    }

    std::size_t upperIndex = 1;

    while (upperIndex < masterGrid_.energyCount() &&
           masterGrid_.energy(upperIndex) < targetEnergy)
    {
        ++upperIndex;
    }

    const std::size_t lowerIndex = upperIndex - 1;
    const Decimal lowerEnergy = masterGrid_.energy(lowerIndex);
    const Decimal upperEnergy = masterGrid_.energy(upperIndex);
    const Decimal fraction = (targetEnergy - lowerEnergy) /
        (upperEnergy - lowerEnergy);

    return (
        static_cast<Decimal>(1.0L) - fraction
    ) * masterSensitivity.at(masterDirectionIndex, lowerIndex) +
        fraction * masterSensitivity.at(masterDirectionIndex, upperIndex);
}
