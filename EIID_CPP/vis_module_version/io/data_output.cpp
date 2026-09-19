// D:\CodexForSR\EIID_CPP\io_translator_version\io\data_output.cpp

#include "data_output.h"
#include "grid.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>

#include <stdexcept>

void saveImageToFile(const std::vector<Decimal>& image, const Grid& grid, const IoConfig& config)
{
    if (image.empty())
    {
        throw std::runtime_error{"Cannot save an empty EIID image."};
    }

    // runEiid() 返回的 image 与 Grid::cells() 使用完全相同的一维排列。
    // 若二者长度不同，继续按下标访问会得到错误的物理坐标，甚至越界。
    if (image.size() != grid.cells().size())
    {
        throw std::runtime_error{"EIID image size does not match the Grid cell count."};
    }

    TFile outputFile{config.outputResultPath.c_str(), "RECREATE"};

    if (outputFile.IsZombie())
    {
        throw std::runtime_error{"Cannot create ROOT output file: " + config.outputResultPath};
    }

    TTree resultTree{config.outputTreeName.c_str(), "EIID direction-energy image"};

    // cellIndex 保留原先的一维下标，便于旧分析代码继续使用。
    ULong64_t cellIndex = 0;
    Decimal weight = static_cast<Decimal>(0.0L);

    // 以下变量给一维 cell 添加可直接理解的物理含义。
    // Double_t 是 ROOT 对 double 的类型别名，能稳定写入 ROOT 的 Double_t 分支。
    ULong64_t healpixPixelId = 0;
    Double_t thetaDegree = 0.0;
    Double_t phiDegree = 0.0;
    Double_t directionX = 0.0;
    Double_t directionY = 0.0;
    Double_t directionZ = 0.0;
    Double_t energyMeV = 0.0;

    resultTree.Branch(config.outputCellIndexBranchName.c_str(), &cellIndex);
    resultTree.Branch(config.outputWeightBranchName.c_str(), &weight);
    resultTree.Branch("healpix_pixel_id", &healpixPixelId);
    resultTree.Branch("theta_degree", &thetaDegree);
    resultTree.Branch("phi_degree", &phiDegree);
    resultTree.Branch("direction_x", &directionX);
    resultTree.Branch("direction_y", &directionY);
    resultTree.Branch("direction_z", &directionZ);
    resultTree.Branch("energy_MeV", &energyMeV);

    for (std::size_t index = 0; index < image.size(); ++index)
    {
        // image[index] 与 grid.cells()[index] 描述的是同一个方向－能量 cell。
        // 这里直接读取 Grid 已经生成好的 Cell，不在输出模块中重复计算 HEALPix。
        const Cell& cell = grid.cells()[index];

        cellIndex = static_cast<ULong64_t>(index);
        weight = image[index];
        healpixPixelId = static_cast<ULong64_t>(cell.healpixPixelId);
        thetaDegree = static_cast<Double_t>(cell.directionAngleDegree);
        phiDegree = static_cast<Double_t>(cell.directionPhiDegree);
        directionX = static_cast<Double_t>(cell.sourceDirection.x);
        directionY = static_cast<Double_t>(cell.sourceDirection.y);
        directionZ = static_cast<Double_t>(cell.sourceDirection.z);
        energyMeV = static_cast<Double_t>(cell.energyMeV);

        if (resultTree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling the ROOT output tree."};
        }
    }

    if (resultTree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write the EIID image tree."};
    }

    outputFile.Close();
}
