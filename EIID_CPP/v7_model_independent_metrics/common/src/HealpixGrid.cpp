#include "HealpixGrid.h"

#include <healpix_base.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

HealpixGrid::HealpixGrid(
    int healpixNside,
    int energyPointCount,
    Decimal energyMinMeV,
    Decimal energyMaxMeV
)
    : healpixNside_{healpixNside},
      energyPointCount_{energyPointCount},
      energyMinMeV_{energyMinMeV},
      energyMaxMeV_{energyMaxMeV}
{
    if (healpixNside_ <= 0 || energyPointCount_ <= 0)
    {
        throw std::runtime_error{"Grid dimensions must be positive."};
    }

    if (!std::isfinite(energyMinMeV_) || !std::isfinite(energyMaxMeV_) ||
        energyMaxMeV_ < energyMinMeV_)
    {
        throw std::runtime_error{"Grid energy bounds are invalid."};
    }

    if (energyPointCount_ == 1 && energyMinMeV_ != energyMaxMeV_)
    {
        throw std::runtime_error{"A one-point grid requires equal energy bounds."};
    }

    buildDirections();
    buildEnergies();
    buildCells();
}

void HealpixGrid::buildDirections()
{
    const Healpix_Base healpix{healpixNside_, RING, SET_NSIDE};
    directions_.reserve(static_cast<std::size_t>(healpix.Npix()));

    for (int pixelId = 0; pixelId < healpix.Npix(); ++pixelId)
    {
        const vec3 direction = healpix.pix2vec(pixelId);
        directions_.push_back(
            Vec3{
                static_cast<Decimal>(direction.x),
                static_cast<Decimal>(direction.y),
                static_cast<Decimal>(direction.z)
            }
        );
    }
}

void HealpixGrid::buildEnergies()
{
    energiesMeV_.reserve(static_cast<std::size_t>(energyPointCount_));
    const Decimal step = energyPointCount_ == 1
        ? static_cast<Decimal>(0.0)
        : (energyMaxMeV_ - energyMinMeV_) /
          static_cast<Decimal>(energyPointCount_ - 1);

    for (int index = 0; index < energyPointCount_; ++index)
    {
        energiesMeV_.push_back(
            energyMinMeV_ + static_cast<Decimal>(index) * step
        );
    }
}

void HealpixGrid::buildCells()
{
    if (directions_.size() >
        std::numeric_limits<std::size_t>::max() / energiesMeV_.size())
    {
        throw std::overflow_error{"Direction-energy grid size overflow."};
    }

    cells_.reserve(directions_.size() * energiesMeV_.size());

    for (std::size_t directionIndex = 0;
         directionIndex < directions_.size();
         ++directionIndex)
    {
        const Decimal z = std::clamp(
            directions_[directionIndex].z,
            static_cast<Decimal>(-1.0),
            static_cast<Decimal>(1.0)
        );
        const Decimal theta = std::acos(z) * static_cast<Decimal>(180.0) / PI;
        Decimal phi = std::atan2(
            directions_[directionIndex].y,
            directions_[directionIndex].x
        ) * static_cast<Decimal>(180.0) / PI;

        if (phi < static_cast<Decimal>(0.0))
        {
            phi += static_cast<Decimal>(360.0);
        }

        for (std::size_t energyIndex = 0;
             energyIndex < energiesMeV_.size();
             ++energyIndex)
        {
            cells_.push_back(
                Cell{
                    directionIndex,
                    energyIndex,
                    directionIndex,
                    theta,
                    phi,
                    directions_[directionIndex],
                    energiesMeV_[energyIndex]
                }
            );
        }
    }
}

const std::vector<Cell>& HealpixGrid::cells() const { return cells_; }

const Cell& HealpixGrid::cell(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    if (directionIndex >= directionCount() || energyIndex >= energyCount())
    {
        throw std::out_of_range{"Grid cell index is out of range."};
    }

    return cells_[directionIndex * energyCount() + energyIndex];
}

const Vec3& HealpixGrid::direction(std::size_t directionIndex) const
{
    if (directionIndex >= directions_.size())
    {
        throw std::out_of_range{"Grid direction index is out of range."};
    }

    return directions_[directionIndex];
}

Decimal HealpixGrid::energy(std::size_t energyIndex) const
{
    if (energyIndex >= energiesMeV_.size())
    {
        throw std::out_of_range{"Grid energy index is out of range."};
    }

    return energiesMeV_[energyIndex];
}

int HealpixGrid::healpixNside() const { return healpixNside_; }
std::size_t HealpixGrid::directionCount() const { return directions_.size(); }
std::size_t HealpixGrid::energyCount() const { return energiesMeV_.size(); }
