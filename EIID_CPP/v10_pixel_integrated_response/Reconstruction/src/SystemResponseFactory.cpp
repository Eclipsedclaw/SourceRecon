#include "SystemResponseFactory.h"

#include "HealpixSubpixelSampler.h"
#include "IGrid.h"
#include "ISystemResponseEvaluator.h"
#include "PixelIntegratedResponseEvaluator.h"
#include "PointSystemResponseEvaluator.h"
#include "ReconConfig.h"

#include <memory>
#include <stdexcept>

std::unique_ptr<ISystemResponseEvaluator> SystemResponseFactory::create(
    const ReconConfig& config,
    const IGrid& grid,
    const IResponseKernel& responseKernel
)
{
    const PixelIntegrationConfig& integration = config.pixelIntegration();

    if (integration.strategy == "pixel_center")
    {
        return std::make_unique<PointSystemResponseEvaluator>(
            config,
            responseKernel
        );
    }

    auto sampler = std::make_unique<HealpixSubpixelSampler>(
        grid.healpixNside(),
        integration.integrationNside
    );

    if (sampler->directionCount() != grid.directionCount())
    {
        throw std::runtime_error{
            "Pixel sampler dimensions do not match the reconstruction grid."
        };
    }

    return std::make_unique<PixelIntegratedResponseEvaluator>(
        config,
        responseKernel,
        std::move(sampler)
    );
}
