#include "RootImageWriter.h"

#include "IGrid.h"
#include "ReconConfig.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <filesystem>
#include <stdexcept>

void RootImageWriter::write(
    const std::vector<Decimal>& image,
    const IGrid& grid,
    const ReconConfig& config
)
{
    if (image.empty() || image.size() != grid.cells().size())
    {
        throw std::runtime_error{"Image size does not match the reconstruction grid."};
    }

    const auto parent = config.outputResultFile().parent_path();

    if (!parent.empty())
    {
        std::filesystem::create_directories(parent);
    }

    TFile file{config.outputResultFile().string().c_str(), "RECREATE"};

    if (file.IsZombie())
    {
        throw std::runtime_error{
            "Cannot create result file: " + config.outputResultFile().string()
        };
    }

    TTree tree{config.outputResultTree().c_str(), "EIID V8 direction-energy image"};
    ULong64_t cellIndex{};
    ULong64_t pixelId{};
    Double_t weight{};
    Double_t theta{};
    Double_t phi{};
    Double_t x{};
    Double_t y{};
    Double_t z{};
    Double_t energy{};
    const auto& names = config.resultBranches();

    tree.Branch(names.cellIndex.c_str(), &cellIndex);
    tree.Branch(names.weight.c_str(), &weight);
    tree.Branch(names.healpixPixelId.c_str(), &pixelId);
    tree.Branch(names.thetaDegree.c_str(), &theta);
    tree.Branch(names.phiDegree.c_str(), &phi);
    tree.Branch(names.directionX.c_str(), &x);
    tree.Branch(names.directionY.c_str(), &y);
    tree.Branch(names.directionZ.c_str(), &z);
    tree.Branch(names.energyMeV.c_str(), &energy);

    for (std::size_t index = 0; index < image.size(); ++index)
    {
        const Cell& cell = grid.cells()[index];
        cellIndex = static_cast<ULong64_t>(index);
        pixelId = static_cast<ULong64_t>(cell.healpixPixelId);
        weight = static_cast<Double_t>(image[index]);
        theta = static_cast<Double_t>(cell.thetaDegree);
        phi = static_cast<Double_t>(cell.phiDegree);
        x = static_cast<Double_t>(cell.sourceDirection.x);
        y = static_cast<Double_t>(cell.sourceDirection.y);
        z = static_cast<Double_t>(cell.sourceDirection.z);
        energy = static_cast<Double_t>(cell.energyMeV);

        if (tree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling the result tree."};
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

    if (tree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write the result tree."};
    }

    file.Close();
}
