#ifndef EIID_V9_DOUBLE_GAUSSIAN_FITTER_H
#define EIID_V9_DOUBLE_GAUSSIAN_FITTER_H

#include "IResponseFitter.h"

class DoubleGaussianFitter final : public IResponseFitter
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
