#include "AbsoluteEfficiencyMap.h"
#include "IGrid.h"
#include "ISystemResponseEvaluator.h"
#include "LmMlemSolver.h"
#include "ReconConfig.h"

#include <cassert>
#include <cmath>
#include <cstddef>
#include <vector>

namespace
{
class TwoCellGrid final : public IGrid
{
public:
    TwoCellGrid()
        : directions_{
              Vec3{0.0, 0.0, -1.0},
              Vec3{0.0, 0.0, -1.0}
          },
          cells_{
              Cell{0, 0, 0, 180.0, 0.0, directions_[0], 1.0},
              Cell{1, 0, 1, 180.0, 0.0, directions_[1], 1.0}
          }
    {
    }

    const std::vector<Cell>& cells() const override { return cells_; }

    const Cell& cell(
        std::size_t directionIndex,
        std::size_t energyIndex
    ) const override
    {
        assert(energyIndex == 0);
        return cells_.at(directionIndex);
    }

    const Vec3& direction(std::size_t index) const override
    {
        return directions_.at(index);
    }

    Decimal energy(std::size_t index) const override
    {
        assert(index == 0);
        return 1.0;
    }

    int healpixNside() const override { return 1; }
    std::size_t directionCount() const override { return 2; }
    std::size_t energyCount() const override { return 1; }

private:
    std::vector<Vec3> directions_;
    std::vector<Cell> cells_;
};

class UnitResponseEvaluator final : public ISystemResponseEvaluator
{
public:
    Decimal evaluate(const Event&, const Cell&) const override
    {
        return 1.0;
    }

    std::size_t samplesPerPixel() const noexcept override
    {
        return 1;
    }

    std::string_view name() const noexcept override
    {
        return "unit_test_response";
    }
};
}

int main()
{
    const TwoCellGrid grid;
    AbsoluteEfficiencyMap efficiency{2, 1};
    efficiency.set(0, 0, 0.25);
    efficiency.set(1, 0, 0.75);
    efficiency.requireComplete();

    const ReconConfig config{"tests/lm_mlem_test_config.json"};
    const UnitResponseEvaluator responseEvaluator;
    const LmMlemSolver solver{grid, efficiency, config, responseEvaluator};

    // Both cells have identical q_ij, but different efficiencies.  With the
    // complete a_ij = efficiency_j * q_ij response in the prediction, the
    // efficiency in the numerator cancels the final MLEM normalization and
    // both reconstructed values remain equal after one iteration.
    const Event event{
        Vec3{0.0, 0.0, 0.0},
        Vec3{0.0, 0.0, 1.0},
        0.0
    };
    const std::vector<Decimal> image = solver.solve({event});

    assert(image.size() == 2);
    assert(std::abs(image[0] - 1.0) < 1.0e-12);
    assert(std::abs(image[1] - 1.0) < 1.0e-12);
    return 0;
}
