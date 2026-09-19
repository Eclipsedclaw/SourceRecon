#include "PointSystemResponseEvaluator.h"

#include "EiidResponse.h"
#include "ReconConfig.h"

PointSystemResponseEvaluator::PointSystemResponseEvaluator(
    const ReconConfig& config,
    const IResponseKernel& responseKernel
)
    : config_{&config},
      responseKernel_{&responseKernel}
{
}

Decimal PointSystemResponseEvaluator::evaluate(
    const Event& event,
    const Cell& cell
) const
{
    return calculateResponse(event, cell, *config_, *responseKernel_);
}

std::size_t PointSystemResponseEvaluator::samplesPerPixel() const noexcept
{
    return 1;
}

std::string_view PointSystemResponseEvaluator::name() const noexcept
{
    return "pixel_center";
}
