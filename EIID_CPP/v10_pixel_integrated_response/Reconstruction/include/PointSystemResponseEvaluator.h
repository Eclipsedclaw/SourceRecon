#ifndef EIID_V10_POINT_SYSTEM_RESPONSE_EVALUATOR_H
#define EIID_V10_POINT_SYSTEM_RESPONSE_EVALUATOR_H

#include "ISystemResponseEvaluator.h"

class ReconConfig;
class IResponseKernel;

// Historical centre-point response, retained as the scientific control group.
class PointSystemResponseEvaluator final : public ISystemResponseEvaluator
{
public:
    PointSystemResponseEvaluator(
        const ReconConfig& config,
        const IResponseKernel& responseKernel
    );

    Decimal evaluate(
        const Event& event,
        const Cell& cell
    ) const override;

    std::size_t samplesPerPixel() const noexcept override;
    std::string_view name() const noexcept override;

private:
    const ReconConfig* config_{};
    const IResponseKernel* responseKernel_{};
};

#endif
