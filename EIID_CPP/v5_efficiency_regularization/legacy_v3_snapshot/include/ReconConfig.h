#ifndef EIID_RECON_CONFIG_H
#define EIID_RECON_CONFIG_H

#include "common.h"

#include <filesystem>
#include <string>

struct EventBranchNames
{
    std::string r1X;
    std::string r1Y;
    std::string r1Z;
    std::string r2X;
    std::string r2Y;
    std::string r2Z;
    std::string e1MeV;
};

struct ResultBranchNames
{
    std::string cellIndex;
    std::string weight;
    std::string healpixPixelId;
    std::string thetaDegree;
    std::string phiDegree;
    std::string directionX;
    std::string directionY;
    std::string directionZ;
    std::string energyMeV;
};

struct SensitivityBranchNames
{
    std::string directionIndex;
    std::string energyIndex;
    std::string healpixPixelId;
    std::string energyMeV;
    std::string sensitivity;
};

// ReconConfig 是 V3 重建器唯一的运行参数入口。
// 相对路径始终以 recon_config.json 所在目录为基准解析。
class ReconConfig
{
public:
    explicit ReconConfig(const std::filesystem::path& configPath);

    const std::filesystem::path& inputEventsFile() const;
    const std::string& inputEventsTree() const;
    const std::filesystem::path& outputResultFile() const;
    const std::string& outputResultTree() const;
    const std::filesystem::path& sensitivityFile() const;
    const std::string& sensitivityTree() const;

    int healpixNside() const;
    const std::string& healpixOrdering() const;
    int energyPointCount() const;
    Decimal energyMinMeV() const;
    Decimal energyMaxMeV() const;

    int iterationCount() const;
    Decimal responseSigmaDegree() const;
    Decimal denominatorFloor() const;
    bool requireCompleteSensitivity() const;

    const EventBranchNames& eventBranches() const;
    const ResultBranchNames& resultBranches() const;
    const SensitivityBranchNames& sensitivityBranches() const;

private:
    std::filesystem::path inputEventsFile_;
    std::string inputEventsTree_;
    std::filesystem::path outputResultFile_;
    std::string outputResultTree_;
    std::filesystem::path sensitivityFile_;
    std::string sensitivityTree_;

    int healpixNside_ = 0;
    std::string healpixOrdering_;
    int energyPointCount_ = 0;
    Decimal energyMinMeV_ = static_cast<Decimal>(0.0L);
    Decimal energyMaxMeV_ = static_cast<Decimal>(0.0L);

    int iterationCount_ = 0;
    Decimal responseSigmaDegree_ = static_cast<Decimal>(0.0L);
    Decimal denominatorFloor_ = static_cast<Decimal>(0.0L);
    bool requireCompleteSensitivity_ = true;

    EventBranchNames eventBranches_;
    ResultBranchNames resultBranches_;
    SensitivityBranchNames sensitivityBranches_;
};

#endif
