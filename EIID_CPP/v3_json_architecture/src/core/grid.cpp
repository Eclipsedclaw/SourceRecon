#include "grid.h"

#include <healpix_base.h>

#include <cmath>
#include <stdexcept>

Grid::Grid(const ReconConfig& config)
    : Grid{
          config.healpixNside(),
          config.energyPointCount(),
          config.energyMinMeV(),
          config.energyMaxMeV()
      }
{}

Grid::Grid(
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
        throw std::runtime_error{"HEALPix Nside and energy point count must be positive."};
    }

    if (!std::isfinite(energyMinMeV_) || !std::isfinite(energyMaxMeV_) ||
        energyMaxMeV_ < energyMinMeV_)
    {
        throw std::runtime_error{"Grid energy bounds are invalid."};
    }

    if (energyPointCount_ == 1 && energyMinMeV_ != energyMaxMeV_)
    {
        throw std::runtime_error{"A one-point energy grid requires equal bounds."};
    }

    buildDirections();
    buildEnergies();
    buildCells();
}

void Grid::buildDirections()
{
    const int pixelCount = 12 * healpixNside_ * healpixNside_;
    const Healpix_Base healpixBase{healpixNside_, RING, SET_NSIDE};

    directions_.reserve(static_cast<std::size_t>(pixelCount));
    healpixPixelIds_.reserve(static_cast<std::size_t>(pixelCount));
    directionAnglesDegree_.reserve(static_cast<std::size_t>(pixelCount));
    directionPhiDegree_.reserve(static_cast<std::size_t>(pixelCount));

    for (int pixelId = 0; pixelId < pixelCount; ++pixelId)
    {
        const vec3 healpixDirection = healpixBase.pix2vec(pixelId);
        const pointing healpixAngle = healpixBase.pix2ang(pixelId);

        directions_.push_back(
            Vec3{
                static_cast<Decimal>(healpixDirection.x),
                static_cast<Decimal>(healpixDirection.y),
                static_cast<Decimal>(healpixDirection.z)
            }
        );

        healpixPixelIds_.push_back(static_cast<std::size_t>(pixelId));
        directionAnglesDegree_.push_back(
            static_cast<Decimal>(healpixAngle.theta) *
            static_cast<Decimal>(180.0L) / PI
        );

        directionPhiDegree_.push_back(
            static_cast<Decimal>(healpixAngle.phi) *
            static_cast<Decimal>(180.0L) / PI
        );
    }

    if (static_cast<int>(directions_.size()) != healpixBase.Npix())
    {
        throw std::runtime_error{"HEALPix pixel count does not match 12 * Nside * Nside."};
    }
}

void Grid::buildEnergies()
{
    energiesMeV_.reserve(static_cast<std::size_t>(energyPointCount_));

    const Decimal step = energyPointCount_ == 1
        ? static_cast<Decimal>(0.0L)
        : (energyMaxMeV_ - energyMinMeV_) /
          static_cast<Decimal>(energyPointCount_ - 1);

    for (int index = 0; index < energyPointCount_; ++index)
    {
        energiesMeV_.push_back(
            energyMinMeV_ + static_cast<Decimal>(index) * step
        );
    }
}

void Grid::buildCells()
{
    cells_.reserve(directions_.size() * energiesMeV_.size());

    for (std::size_t directionIndex = 0;
         directionIndex < directions_.size();
         ++directionIndex)
    {
        for (std::size_t energyIndex = 0;
             energyIndex < energiesMeV_.size();
             ++energyIndex)
        {
            cells_.push_back(
                Cell{
                    directionIndex,
                    energyIndex,
                    healpixPixelIds_[directionIndex],
                    directionAnglesDegree_[directionIndex],
                    directionPhiDegree_[directionIndex],
                    directions_[directionIndex],
                    energiesMeV_[energyIndex]
                }
            );
        }
    }
}

const std::vector<Cell>& Grid::cells() const { return cells_; }

const Cell& Grid::cell(
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

const Vec3& Grid::direction(std::size_t directionIndex) const
{
    if (directionIndex >= directions_.size())
    {
        throw std::out_of_range{"Grid direction index is out of range."};
    }

    return directions_[directionIndex];
}

Decimal Grid::energy(std::size_t energyIndex) const
{
    if (energyIndex >= energiesMeV_.size())
    {
        throw std::out_of_range{"Grid energy index is out of range."};
    }

    return energiesMeV_[energyIndex];
}

int Grid::healpixNside() const { return healpixNside_; }
std::size_t Grid::directionCount() const { return directions_.size(); }
std::size_t Grid::energyCount() const { return energiesMeV_.size(); }
