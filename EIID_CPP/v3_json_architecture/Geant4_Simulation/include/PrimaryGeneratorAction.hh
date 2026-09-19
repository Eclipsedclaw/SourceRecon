#ifndef EIID_V3_PRIMARY_GENERATOR_ACTION_HH
#define EIID_V3_PRIMARY_GENERATOR_ACTION_HH

#include "G4VUserPrimaryGeneratorAction.hh"

#include <memory>

class ConfigManager;
class G4Event;
class G4ParticleGun;
class SimulationGrid;

class PrimaryGeneratorAction final : public G4VUserPrimaryGeneratorAction
{
public:
    PrimaryGeneratorAction(
        const ConfigManager& config,
        const SimulationGrid& grid
    );
    ~PrimaryGeneratorAction() override;

    void GeneratePrimaries(G4Event* event) override;

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};
    std::unique_ptr<G4ParticleGun> particleGun_;
};

#endif
