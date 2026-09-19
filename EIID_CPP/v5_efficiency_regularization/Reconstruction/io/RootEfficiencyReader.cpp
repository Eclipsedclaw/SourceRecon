#include "RootEfficiencyReader.h"

#include "EfficiencyFileSchema.h"
#include "IGrid.h"
#include "ReconConfig.h"

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
template <typename T>
const T& requireObject(TFile& file, const char* name)
{
    const T* object = file.Get<T>(name);

    if (object == nullptr)
    {
        throw std::runtime_error{"Missing efficiency metadata: " + std::string{name}};
    }

    return *object;
}

bool nearlyEqual(double left, double right)
{
    const double scale = std::max({1.0, std::abs(left), std::abs(right)});
    return std::abs(left - right) <= 1.0e-10 * scale;
}
}

AbsoluteEfficiencyMap RootEfficiencyReader::read(
    const ReconConfig& config,
    const IGrid& grid
)
{
    std::unique_ptr<TFile> file{
        TFile::Open(config.efficiencyFile().string().c_str(), "READ")
    };

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{
            "Cannot open absolute-efficiency file: " +
            config.efficiencyFile().string()
        };
    }

    TTree* tree = file->Get<TTree>(config.efficiencyTree().c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find efficiency tree: " + config.efficiencyTree()};
    }

    const auto& branches = config.efficiencyBranches();

    if (tree->GetBranch(branches.cellIndex.c_str()) == nullptr ||
        tree->GetBranch(branches.efficiency.c_str()) == nullptr)
    {
        throw std::runtime_error{"Efficiency tree requires cell_index and efficiency."};
    }

    const auto& nside = requireObject<TParameter<int>>(
        *file,
        EfficiencyFileSchema::nsideMetadata
    );
    const auto& ordering = requireObject<TNamed>(
        *file,
        EfficiencyFileSchema::orderingMetadata
    );
    const auto& directionCount = requireObject<TParameter<Long64_t>>(
        *file,
        EfficiencyFileSchema::directionCountMetadata
    );
    const auto& energyCount = requireObject<TParameter<Long64_t>>(
        *file,
        EfficiencyFileSchema::energyCountMetadata
    );
    const auto& energyMin = requireObject<TParameter<double>>(
        *file,
        EfficiencyFileSchema::energyMinMetadata
    );
    const auto& energyMax = requireObject<TParameter<double>>(
        *file,
        EfficiencyFileSchema::energyMaxMetadata
    );
    const auto& sourceRadius = requireObject<TParameter<double>>(
        *file,
        EfficiencyFileSchema::sourceRadiusMetadata
    );
    const auto& definition = requireObject<TNamed>(
        *file,
        EfficiencyFileSchema::definitionMetadata
    );

    if (nside.GetVal() != grid.healpixNside() ||
        std::string{ordering.GetTitle()} != "RING" ||
        directionCount.GetVal() != static_cast<Long64_t>(grid.directionCount()) ||
        energyCount.GetVal() != static_cast<Long64_t>(grid.energyCount()) ||
        !nearlyEqual(energyMin.GetVal(), grid.energy(0)) ||
        !nearlyEqual(energyMax.GetVal(), grid.energy(grid.energyCount() - 1)) ||
        !(sourceRadius.GetVal() > 0.0) ||
        std::string{definition.GetTitle()} !=
            EfficiencyFileSchema::efficiencyDefinition)
    {
        throw std::runtime_error{
            "Absolute-efficiency metadata does not match the reconstruction grid or definition."
        };
    }

    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> cellIndex{
        reader,
        branches.cellIndex.c_str()
    };
    TTreeReaderValue<Double_t> efficiency{
        reader,
        branches.efficiency.c_str()
    };
    AbsoluteEfficiencyMap result{grid.directionCount(), grid.energyCount()};

    while (reader.Next())
    {
        result.setFlat(
            static_cast<std::size_t>(*cellIndex),
            static_cast<Decimal>(*efficiency)
        );
    }

    result.requireComplete();
    return result;
}
