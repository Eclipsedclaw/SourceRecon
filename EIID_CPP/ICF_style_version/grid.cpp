#include "include/grid.h"

#include <cmath>
#include <stdexcept>

Grid::Grid(const Parameter& parameter)
{
    parameter_ = &parameter;

    if (parameter_->directionPointCount <= 0 || parameter_->energyPointCount <= 0)
    {
        throw std::runtime_error{"Grid point counts must be positive."};
    }

    buildDirections();
    buildEnergies();
    buildCells();
}

void Grid::buildDirections()
{
    const int pointCount = parameter_->directionPointCount;
    const Decimal step = pointCount == 1 ? static_cast<Decimal>(0.0L) : (parameter_->directionMaxDegree - parameter_->directionMinDegree) / static_cast<Decimal>(pointCount - 1);

    for (int index = 0; index < pointCount; ++index)
    {
        const Decimal angleDegree = parameter_->directionMinDegree + static_cast<Decimal>(index) * step;
        const Decimal angleRadian = angleDegree * PI / static_cast<Decimal>(180.0L);

        // sourceDirection 指向天空中的源；0 度对应相机正前方 -Z。
        const Vec3 direction{std::sin(angleRadian), static_cast<Decimal>(0.0L), -std::cos(angleRadian)};

        directionAnglesDegree_.push_back(angleDegree);
        directions_.push_back(direction);
    }
}

void Grid::buildEnergies()
{
    const int pointCount = parameter_->energyPointCount;
    const Decimal step = pointCount == 1 ? static_cast<Decimal>(0.0L) : (parameter_->energyMaxMeV - parameter_->energyMinMeV) / static_cast<Decimal>(pointCount - 1);

    for (int index = 0; index < pointCount; ++index)
    {
        const Decimal energyMeV = parameter_->energyMinMeV + static_cast<Decimal>(index) * step;
        energiesMeV_.push_back(energyMeV);
    }
}

void Grid::buildCells()
{
    for (std::size_t directionIndex = 0; directionIndex < directions_.size(); ++directionIndex)
    {
        for (std::size_t energyIndex = 0; energyIndex < energiesMeV_.size(); ++energyIndex)
        {
            const Cell cell{directionIndex, energyIndex, directionAnglesDegree_[directionIndex], directions_[directionIndex], energiesMeV_[energyIndex], parameter_->defaultSensitivity};
            cells_.push_back(cell);
        }
    }
}

const std::vector<Cell>& Grid::cells() const
{
    return cells_;
}

std::size_t Grid::directionCount() const
{
    return directions_.size();
}

std::size_t Grid::energyCount() const
{
    return energiesMeV_.size();
}
