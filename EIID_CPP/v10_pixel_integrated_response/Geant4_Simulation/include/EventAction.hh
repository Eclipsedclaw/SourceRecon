#ifndef EIID_V7_EVENT_ACTION_HH
#define EIID_V7_EVENT_ACTION_HH

#include "G4UserEventAction.hh"

class ConfigManager;
class G4Event;
class RunAction;
class SimulationGrid;

class EventAction final : public G4UserEventAction
{
public:
    EventAction(
        const ConfigManager& config,
        const SimulationGrid& grid,
        RunAction& runAction
    );

    void EndOfEventAction(const G4Event* event) override;

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};
    RunAction* runAction_{};
    int hitsCollectionId_{-1};
};

#endif
