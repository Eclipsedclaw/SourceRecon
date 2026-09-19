#ifndef DOPPLER_V7_EXPERIMENT_PHYSICS_LIST_HH
#define DOPPLER_V7_EXPERIMENT_PHYSICS_LIST_HH

#include "G4VModularPhysicsList.hh"

class ConfigManager;

// 三组实验只通过这个类切换 Compton 模型，其余过程保持完全一致。
class ExperimentPhysicsList final : public G4VModularPhysicsList
{
public:
    explicit ExperimentPhysicsList(const ConfigManager& config);
    ~ExperimentPhysicsList() override = default;

    void ConstructParticle() override;
    void ConstructProcess() override;
    void SetCuts() override;

private:
    void addElectromagneticPhysics();

    const ConfigManager* config_{};
};

#endif
