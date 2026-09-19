#include "KernelParameterTable.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace
{
bool sameCoordinate(Decimal left, Decimal right)
{
    const Decimal scale = std::max(
        static_cast<Decimal>(1.0),
        std::max(std::abs(left), std::abs(right))
    );
    return std::abs(left - right) <=
        static_cast<Decimal>(1.0e-10) * scale;
}

void addUnique(std::vector<Decimal>& values, Decimal value)
{
    const auto found = std::find_if(
        values.begin(),
        values.end(),
        [value](Decimal candidate)
        {
            return sameCoordinate(candidate, value);
        }
    );

    if (found == values.end())
    {
        values.push_back(value);
    }
}

std::pair<std::size_t, std::size_t> bracket(
    const std::vector<Decimal>& coordinates,
    Decimal value
)
{
    if (coordinates.empty())
    {
        throw std::logic_error{"Cannot bracket an empty coordinate axis."};
    }

    if (value <= coordinates.front())
    {
        return {0, 0};
    }

    if (value >= coordinates.back())
    {
        const std::size_t last = coordinates.size() - 1;
        return {last, last};
    }

    const auto upper = std::upper_bound(
        coordinates.begin(),
        coordinates.end(),
        value
    );
    const std::size_t high = static_cast<std::size_t>(
        std::distance(coordinates.begin(), upper)
    );
    return {high - 1, high};
}

Decimal fraction(Decimal low, Decimal high, Decimal value)
{
    return sameCoordinate(low, high)
        ? static_cast<Decimal>(0.0)
        : (value - low) / (high - low);
}

Decimal lerp(Decimal left, Decimal right, Decimal weight)
{
    return left + weight * (right - left);
}

KernelParameters lerpParameters(
    const KernelParameters& left,
    const KernelParameters& right,
    Decimal weight
)
{
    KernelParameters result;
    result.energyMeV = lerp(left.energyMeV, right.energyMeV, weight);
    result.scatterAngleDegree = lerp(
        left.scatterAngleDegree,
        right.scatterAngleDegree,
        weight
    );
    result.voigtMeanDegree = lerp(
        left.voigtMeanDegree,
        right.voigtMeanDegree,
        weight
    );
    result.voigtGaussianSigmaDegree = lerp(
        left.voigtGaussianSigmaDegree,
        right.voigtGaussianSigmaDegree,
        weight
    );
    result.voigtLorentzFwhmDegree = lerp(
        left.voigtLorentzFwhmDegree,
        right.voigtLorentzFwhmDegree,
        weight
    );
    result.doubleGaussianMeanDegree = lerp(
        left.doubleGaussianMeanDegree,
        right.doubleGaussianMeanDegree,
        weight
    );
    result.doubleGaussianCoreSigmaDegree = lerp(
        left.doubleGaussianCoreSigmaDegree,
        right.doubleGaussianCoreSigmaDegree,
        weight
    );
    result.doubleGaussianTailSigmaDegree = lerp(
        left.doubleGaussianTailSigmaDegree,
        right.doubleGaussianTailSigmaDegree,
        weight
    );
    result.doubleGaussianCoreWeight = lerp(
        left.doubleGaussianCoreWeight,
        right.doubleGaussianCoreWeight,
        weight
    );
    result.gaussianLorentzianMeanDegree = lerp(
        left.gaussianLorentzianMeanDegree,
        right.gaussianLorentzianMeanDegree,
        weight
    );
    result.gaussianLorentzianSigmaDegree = lerp(
        left.gaussianLorentzianSigmaDegree,
        right.gaussianLorentzianSigmaDegree,
        weight
    );
    result.gaussianLorentzianLorentzFwhmDegree = lerp(
        left.gaussianLorentzianLorentzFwhmDegree,
        right.gaussianLorentzianLorentzFwhmDegree,
        weight
    );
    result.gaussianLorentzianLorentzWeight = lerp(
        left.gaussianLorentzianLorentzWeight,
        right.gaussianLorentzianLorentzWeight,
        weight
    );
    return result;
}
}

void KernelParameterTable::add(const KernelParameters& parameters)
{
    if (finalized_)
    {
        throw std::logic_error{"Cannot add rows after parameter-table finalization."};
    }

    pending_.push_back(parameters);
}

