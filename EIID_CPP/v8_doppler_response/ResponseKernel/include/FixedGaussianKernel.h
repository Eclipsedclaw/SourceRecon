#ifndef EIID_V8_FIXED_GAUSSIAN_KERNEL_H
#define EIID_V8_FIXED_GAUSSIAN_KERNEL_H

#include "IResponseKernel.h"

class FixedGaussianKernel final : public IResponseKernel
{
public:
    explicit FixedGaussianKernel(Decimal sigmaDegree);

    Decimal evaluate(const ResponseQuery& query) const override;
    std::string_view name() const noexcept override;

private:
    Decimal sigmaDegree_{};
};

#endif
