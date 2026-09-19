#pragma once
#include "EfficiencyRun.hh"
#include "IEmissionConePolicy.hh"
#include "ISourceGeometry.hh"
#include "SimulationGrid.hh"
#include <G4UserRunAction.hh>
#include <memory>

class RunAction final : public G4UserRunAction
{
  public:
    RunAction(const Campaign& campaign, const SimulationGrid& grid, const RunContext& context,
              std::shared_ptr<const ISourceGeometry> source, std::shared_ptr<const IEmissionConePolicy> cone,
              const nlohmann::json& software);
    G4Run* GenerateRun() override;
    void EndOfRunAction(const G4Run* run) override;
    void recordEvent(std::uint64_t cell, bool front, bool rear, bool hit);

  private:
    const Campaign& campaign_;
    const SimulationGrid& grid_;
    const RunContext& context_;
    std::shared_ptr<const ISourceGeometry> source_;
    std::shared_ptr<const IEmissionConePolicy> cone_;
    const nlohmann::json& software_;
    EfficiencyRun* current_{}; // 所有权属于 Geant4，本类只借用本线程的 Run。
};
