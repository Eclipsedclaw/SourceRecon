#include "HistogramKernel.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

HistogramKernel::HistogramKernel(
    std::vector<Decimal> energyCenters,
    std::vector<Decimal> angleCenters,
    std::vector<Decimal> deltaCenters,
    std::vector<Decimal> density
)
    : energyCenters_{std::move(energyCenters)},
      angleCenters_{std::move(angleCenters)},
      deltaCenters_{std::move(deltaCenters)},
      density_{std::move(density)}
{
    if (energyCenters_.empty() || angleCenters_.empty() ||
        deltaCenters_.empty() ||
        density_.size() != energyCenters_.size() * angleCenters_.size() *
            deltaCenters_.size())
    {
        throw std::invalid_argument{"Histogram response dimensions are invalid."};
    }
}

Decimal HistogramKernel::evaluate(const ResponseQuery& query) const
{
    if (deltaCenters_.size() > 1)
    {
        const Decimal lowEdge = deltaCenters_.front() -
            static_cast<Decimal>(0.5) *
            (deltaCenters_[1] - deltaCenters_.front());
        const Decimal highEdge = deltaCenters_.back() +
            static_cast<Decimal>(0.5) *
            (deltaCenters_.back() - deltaCenters_[deltaCenters_.size() - 2]);

        if (query.deltaThetaDegree < lowEdge ||
            query.deltaThetaDegree > highEdge)
        {
            return static_cast<Decimal>(0.0);
        }
    }

    const std::size_t energy = nearest(energyCenters_, query.incidentEnergyMeV);
    const std::size_t angle = nearest(angleCenters_, query.scatterAngleDegree);
    const std::size_t delta = nearest(deltaCenters_, query.deltaThetaDegree);
    return density_.at(flatIndex(energy, angle, delta));
}

std::string_view HistogramKernel::name() const noexcept
{
    return "histogram";
}

std::size_t HistogramKernel::nearest(
    const std::vector<Decimal>& coordinates,
    Decimal value
) const
{
    const auto upper = std::lower_bound(coordinates.begin(), coordinates.end(), value);

    if (upper == coordinates.begin())
    {
        return 0;
    }

    if (upper == coordinates.end())
    {
        return coordinates.size() - 1;
    }

    const std::size_t high = static_cast<std::size_t>(
        std::distance(coordinates.begin(), upper)
    );
    const std::size_t low = high - 1;
    return std::abs(value - coordinates[low]) <=
        std::abs(coordinates[high] - value) ? low : high;
}

std::size_t HistogramKernel::flatIndex(
    std::size_t energy,
    std::size_t angle,
    std::size_t delta
) const
{
    return (energy * angleCenters_.size() + angle) * deltaCenters_.size() + delta;
}
