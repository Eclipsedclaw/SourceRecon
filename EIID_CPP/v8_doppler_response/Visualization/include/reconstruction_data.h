#ifndef EIID_RECONSTRUCTION_DATA_H
#define EIID_RECONSTRUCTION_DATA_H

#include "vis_config.h"

#include <cstdint>
#include <vector>

// ImageCell 对应结果树中的一行，即一个“方向－能量”联合 cell。
struct ImageCell
{
    std::uint64_t cellIndex;
    std::uint64_t healpixPixelId;

    double thetaDegree;
    double phiDegree;

    double directionX;
    double directionY;
    double directionZ;

    double energyMeV;
    double weight;
};

struct ReconstructionData
{
    std::vector<ImageCell> cells;
};

// ROOT 的读取细节集中在这里，具体 Plotter 只接收普通 C++ 数据。
class ReconstructionDataReader
{
public:
    static ReconstructionData read(const VisConfig& config);
};

#endif
