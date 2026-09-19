#ifndef EIID_V9_GAUSSIAN_LORENTZIAN_MIXTURE_FITTER_H
#define EIID_V9_GAUSSIAN_LORENTZIAN_MIXTURE_FITTER_H

#include "IResponseFitter.h"

// This fitter models two event populations with a weighted sum:
//   (1 - eta) * Gaussian + eta * Lorentzian.
// It is deliberately not called a Voigt approximation because the Gaussian
// and Lorentzian widths are independent fit parameters.
class GaussianLorentzianMixtureFitter final : public IResponseFitter
{
public:
    ResponseFitResult fit(TH1D& histogram) const override;
    double density(
        double armDegree,
        const ResponseFitResult& result
    ) const override;
    std::size_t parameterCount() const noexcept override;
    std::string_view name() const noexcept override;
};

#endif
