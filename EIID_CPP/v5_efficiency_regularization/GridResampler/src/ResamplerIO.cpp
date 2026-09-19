#include "ResamplerIO.h"

#include "EfficiencyFileSchema.h"
#include "IGrid.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <utility>

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

EfficiencyDataset ResamplerIO::read(
    const std::filesystem::path& path,
    const std::string& treeName,
    const IGrid& grid
)
{
    std::unique_ptr<TFile> file{TFile::Open(path.string().c_str(), "READ")};

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{"Cannot open Master efficiency file: " + path.string()};
    }

    TTree* tree = file->Get<TTree>(treeName.c_str());

    if (tree == nullptr ||
        tree->GetBranch(EfficiencyFileSchema::cellIndexBranch) == nullptr ||
        tree->GetBranch(EfficiencyFileSchema::efficiencyBranch) == nullptr)
    {
        throw std::runtime_error{"Master efficiency tree has an invalid schema."};
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
        throw std::runtime_error{"Master efficiency metadata does not match its configured grid."};
    }

    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> index{
        reader,
        EfficiencyFileSchema::cellIndexBranch
    };
    TTreeReaderValue<Double_t> value{
        reader,
        EfficiencyFileSchema::efficiencyBranch
    };
    AbsoluteEfficiencyMap map{grid.directionCount(), grid.energyCount()};

    while (reader.Next())
    {
        map.setFlat(
            static_cast<std::size_t>(*index),
            static_cast<Decimal>(*value)
        );
    }

    map.requireComplete();
    return EfficiencyDataset{std::move(map), sourceRadius.GetVal()};
}

void ResamplerIO::write(
    const std::filesystem::path& path,
    const std::string& treeName,
    const IGrid& grid,
    const AbsoluteEfficiencyMap& values,
    double sourceRadiusMm
)
{
    values.requireComplete();

    if (values.directionCount() != grid.directionCount() ||
        values.energyCount() != grid.energyCount() ||
        !(sourceRadiusMm > 0.0))
    {
        throw std::runtime_error{"Target efficiency data or source radius is invalid."};
    }

    if (!path.parent_path().empty())
    {
        std::filesystem::create_directories(path.parent_path());
    }

    TFile file{path.string().c_str(), "RECREATE"};

    if (file.IsZombie())
    {
        throw std::runtime_error{"Cannot create Target efficiency file: " + path.string()};
    }

    TTree tree{treeName.c_str(), "Direction-energy absolute detection efficiency"};
    ULong64_t cellIndex{};
    Double_t efficiency{};
    tree.Branch(EfficiencyFileSchema::cellIndexBranch, &cellIndex);
    tree.Branch(EfficiencyFileSchema::efficiencyBranch, &efficiency);

    for (std::size_t index = 0; index < values.size(); ++index)
    {
        cellIndex = static_cast<ULong64_t>(index);
        efficiency = static_cast<Double_t>(values.atFlat(index));

        if (tree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling Target efficiency tree."};
        }
    }

    TParameter<int>{EfficiencyFileSchema::nsideMetadata, grid.healpixNside()}.Write();
    TNamed{EfficiencyFileSchema::orderingMetadata, "RING"}.Write();
    TParameter<Long64_t>{
        EfficiencyFileSchema::directionCountMetadata,
        static_cast<Long64_t>(grid.directionCount())
    }.Write();
    TParameter<Long64_t>{
        EfficiencyFileSchema::energyCountMetadata,
        static_cast<Long64_t>(grid.energyCount())
    }.Write();
    TParameter<double>{EfficiencyFileSchema::energyMinMetadata, grid.energy(0)}.Write();
    TParameter<double>{
        EfficiencyFileSchema::energyMaxMetadata,
        grid.energy(grid.energyCount() - 1)
    }.Write();
    TParameter<double>{EfficiencyFileSchema::sourceRadiusMetadata, sourceRadiusMm}.Write();
    TNamed{
        EfficiencyFileSchema::definitionMetadata,
        EfficiencyFileSchema::efficiencyDefinition
    }.Write();

    if (tree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write Target efficiency tree."};
    }

    file.Close();
}
