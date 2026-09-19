#pragma once
#include "RunAction.hh"
#include <G4VUserActionInitialization.hh>

class ActionInitialization final : public G4VUserActionInitialization
{
  public:
    ActionInitialization(const Campaign& campaign, const SimulationGrid& grid, const RunContext& context,
                         std::shared_ptr<const ISourceGeometry> source, std::shared_ptr<const IEmissionConePolicy> cone,
                         const nlohmann::json& software);
    void BuildForMaster() const override;
    void Build() const override;

  private:
    RunAction* makeRunAction() const;
    const Campaign& campaign_;
    const SimulationGrid& grid_;
    const RunContext& context_;
    std::shared_ptr<const ISourceGeometry> source_;
    std::shared_ptr<const IEmissionConePolicy> cone_;
    const nlohmann::json& software_;
};
