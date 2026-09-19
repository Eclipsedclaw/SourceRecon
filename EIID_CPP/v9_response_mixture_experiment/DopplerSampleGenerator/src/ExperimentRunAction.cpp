#include "ExperimentRunAction.hh"

#include "ConfigManager.hh"
#include "ExperimentRootWriter.hh"

#include "G4Run.hh"
#include "G4ios.hh"

#include <stdexcept>

ExperimentRunAction::ExperimentRunAction(const ConfigManager& config)
    : config_{&config},
      writer_{std::make_unique<ExperimentRootWriter>(config)}
{
}

ExperimentRunAction::~ExperimentRunAction() = default;

void ExperimentRunAction::BeginOfRunAction(const G4Run*)
{
    counters_ = {};
    writer_->open();

    G4cout << "Doppler V9 calibration sample: " << config_->experimentName()
           << ", Compton model = " << config_->comptonModel()
           << ", requested events = " << config_->numberOfEvents()
           << G4endl;
}

void ExperimentRunAction::EndOfRunAction(const G4Run*)
{
    writer_->finish(counters_);

    G4cout << "Experiment completed. selected/emitted = "
           << counters_.selectedTruth << '/' << counters_.emitted << G4endl
           << "  events with any detector hit: "
           << counters_.eventsWithAnyHit << G4endl
           << "  events with any gamma hit: "
           << counters_.eventsWithAnyGammaHit << G4endl
           << "  events with primary-gamma hit: "
           << counters_.eventsWithPrimaryGammaHit << G4endl
           << "  no primary-gamma step: "
           << counters_.rejectedNoPrimaryGammaStep << G4endl
           << "  primary gamma missed ch2: "
           << counters_.rejectedMissedFrontChamber << G4endl
           << "  entered ch2 but no discrete interaction: "
           << counters_.rejectedNoPrimaryInteraction << G4endl
           << "  wrong first interaction: "
           << counters_.rejectedWrongFirstInteraction << G4endl
           << "  missing second interaction: "
           << counters_.rejectedMissingSecondInteraction << G4endl
           << "  wrong second interaction: "
           << counters_.rejectedWrongSecondInteraction << G4endl
           << "  below layer threshold: "
           << counters_.rejectedLayerThreshold << G4endl
           << "  invalid truth kinematics: "
           << counters_.rejectedTruthKinematics << G4endl
           << "ROOT: " << config_->outputRootFile().string() << G4endl
           << "summary: " << config_->summaryJsonFile().string() << G4endl;
}

void ExperimentRunAction::recordEmitted()
{
    ++counters_.emitted;
}

void ExperimentRunAction::recordHitDiagnostics(
    bool sawAnyHit,
    bool sawAnyGammaHit,
    bool sawPrimaryGammaHit
)
{
    if (sawAnyHit)
    {
        ++counters_.eventsWithAnyHit;
    }

    if (sawAnyGammaHit)
    {
        ++counters_.eventsWithAnyGammaHit;
    }

    if (sawPrimaryGammaHit)
    {
        ++counters_.eventsWithPrimaryGammaHit;
    }
}

void ExperimentRunAction::recordRejected(RejectionReason reason)
{
    switch (reason)
    {
        case RejectionReason::noPrimaryGammaStep:
            ++counters_.rejectedNoPrimaryGammaStep;
            break;
        case RejectionReason::missedFrontChamber:
            ++counters_.rejectedMissedFrontChamber;
            break;
        case RejectionReason::noPrimaryInteraction:
            ++counters_.rejectedNoPrimaryInteraction;
            break;
        case RejectionReason::wrongFirstInteraction:
            ++counters_.rejectedWrongFirstInteraction;
            break;
        case RejectionReason::missingSecondInteraction:
            ++counters_.rejectedMissingSecondInteraction;
            break;
        case RejectionReason::wrongSecondInteraction:
            ++counters_.rejectedWrongSecondInteraction;
            break;
        case RejectionReason::layerThreshold:
            ++counters_.rejectedLayerThreshold;
            break;
        case RejectionReason::truthKinematics:
            ++counters_.rejectedTruthKinematics;
            break;
    }
}

void ExperimentRunAction::recordSelected(const ExperimentRecord& record)
{
    ++counters_.selectedTruth;

    if (record.detectorKinematicsValid != 0)
    {
        ++counters_.detectorKinematicsValid;
    }
    else
    {
        ++counters_.detectorKinematicsInvalid;
    }

    writer_->write(record);
}
