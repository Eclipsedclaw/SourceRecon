#include "EventAction.hh"

#include "ConfigManager.hh"
#include "RunAction.hh"
#include "SimulationGrid.hh"
#include "TrackerHit.hh"

#include "G4Event.hh"
#include "G4HCofThisEvent.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace
{
struct LayerAccumulator
{
    G4double energy{};
    G4ThreeVector energyWeightedPosition;

    void add(const B2::TrackerHit& hit)
    {
        const G4double depositedEnergy = hit.GetEdep();

        if (depositedEnergy <= 0.0)
        {
            return;
        }

        energy += depositedEnergy;
        energyWeightedPosition += depositedEnergy * hit.GetPos();
    }

    G4ThreeVector centroid() const
    {
        if (energy <= 0.0)
        {
            return {};
        }

        return energyWeightedPosition / energy;
    }
};
}

EventAction::EventAction(
    const ConfigManager& config,
    const SimulationGrid& grid,
    RunAction& runAction
)
    : config_{&config},
      grid_{&grid},
      runAction_{&runAction}
{
}

void EventAction::EndOfEventAction(const G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"EndOfEventAction received a null G4Event."};
    }

    const SimulationCell& cell = grid_->cellForEvent(
        static_cast<std::uint64_t>(event->GetEventID())
    );
    // G4Event itself is read-only here, but Geant4 11.2 returns a mutable
    // hit-container pointer and G4HCofThisEvent::GetHC() is not const-qualified.
    // We do not modify the container; the non-const pointer only matches the
    // Geant4 API required to retrieve the collection.
    G4HCofThisEvent* collections = event->GetHCofThisEvent();
    LayerAccumulator frontLayer;
    LayerAccumulator rearLayer;
    bool hasRecordedHit = false;

    if (hitsCollectionId_ < 0)
    {
        // TrackerSD::Initialize() registers and resolves this collection by
        // its unique collection name.  Using a leading-slash SD path here is
        // parsed differently by G4HCtable and therefore cannot be found.
        hitsCollectionId_ = G4SDManager::GetSDMpointer()->GetCollectionID(
            "TrackerHitsCollection"
        );

        if (hitsCollectionId_ < 0)
        {
            throw std::runtime_error{
                "Cannot find TrackerHitsCollection."
            };
        }
    }

    if (collections != nullptr && hitsCollectionId_ >= 0)
    {
        const auto* hits = static_cast<const B2::TrackerHitsCollection*>(
            collections->GetHC(hitsCollectionId_)
        );

        if (hits != nullptr)
        {
            for (std::size_t index = 0;
                 index < static_cast<std::size_t>(hits->entries());
                 ++index)
            {
                const B2::TrackerHit* hit = (*hits)[index];

                if (hit == nullptr)
                {
                    continue;
                }

                hasRecordedHit = true;

                if (hit->GetChamberNb() == config_->frontChamberId())
                {
                    frontLayer.add(*hit);
                }
                else if (hit->GetChamberNb() == config_->rearChamberId())
                {
                    rearLayer.add(*hit);
                }
            }
        }
    }

    const G4double threshold = config_->minimumLayerEnergyMeV() * MeV;
    const bool frontPassed = frontLayer.energy > threshold;
    const bool rearPassed = rearLayer.energy > threshold;
    const bool validTrigger = frontPassed && rearPassed;
    runAction_->recordEvent(cell.flatIndex, frontPassed, rearPassed, hasRecordedHit);

    if (!validTrigger || config_->mode() != 1)
    {
        return;
    }

    const G4ThreeVector r1 = frontLayer.centroid();
    const G4ThreeVector r2 = rearLayer.centroid();

    // 这里固定执行 ch2(前层，ID 0) -> ch1(后层，ID 1) 的重组约定。
    runAction_->recordCompactEvent(
        CompactEventRecord{
            static_cast<std::int64_t>(event->GetEventID()),
            static_cast<std::int64_t>(cell.flatIndex),
            r1.x() / mm,
            r1.y() / mm,
            r1.z() / mm,
            r2.x() / mm,
            r2.y() / mm,
            r2.z() / mm,
            frontLayer.energy / MeV
        }
    );
}
