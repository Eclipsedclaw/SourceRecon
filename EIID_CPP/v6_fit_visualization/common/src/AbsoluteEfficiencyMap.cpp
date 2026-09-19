#include "AbsoluteEfficiencyMap.h"

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace
{
std::size_t checkedSize(std::size_t directions, std::size_t energies)
{
    if (directions == 0 || energies == 0 ||
        directions > std::numeric_limits<std::size_t>::max() / energies)
    {
        throw std::runtime_error{"AbsoluteEfficiencyMap dimensions are invalid."};
    }

    return directions * energies;
}
}

AbsoluteEfficiencyMap::AbsoluteEfficiencyMap(
    std::size_t directionCount,
    std::size_t energyCount
)
    : directionCount_{directionCount},
      energyCount_{energyCount},
      values_(checkedSize(directionCount, energyCount), static_cast<Decimal>(0.0)),
      assigned_(values_.size(), static_cast<std::uint8_t>(0))
{
}

std::size_t AbsoluteEfficiencyMap::directionCount() const { return directionCount_; }
std::size_t AbsoluteEfficiencyMap::energyCount() const { return energyCount_; }
std::size_t AbsoluteEfficiencyMap::size() const { return values_.size(); }

std::size_t AbsoluteEfficiencyMap::flatIndex(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    if (directionIndex >= directionCount_ || energyIndex >= energyCount_)
    {
        throw std::out_of_range{"Absolute-efficiency index is outside the grid."};
    }

    return directionIndex * energyCount_ + energyIndex;
}

Decimal AbsoluteEfficiencyMap::at(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    return atFlat(flatIndex(directionIndex, energyIndex));
}

Decimal AbsoluteEfficiencyMap::atFlat(std::size_t index) const
{
    if (index >= values_.size())
    {
        throw std::out_of_range{"Flat absolute-efficiency index is out of range."};
    }

    return values_[index];
}

void AbsoluteEfficiencyMap::set(
    std::size_t directionIndex,
    std::size_t energyIndex,
    Decimal value
)
{
    setFlat(flatIndex(directionIndex, energyIndex), value);
}

void AbsoluteEfficiencyMap::setFlat(std::size_t index, Decimal value)
{
    if (index >= values_.size())
    {
        throw std::out_of_range{"Flat absolute-efficiency index is out of range."};
    }

    if (!std::isfinite(value) || value < static_cast<Decimal>(0.0) ||
        value > static_cast<Decimal>(1.0))
    {
        throw std::runtime_error{"Absolute efficiency must be finite and within [0, 1]."};
    }

    if (assigned_[index] != 0)
    {
        throw std::runtime_error{"An absolute-efficiency cell was assigned twice."};
    }

    values_[index] = value;
    assigned_[index] = static_cast<std::uint8_t>(1);
    ++assignedCount_;
}

void AbsoluteEfficiencyMap::requireComplete() const
{
    if (assignedCount_ != values_.size())
    {
        throw std::runtime_error{
            "Absolute-efficiency map is incomplete: " +
            std::to_string(assignedCount_) + " of " +
            std::to_string(values_.size()) + " cells were assigned."
        };
    }
}
