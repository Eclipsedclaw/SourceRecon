#ifndef EIID_V9_GAUSSIAN_LORENTZIAN_MIXTURE_KERNEL_H
#define EIID_V9_GAUSSIAN_LORENTZIAN_MIXTURE_KERNEL_H

#include "IResponseKernel.h"
#include "KernelParameterTable.h"

class GaussianLorentzianMixtureKernel final : public IResponseKernel
{
public:
    explicit GaussianLorentzianMixtureKernel(KernelParameterTable table);

    Decimal evaluate(const ResponseQuery& query) const override;
    std::string_view name() const noexcept override;

private:
    KernelParameterTable table_;
};

#endif
