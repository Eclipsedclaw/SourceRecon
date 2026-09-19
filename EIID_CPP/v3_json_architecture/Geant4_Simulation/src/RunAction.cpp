#include "RunAction.hh"

#include "ConfigManager.hh"
#include "SimulationGrid.hh"

#include "G4Run.hh"
#include "G4ios.hh"

#include <algorithm>
#include <stdexcept>

RunAction::RunAction(
    const ConfigManager& config,
    const SimulationGrid& grid
)
    : config_{&config},
      grid_{&grid},
      emittedCounts_(grid.fullCellCount(), 0),
      validCounts_(grid.fullCellCount(), 0),
      writer_{std::make_unique<RootWriter>(config, grid)}
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

    G4cout << "V3 simulation mode = " << config_->mode()
           << ", active cells = " << grid_->activeCellCount()
           << ", requested events = " << grid_->totalEventCount()
           << G4endl;
}

void RunAction::EndOfRunAction(const G4Run*)
{
    if (config_->mode() == 0)
    {
        writer_->writeSensitivityOutput(emittedCounts_, validCounts_);
        G4cout << "Sensitivity table written to: "
               << config_->sensitivityRootFile().string()
               << G4endl;
    }
    else
    {
        writer_->finishEventOutput();
        G4cout << "Compact event file written to: "
               << config_->eventsRootFile().string()
               << G4endl;
    }
}

void RunAction::recordEvent(std::size_t flatCellIndex, bool validTrigger)
{
    if (flatCellIndex >= emittedCounts_.size())
    {
        throw std::out_of_range{"Simulation cell index is outside RunAction counters."};
    }

    ++emittedCounts_[flatCellIndex];

    if (validTrigger)
    {
        ++validCounts_[flatCellIndex];
    }
}

void RunAction::recordCompactEvent(const CompactEventRecord& event)
{
    if (config_->mode() != 1)
    {
        throw std::logic_error{
            "Compact events may only be written when simulation mode is 1."
        };
    }

    writer_->writeCompactEvent(event);
}
