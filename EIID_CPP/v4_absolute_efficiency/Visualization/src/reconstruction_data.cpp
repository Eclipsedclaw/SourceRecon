#include "reconstruction_data.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <array>
#include <memory>
#include <stdexcept>
#include <string>

namespace
{
void requireBranches(TTree& tree)
{
    constexpr std::array<const char*, 9> branchNames{
        "cell_index",
        "weight",
        "healpix_pixel_id",
        "theta_degree",
        "phi_degree",
        "direction_x",
        "direction_y",
        "direction_z",
        "energy_MeV"
    };

    for (const char* branchName : branchNames)
    {
        if (tree.GetBranch(branchName) == nullptr)
        {
            throw std::runtime_error{"Missing ROOT branch in result tree: " + std::string{branchName}};
        }
    }
}
}

ReconstructionData ReconstructionDataReader::read(const VisConfig& config)
{
    std::unique_ptr<TFile> inputFile{
        TFile::Open(config.inputRootFilePath().string().c_str(), "READ")
    };

    if (!inputFile || inputFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open ROOT result file: " + config.inputRootFilePath().string()};
    }

    TTree* resultTree = inputFile->Get<TTree>(config.inputTreeName().c_str());

    if (resultTree == nullptr)
    {
        throw std::runtime_error{"Cannot find ROOT result tree: " + config.inputTreeName()};
    }

    requireBranches(*resultTree);

    TTreeReader reader{resultTree};
    TTreeReaderValue<ULong64_t> cellIndex{reader, "cell_index"};
    TTreeReaderValue<Double_t> weight{reader, "weight"};
    TTreeReaderValue<ULong64_t> healpixPixelId{reader, "healpix_pixel_id"};
    TTreeReaderValue<Double_t> thetaDegree{reader, "theta_degree"};
    TTreeReaderValue<Double_t> phiDegree{reader, "phi_degree"};
    TTreeReaderValue<Double_t> directionX{reader, "direction_x"};
    TTreeReaderValue<Double_t> directionY{reader, "direction_y"};
    TTreeReaderValue<Double_t> directionZ{reader, "direction_z"};
    TTreeReaderValue<Double_t> energyMeV{reader, "energy_MeV"};

    ReconstructionData data;
    data.cells.reserve(static_cast<std::size_t>(resultTree->GetEntries()));

    while (reader.Next())
    {
        data.cells.push_back(
            ImageCell{
                static_cast<std::uint64_t>(*cellIndex),
                static_cast<std::uint64_t>(*healpixPixelId),
                *thetaDegree,
                *phiDegree,
                *directionX,
                *directionY,
                *directionZ,
                *energyMeV,
                *weight
            }
        );
    }

    if (data.cells.empty())
    {
        throw std::runtime_error{"The ROOT result tree contains no image cells."};
    }

    return data;
}
