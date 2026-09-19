#include "RunAction.hh"

#include "ConfigManager.hh"
#include "SimulationGrid.hh"

#include "G4Run.hh"
#include "G4ios.hh"

#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <utility>

RunAction::RunAction(
    const ConfigManager& config,
    const SimulationGrid& grid,
    std::shared_ptr<const ISourceGeometry> sourceGeometry,
    std::shared_ptr<const IEmissionConePolicy> conePolicy
)
    : config_{&config},
      grid_{&grid},
      emittedCounts_(grid.fullCellCount(), 0),
      validCounts_(grid.fullCellCount(), 0),
      writer_{std::make_unique<RootWriter>(
          config,
          grid,
          std::move(sourceGeometry),
          std::move(conePolicy)
      )}
{
}

RunAction::~RunAction() = default;

void RunAction::BeginOfRunAction(const G4Run*)
{
    std::fill(emittedCounts_.begin(), emittedCounts_.end(), 0);
    std::fill(validCounts_.begin(), validCounts_.end(), 0);
    eventsWithHits_ = 0;
    frontPassedEvents_ = 0;
    rearPassedEvents_ = 0;

    if (config_->mode() == 1)
    {
        writer_->beginEventOutput();
    }

    G4cout << "Raw-efficiency simulator (particle-init fix 2026-09-13), mode = " << config_->mode()
           << ", active cells = " << grid_->activeCellCount()
           << ", requested events = " << grid_->totalEventCount()
           << G4endl;
}

void RunAction::EndOfRunAction(const G4Run*)
{
    const auto emitted = std::accumulate(emittedCounts_.begin(), emittedCounts_.end(), std::uint64_t{0});
    const auto valid = std::accumulate(validCounts_.begin(), validCounts_.end(), std::uint64_t{0});
    const auto positiveCells = std::count_if(validCounts_.begin(), validCounts_.end(), [](std::uint64_t count)
    {
        return count > 0;
    });

    G4cout << "Raw-efficiency run summary:\n"
           << "  Completed events: " << emitted << '\n'
           << "  Events with recorded detector hits: " << eventsWithHits_ << '\n'
           << "  Events passing ch2 threshold: " << frontPassedEvents_ << '\n'
           << "  Events passing ch1 threshold: " << rearPassedEvents_ << '\n'
           << "  Valid two-layer triggers: " << valid << '\n'
           << "  Cells with valid triggers: " << positiveCells << G4endl;

    if (valid == 0)
    {
        G4cout << "WARNING: no valid triggers; zero raw efficiencies will be preserved.\n"
               << "Check the actual particle, detector hits and layer counters before increasing statistics."
               << G4endl;
    }

    if (config_->mode() == 0)
    {
        writer_->writeEfficiencyOutput(emittedCounts_, validCounts_);
        G4cout << "Raw absolute-efficiency map written to: "
               << config_->efficiencyRootFile().string() << G4endl;
    }
    else
    {
        writer_->finishEventOutput();
        G4cout << "Compact event file written to: "
               << config_->eventsRootFile().string() << G4endl;
    }
}

void RunAction::recordEvent(std::size_t index, bool frontPassed, bool rearPassed, bool hasRecordedHit)
{
    if (index >= emittedCounts_.size())
    {
        throw std::out_of_range{"Simulation cell index is out of range."};
    }

    ++emittedCounts_[index];
    eventsWithHits_ += hasRecordedHit ? 1 : 0;
    frontPassedEvents_ += frontPassed ? 1 : 0;
    rearPassedEvents_ += rearPassed ? 1 : 0;

    if (frontPassed && rearPassed)
    {
        ++validCounts_[index];
    }
}

void RunAction::recordCompactEvent(const CompactEventRecord& event)
{
    if (config_->mode() != 1)
    {
        throw std::logic_error{"Compact events can only be written in mode 1."};
    }

    writer_->writeCompactEvent(event);
}
