#include "FixedGaussianKernel.h"

#include "Common.h"

#include <cmath>
#include <stdexcept>

namespace
{
Decimal gaussianDensity(Decimal value, Decimal mean, Decimal sigma)
{
    const Decimal standardized = (value - mean) / sigma;
    return std::exp(static_cast<Decimal>(-0.5) * standardized * standardized) /
        (std::sqrt(static_cast<Decimal>(2.0) * PI) * sigma);
}
}

FixedGaussianKernel::FixedGaussianKernel(Decimal sigmaDegree)
    : sigmaDegree_{sigmaDegree}
{
    if (!std::isfinite(sigmaDegree_) || sigmaDegree_ <= 0.0)
    {
        throw std::invalid_argument{"Fixed Gaussian sigma must be positive."};
    }
}

Decimal FixedGaussianKernel::evaluate(const ResponseQuery& query) const
{
    return gaussianDensity(query.deltaThetaDegree, 0.0, sigmaDegree_);
}

std::string_view FixedGaussianKernel::name() const noexcept
{
    return "fixed_gaussian";
}
