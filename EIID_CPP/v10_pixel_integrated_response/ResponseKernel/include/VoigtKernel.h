#ifndef EIID_V10_VOIGT_KERNEL_H
#define EIID_V10_VOIGT_KERNEL_H

#include "IResponseKernel.h"
#include "KernelParameterTable.h"

class VoigtKernel final : public IResponseKernel
{
public:
    explicit VoigtKernel(KernelParameterTable table);

    Decimal evaluate(const ResponseQuery& query) const override;
    std::string_view name() const noexcept override;

private:
    KernelParameterTable table_;
};

#endif
