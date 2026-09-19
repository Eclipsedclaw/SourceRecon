#include "sensitivity_reader.h"

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
void requireBranch(TTree& tree, const std::string& branchName)
{
    if (tree.GetBranch(branchName.c_str()) == nullptr)
    {
        throw std::runtime_error{"Missing sensitivity ROOT branch: " + branchName};
    }
}
}

SensitivityMatrix readSensitivityFromRoot(
    const ReconConfig& config,
    const Grid& grid
)
{
    std::unique_ptr<TFile> inputFile{
        TFile::Open(config.sensitivityFile().string().c_str(), "READ")
    };

    if (!inputFile || inputFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open sensitivity ROOT file: " + config.sensitivityFile().string()};
    }

    TTree* tree = inputFile->Get<TTree>(config.sensitivityTree().c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find sensitivity tree: " + config.sensitivityTree()};
    }

    const SensitivityBranchNames& branches = config.sensitivityBranches();
    requireBranch(*tree, branches.directionIndex);
    requireBranch(*tree, branches.energyIndex);
    requireBranch(*tree, branches.healpixPixelId);
    requireBranch(*tree, branches.energyMeV);
    requireBranch(*tree, branches.sensitivity);

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
            "Sensitivity ROOT file is missing mandatory grid metadata."
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
            "Sensitivity ROOT metadata does not match the reconstruction grid."
        };
    }

    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> directionIndex{
        reader,
        branches.directionIndex.c_str()
    };

    TTreeReaderValue<ULong64_t> energyIndex{
        reader,
        branches.energyIndex.c_str()
    };

    TTreeReaderValue<ULong64_t> healpixPixelId{
        reader,
        branches.healpixPixelId.c_str()
    };

    TTreeReaderValue<Double_t> energyMeV{
        reader,
        branches.energyMeV.c_str()
    };

    TTreeReaderValue<Double_t> sensitivity{
        reader,
        branches.sensitivity.c_str()
    };

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
                "Sensitivity healpix_pixel_id does not match direction_index."
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
                "Sensitivity energy coordinates do not match the reconstruction grid."
            };
        }

        matrix.set(
            direction,
            energy,
            static_cast<Decimal>(*sensitivity)
        );
    }

    if (config.requireCompleteSensitivity())
    {
        matrix.requireComplete();
    }

    return matrix;
}
