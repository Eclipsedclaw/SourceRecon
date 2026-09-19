#ifndef EIID_V8_I_RESPONSE_FITTER_H
#define EIID_V8_I_RESPONSE_FITTER_H

#include <cstddef>
#include <string>
#include <string_view>

class TH1D;

struct ResponseFitResult
{
    std::string model;
    bool converged{};
    double meanDegree{};
    double gaussianSigmaDegree{};
    double lorentzFwhmDegree{};
    double coreSigmaDegree{};
    double tailSigmaDegree{};
    double coreWeight{};
};

class IResponseFitter
{
public:
    virtual ~IResponseFitter() = default;
    virtual ResponseFitResult fit(TH1D& histogram) const = 0;
    virtual double density(
        double armDegree,
        const ResponseFitResult& result
    ) const = 0;
    virtual std::size_t parameterCount() const noexcept = 0;
    virtual std::string_view name() const noexcept = 0;
};

#endif
