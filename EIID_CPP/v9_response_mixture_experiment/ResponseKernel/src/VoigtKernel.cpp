#include "VoigtKernel.h"

#include "TMath.h"

#include <cmath>
#include <stdexcept>
#include <utility>

VoigtKernel::VoigtKernel(KernelParameterTable table)
    : table_{std::move(table)}
{
}

Decimal VoigtKernel::evaluate(const ResponseQuery& query) const
{
    const KernelParameters parameters = table_.interpolate(
        query.incidentEnergyMeV,
        query.scatterAngleDegree
    );

    if (!std::isfinite(parameters.voigtGaussianSigmaDegree) ||
        parameters.voigtGaussianSigmaDegree <= 0.0 ||
        !std::isfinite(parameters.voigtLorentzFwhmDegree) ||
        parameters.voigtLorentzFwhmDegree < 0.0)
    {
        throw std::runtime_error{"Interpolated Voigt widths are invalid."};
    }

    // ROOT defines lg as the Lorentzian full width at half maximum.  TMath's
    // implementation is normalized, so changing widths does not introduce an
    // artificial source-intensity bias into q_ij.
    return static_cast<Decimal>(TMath::Voigt(
        query.deltaThetaDegree - parameters.voigtMeanDegree,
        parameters.voigtGaussianSigmaDegree,
        parameters.voigtLorentzFwhmDegree,
        4
    ));
}

std::string_view VoigtKernel::name() const noexcept
{
    return "voigt";
}
