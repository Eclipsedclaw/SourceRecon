#ifndef DOPPLER_V7_EXPERIMENT_RECORD_HH
#define DOPPLER_V7_EXPERIMENT_RECORD_HH

#include <cstdint>

// 一个被接受的事例同时保存两套结果：
//
// truth*    使用第一次 Compton 的真实转移能量和真实光子方向，
//           用于尽量纯粹地观察束缚电子/Doppler 展宽。
// detector* 使用每层全部 Step 的沉积总能量和能量加权质心，
//           用于观察真实读出聚合额外引入的展宽。
struct ExperimentRecord
{
    std::int64_t eventId{};
    std::int32_t primaryInteractionCount{};
    std::int32_t secondInteractionCode{}; // 1=compt，2=phot。
    std::int32_t detectorKinematicsValid{};

    double truthE1MeV{};
    double detectorE1MeV{};
    double detectorE2MeV{};

    double truthR1Xmm{};
    double truthR1Ymm{};
    double truthR1Zmm{};
    double truthR2Xmm{};
    double truthR2Ymm{};
    double truthR2Zmm{};

    double detectorR1Xmm{};
    double detectorR1Ymm{};
    double detectorR1Zmm{};
    double detectorR2Xmm{};
    double detectorR2Ymm{};
    double detectorR2Zmm{};

    double incomingX{};
    double incomingY{};
    double incomingZ{};
    double outgoingX{};
    double outgoingY{};
    double outgoingZ{};

    double truthThetaGeoDegree{};
    double truthThetaKinDegree{};
    double truthArmDegree{};
    double truthReconstructedEnergyMeV{};
    double truthEnergyResidualMeV{};
    double truthRelativeEnergyResidual{};

    double detectorThetaGeoDegree{};
    double detectorThetaKinDegree{};
    double detectorArmDegree{};
    double detectorReconstructedEnergyMeV{};
    double detectorEnergyResidualMeV{};
    double detectorRelativeEnergyResidual{};
};

struct ExperimentCounters
{
    std::uint64_t emitted{};

    std::uint64_t eventsWithAnyHit{};
    std::uint64_t eventsWithAnyGammaHit{};
    std::uint64_t eventsWithPrimaryGammaHit{};

    std::uint64_t rejectedNoPrimaryGammaStep{};
    std::uint64_t rejectedMissedFrontChamber{};
    std::uint64_t rejectedNoPrimaryInteraction{};
    std::uint64_t rejectedWrongFirstInteraction{};
    std::uint64_t rejectedMissingSecondInteraction{};
    std::uint64_t rejectedWrongSecondInteraction{};
    std::uint64_t rejectedLayerThreshold{};
    std::uint64_t rejectedTruthKinematics{};

    std::uint64_t selectedTruth{};
    std::uint64_t detectorKinematicsValid{};
    std::uint64_t detectorKinematicsInvalid{};
};

#endif
