#include "PixelIntegratedResponseEvaluator.h"

#include "EiidResponse.h"
#include "IPixelDirectionSampler.h"
#include "ReconConfig.h"

#include <stdexcept>
#include <utility>

PixelIntegratedResponseEvaluator::PixelIntegratedResponseEvaluator(
    const ReconConfig& config,
    const IResponseKernel& responseKernel,
    std::unique_ptr<IPixelDirectionSampler> sampler
)
    : config_{&config},
      responseKernel_{&responseKernel},
      sampler_{std::move(sampler)}
{
    if (!sampler_ || sampler_->samplesPerPixel() == 0)
    {
        throw std::runtime_error{
            "Pixel-integrated response requires a non-empty direction sampler."
        };
    }
}

PixelIntegratedResponseEvaluator::~PixelIntegratedResponseEvaluator() = default;

Decimal PixelIntegratedResponseEvaluator::evaluate(
    const Event& event,
    const Cell& cell
) const
{
    const auto directions = sampler_->directions(cell.directionIndex);
    Decimal sum = static_cast<Decimal>(0.0);

    for (const Vec3& direction : directions)
    {
        sum += calculateDirectionalResponse(
            event,
            cell.energyMeV,
            direction,
            *config_,
            *responseKernel_
        );
    }

    return sum / static_cast<Decimal>(directions.size());
}

std::size_t PixelIntegratedResponseEvaluator::samplesPerPixel() const noexcept
{
    return sampler_->samplesPerPixel();
}

std::string_view PixelIntegratedResponseEvaluator::name() const noexcept
{
    return sampler_->name();
}
