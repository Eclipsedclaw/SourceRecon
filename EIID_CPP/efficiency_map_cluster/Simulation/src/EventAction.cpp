#include "EventAction.hh"
#include "TrackerHit.hh"
#include <G4Event.hh>
#include <G4HCofThisEvent.hh>
#include <G4SDManager.hh>
#include <G4SystemOfUnits.hh>
#include <stdexcept>

void EventAction::EndOfEventAction(const G4Event* event)
{
    if (!event || event->IsAborted())
    {
        throw std::runtime_error{"Aborted event; block must be retried"};
    }
    if (collectionId_ < 0)
    {
        collectionId_ = G4SDManager::GetSDMpointer()->GetCollectionID("TrackerHitsCollection");
        if (collectionId_ < 0)
        {
            throw std::runtime_error{"Cannot find TrackerHitsCollection"};
        }
    }
    double frontEnergy = 0, rearEnergy = 0;
    bool hasHit = false;
    auto* collections = event->GetHCofThisEvent();
    if (collections)
    {
        const auto* hits = static_cast<const B2::TrackerHitsCollection*>(collections->GetHC(collectionId_));
        if (hits)
        {
            for (std::size_t i = 0; i < hits->entries(); ++i)
            {
                const auto* hit = (*hits)[i];
                if (!hit)
                {
                    continue;
                }
                hasHit = true;
                if (hit->GetEdep() <= 0)
                {
                    continue;
                }
                // 与串行版同样按 chamber 累加所有正能量沉积，不要求完全吸收。
                if (hit->GetChamberNb() == config_.frontChamberId())
                {
                    frontEnergy += hit->GetEdep();
                }
                if (hit->GetChamberNb() == config_.rearChamberId())
                {
                    rearEnergy += hit->GetEdep();
                }
            }
        }
    }
    const auto globalEvent = context_.task.firstEvent + static_cast<std::uint64_t>(event->GetEventID());
    const double threshold = config_.minimumLayerEnergyMeV() * MeV;
    run_.recordEvent(grid_.cellForEvent(globalEvent).flatIndex, frontEnergy > threshold, rearEnergy > threshold,
                     hasHit);
}
