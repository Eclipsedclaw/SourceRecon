#include "GaussianLorentzianMixtureKernel.h"

#include "Common.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace
{
Decimal gaussianDensity(Decimal value, Decimal mean, Decimal sigma)
{
    const Decimal standardized = (value - mean) / sigma;
    return std::exp(static_cast<Decimal>(-0.5) * standardized * standardized) /
        (std::sqrt(static_cast<Decimal>(2.0) * PI) * sigma);
}

Decimal lorentzianDensity(Decimal value, Decimal mean, Decimal fwhm)
{
    const Decimal halfWidth = static_cast<Decimal>(0.5) * fwhm;
    const Decimal difference = value - mean;
    return halfWidth /
        (PI * (difference * difference + halfWidth * halfWidth));
}
}

GaussianLorentzianMixtureKernel::GaussianLorentzianMixtureKernel(
    KernelParameterTable table
)
    : table_{std::move(table)}
{
}

Decimal GaussianLorentzianMixtureKernel::evaluate(
    const ResponseQuery& query
) const
{
    const KernelParameters parameters = table_.interpolate(
        query.incidentEnergyMeV,
        query.scatterAngleDegree
    );

    if (!std::isfinite(parameters.gaussianLorentzianSigmaDegree) ||
        parameters.gaussianLorentzianSigmaDegree <= 0.0 ||
        !std::isfinite(parameters.gaussianLorentzianLorentzFwhmDegree) ||
        parameters.gaussianLorentzianLorentzFwhmDegree <= 0.0)
    {
        throw std::runtime_error{
            "Interpolated Gaussian-Lorentzian mixture widths are invalid."
        };
    }

    const Decimal weight = std::clamp(
        parameters.gaussianLorentzianLorentzWeight,
        static_cast<Decimal>(0.0),
        static_cast<Decimal>(1.0)
    );
    const Decimal gaussian = gaussianDensity(
        query.deltaThetaDegree,
        parameters.gaussianLorentzianMeanDegree,
        parameters.gaussianLorentzianSigmaDegree
    );
    const Decimal lorentzian = lorentzianDensity(
        query.deltaThetaDegree,
        parameters.gaussianLorentzianMeanDegree,
        parameters.gaussianLorentzianLorentzFwhmDegree
    );
    return (static_cast<Decimal>(1.0) - weight) * gaussian +
        weight * lorentzian;
}

std::string_view GaussianLorentzianMixtureKernel::name() const noexcept
{
    return "gaussian_lorentzian_mixture";
}