void KernelParameterTable::finalize()
{
    if (finalized_)
    {
        return;
    }

    if (pending_.empty())
    {
        throw std::runtime_error{"The response parameter table is empty."};
    }

    for (const KernelParameters& row : pending_)
    {
        if (!std::isfinite(row.energyMeV) || row.energyMeV <= 0.0 ||
            !std::isfinite(row.scatterAngleDegree) ||
            row.scatterAngleDegree < 0.0 || row.scatterAngleDegree > 180.0)
        {
            throw std::runtime_error{"A response-table coordinate is invalid."};
        }

        if (!std::isfinite(row.voigtMeanDegree) ||
            !std::isfinite(row.voigtGaussianSigmaDegree) ||
            row.voigtGaussianSigmaDegree <= 0.0 ||
            !std::isfinite(row.voigtLorentzFwhmDegree) ||
            row.voigtLorentzFwhmDegree < 0.0 ||
            !std::isfinite(row.doubleGaussianMeanDegree) ||
            !std::isfinite(row.doubleGaussianCoreSigmaDegree) ||
            row.doubleGaussianCoreSigmaDegree <= 0.0 ||
            !std::isfinite(row.doubleGaussianTailSigmaDegree) ||
            row.doubleGaussianTailSigmaDegree <= 0.0 ||
            !std::isfinite(row.doubleGaussianCoreWeight) ||
            row.doubleGaussianCoreWeight < 0.0 ||
            row.doubleGaussianCoreWeight > 1.0 ||
            !std::isfinite(row.gaussianLorentzianMeanDegree) ||
            !std::isfinite(row.gaussianLorentzianSigmaDegree) ||
            row.gaussianLorentzianSigmaDegree <= 0.0 ||
            !std::isfinite(row.gaussianLorentzianLorentzFwhmDegree) ||
            row.gaussianLorentzianLorentzFwhmDegree <= 0.0 ||
            !std::isfinite(row.gaussianLorentzianLorentzWeight) ||
            row.gaussianLorentzianLorentzWeight < 0.0 ||
            row.gaussianLorentzianLorentzWeight > 1.0)
        {
            throw std::runtime_error{"A response-table model parameter is invalid."};
        }

        addUnique(energies_, row.energyMeV);
        addUnique(angles_, row.scatterAngleDegree);
    }

    std::sort(energies_.begin(), energies_.end());
    std::sort(angles_.begin(), angles_.end());
    grid_.resize(energies_.size() * angles_.size());
    std::vector<bool> filled(grid_.size(), false);

    for (const KernelParameters& row : pending_)
    {
        const auto energy = std::find_if(
            energies_.begin(), energies_.end(),
            [&row](Decimal value) { return sameCoordinate(value, row.energyMeV); }
        );
        const auto angle = std::find_if(
            angles_.begin(), angles_.end(),
            [&row](Decimal value)
            {
                return sameCoordinate(value, row.scatterAngleDegree);
            }
        );
        const std::size_t index = flatIndex(
            static_cast<std::size_t>(std::distance(energies_.begin(), energy)),
            static_cast<std::size_t>(std::distance(angles_.begin(), angle))
        );

        if (filled[index])
        {
            throw std::runtime_error{"Duplicate energy/angle response-table row."};
        }

        grid_[index] = row;
        filled[index] = true;
    }

    if (std::find(filled.begin(), filled.end(), false) != filled.end())
    {
        throw std::runtime_error{
            "Response parameter rows do not form a complete rectangular grid."
        };
    }

    pending_.clear();
    finalized_ = true;
}

KernelParameters KernelParameterTable::interpolate(
    Decimal energyMeV,
    Decimal scatterAngleDegree
) const
{
    if (!finalized_)
    {
        throw std::logic_error{"Parameter table must be finalized before use."};
    }

    const auto [energyLow, energyHigh] = bracket(energies_, energyMeV);
    const auto [angleLow, angleHigh] = bracket(angles_, scatterAngleDegree);
    const Decimal energyWeight = fraction(
        energies_[energyLow], energies_[energyHigh], energyMeV
    );
    const Decimal angleWeight = fraction(
        angles_[angleLow], angles_[angleHigh], scatterAngleDegree
    );

    const KernelParameters lowAngle = lerpParameters(
        grid_[flatIndex(energyLow, angleLow)],
        grid_[flatIndex(energyHigh, angleLow)],
        energyWeight
    );
    const KernelParameters highAngle = lerpParameters(
        grid_[flatIndex(energyLow, angleHigh)],
        grid_[flatIndex(energyHigh, angleHigh)],
        energyWeight
    );
    KernelParameters result = lerpParameters(
        lowAngle,
        highAngle,
        angleWeight
    );
    result.energyMeV = energyMeV;
    result.scatterAngleDegree = scatterAngleDegree;
    return result;
}

bool KernelParameterTable::empty() const noexcept
{
    return pending_.empty() && grid_.empty();
}

std::size_t KernelParameterTable::energyCount() const noexcept
{
    return energies_.size();
}

std::size_t KernelParameterTable::angleCount() const noexcept
{
    return angles_.size();
}

std::size_t KernelParameterTable::flatIndex(
    std::size_t energyIndex,
    std::size_t angleIndex
) const
{
    return energyIndex * angles_.size() + angleIndex;
}
