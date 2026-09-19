#ifndef EIID_V6_ROOT_WRITER_H
#define EIID_V6_ROOT_WRITER_H

#include <cstdint>
#include <memory>
#include <vector>

class ConfigManager;
class IEmissionConePolicy;
class ISourceGeometry;
class SimulationGrid;
class TFile;
class TTree;

struct CompactEventRecord
{
    std::int64_t eventId{};
    std::int64_t sourceCellIndex{};
    double r1X{};
    double r1Y{};
    double r1Z{};
    double r2X{};
    double r2Y{};
    double r2Z{};
    double e1MeV{};
};

class RootWriter
{
public:
    RootWriter(
        const ConfigManager& config,
        const SimulationGrid& grid,
        std::shared_ptr<const ISourceGeometry> sourceGeometry,
        std::shared_ptr<const IEmissionConePolicy> conePolicy
    );
    ~RootWriter();
    RootWriter(const RootWriter&) = delete;
    RootWriter& operator=(const RootWriter&) = delete;

    void beginEventOutput();
    void writeCompactEvent(const CompactEventRecord& event);
    void finishEventOutput();
    void writeEfficiencyOutput(
        const std::vector<std::uint64_t>& emittedCounts,
        const std::vector<std::uint64_t>& validCounts
    ) const;

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};
    std::shared_ptr<const ISourceGeometry> sourceGeometry_;
    std::shared_ptr<const IEmissionConePolicy> conePolicy_;
    std::unique_ptr<TFile> eventFile_;
    TTree* eventTree_{};
    CompactEventRecord eventBuffer_;
};

#endif
