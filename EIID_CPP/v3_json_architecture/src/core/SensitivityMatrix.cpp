#include "SensitivityMatrix.h"

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace
{
std::size_t checkedProduct(std::size_t left, std::size_t right)
{
    if (left == 0 || right == 0)
    {
        throw std::runtime_error{"SensitivityMatrix dimensions must be positive."};
    }

    if (left > std::numeric_limits<std::size_t>::max() / right)
    {
        throw std::overflow_error{"SensitivityMatrix dimensions overflow size_t."};
    }

    return left * right;
}
}

SensitivityMatrix::SensitivityMatrix(
    std::size_t directionCount,
    std::size_t energyCount
)
    : directionCount_{directionCount},
      energyCount_{energyCount},
      values_(checkedProduct(directionCount, energyCount), static_cast<Decimal>(0.0L)),
      assigned_(values_.size(), static_cast<std::uint8_t>(0))
{}

std::size_t SensitivityMatrix::directionCount() const { return directionCount_; }
std::size_t SensitivityMatrix::energyCount() const { return energyCount_; }
std::size_t SensitivityMatrix::size() const { return values_.size(); }
std::size_t SensitivityMatrix::assignedCount() const { return assignedCount_; }

std::size_t SensitivityMatrix::flatIndex(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    if (directionIndex >= directionCount_ || energyIndex >= energyCount_)
    {
        throw std::out_of_range{"SensitivityMatrix index is outside the configured grid."};
    }

    return directionIndex * energyCount_ + energyIndex;
}

bool SensitivityMatrix::has(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    return assigned_[flatIndex(directionIndex, energyIndex)] != 0;
}

Decimal SensitivityMatrix::at(
    std::size_t directionIndex,
    std::size_t energyIndex
) const
{
    return values_[flatIndex(directionIndex, energyIndex)];
}

Decimal SensitivityMatrix::atFlat(std::size_t index) const
{
    if (index >= values_.size())
    {
        throw std::out_of_range{"Flat sensitivity index is outside the configured grid."};
    }

    return values_[index];
}

void SensitivityMatrix::set(
    std::size_t directionIndex,
    std::size_t energyIndex,
    Decimal value
)
{
    if (!std::isfinite(value) || value < static_cast<Decimal>(0.0L))
    {
        throw std::runtime_error{"Sensitivity values must be finite and non-negative."};
    }

    const std::size_t index = flatIndex(directionIndex, energyIndex);

    if (assigned_[index] != 0)
    {
        throw std::runtime_error{"A sensitivity cell was assigned more than once."};
    }

    values_[index] = value;
    assigned_[index] = static_cast<std::uint8_t>(1);
    ++assignedCount_;
}

void SensitivityMatrix::requireComplete() const
{
    if (assignedCount_ != values_.size())
    {
        throw std::runtime_error{
            "Sensitivity matrix is incomplete: assigned " +
            std::to_string(assignedCount_) + " of " +
            std::to_string(values_.size()) + " cells."
        };
    }
}
