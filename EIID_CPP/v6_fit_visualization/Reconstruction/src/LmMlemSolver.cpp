#include "LmMlemSolver.h"

#include "EiidResponse.h"
#include "ReconConfig.h"

#include <cmath>
#include <stdexcept>

LmMlemSolver::LmMlemSolver(
    const IGrid& grid,
    const AbsoluteEfficiencyMap& efficiency,
    const ReconConfig& config
)
    : grid_{&grid}, efficiency_{&efficiency}, config_{&config}
{
    if (efficiency.directionCount() != grid.directionCount() ||
        efficiency.energyCount() != grid.energyCount())
    {
        throw std::runtime_error{"Efficiency dimensions do not match the grid."};
    }
}

std::vector<Decimal> LmMlemSolver::solve(
    const std::vector<Event>& events
) const
{
    if (events.empty())
    {
        throw std::runtime_error{"LM-MLEM cannot reconstruct an empty event set."};
    }

    const auto& cells = grid_->cells();
    std::vector<Decimal> image(cells.size(), static_cast<Decimal>(0.0));

    for (std::size_t cell = 0; cell < cells.size(); ++cell)
    {
        if (efficiency_->atFlat(cell) > static_cast<Decimal>(0.0))
        {
            image[cell] = static_cast<Decimal>(1.0);
        }
    }

    for (int iteration = 0;
         iteration < config_->iterationCount();
         ++iteration)
    {
        std::vector<Decimal> update(cells.size(), static_cast<Decimal>(0.0));
        std::vector<Decimal> response(cells.size(), static_cast<Decimal>(0.0));

        for (const Event& event : events)
        {
            Decimal prediction = static_cast<Decimal>(0.0);

            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                if (image[cell] <= static_cast<Decimal>(0.0))
                {
                    response[cell] = static_cast<Decimal>(0.0);
                    continue;
                }

                // calculateResponse() is the conditional event-shape term
                // q_ij.  The complete system response is
                // a_ij = efficiency_j * q_ij.  The absolute efficiency must
                // therefore participate in the forward prediction; applying
                // it only as the final MLEM normalization is inconsistent.
                const Decimal conditionalResponse =
                    calculateResponse(event, cells[cell], *config_);
                response[cell] =
                    efficiency_->atFlat(cell) * conditionalResponse;
                prediction += response[cell] * image[cell];
            }

            if (prediction <= config_->denominatorFloor())
            {
                throw std::runtime_error{
                    "An event cannot be explained by any positive-efficiency cell."
                };
            }

            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                update[cell] += response[cell] / prediction;
            }
        }

        for (std::size_t cell = 0; cell < cells.size(); ++cell)
        {
            const Decimal efficiency = efficiency_->atFlat(cell);

            if (efficiency > static_cast<Decimal>(0.0))
            {
                image[cell] *= update[cell] / efficiency;

                if (!std::isfinite(image[cell]))
                {
                    throw std::runtime_error{"LM-MLEM produced a non-finite value."};
                }
            }
            else
            {
                image[cell] = static_cast<Decimal>(0.0);
            }
        }
    }

    return image;
}
