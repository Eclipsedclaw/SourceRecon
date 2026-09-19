#ifndef EIID_V9_I_RESPONSE_KERNEL_H
#define EIID_V9_I_RESPONSE_KERNEL_H

#include "ResponseQuery.h"

#include <string_view>

class IResponseKernel
{
public:
    virtual ~IResponseKernel() = default;

    // Return a normalized ARM probability density in inverse degrees.
    virtual Decimal evaluate(const ResponseQuery& query) const = 0;
    virtual std::string_view name() const noexcept = 0;
};

#endif
