#ifndef EIID_V10_PIXEL_INTEGRATED_RESPONSE_EVALUATOR_H
#define EIID_V10_PIXEL_INTEGRATED_RESPONSE_EVALUATOR_H

#include "ISystemResponseEvaluator.h"

#include <memory>

class IPixelDirectionSampler;
class ReconConfig;
class IResponseKernel;

// Approximates the response averaged over a parent pixel:
// q_bar = (1/M) * sum_k q(direction_k).
class PixelIntegratedResponseEvaluator final :
    public ISystemResponseEvaluator
{
public:
    PixelIntegratedResponseEvaluator(
        const ReconConfig& config,
        const IResponseKernel& responseKernel,
        std::unique_ptr<IPixelDirectionSampler> sampler
    );

    ~PixelIntegratedResponseEvaluator() override;

    Decimal evaluate(
        const Event& event,
        const Cell& cell
    ) const override;

    std::size_t samplesPerPixel() const noexcept override;
    std::string_view name() const noexcept override;

private:
    const ReconConfig* config_{};
    const IResponseKernel* responseKernel_{};
    std::unique_ptr<IPixelDirectionSampler> sampler_;
};

#endif
