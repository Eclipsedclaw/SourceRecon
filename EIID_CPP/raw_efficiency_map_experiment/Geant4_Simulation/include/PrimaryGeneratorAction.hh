#ifndef EIID_V7_PRIMARY_GENERATOR_ACTION_HH
#define EIID_V7_PRIMARY_GENERATOR_ACTION_HH

#include "G4VUserPrimaryGeneratorAction.hh"

#include <memory>

class ConfigManager;
class G4Event;
class G4ParticleGun;
class IEmissionConePolicy;
class ISourceGeometry;
class SimulationGrid;

class PrimaryGeneratorAction final : public G4VUserPrimaryGeneratorAction
{
public:
    PrimaryGeneratorAction(
        const ConfigManager& config,
        const SimulationGrid& grid,
        std::shared_ptr<const ISourceGeometry> sourceGeometry,
        std::shared_ptr<const IEmissionConePolicy> conePolicy
    );
    ~PrimaryGeneratorAction() override;
    void GeneratePrimaries(G4Event* event) override;

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};
    std::shared_ptr<const ISourceGeometry> sourceGeometry_;
    std::shared_ptr<const IEmissionConePolicy> conePolicy_;
    std::unique_ptr<G4ParticleGun> particleGun_;
    // 粒子枪默认已有 geantino，不能用“指针非空”表示配置已生效。
    // 这个标志只记录本类是否明确设置过 JSON 指定的粒子。
    bool particleConfigured_{};
};

#endif
