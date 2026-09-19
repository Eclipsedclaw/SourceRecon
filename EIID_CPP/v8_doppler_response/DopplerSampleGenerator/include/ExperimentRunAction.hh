#ifndef DOPPLER_V7_EXPERIMENT_RUN_ACTION_HH
#define DOPPLER_V7_EXPERIMENT_RUN_ACTION_HH

#include "ExperimentRecord.hh"
#include "G4UserRunAction.hh"

#include <memory>

class ConfigManager;
class ExperimentRootWriter;
class G4Run;

enum class RejectionReason
{
    noPrimaryGammaStep,
    missedFrontChamber,
    noPrimaryInteraction,
    wrongFirstInteraction,
    missingSecondInteraction,
    wrongSecondInteraction,
    layerThreshold,
    truthKinematics
};

class ExperimentRunAction final : public G4UserRunAction
{
public:
    explicit ExperimentRunAction(const ConfigManager& config);
    ~ExperimentRunAction() override;

    void BeginOfRunAction(const G4Run* run) override;
    void EndOfRunAction(const G4Run* run) override;

    void recordEmitted();
    void recordHitDiagnostics(
        bool sawAnyHit,
        bool sawAnyGammaHit,
        bool sawPrimaryGammaHit
    );
    void recordRejected(RejectionReason reason);
    void recordSelected(const ExperimentRecord& record);

private:
    const ConfigManager* config_{};
    ExperimentCounters counters_;
    std::unique_ptr<ExperimentRootWriter> writer_;
};

#endif
