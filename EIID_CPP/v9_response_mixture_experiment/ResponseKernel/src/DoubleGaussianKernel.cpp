#include "DoubleGaussianKernel.h"

#include "Common.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace
{
Decimal gaussianDensity(Decimal value, Decimal mean, Decimal sigma)
{
    if (!std::isfinite(sigma) || sigma <= 0.0)
    {
        throw std::runtime_error{"Interpolated Gaussian sigma is invalid."};
    }

    const Decimal standardized = (value - mean) / sigma;
    return std::exp(static_cast<Decimal>(-0.5) * standardized * standardized) /
        (std::sqrt(static_cast<Decimal>(2.0) * PI) * sigma);
}
}

DoubleGaussianKernel::DoubleGaussianKernel(KernelParameterTable table)
    : table_{std::move(table)}
{
}

Decimal DoubleGaussianKernel::evaluate(const ResponseQuery& query) const
{
    const KernelParameters parameters = table_.interpolate(
        query.incidentEnergyMeV,
        query.scatterAngleDegree
    );
    const Decimal weight = std::clamp(
        parameters.doubleGaussianCoreWeight,
        static_cast<Decimal>(0.0),
        static_cast<Decimal>(1.0)
    );
    const Decimal core = gaussianDensity(
        query.deltaThetaDegree,
        parameters.doubleGaussianMeanDegree,
        parameters.doubleGaussianCoreSigmaDegree
    );
    const Decimal tail = gaussianDensity(
        query.deltaThetaDegree,
        parameters.doubleGaussianMeanDegree,
        parameters.doubleGaussianTailSigmaDegree
    );
    return weight * core + (static_cast<Decimal>(1.0) - weight) * tail;
}

std::string_view DoubleGaussianKernel::name() const noexcept
{
    return "double_gaussian";
}
