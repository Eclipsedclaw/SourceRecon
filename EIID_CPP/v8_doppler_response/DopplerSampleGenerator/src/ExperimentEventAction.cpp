#include "ExperimentEventAction.hh"

#include "ConfigManager.hh"
#include "ExperimentRecord.hh"
#include "ExperimentRunAction.hh"
#include "TrackerHit.hh"

#include "G4Event.hh"
#include "G4HCofThisEvent.hh"
#include "G4PhysicalConstants.hh"
#include "G4SDManager.hh"
#include "G4SystemOfUnits.hh"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <optional>
#include <stdexcept>
#include <vector>

namespace
{
struct LayerAccumulator
{
    G4double deposited{};
    G4ThreeVector energyWeightedPosition;

    void add(const B2::TrackerHit& hit)
    {
        const G4double energy = hit.GetEdep();

        if (energy <= 0.0)
        {
            return;
        }

        // 一个宏观 hit 可以由反冲电子、次级电子和退激发光子的许多 Step
        // 共同组成。这里按照真实硬件读出的含义聚合，而不是数 Step 个数。
        deposited += energy;
        energyWeightedPosition += energy * hit.GetPos();
    }

    G4ThreeVector centroid() const
    {
        return deposited > 0.0
            ? energyWeightedPosition / deposited
            : G4ThreeVector{};
    }
};

struct GammaInteraction
{
    G4String process;
    G4int chamberId{-1};
    G4ThreeVector position;
    G4ThreeVector incomingDirection;
    G4ThreeVector outgoingDirection;
    G4double incomingEnergy{};
    G4double outgoingEnergy{};
};

double clampedAcos(double cosine)
{
    return std::acos(std::clamp(cosine, -1.0, 1.0));
}

std::optional<G4double> kinematicAngleFromFirstDeposit(
    G4double incidentEnergy,
    G4double firstDeposit
)
{
    // 评估阶段知道单能源的真值 E。若第一次沉积为 e1，静止自由电子
    // 公式对应的散射光子能量就是 E-e1。
    if (!(incidentEnergy > 0.0) || !(firstDeposit > 0.0) ||
        firstDeposit >= incidentEnergy)
    {
        return std::nullopt;
    }

    const G4double scatteredEnergy = incidentEnergy - firstDeposit;
    const G4double cosine = 1.0 - electron_mass_c2 *
        (1.0 / scatteredEnergy - 1.0 / incidentEnergy);

    constexpr G4double numericalTolerance = 1.0e-10;

    if (!std::isfinite(cosine) || cosine < -1.0 - numericalTolerance ||
        cosine > 1.0 + numericalTolerance)
    {
        return std::nullopt;
    }

    return clampedAcos(cosine);
}

std::optional<G4double> reconstructEiidEnergy(
    G4double firstDeposit,
    G4double geometricAngle
)
{
    const G4double oneMinusCosine = 1.0 - std::cos(geometricAngle);

    if (!(firstDeposit > 0.0) || !(oneMinusCosine > 0.0))
    {
        return std::nullopt;
    }

    const G4double discriminant =
        firstDeposit * firstDeposit +
        4.0 * firstDeposit * electron_mass_c2 / oneMinusCosine;

    if (!std::isfinite(discriminant) || discriminant < 0.0)
    {
        return std::nullopt;
    }

    return 0.5 * (firstDeposit + std::sqrt(discriminant));
}

bool isObservableSecondProcess(const GammaInteraction& interaction)
{
    return interaction.process == "compt" || interaction.process == "phot";
}


bool isPrimaryGamma(const B2::TrackerHit& hit)
{
    return hit.GetCreatorProcess() == "primary" &&
        hit.GetParticleName() == "gamma";
}

bool isDiscreteProcess(const G4String& process)
{
    return process != "Transportation" && process != "StepLimiter" &&
        process != "none";
}
}

ExperimentEventAction::ExperimentEventAction(
    const ConfigManager& config,
    ExperimentRunAction& runAction
)
    : config_{&config},
      runAction_{&runAction}
{
}

void ExperimentEventAction::BeginOfEventAction(const G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"BeginOfEventAction received a null event."};
    }

    runAction_->recordEmitted();
}

