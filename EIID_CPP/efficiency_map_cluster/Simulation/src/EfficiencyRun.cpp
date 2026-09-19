#include "EfficiencyRun.hh"

void EfficiencyRun::Merge(const G4Run* other)
{
    const auto& source = static_cast<const EfficiencyRun&>(*other);
    for (const auto& [cell, counts] : source.counts)
    {
        addCounts(this->counts[cell], counts);
    }
    G4Run::Merge(other);
}
