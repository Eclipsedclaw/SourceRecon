#pragma once
#include "RunAction.hh"
#include <G4UserEventAction.hh>

class EventAction final : public G4UserEventAction
{
  public:
    EventAction(const ConfigManager& config, const SimulationGrid& grid, const RunContext& context, RunAction& run)
        : config_{config}, grid_{grid}, context_{context}, run_{run}
    {
    }
    void EndOfEventAction(const G4Event* event) override;

  private:
    const ConfigManager& config_;
    const SimulationGrid& grid_;
    const RunContext& context_;
    RunAction& run_;
    int collectionId_ = -1; // 每个线程单独缓存自己的 collection ID。
};
