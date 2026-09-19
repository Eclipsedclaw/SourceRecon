#ifndef EIID_V7_RUN_ACTION_HH
#define EIID_V7_RUN_ACTION_HH

#include "G4UserRunAction.hh"
#include "root_writer.h"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

class ConfigManager;
class G4Run;
class IEmissionConePolicy;
class ISourceGeometry;
class SimulationGrid;

class RunAction final : public G4UserRunAction
{
public:
    RunAction(
        const ConfigManager& config,
        const SimulationGrid& grid,
        std::shared_ptr<const ISourceGeometry> sourceGeometry,
        std::shared_ptr<const IEmissionConePolicy> conePolicy
    );
    ~RunAction() override;
    void BeginOfRunAction(const G4Run*) override;
    void EndOfRunAction(const G4Run*) override;
    void recordEvent(std::size_t flatCellIndex, bool frontPassed, bool rearPassed, bool hasRecordedHit);
    void recordCompactEvent(const CompactEventRecord& event);

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};
    std::vector<std::uint64_t> emittedCounts_;
    std::vector<std::uint64_t> validCounts_;
    // 只增加少量运行摘要，不输出逐 Step 的大文件。
    std::uint64_t eventsWithHits_{};
    std::uint64_t frontPassedEvents_{};
    std::uint64_t rearPassedEvents_{};
    std::unique_ptr<RootWriter> writer_;
};

#endif