void ExperimentEventAction::EndOfEventAction(const G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"EndOfEventAction received a null event."};
    }

    if (hitsCollectionId_ < 0)
    {
        hitsCollectionId_ = G4SDManager::GetSDMpointer()->GetCollectionID(
            "TrackerHitsCollection"
        );

        if (hitsCollectionId_ < 0)
        {
            throw std::runtime_error{"Cannot find TrackerHitsCollection."};
        }
    }

    const B2::TrackerHitsCollection* hits = nullptr;
    G4HCofThisEvent* collections = event->GetHCofThisEvent();

    if (collections != nullptr)
    {
        hits = static_cast<const B2::TrackerHitsCollection*>(
            collections->GetHC(hitsCollectionId_)
        );
    }

    LayerAccumulator front;
    LayerAccumulator rear;
    std::vector<const B2::TrackerHit*> primaryGammaSteps;
    bool sawAnyHit = false;
    bool sawAnyGammaHit = false;

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

            sawAnyHit = true;

            if (hit->GetParticleName() == "gamma")
            {
                sawAnyGammaHit = true;
            }

            if (hit->GetChamberNb() == config_->frontChamberId())
            {
                front.add(*hit);
            }
            else if (hit->GetChamberNb() == config_->rearChamberId())
            {
                rear.add(*hit);
            }

            if (isPrimaryGamma(*hit))
            {
                primaryGammaSteps.push_back(hit);
            }
        }
    }

    runAction_->recordHitDiagnostics(
        sawAnyHit,
        sawAnyGammaHit,
        !primaryGammaSteps.empty()
    );

    // 同一条主光子的 StepID 单调增加。显式排序可避免 hit collection 中
    // 次级粒子的处理顺序影响主光子相互作用的先后关系。
    std::sort(
        primaryGammaSteps.begin(),
        primaryGammaSteps.end(),
        [](const B2::TrackerHit* left, const B2::TrackerHit* right)
        {
            return left->GetStepID() < right->GetStepID();
        }
    );

    const bool enteredFront = std::any_of(
        primaryGammaSteps.begin(),
        primaryGammaSteps.end(),
        [this](const B2::TrackerHit* hit)
        {
            return hit->GetChamberNb() == config_->frontChamberId();
        }
    );
    std::vector<GammaInteraction> interactions;

    for (const B2::TrackerHit* hit : primaryGammaSteps)
    {
        const G4String process = hit->GetpostProcess();

        if (!isDiscreteProcess(process))
        {
            continue;
        }

        interactions.push_back(
            GammaInteraction{
                process,
                hit->GetChamberNb(),
                hit->GetPos(),
                hit->GetMomentum().unit(),
                hit->GetPostMomentum().unit(),
                hit->GetPreKineticEnergy(),
                hit->GetKineticEnergy()
            }
        );
    }

    if (interactions.empty())
    {
        if (primaryGammaSteps.empty())
        {
            runAction_->recordRejected(RejectionReason::noPrimaryGammaStep);
            return;
        }

        if (!enteredFront)
        {
            runAction_->recordRejected(RejectionReason::missedFrontChamber);
            return;
        }

        runAction_->recordRejected(RejectionReason::noPrimaryInteraction);
        return;
    }

    // 只约束主光子的第一个离散物理过程，而不是要求 chamber 内只有一个 Step。
    if (interactions[0].process != "compt" ||
        interactions[0].chamberId != config_->frontChamberId())
    {
        runAction_->recordRejected(RejectionReason::wrongFirstInteraction);
        return;
    }

    if (interactions.size() < 2)
    {
        runAction_->recordRejected(RejectionReason::missingSecondInteraction);
        return;
    }

    // 第二次相互作用只负责提供 r2。它可以再次 Compton，也可以光电吸收。
    // 第二次之后光子继续散射或逃逸均允许，不再要求“恰好两个过程”。
    if (interactions[1].chamberId != config_->rearChamberId() ||
        !isObservableSecondProcess(interactions[1]))
    {
        runAction_->recordRejected(RejectionReason::wrongSecondInteraction);
        return;
    }

    const G4double minimumEnergy = config_->minimumLayerEnergyMeV() * MeV;

    if (front.deposited <= minimumEnergy || rear.deposited <= minimumEnergy)
    {
        runAction_->recordRejected(RejectionReason::layerThreshold);
        return;
    }

    const GammaInteraction& first = interactions[0];
    const GammaInteraction& secondInteraction = interactions[1];
    const G4double sourceEnergy = config_->sourceEnergyMeV() * MeV;
    const G4double truthE1 = first.incomingEnergy - first.outgoingEnergy;

    if (first.incomingDirection.mag2() == 0.0 ||
        first.outgoingDirection.mag2() == 0.0)
    {
        runAction_->recordRejected(RejectionReason::truthKinematics);
        return;
    }

    const G4ThreeVector incoming = first.incomingDirection.unit();
    const G4ThreeVector outgoing = first.outgoingDirection.unit();
    const G4double truthThetaGeo = clampedAcos(incoming.dot(outgoing));
    const auto truthThetaKin = kinematicAngleFromFirstDeposit(sourceEnergy, truthE1);
    const auto truthEnergy = reconstructEiidEnergy(truthE1, truthThetaGeo);

    if (!truthThetaKin || !truthEnergy)
    {
        runAction_->recordRejected(RejectionReason::truthKinematics);
        return;
    }

    const G4ThreeVector detectorR1 = front.centroid();
    const G4ThreeVector detectorR2 = rear.centroid();
    const G4ThreeVector detectorDisplacement = detectorR2 - detectorR1;
    const auto detectorThetaKin =
        kinematicAngleFromFirstDeposit(sourceEnergy, front.deposited);
    std::optional<G4double> detectorThetaGeo;
    std::optional<G4double> detectorEnergy;

    if (detectorDisplacement.mag2() > 0.0)
    {
        detectorThetaGeo = clampedAcos(
            incoming.dot(detectorDisplacement.unit())
        );
        detectorEnergy = reconstructEiidEnergy(
            front.deposited,
            *detectorThetaGeo
        );
    }

    const bool detectorValid =
        detectorThetaKin.has_value() && detectorThetaGeo.has_value() &&
        detectorEnergy.has_value();
    const double notANumber = std::numeric_limits<double>::quiet_NaN();

    ExperimentRecord record;
    record.eventId = static_cast<std::int64_t>(event->GetEventID());
    record.primaryInteractionCount =
        static_cast<std::int32_t>(interactions.size());
    record.secondInteractionCode =
        secondInteraction.process == "compt" ? 1 : 2;
    record.detectorKinematicsValid = detectorValid ? 1 : 0;

    record.truthE1MeV = truthE1 / MeV;
    record.detectorE1MeV = front.deposited / MeV;
    record.detectorE2MeV = rear.deposited / MeV;

    record.truthR1Xmm = first.position.x() / mm;
    record.truthR1Ymm = first.position.y() / mm;
    record.truthR1Zmm = first.position.z() / mm;
    record.truthR2Xmm = secondInteraction.position.x() / mm;
    record.truthR2Ymm = secondInteraction.position.y() / mm;
    record.truthR2Zmm = secondInteraction.position.z() / mm;
    record.detectorR1Xmm = detectorR1.x() / mm;
    record.detectorR1Ymm = detectorR1.y() / mm;
    record.detectorR1Zmm = detectorR1.z() / mm;
    record.detectorR2Xmm = detectorR2.x() / mm;
    record.detectorR2Ymm = detectorR2.y() / mm;
    record.detectorR2Zmm = detectorR2.z() / mm;

    record.incomingX = incoming.x();
    record.incomingY = incoming.y();
    record.incomingZ = incoming.z();
    record.outgoingX = outgoing.x();
    record.outgoingY = outgoing.y();
    record.outgoingZ = outgoing.z();

    record.truthThetaGeoDegree = truthThetaGeo / degree;
    record.truthThetaKinDegree = *truthThetaKin / degree;
    record.truthArmDegree = (*truthThetaKin - truthThetaGeo) / degree;
    record.truthReconstructedEnergyMeV = *truthEnergy / MeV;
    record.truthEnergyResidualMeV = (*truthEnergy - sourceEnergy) / MeV;
    record.truthRelativeEnergyResidual =
        (*truthEnergy - sourceEnergy) / sourceEnergy;

    record.detectorThetaGeoDegree = detectorThetaGeo
        ? *detectorThetaGeo / degree
        : notANumber;
    record.detectorThetaKinDegree = detectorThetaKin
        ? *detectorThetaKin / degree
        : notANumber;
    record.detectorArmDegree = detectorValid
        ? (*detectorThetaKin - *detectorThetaGeo) / degree
        : notANumber;
    record.detectorReconstructedEnergyMeV = detectorEnergy
        ? *detectorEnergy / MeV
        : notANumber;
    record.detectorEnergyResidualMeV = detectorEnergy
        ? (*detectorEnergy - sourceEnergy) / MeV
        : notANumber;
    record.detectorRelativeEnergyResidual = detectorEnergy
        ? (*detectorEnergy - sourceEnergy) / sourceEnergy
        : notANumber;

    runAction_->recordSelected(record);
}
