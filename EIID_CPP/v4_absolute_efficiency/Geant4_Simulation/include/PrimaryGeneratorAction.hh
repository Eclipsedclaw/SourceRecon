#ifndef EIID_V4_PRIMARY_GENERATOR_ACTION_HH
#define EIID_V4_PRIMARY_GENERATOR_ACTION_HH

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
};

#endif
