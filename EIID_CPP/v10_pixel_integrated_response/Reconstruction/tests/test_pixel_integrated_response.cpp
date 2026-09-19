#include "EiidResponse.h"
#include "IPixelDirectionSampler.h"
#include "IResponseKernel.h"
#include "PixelIntegratedResponseEvaluator.h"
#include "ReconConfig.h"

#include <cassert>
#include <cmath>
#include <memory>
#include <span>
#include <string_view>
#include <utility>
#include <vector>

namespace
{
class TwoDirectionSampler final : public IPixelDirectionSampler
{
public:
    TwoDirectionSampler()
        : directions_{
              Vec3{0.0, 0.0, -1.0},
              Vec3{-std::sqrt(3.0) / 2.0, 0.0, -0.5}
          }
    {
    }

    std::span<const Vec3> directions(std::size_t index) const override
    {
        assert(index == 0);
        return directions_;
    }

    int reconstructionNside() const noexcept override
    {
        return 1;
    }

    int integrationNside() const noexcept override
    {
        return 1;
    }

    std::size_t directionCount() const noexcept override
    {
        return 1;
    }

    std::size_t samplesPerPixel() const noexcept override
    {
        return 2;
    }

    std::string_view name() const noexcept override
    {
        return "two_test_points";
    }

private:
    std::vector<Vec3> directions_;
};

class QuadraticResidualKernel final : public IResponseKernel
{
public:
    Decimal evaluate(const ResponseQuery& query) const override
    {
        return 1.0 +
            query.deltaThetaDegree * query.deltaThetaDegree;
    }

    std::string_view name() const noexcept override
    {
        return "quadratic_test_kernel";
    }
};
}

int main()
{
    const ReconConfig config{"tests/lm_mlem_test_config.json"};
    const QuadraticResidualKernel kernel;
    const Event event{
        Vec3{0.0, 0.0, 0.0},
        Vec3{0.0, 0.0, 1.0},
        0.338
    };
    const Cell cell{0, 0, 0, 0.0, 0.0, Vec3{0.0, 0.0, -1.0}, 1.0};

    auto sampler = std::make_unique<TwoDirectionSampler>();
    const std::vector<Vec3> directions{
        sampler->directions(0).begin(),
        sampler->directions(0).end()
    };
    const PixelIntegratedResponseEvaluator evaluator{
        config,
        kernel,
        std::move(sampler)
    };

    Decimal expected{};

    for (const Vec3& direction : directions)
    {
        expected += calculateDirectionalResponse(
            event,
            cell.energyMeV,
            direction,
            config,
            kernel
        );
    }

    expected /= static_cast<Decimal>(directions.size());
    const Decimal actual = evaluator.evaluate(event, cell);

    assert(evaluator.samplesPerPixel() == 2);
    assert(std::abs(actual - expected) < 1.0e-12);
    return 0;
}
