#ifndef DOPPLER_V7_EXPERIMENT_FIXED_POINT_SOURCE_ACTION_HH
#define DOPPLER_V7_EXPERIMENT_FIXED_POINT_SOURCE_ACTION_HH

#include "G4ThreeVector.hh"
#include "G4VUserPrimaryGeneratorAction.hh"

#include <memory>

class AutoBoundingConePolicy;
class ConfigManager;
class DetectorGeometryInfo;
class G4Event;
class G4ParticleGun;

// “点源”表示所有事例都从同一个空间坐标发出。
// 为了不把绝大多数光子浪费在远离相机的方向上，动量方向仍在一个小锥内随机。
class FixedPointSourceAction final : public G4VUserPrimaryGeneratorAction
{
public:
    FixedPointSourceAction(
        const ConfigManager& config,
        const DetectorGeometryInfo& geometry
    );
    ~FixedPointSourceAction() override;

    void GeneratePrimaries(G4Event* event) override;

    const G4ThreeVector& sourcePosition() const;

private:
    const ConfigManager* config_{};
    G4ThreeVector sourcePosition_;
    std::unique_ptr<AutoBoundingConePolicy> conePolicy_;
    std::unique_ptr<G4ParticleGun> particleGun_;
    bool particleConfigured_{};
};

#endif
