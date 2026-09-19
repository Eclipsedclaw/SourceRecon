#ifndef EIID_V3_ROOT_WRITER_H
#define EIID_V3_ROOT_WRITER_H

#include "ConfigManager.hh"
#include "SimulationGrid.hh"

#include <cstdint>
#include <memory>
#include <vector>

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

// ROOT 写盘集中在这个类中，Geant4 Action 不直接管理 TFile/TTree 生命周期。
class RootWriter
{
public:
    RootWriter(const ConfigManager& config, const SimulationGrid& grid);
    ~RootWriter();

    RootWriter(const RootWriter&) = delete;
    RootWriter& operator=(const RootWriter&) = delete;

    void beginEventOutput();
    void writeCompactEvent(const CompactEventRecord& event);
    void finishEventOutput();

    void writeSensitivityOutput(
        const std::vector<std::uint64_t>& emittedCounts,
        const std::vector<std::uint64_t>& validCounts
    ) const;

private:
    const ConfigManager* config_{};
    const SimulationGrid* grid_{};

    std::unique_ptr<TFile> eventFile_;
    TTree* eventTree_{};
    CompactEventRecord eventBuffer_;
};

#endif
