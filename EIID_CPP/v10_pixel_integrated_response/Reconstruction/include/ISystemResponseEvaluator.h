#ifndef EIID_V10_I_SYSTEM_RESPONSE_EVALUATOR_H
#define EIID_V10_I_SYSTEM_RESPONSE_EVALUATOR_H

#include "PhysicsTypes.h"

#include <cstddef>
#include <string_view>

// Provides only the conditional event-shape term q_ij.  Absolute efficiency
// remains an explicit and separate factor in LM-MLEM: a_ij = s_j * q_ij.
class ISystemResponseEvaluator
{
public:
    virtual ~ISystemResponseEvaluator() = default;

    virtual Decimal evaluate(
        const Event& event,
        const Cell& cell
    ) const = 0;

    virtual std::size_t samplesPerPixel() const noexcept = 0;
    virtual std::string_view name() const noexcept = 0;
};

#endif
