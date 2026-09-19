#include "mlem_core.h"

#include <cmath>
#include <stdexcept>
#include <vector>

LmMlemSolver::LmMlemSolver(
    const Grid& grid,
    const SensitivityMatrix& sensitivity,
    const ReconConfig& config
)
    : grid_{&grid},
      sensitivity_{&sensitivity},
      config_{&config}
{
    if (sensitivity_->directionCount() != grid_->directionCount() ||
        sensitivity_->energyCount() != grid_->energyCount())
    {
        throw std::runtime_error{"Sensitivity dimensions do not match the reconstruction grid."};
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

    const std::vector<Cell>& cells = grid_->cells();
    std::vector<Decimal> image(cells.size(), static_cast<Decimal>(0.0L));

    // 乘法更新不能让初值为零的 cell 恢复为正数。
    // 只有具有正敏感度的物理 cell 才以 1 初始化。
    for (std::size_t cell = 0; cell < cells.size(); ++cell)
    {
        if (sensitivity_->atFlat(cell) > static_cast<Decimal>(0.0L))
        {
            image[cell] = static_cast<Decimal>(1.0L);
        }
    }

    for (int iteration = 0;
         iteration < config_->iterationCount();
         ++iteration)
    {
        std::vector<Decimal> update(cells.size(), static_cast<Decimal>(0.0L));
        std::vector<Decimal> eventResponse(cells.size(), static_cast<Decimal>(0.0L));

        for (const Event& event : events)
        {
            Decimal prediction = static_cast<Decimal>(0.0L);

            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                if (image[cell] <= static_cast<Decimal>(0.0L))
                {
                    eventResponse[cell] = static_cast<Decimal>(0.0L);
                    continue;
                }

                eventResponse[cell] = calculateResponse(
                    event,
                    cells[cell],
                    *config_
                );

                prediction += eventResponse[cell] * image[cell];
            }

            if (prediction <= config_->denominatorFloor())
            {
                throw std::runtime_error{
                    "An event cannot be explained by any cell with positive sensitivity."
                };
            }

            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                update[cell] += eventResponse[cell] / prediction;
            }
        }

        for (std::size_t cell = 0; cell < cells.size(); ++cell)
        {
            const Decimal sensitivity = sensitivity_->atFlat(cell);

            // 真实敏感度进入 LM-MLEM 分母。
            // 这是强制防呆：s_j <= 0 时绝不执行除法，并将该 cell 明确置零。
            if (sensitivity > static_cast<Decimal>(0.0L))
            {
                image[cell] *= update[cell] / sensitivity;

                if (!std::isfinite(image[cell]))
                {
                    throw std::runtime_error{"LM-MLEM produced a non-finite image value."};
                }
            }
            else
            {
                image[cell] = static_cast<Decimal>(0.0L);
            }
        }
    }

    return image;
}
