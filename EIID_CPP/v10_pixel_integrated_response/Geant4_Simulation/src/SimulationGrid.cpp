#include "SimulationGrid.hh"

#include <healpix_base.h>

#include <cmath>
#include <limits>
#include <stdexcept>

namespace
{
constexpr double pi = 3.14159265358979323846;
}

SimulationGrid::SimulationGrid(const ConfigManager& config)
    : particlesPerCell_{config.particlesPerCell()},
      directionCount_{
          static_cast<std::size_t>(12) *
          static_cast<std::size_t>(config.healpixNside()) *
          static_cast<std::size_t>(config.healpixNside())
      },
      energyCount_{static_cast<std::size_t>(config.energyPointCount())}
{
    const Healpix_Base healpix{
        config.healpixNside(),
        RING,
        SET_NSIDE
    };

    const double energyStep = energyCount_ > 1
        ? (config.energyMaxMeV() - config.energyMinMeV()) /
              static_cast<double>(energyCount_ - 1)
        : 0.0;

    fullCells_.reserve(directionCount_ * energyCount_);

    for (std::size_t directionIndex = 0;
         directionIndex < directionCount_;
         ++directionIndex)
    {
        const vec3 direction = healpix.pix2vec(
            static_cast<int>(directionIndex)
        );
        const pointing angles = healpix.pix2ang(
            static_cast<int>(directionIndex)
        );
        const bool activeDirection =
            !config.frontHemisphereOnly() || direction.z <= 0.0;

        for (std::size_t energyIndex = 0;
             energyIndex < energyCount_;
             ++energyIndex)
        {
            const std::size_t flatIndex =
                directionIndex * energyCount_ + energyIndex;

            fullCells_.push_back(
                SimulationCell{
                    flatIndex,
                    directionIndex,
                    energyIndex,
                    static_cast<std::int64_t>(directionIndex),
                    direction.x,
                    direction.y,
                    direction.z,
                    angles.theta * 180.0 / pi,
                    angles.phi * 180.0 / pi,
                    config.energyMinMeV() +
                        static_cast<double>(energyIndex) * energyStep
                }
            );

            if (activeDirection)
            {
                activeFlatIndices_.push_back(flatIndex);
            }
        }
    }

    if (activeFlatIndices_.empty())
    {
        throw std::runtime_error{"Simulation grid contains no active cells."};
    }

    const std::uint64_t active =
        static_cast<std::uint64_t>(activeFlatIndices_.size());
    const std::uint64_t particles =
        static_cast<std::uint64_t>(particlesPerCell_);

    if (active > std::numeric_limits<std::uint64_t>::max() / particles)
    {
        throw std::overflow_error{"Requested Geant4 event count overflows uint64."};
    }
}

std::size_t SimulationGrid::directionCount() const { return directionCount_; }
std::size_t SimulationGrid::energyCount() const { return energyCount_; }
std::size_t SimulationGrid::fullCellCount() const { return fullCells_.size(); }
std::size_t SimulationGrid::activeCellCount() const
{
    return activeFlatIndices_.size();
}

std::uint64_t SimulationGrid::totalEventCount() const
{
    return static_cast<std::uint64_t>(activeFlatIndices_.size()) *
           static_cast<std::uint64_t>(particlesPerCell_);
}

const SimulationCell& SimulationGrid::fullCell(std::size_t flatIndex) const
{
    return fullCells_.at(flatIndex);
}

const SimulationCell& SimulationGrid::cellForEvent(std::uint64_t eventId) const
{
    const std::uint64_t activeIndex =
        eventId / static_cast<std::uint64_t>(particlesPerCell_);

    if (activeIndex >= activeFlatIndices_.size())
    {
        throw std::out_of_range{"Geant4 eventID is outside the simulation grid."};
    }

    return fullCells_.at(activeFlatIndices_.at(
        static_cast<std::size_t>(activeIndex)
    ));
}
