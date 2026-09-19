#include "DoubleGaussianFitter.h"

#include "TF1.h"
#include "TFitResult.h"
#include "TFitResultPtr.h"
#include "TH1D.h"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <utility>

namespace
{
double gaussian(double value, double mean, double sigma)
{
    const double z = (value - mean) / sigma;
    return std::exp(-0.5 * z * z) /
        (std::sqrt(2.0 * std::numbers::pi) * sigma);
}
}

ResponseFitResult DoubleGaussianFitter::fit(TH1D& histogram) const
{
    const double width = histogram.GetXaxis()->GetXmax() -
        histogram.GetXaxis()->GetXmin();
    const double rms = std::max(histogram.GetRMS(), 0.05);
    const double normalization = std::max(
        histogram.Integral() * histogram.GetBinWidth(1),
        1.0
    );
    TF1 function{
        "double_gaussian_calibration_fit",
        [](double* x, double* p)
        {
            const double core = gaussian(x[0], p[1], p[2]);
            const double tail = gaussian(x[0], p[1], p[3]);
            return p[0] * (p[4] * core + (1.0 - p[4]) * tail);
        },
        histogram.GetXaxis()->GetXmin(),
        histogram.GetXaxis()->GetXmax(),
        5
    };
    function.SetParameters(
        normalization,
        histogram.GetMean(),
        0.45 * rms,
        1.8 * rms,
        0.75
    );
    function.SetParLimits(1, -0.25 * width, 0.25 * width);
    function.SetParLimits(2, 1.0e-4, width);
    function.SetParLimits(3, 1.0e-4, 2.0 * width);
    function.SetParLimits(4, 0.001, 0.999);

    // Use the same Poisson likelihood as the Voigt fit so both models are
    // compared under identical sparse-count assumptions.
    const TFitResultPtr status = histogram.Fit(&function, "Q0LS");
    double coreSigma = std::max(function.GetParameter(2), 1.0e-4);
    double tailSigma = std::max(function.GetParameter(3), 1.0e-4);
    double coreWeight = std::clamp(function.GetParameter(4), 0.0, 1.0);

    if (tailSigma < coreSigma)
    {
        std::swap(coreSigma, tailSigma);
        coreWeight = 1.0 - coreWeight;
    }

    return ResponseFitResult{
        "double_gaussian",
        status.Get() != nullptr && status->IsValid(),
        function.GetParameter(1),
        0.0,
        0.0,
        coreSigma,
        tailSigma,
        coreWeight
    };
}

double DoubleGaussianFitter::density(
    double armDegree,
    const ResponseFitResult& result
) const
{
    return result.coreWeight * gaussian(
        armDegree,
        result.meanDegree,
        result.coreSigmaDegree
    ) + (1.0 - result.coreWeight) * gaussian(
        armDegree,
        result.meanDegree,
        result.tailSigmaDegree
    );
}

std::size_t DoubleGaussianFitter::parameterCount() const noexcept { return 4; }
std::string_view DoubleGaussianFitter::name() const noexcept { return "double_gaussian"; }
