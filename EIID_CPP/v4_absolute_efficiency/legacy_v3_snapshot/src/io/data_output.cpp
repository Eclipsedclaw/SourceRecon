#include "data_output.h"

#include "grid.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <filesystem>
#include <stdexcept>

void saveImageToFile(
    const std::vector<Decimal>& image,
    const Grid& grid,
    const ReconConfig& config
)
{
    if (image.empty())
    {
        throw std::runtime_error{"Cannot save an empty EIID image."};
    }

    if (image.size() != grid.cells().size())
    {
        throw std::runtime_error{"EIID image size does not match the Grid cell count."};
    }

    const std::filesystem::path parent =
        config.outputResultFile().parent_path();

    if (!parent.empty())
    {
        std::filesystem::create_directories(parent);
    }

    TFile outputFile{config.outputResultFile().string().c_str(), "RECREATE"};

    if (outputFile.IsZombie())
    {
        throw std::runtime_error{"Cannot create result ROOT file: " + config.outputResultFile().string()};
    }

    TTree resultTree{
        config.outputResultTree().c_str(),
        "EIID V3 direction-energy image"
    };

    ULong64_t cellIndex = 0;
    ULong64_t healpixPixelId = 0;
    Double_t weight = 0.0;
    Double_t thetaDegree = 0.0;
    Double_t phiDegree = 0.0;
    Double_t directionX = 0.0;
    Double_t directionY = 0.0;
    Double_t directionZ = 0.0;
    Double_t energyMeV = 0.0;

    const ResultBranchNames& branches = config.resultBranches();
    resultTree.Branch(branches.cellIndex.c_str(), &cellIndex);
    resultTree.Branch(branches.weight.c_str(), &weight);
    resultTree.Branch(branches.healpixPixelId.c_str(), &healpixPixelId);
    resultTree.Branch(branches.thetaDegree.c_str(), &thetaDegree);
    resultTree.Branch(branches.phiDegree.c_str(), &phiDegree);
    resultTree.Branch(branches.directionX.c_str(), &directionX);
    resultTree.Branch(branches.directionY.c_str(), &directionY);
    resultTree.Branch(branches.directionZ.c_str(), &directionZ);
    resultTree.Branch(branches.energyMeV.c_str(), &energyMeV);

    for (std::size_t index = 0; index < image.size(); ++index)
    {
        const Cell& cell = grid.cells()[index];
        cellIndex = static_cast<ULong64_t>(index);
        healpixPixelId = static_cast<ULong64_t>(cell.healpixPixelId);
        weight = static_cast<Double_t>(image[index]);
        thetaDegree = static_cast<Double_t>(cell.directionAngleDegree);
        phiDegree = static_cast<Double_t>(cell.directionPhiDegree);
        directionX = static_cast<Double_t>(cell.sourceDirection.x);
        directionY = static_cast<Double_t>(cell.sourceDirection.y);
        directionZ = static_cast<Double_t>(cell.sourceDirection.z);
        energyMeV = static_cast<Double_t>(cell.energyMeV);

        if (resultTree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling the EIID V3 result tree."};
        }
    }

    TParameter<int>{"healpix_nside", grid.healpixNside()}.Write();
    TNamed{"healpix_ordering", "RING"}.Write();
    TParameter<Long64_t>{
        "direction_count",
        static_cast<Long64_t>(grid.directionCount())
    }.Write();
    TParameter<Long64_t>{
        "energy_count",
        static_cast<Long64_t>(grid.energyCount())
    }.Write();

    if (resultTree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write the EIID V3 result tree."};
    }

    outputFile.Close();
}
