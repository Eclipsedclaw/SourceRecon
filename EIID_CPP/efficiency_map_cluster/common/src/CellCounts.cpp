#include "CellCounts.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

void addCounts(CellCounts& target, const CellCounts& source)
{
    auto add = [](std::uint64_t& to, std::uint64_t from)
    {
        if (from > std::numeric_limits<std::uint64_t>::max() - to)
        {
            throw std::overflow_error{"Counter overflow"};
        }
        to += from;
    };
    if (target.coneFraction != 0 && source.coneFraction != 0 &&
        std::abs(target.coneFraction - source.coneFraction) > 1e-12 * target.coneFraction)
    {
        throw std::runtime_error{"Cone fractions do not match"};
    }
    add(target.emitted, source.emitted);
    add(target.valid, source.valid);
    add(target.hits, source.hits);
    add(target.front, source.front);
    add(target.rear, source.rear);
    if (source.coneFraction != 0)
    {
        target.coneFraction = source.coneFraction;
    }
}

void validateCounts(const Counts& counts, const TaskSpec& task, const ConfigManager& config)
{
    if (task.eventCount == 0 || task.firstEvent > config.totalEvents() ||
        task.eventCount > config.totalEvents() - task.firstEvent)
    {
        throw std::runtime_error{"Invalid task range"};
    }
    const auto n = config.particlesPerCell();
    const auto end = task.firstEvent + task.eventCount;
    const auto first = task.firstEvent / n;
    const auto last = (end - 1) / n;
    if (counts.size() != last - first + 1)
    {
        throw std::runtime_error{"Missing or extra cells in chunk"};
    }
    for (std::uint64_t ordinal = first; ordinal <= last; ++ordinal)
    {
        const auto found = counts.find(config.firstActiveCell() + ordinal);
        if (found == counts.end())
        {
            throw std::runtime_error{"Wrong cell indices in chunk"};
        }
        const auto& c = found->second;
        const auto expected = std::min(end, (ordinal + 1) * n) - std::max(task.firstEvent, ordinal * n);
        if (c.emitted != expected || c.valid > c.front || c.valid > c.rear || c.front > c.hits || c.rear > c.hits ||
            c.hits > c.emitted || !std::isfinite(c.coneFraction) || c.coneFraction <= 0 || c.coneFraction > 1)
        {
            throw std::runtime_error{"Incomplete counters or invalid cone fraction at cell " +
                                     std::to_string(found->first)};
        }
    }
}
