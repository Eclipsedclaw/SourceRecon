#ifndef EIID_V7_RECON_CONFIG_H
#define EIID_V7_RECON_CONFIG_H

#include "Common.h"
#include "ResponseKernelFactory.h"

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

struct EfficiencyBranchNames
{
    std::string cellIndex;
    std::string efficiency;
};

class ReconConfig
{
public:
    explicit ReconConfig(const std::filesystem::path& configPath);

    const std::filesystem::path& inputEventsFile() const;
    const std::string& inputEventsTree() const;
    const std::filesystem::path& outputResultFile() const;
    const std::string& outputResultTree() const;
    const std::filesystem::path& efficiencyFile() const;
    const std::string& efficiencyTree() const;
    int healpixNside() const;
    const std::string& healpixOrdering() const;
    int energyPointCount() const;
    Decimal energyMinMeV() const;
    Decimal energyMaxMeV() const;
    int iterationCount() const;
    Decimal responseSigmaDegree() const;
    const ResponseKernelConfig& responseKernel() const;
    Decimal denominatorFloor() const;
    const EventBranchNames& eventBranches() const;
    const ResultBranchNames& resultBranches() const;
    const EfficiencyBranchNames& efficiencyBranches() const;

private:
    std::filesystem::path inputEventsFile_;
    std::string inputEventsTree_;
    std::filesystem::path outputResultFile_;
    std::string outputResultTree_;
    std::filesystem::path efficiencyFile_;
    std::string efficiencyTree_;
    int healpixNside_{};
    std::string healpixOrdering_;
    int energyPointCount_{};
    Decimal energyMinMeV_{};
    Decimal energyMaxMeV_{};
    int iterationCount_{};
    Decimal responseSigmaDegree_{};
    ResponseKernelConfig responseKernel_;
    Decimal denominatorFloor_{};
    EventBranchNames eventBranches_;
    ResultBranchNames resultBranches_;
    EfficiencyBranchNames efficiencyBranches_;
};

#endif
