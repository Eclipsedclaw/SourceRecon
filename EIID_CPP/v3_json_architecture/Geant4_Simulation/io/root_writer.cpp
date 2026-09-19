#include "root_writer.h"

#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>

#include <filesystem>
#include <stdexcept>
#include <string>

namespace
{
void createParentDirectory(const std::filesystem::path& filePath)
{
    const std::filesystem::path parent = filePath.parent_path();

    if (!parent.empty())
    {
        std::filesystem::create_directories(parent);
    }
}
}

RootWriter::RootWriter(
    const ConfigManager& config,
    const SimulationGrid& grid
)
    : config_{&config},
      grid_{&grid}
{
}

RootWriter::~RootWriter()
{
    try
    {
        finishEventOutput();
    }
    catch (...)
    {
        // 析构函数不能把异常传播到 Geant4 的清理阶段。
    }
}

void RootWriter::beginEventOutput()
{
    if (eventFile_)
    {
        throw std::logic_error{"Compact-event ROOT output is already open."};
    }

    createParentDirectory(config_->eventsRootFile());
    eventFile_.reset(TFile::Open(
        config_->eventsRootFile().string().c_str(),
        "RECREATE"
    ));

    if (!eventFile_ || eventFile_->IsZombie())
    {
        throw std::runtime_error{
            "Cannot create compact-event ROOT file: " +
            config_->eventsRootFile().string()
        };
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
        throw std::logic_error{"Compact-event ROOT output has not been opened."};
    }

    eventBuffer_ = event;

    if (eventTree_->Fill() < 0)
    {
        throw std::runtime_error{"Failed while filling compact-event ROOT tree."};
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
        throw std::runtime_error{"Failed to write compact-event ROOT tree."};
    }

    eventFile_->Close();
    eventTree_ = nullptr;
    eventFile_.reset();
}

void RootWriter::writeSensitivityOutput(
    const std::vector<std::uint64_t>& emittedCounts,
    const std::vector<std::uint64_t>& validCounts
) const
{
    if (emittedCounts.size() != grid_->fullCellCount() ||
        validCounts.size() != grid_->fullCellCount())
    {
        throw std::runtime_error{
            "Sensitivity counter dimensions do not match the simulation grid."
        };
    }

    createParentDirectory(config_->sensitivityRootFile());
    TFile outputFile{
        config_->sensitivityRootFile().string().c_str(),
        "RECREATE"
    };

    if (outputFile.IsZombie())
    {
        throw std::runtime_error{
            "Cannot create sensitivity ROOT file: " +
            config_->sensitivityRootFile().string()
        };
    }

    TTree tree{
        config_->sensitivityTreeName().c_str(),
        "Absolute trigger sensitivity for each direction-energy cell"
    };

    ULong64_t cellIndex{};
    ULong64_t directionIndex{};
    ULong64_t energyIndex{};
    ULong64_t healpixPixelId{};
    Double_t thetaDegree{};
    Double_t phiDegree{};
    Double_t directionX{};
    Double_t directionY{};
    Double_t directionZ{};
    Double_t energyMeV{};
    ULong64_t emittedCount{};
    ULong64_t validCount{};
    Double_t sensitivity{};

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
    tree.Branch("sensitivity", &sensitivity);

    for (std::size_t index = 0; index < grid_->fullCellCount(); ++index)
    {
        const SimulationCell& cell = grid_->fullCell(index);
        cellIndex = static_cast<ULong64_t>(cell.flatIndex);
        directionIndex = static_cast<ULong64_t>(cell.directionIndex);
        energyIndex = static_cast<ULong64_t>(cell.energyIndex);
        healpixPixelId = static_cast<ULong64_t>(cell.healpixPixelId);
        thetaDegree = cell.thetaDegree;
        phiDegree = cell.phiDegree;
        directionX = cell.directionX;
        directionY = cell.directionY;
        directionZ = cell.directionZ;
        energyMeV = cell.energyMeV;
        emittedCount = static_cast<ULong64_t>(emittedCounts[index]);
        validCount = static_cast<ULong64_t>(validCounts[index]);

        // 绝对敏感度 s_emitted 是“有效触发概率”，因此分母必须是发射数。
        sensitivity = emittedCount > 0
            ? static_cast<Double_t>(validCount) /
                  static_cast<Double_t>(emittedCount)
            : 0.0;

        if (tree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling sensitivity tree."};
        }
    }

    TParameter<int>{"healpix_nside", config_->healpixNside()}.Write();
    TNamed{"healpix_ordering", "RING"}.Write();
    TParameter<Long64_t>{
        "direction_count",
        static_cast<Long64_t>(grid_->directionCount())
    }.Write();
    TParameter<Long64_t>{
        "energy_count",
        static_cast<Long64_t>(grid_->energyCount())
    }.Write();

    if (tree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write sensitivity ROOT tree."};
    }

    outputFile.Close();
}
