#include "RunAction.hh"

#include "ConfigManager.hh"
#include "SimulationGrid.hh"

#include "G4Run.hh"
#include "G4ios.hh"

#include <algorithm>
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

    if (config_->mode() == 1)
    {
        writer_->beginEventOutput();
    }

    G4cout << "V7 simulation mode = " << config_->mode()
           << ", active cells = " << grid_->activeCellCount()
           << ", requested events = " << grid_->totalEventCount()
           << G4endl;
}

void RunAction::EndOfRunAction(const G4Run*)
{
    if (config_->mode() == 0)
    {
        writer_->writeEfficiencyOutput(emittedCounts_, validCounts_);
        G4cout << "Absolute-efficiency map written to: "
               << config_->efficiencyRootFile().string() << G4endl;
    }
    else
    {
        writer_->finishEventOutput();
        G4cout << "Compact event file written to: "
               << config_->eventsRootFile().string() << G4endl;
    }
}

void RunAction::recordEvent(std::size_t index, bool validTrigger)
{
    if (index >= emittedCounts_.size())
    {
        throw std::out_of_range{"Simulation cell index is out of range."};
    }

    ++emittedCounts_[index];

    if (validTrigger)
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
