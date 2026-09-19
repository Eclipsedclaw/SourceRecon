#include "ResamplerIO.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>

namespace
{
void requireBranch(TTree& tree, const char* branchName)
{
    if (tree.GetBranch(branchName) == nullptr)
    {
        throw std::runtime_error{"Missing sensitivity branch: " + std::string{branchName}};
    }
}
}

SensitivityMatrix ResamplerIO::read(
    const std::filesystem::path& filePath,
    const std::string& treeName,
    const Grid& grid
)
{
    std::unique_ptr<TFile> inputFile{
        TFile::Open(filePath.string().c_str(), "READ")
    };

    if (!inputFile || inputFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open Master sensitivity file: " + filePath.string()};
    }

    TTree* tree = inputFile->Get<TTree>(treeName.c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find Master sensitivity tree: " + treeName};
    }

    requireBranch(*tree, "direction_index");
    requireBranch(*tree, "energy_index");
    requireBranch(*tree, "healpix_pixel_id");
    requireBranch(*tree, "energy_MeV");
    requireBranch(*tree, "sensitivity");

    const auto* storedNside = inputFile->Get<TParameter<int>>(
        "healpix_nside"
    );
    const auto* storedOrdering = inputFile->Get<TNamed>(
        "healpix_ordering"
    );
    const auto* storedDirectionCount = inputFile->Get<TParameter<Long64_t>>(
        "direction_count"
    );
    const auto* storedEnergyCount = inputFile->Get<TParameter<Long64_t>>(
        "energy_count"
    );

    if (storedNside == nullptr || storedOrdering == nullptr ||
        storedDirectionCount == nullptr ||
        storedEnergyCount == nullptr)
    {
        throw std::runtime_error{
            "Master sensitivity file is missing mandatory grid metadata."
        };
    }

    if (std::string{storedOrdering->GetTitle()} != "RING" ||
        storedNside->GetVal() != grid.healpixNside() ||
        storedDirectionCount->GetVal() !=
            static_cast<Long64_t>(grid.directionCount()) ||
        storedEnergyCount->GetVal() !=
            static_cast<Long64_t>(grid.energyCount()))
    {
        throw std::runtime_error{
            "Master sensitivity metadata does not match its configured grid."
        };
    }

    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> directionIndex{reader, "direction_index"};
    TTreeReaderValue<ULong64_t> energyIndex{reader, "energy_index"};
    TTreeReaderValue<ULong64_t> healpixPixelId{
        reader,
        "healpix_pixel_id"
    };
    TTreeReaderValue<Double_t> energyMeV{reader, "energy_MeV"};
    TTreeReaderValue<Double_t> sensitivity{reader, "sensitivity"};

    SensitivityMatrix matrix{grid.directionCount(), grid.energyCount()};

    while (reader.Next())
    {
        const std::size_t direction =
            static_cast<std::size_t>(*directionIndex);
        const std::size_t energy =
            static_cast<std::size_t>(*energyIndex);

        if (*healpixPixelId != *directionIndex)
        {
            throw std::runtime_error{
                "Master healpix_pixel_id does not match direction_index."
            };
        }

        const Decimal configuredEnergy = grid.energy(energy);
        const Decimal storedEnergy = static_cast<Decimal>(*energyMeV);
        const Decimal scale = std::max(
            static_cast<Decimal>(1.0L),
            std::abs(configuredEnergy)
        );

        if (std::abs(storedEnergy - configuredEnergy) >
            static_cast<Decimal>(1.0e-10L) * scale)
        {
            throw std::runtime_error{
                "Master sensitivity energy coordinates do not match the configured grid."
            };
        }

        matrix.set(
            direction,
            energy,
            static_cast<Decimal>(*sensitivity)
        );
    }

    matrix.requireComplete();
    return matrix;
}

void ResamplerIO::write(
    const std::filesystem::path& filePath,
    const std::string& treeName,
    const Grid& grid,
    const SensitivityMatrix& sensitivity
)
{
    if (sensitivity.directionCount() != grid.directionCount() ||
        sensitivity.energyCount() != grid.energyCount())
    {
        throw std::runtime_error{"Target sensitivity dimensions do not match the Target grid."};
    }

    sensitivity.requireComplete();

    TFile outputFile{filePath.string().c_str(), "RECREATE"};

    if (outputFile.IsZombie())
    {
        throw std::runtime_error{"Cannot create Target sensitivity file: " + filePath.string()};
    }

    TTree tree{treeName.c_str(), "Resampled HEALPix sensitivity"};

    ULong64_t cellIndex = 0;
    ULong64_t directionIndex = 0;
    ULong64_t energyIndex = 0;
    ULong64_t healpixPixelId = 0;
    ULong64_t emittedCount = 0;
    ULong64_t validCount = 0;
    Double_t thetaDegree = 0.0;
    Double_t phiDegree = 0.0;
    Double_t directionX = 0.0;
    Double_t directionY = 0.0;
    Double_t directionZ = 0.0;
    Double_t energyMeV = 0.0;
    Double_t value = 0.0;

    tree.Branch("cell_index", &cellIndex);
    tree.Branch("direction_index", &directionIndex);
    tree.Branch("energy_index", &energyIndex);
    tree.Branch("healpix_pixel_id", &healpixPixelId);
    tree.Branch("theta_degree", &thetaDegree);
    tree.Branch("phi_degree", &phiDegree);
    tree.Branch("direction_x", &directionX);
    tree.Branch("direction_y", &directionY);
    tree.Branch("direction_z", &directionZ);
    tree.Branch("energy_MeV", &energyMeV);
    tree.Branch("emitted_count", &emittedCount);
    tree.Branch("valid_count", &validCount);
    tree.Branch("sensitivity", &value);

    for (const Cell& cell : grid.cells())
    {
        cellIndex = static_cast<ULong64_t>(
            cell.directionIndex * grid.energyCount() + cell.energyIndex
        );

        directionIndex = static_cast<ULong64_t>(cell.directionIndex);
        energyIndex = static_cast<ULong64_t>(cell.energyIndex);
        healpixPixelId = static_cast<ULong64_t>(cell.healpixPixelId);
        thetaDegree = static_cast<Double_t>(cell.directionAngleDegree);
        phiDegree = static_cast<Double_t>(cell.directionPhiDegree);
        directionX = static_cast<Double_t>(cell.sourceDirection.x);
        directionY = static_cast<Double_t>(cell.sourceDirection.y);
        directionZ = static_cast<Double_t>(cell.sourceDirection.z);
        energyMeV = static_cast<Double_t>(cell.energyMeV);
        value = static_cast<Double_t>(
            sensitivity.at(cell.directionIndex, cell.energyIndex)
        );

        if (tree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling Target sensitivity tree."};
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
        throw std::runtime_error{"Failed to write Target sensitivity tree."};
    }

    outputFile.Close();
}
