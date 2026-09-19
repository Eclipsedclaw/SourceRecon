#ifndef EIID_V4_SIMULATION_GRID_HH
#define EIID_V4_SIMULATION_GRID_HH

#include "ConfigManager.hh"

#include <cstddef>
#include <cstdint>
#include <vector>

struct SimulationCell
{
    std::size_t flatIndex{};
    std::size_t directionIndex{};
    std::size_t energyIndex{};
    std::int64_t healpixPixelId{};
    double directionX{};
    double directionY{};
    double directionZ{};
    double thetaDegree{};
    double phiDegree{};
    double energyMeV{};
};

// 该类只负责把 eventID 映射到“方向 × 能量”的 cell；不包含探测器物理。
class SimulationGrid
{
public:
    explicit SimulationGrid(const ConfigManager& config);

    std::size_t directionCount() const;
    std::size_t energyCount() const;
    std::size_t fullCellCount() const;
    std::size_t activeCellCount() const;
    std::uint64_t totalEventCount() const;

    const SimulationCell& fullCell(std::size_t flatIndex) const;
    const SimulationCell& cellForEvent(std::uint64_t eventId) const;

private:
    int particlesPerCell_{};
    std::size_t directionCount_{};
    std::size_t energyCount_{};
    std::vector<SimulationCell> fullCells_;
    std::vector<std::size_t> activeFlatIndices_;
};

#endif
