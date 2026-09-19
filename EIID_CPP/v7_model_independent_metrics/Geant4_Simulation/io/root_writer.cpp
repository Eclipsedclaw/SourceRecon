#include "root_writer.h"

#include "AbsoluteEfficiencyEstimator.hh"
#include "ConfigManager.hh"
#include "EfficiencyFileSchema.h"
#include "IEmissionConePolicy.hh"
#include "ISourceGeometry.hh"
#include "SimulationGrid.hh"

#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <filesystem>
#include <stdexcept>
#include <utility>

namespace
{
void createParent(const std::filesystem::path& path)
{
    if (!path.parent_path().empty())
    {
        std::filesystem::create_directories(path.parent_path());
    }
}
}

RootWriter::RootWriter(
    const ConfigManager& config,
    const SimulationGrid& grid,
    std::shared_ptr<const ISourceGeometry> sourceGeometry,
    std::shared_ptr<const IEmissionConePolicy> conePolicy
)
    : config_{&config},
      grid_{&grid},
      sourceGeometry_{std::move(sourceGeometry)},
      conePolicy_{std::move(conePolicy)}
{
    if (!sourceGeometry_ || !conePolicy_)
    {
        throw std::invalid_argument{"RootWriter requires source and cone policies."};
    }
}

RootWriter::~RootWriter()
{
    try
    {
        finishEventOutput();
    }
    catch (...)
    {
    }
}

void RootWriter::beginEventOutput()
{
    if (eventFile_)
    {
        throw std::logic_error{"Compact-event output is already open."};
    }

    createParent(config_->eventsRootFile());
    eventFile_.reset(TFile::Open(
        config_->eventsRootFile().string().c_str(),
        "RECREATE"
    ));

    if (!eventFile_ || eventFile_->IsZombie())
    {
        throw std::runtime_error{"Cannot create compact-event ROOT file."};
    }

    eventTree_ = new TTree(
        config_->eventsTreeName().c_str(),
        "Triggered Compton events generated directly by Geant4"
    );
    eventTree_->Branch("eventID", &eventBuffer_.eventId);
    eventTree_->Branch("source_cell_index", &eventBuffer_.sourceCellIndex);
    eventTree_->Branch("r1_x", &eventBuffer_.r1X);
    eventTree_->Branch("r1_y", &eventBuffer_.r1Y);
    eventTree_->Branch("r1_z", &eventBuffer_.r1Z);
    eventTree_->Branch("r2_x", &eventBuffer_.r2X);
    eventTree_->Branch("r2_y", &eventBuffer_.r2Y);
    eventTree_->Branch("r2_z", &eventBuffer_.r2Z);
    eventTree_->Branch("e1_MeV", &eventBuffer_.e1MeV);
}

void RootWriter::writeCompactEvent(const CompactEventRecord& event)
{
    if (!eventFile_ || eventTree_ == nullptr)
    {
        throw std::logic_error{"Compact-event output is not open."};
    }

    eventBuffer_ = event;

    if (eventTree_->Fill() < 0)
    {
        throw std::runtime_error{"Failed while filling compact-event tree."};
    }
}

void RootWriter::finishEventOutput()
{
    if (!eventFile_)
    {
        return;
    }

    eventFile_->cd();

    if (eventTree_ == nullptr || eventTree_->Write() <= 0)
    {
        throw std::runtime_error{"Failed to write compact-event tree."};
    }

    eventFile_->Close();
    eventTree_ = nullptr;
    eventFile_.reset();
}

void RootWriter::writeEfficiencyOutput(
    const std::vector<std::uint64_t>& emittedCounts,
    const std::vector<std::uint64_t>& validCounts
) const
{
    if (emittedCounts.size() != grid_->fullCellCount() ||
        validCounts.size() != grid_->fullCellCount())
    {
        throw std::runtime_error{"Efficiency counters do not match the grid."};
    }

    createParent(config_->efficiencyRootFile());
    TFile file{config_->efficiencyRootFile().string().c_str(), "RECREATE"};

    if (file.IsZombie())
    {
        throw std::runtime_error{"Cannot create absolute-efficiency ROOT file."};
    }

    TTree tree{
        config_->efficiencyTreeName().c_str(),
        "Direction-energy absolute detection efficiency"
    };
    ULong64_t cellIndex{};
    Double_t efficiency{};
    tree.Branch(EfficiencyFileSchema::cellIndexBranch, &cellIndex);
    tree.Branch(EfficiencyFileSchema::efficiencyBranch, &efficiency);

    for (std::size_t index = 0; index < grid_->fullCellCount(); ++index)
    {
        const SimulationCell& cell = grid_->fullCell(index);
        const G4ThreeVector sourcePosition = sourceGeometry_->position(cell);
        const EmissionCone cone = conePolicy_->coneFor(sourcePosition);
        cellIndex = static_cast<ULong64_t>(index);
        efficiency = AbsoluteEfficiencyEstimator::estimate(
            validCounts[index],
            emittedCounts[index],
            cone.halfAngle
        );

        if (tree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling efficiency tree."};
        }
    }

    TParameter<int>{EfficiencyFileSchema::nsideMetadata, config_->healpixNside()}.Write();
    TNamed{EfficiencyFileSchema::orderingMetadata, "RING"}.Write();
    TParameter<Long64_t>{
        EfficiencyFileSchema::directionCountMetadata,
        static_cast<Long64_t>(grid_->directionCount())
    }.Write();
    TParameter<Long64_t>{
        EfficiencyFileSchema::energyCountMetadata,
        static_cast<Long64_t>(grid_->energyCount())
    }.Write();
    TParameter<double>{EfficiencyFileSchema::energyMinMetadata, config_->energyMinMeV()}.Write();
    TParameter<double>{EfficiencyFileSchema::energyMaxMetadata, config_->energyMaxMeV()}.Write();
    TParameter<double>{
        EfficiencyFileSchema::sourceRadiusMetadata,
        sourceGeometry_->radiusMm()
    }.Write();
    TNamed{
        EfficiencyFileSchema::definitionMetadata,
        EfficiencyFileSchema::efficiencyDefinition
    }.Write();

    if (tree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write absolute-efficiency tree."};
    }

    file.Close();
}
