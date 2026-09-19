#include "GaussianLorentzianMixtureFitter.h"

#include "TF1.h"
#include "TFitResult.h"
#include "TFitResultPtr.h"
#include "TH1D.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <numbers>
#include <string>

namespace
{
double gaussianDensity(double value, double mean, double sigma)
{
    const double standardized = (value - mean) / sigma;
    return std::exp(-0.5 * standardized * standardized) /
        (std::sqrt(2.0 * std::numbers::pi) * sigma);
}

double lorentzianDensity(double value, double mean, double fwhm)
{
    const double halfWidth = 0.5 * fwhm;
    const double difference = value - mean;
    return halfWidth /
        (std::numbers::pi * (difference * difference + halfWidth * halfWidth));
}

struct Candidate
{
    bool hasResult{};
    bool valid{};
    double objective{std::numeric_limits<double>::infinity()};
    std::array<double, 5> parameters{};
    int status{-1};
    int covarianceStatus{-1};
    double edm{std::numeric_limits<double>::quiet_NaN()};
    unsigned int calls{};
};

bool isBetter(const Candidate& candidate, const Candidate& current)
{
    if (!candidate.hasResult)
    {
        return false;
    }

    if (!current.hasResult)
    {
        return true;
    }

    if (candidate.valid != current.valid)
    {
        return candidate.valid;
    }

    return candidate.objective < current.objective;
}
}

ResponseFitResult GaussianLorentzianMixtureFitter::fit(TH1D& histogram) const
{
    const double minimum = histogram.GetXaxis()->GetXmin();
    const double maximum = histogram.GetXaxis()->GetXmax();
    const double width = maximum - minimum;
    const double binWidth = histogram.GetBinWidth(1);
    const double normalization = std::max(
        histogram.Integral() * binWidth,
        1.0
    );

    double probabilities[5]{0.10, 0.16, 0.50, 0.84, 0.90};
    double quantiles[5]{};
    histogram.GetQuantiles(5, quantiles, probabilities);
    const double robustMean = quantiles[2];
    const double robustSigma = std::max(
        0.5 * (quantiles[3] - quantiles[1]),
        std::max(0.5 * binWidth, 1.0e-3)
    );
    const double robustTailFwhm = std::max(
        quantiles[4] - quantiles[0],
        2.0 * robustSigma
    );

    const std::array<double, 3> initialWeights{0.10, 0.25, 0.45};
    const std::array<double, 3> tailScale{1.0, 2.0, 4.0};
    Candidate best;

    for (std::size_t attempt = 0; attempt < initialWeights.size(); ++attempt)
    {
        TF1 function{
            ("gaussian_lorentzian_mixture_fit_" +
             std::to_string(attempt)).c_str(),
            [](double* x, double* p)
            {
                const double gaussian = gaussianDensity(x[0], p[1], p[2]);
                const double lorentzian = lorentzianDensity(x[0], p[1], p[3]);
                return p[0] * (
                    (1.0 - p[4]) * gaussian + p[4] * lorentzian
                );
            },
            minimum,
            maximum,
            5
        };
        function.SetParameters(
            normalization,
            robustMean,
            robustSigma,
            robustTailFwhm * tailScale[attempt],
            initialWeights[attempt]
        );
        function.SetParLimits(0, 1.0e-12, 10.0 * normalization);
        function.SetParLimits(1, -0.25 * width, 0.25 * width);
        function.SetParLimits(2, std::max(0.25 * binWidth, 1.0e-4), width);
        function.SetParLimits(3, std::max(0.25 * binWidth, 1.0e-4), 2.0 * width);
        function.SetParLimits(4, 0.001, 0.999);

        const TFitResultPtr fitResult = histogram.Fit(&function, "Q0LNS");
        Candidate candidate;
        candidate.hasResult = fitResult.Get() != nullptr;

        if (candidate.hasResult)
        {
            candidate.objective = fitResult->MinFcnValue();
            candidate.status = fitResult->Status();
            candidate.covarianceStatus = fitResult->CovMatrixStatus();
            candidate.edm = fitResult->Edm();
            candidate.calls = static_cast<unsigned int>(fitResult->NCalls());

            for (std::size_t parameter = 0;
                 parameter < candidate.parameters.size();
                 ++parameter)
            {
                candidate.parameters[parameter] =
                    function.GetParameter(static_cast<int>(parameter));
            }

            candidate.valid = fitResult->IsValid() &&
                candidate.status == 0 &&
                candidate.covarianceStatus >= 2 &&
                std::isfinite(candidate.objective) &&
                std::isfinite(candidate.edm) &&
                std::all_of(
                    candidate.parameters.begin(),
                    candidate.parameters.end(),
                    [](double value) { return std::isfinite(value); }
                );
        }

        if (isBetter(candidate, best))
        {
            best = candidate;
        }
    }

    ResponseFitResult result;
    result.model = "gaussian_lorentzian_mixture";
    result.converged = best.hasResult && best.valid;
    result.fitStatus = best.status;
    result.covarianceStatus = best.covarianceStatus;
    result.estimatedDistanceToMinimum = best.edm;
    result.functionCalls = best.calls;
    result.meanDegree = best.parameters[1];
    result.gaussianLorentzianSigmaDegree = std::max(
        best.parameters[2],
        1.0e-4
    );
    result.gaussianLorentzianLorentzFwhmDegree = std::max(
        best.parameters[3],
        1.0e-4
    );
    result.gaussianLorentzianLorentzWeight = std::clamp(
        best.parameters[4],
        0.0,
        1.0
    );
    return result;
}

double GaussianLorentzianMixtureFitter::density(
    double armDegree,
    const ResponseFitResult& result
) const
{
    const double weight = std::clamp(
        result.gaussianLorentzianLorentzWeight,
        0.0,
        1.0
    );
    return (1.0 - weight) * gaussianDensity(
        armDegree,
        result.meanDegree,
        result.gaussianLorentzianSigmaDegree
    ) + weight * lorentzianDensity(
        armDegree,
        result.meanDegree,
        result.gaussianLorentzianLorentzFwhmDegree
    );
}

std::size_t GaussianLorentzianMixtureFitter::parameterCount() const noexcept
{
    return 4;
}

std::string_view GaussianLorentzianMixtureFitter::name() const noexcept
{
    return "gaussian_lorentzian_mixture";
}
