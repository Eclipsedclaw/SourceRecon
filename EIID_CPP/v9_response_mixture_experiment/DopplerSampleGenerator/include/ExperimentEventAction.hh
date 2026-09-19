#ifndef DOPPLER_V7_EXPERIMENT_EVENT_ACTION_HH
#define DOPPLER_V7_EXPERIMENT_EVENT_ACTION_HH

#include "G4UserEventAction.hh"

class ConfigManager;
class ExperimentRunAction;
class G4Event;

class ExperimentEventAction final : public G4UserEventAction
{
public:
    ExperimentEventAction(
        const ConfigManager& config,
        ExperimentRunAction& runAction
    );

    void BeginOfEventAction(const G4Event* event) override;
    void EndOfEventAction(const G4Event* event) override;

private:
    const ConfigManager* config_{};
    ExperimentRunAction* runAction_{};
    int hitsCollectionId_{-1};
};

#endif
