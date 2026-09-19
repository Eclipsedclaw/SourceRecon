#include "VoigtFitter.h"

#include "TF1.h"
#include "TFitResult.h"
#include "TFitResultPtr.h"
#include "TH1D.h"
#include "TMath.h"

#include <algorithm>
#include <cmath>

ResponseFitResult VoigtFitter::fit(TH1D& histogram) const
{
    const double width = histogram.GetXaxis()->GetXmax() -
        histogram.GetXaxis()->GetXmin();
    const double rms = std::max(histogram.GetRMS(), 0.05);
    const double normalization = std::max(
        histogram.Integral() * histogram.GetBinWidth(1),
        1.0
    );
    TF1 function{
        "voigt_calibration_fit",
        "[0]*TMath::Voigt(x-[1],[2],[3],4)",
        histogram.GetXaxis()->GetXmin(),
        histogram.GetXaxis()->GetXmax()
    };
    function.SetParameters(normalization, histogram.GetMean(), 0.6 * rms, rms);
    function.SetParLimits(1, -0.25 * width, 0.25 * width);
    function.SetParLimits(2, 1.0e-4, width);
    function.SetParLimits(3, 0.0, 2.0 * width);

    // Calibration histograms contain only a few hundred selected events at
    // some energies, so many fine ARM bins are empty. A Poisson binned
    // likelihood (L) is appropriate for these sparse counts; the default
    // chi-square fit would be unreliable in this regime.
    const TFitResultPtr status = histogram.Fit(&function, "Q0LS");

    ResponseFitResult result;
    result.model = "voigt";
    result.meanDegree = function.GetParameter(1);
    result.gaussianSigmaDegree = std::max(
        function.GetParameter(2),
        1.0e-4
    );
    result.lorentzFwhmDegree = std::max(function.GetParameter(3), 0.0);

    if (status.Get() != nullptr)
    {
        result.fitStatus = status->Status();
        result.covarianceStatus = status->CovMatrixStatus();
        result.estimatedDistanceToMinimum = status->Edm();
        result.functionCalls = static_cast<unsigned int>(status->NCalls());
    }

    result.converged = status.Get() != nullptr &&
        status->IsValid() &&
        result.fitStatus == 0 &&
        result.covarianceStatus >= 2 &&
        std::isfinite(result.estimatedDistanceToMinimum) &&
        std::isfinite(result.meanDegree) &&
        std::isfinite(result.gaussianSigmaDegree) &&
        std::isfinite(result.lorentzFwhmDegree);

    return result;
}

double VoigtFitter::density(
    double armDegree,
    const ResponseFitResult& result
) const
{
    return TMath::Voigt(
        armDegree - result.meanDegree,
        result.gaussianSigmaDegree,
        result.lorentzFwhmDegree,
        4
    );
}

std::size_t VoigtFitter::parameterCount() const noexcept { return 3; }
std::string_view VoigtFitter::name() const noexcept { return "voigt"; }
