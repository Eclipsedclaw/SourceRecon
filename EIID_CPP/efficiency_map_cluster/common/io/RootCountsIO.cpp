#include "RootSchema.h"
#include <TFile.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>
#include <chrono>
#include <memory>
#include <stdexcept>

namespace
{
    std::filesystem::path temporaryPath(const std::filesystem::path& path)
    {
        // 临时文件与正式文件位于同一文件系统；写完再 rename，读取端不看半个文件。
        const auto stamp = std::chrono::high_resolution_clock::now().time_since_epoch().count();
        return std::filesystem::path{path.string() + ".tmp." + std::to_string(stamp)};
    }

    void checkWrite(TFile& file)
    {
        file.Flush();
        if (file.TestBit(TFile::kWriteError))
        {
            throw std::runtime_error{"ROOT write failed (disk/quota?)"};
        }
    }

    template <class T> void checkParameter(TFile& file, const char* name, T expected)
    {
        const auto* value = file.Get<TParameter<T>>(name);
        if (!value || value->GetVal() != expected)
        {
            throw std::runtime_error{std::string{"Final ROOT grid metadata mismatch: "} + name};
        }
    }
} // namespace

ChunkData readChunk(const std::filesystem::path& path)
{
    std::unique_ptr<TFile> file{TFile::Open(path.string().c_str(), "READ")};
    if (!file || file->IsZombie() || file->TestBit(TFile::kRecovered))
    {
        throw std::runtime_error{"Cannot read a complete chunk: " + path.string()};
    }
    auto* metadata = file->Get<TNamed>("chunk_metadata");
    auto* tree = file->Get<TTree>("ChunkCounts");
    if (!metadata || !tree)
    {
        throw std::runtime_error{"Missing chunk metadata/tree: " + path.string()};
    }
    ChunkData result;
    result.metadata = nlohmann::json::parse(metadata->GetTitle());
    if (!result.metadata.at("complete").get<bool>())
    {
        throw std::runtime_error{"Incomplete chunk"};
    }
    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> index{reader, "cell_index"};
    TTreeReaderValue<ULong64_t> emitted{reader, "emitted_count"};
    TTreeReaderValue<ULong64_t> valid{reader, "valid_count"};
    TTreeReaderValue<ULong64_t> hits{reader, "hit_count"};
    TTreeReaderValue<ULong64_t> front{reader, "front_count"};
    TTreeReaderValue<ULong64_t> rear{reader, "rear_count"};
    TTreeReaderValue<Double_t> fraction{reader, "cone_solid_angle_fraction"};
    while (reader.Next())
    {
        if (!result.counts.emplace(*index, CellCounts{*emitted, *valid, *hits, *front, *rear, *fraction}).second)
        {
            throw std::runtime_error{"Duplicate cell in " + path.string()};
        }
    }
    if (reader.GetEntryStatus() != TTreeReader::kEntryBeyondEnd)
    {
        throw std::runtime_error{"ROOT branch type or read error: " + path.string()};
    }
    return result;
}

void writeChunk(const std::filesystem::path& path, const ChunkData& data)
{
    if (std::filesystem::exists(path))
    {
        throw std::runtime_error{"Refusing to overwrite chunk: " + path.string()};
    }
    std::filesystem::create_directories(path.parent_path());
    const auto temporary = temporaryPath(path);
    {
        TFile file{temporary.string().c_str(), "CREATE"};
        if (file.IsZombie())
        {
            throw std::runtime_error{"Cannot create " + temporary.string()};
        }
        const std::string text = data.metadata.dump();
        if (TNamed{"chunk_metadata", text.c_str()}.Write() <= 0)
        {
            throw std::runtime_error{"Metadata write failed"};
        }
        ULong64_t index{}, emitted{}, valid{}, hits{}, front{}, rear{};
        Double_t fraction{};
        TTree tree{"ChunkCounts", "Completed block: integer counts, not averaged efficiencies"};
        tree.Branch("cell_index", &index);
        tree.Branch("emitted_count", &emitted);
        tree.Branch("valid_count", &valid);
        tree.Branch("hit_count", &hits);
        tree.Branch("front_count", &front);
        tree.Branch("rear_count", &rear);
        tree.Branch("cone_solid_angle_fraction", &fraction);
        for (const auto& [cell, c] : data.counts)
        {
            index = cell;
            emitted = c.emitted;
            valid = c.valid;
            hits = c.hits;
            front = c.front;
            rear = c.rear;
            fraction = c.coneFraction;
            if (tree.Fill() < 0)
            {
                throw std::runtime_error{"Chunk Fill failed"};
            }
        }
        if (tree.Write() <= 0)
        {
            throw std::runtime_error{"Chunk tree write failed"};
        }
        checkWrite(file);
        tree.SetDirectory(nullptr);
        file.Close();
        if (file.TestBit(TFile::kWriteError))
        {
            throw std::runtime_error{"Chunk close failed"};
        }
    }
    // 再读一次确保可用，然后发布；失败的 .tmp 留作诊断，合并器不会读取它。
    const auto check = readChunk(temporary);
    if (check.metadata != data.metadata || check.counts.size() != data.counts.size())
    {
        throw std::runtime_error{"Chunk readback failed"};
    }
    for (const auto& [cell, c] : data.counts)
    {
        const auto& r = check.counts.at(cell);
        if (r.emitted != c.emitted || r.valid != c.valid || r.hits != c.hits || r.front != c.front ||
            r.rear != c.rear || r.coneFraction != c.coneFraction)
        {
            throw std::runtime_error{"Chunk readback counts differ"};
        }
    }
    if (std::filesystem::exists(path))
    {
        throw std::runtime_error{"Concurrent output detected"};
    }
    std::filesystem::rename(temporary, path);
}

void writeFinal(const std::filesystem::path& path, const Campaign& campaign, const Counts& counts,
                const nlohmann::json& software)
{
    // 最终文件不静默覆盖：重新合并时必须先移走旧最终文件，分块可以原样保留。
    if (std::filesystem::exists(path))
    {
        throw std::runtime_error{"Final output exists; move it aside first: " + path.string()};
    }
    const auto temporary = temporaryPath(path);
    const auto& config = campaign.config;
    {
        TFile file{temporary.string().c_str(), "CREATE"};
        if (file.IsZombie())
        {
            throw std::runtime_error{"Cannot create final ROOT"};
        }
        auto saveMetadata = [](auto object)
        {
            if (object.Write() <= 0)
            {
                throw std::runtime_error{"Final metadata write failed"};
            }
        };
        saveMetadata(TParameter<int>{"healpix_nside", config.healpixNside()});
        saveMetadata(TNamed{"healpix_ordering", "RING"});
        saveMetadata(TParameter<Long64_t>{"direction_count", static_cast<Long64_t>(config.directionCount())});
        saveMetadata(TParameter<Long64_t>{"energy_count", config.energyPointCount()});
        saveMetadata(TParameter<double>{"energy_min_MeV", config.energyMinMeV()});
        saveMetadata(TParameter<double>{"energy_max_MeV", config.energyMaxMeV()});
        saveMetadata(TParameter<double>{"source_radius_mm", config.hemisphereRadiusMm()});
        saveMetadata(
            TNamed{"efficiency_definition", "isotropic_point_source_absolute_detection_efficiency_4pi_raw_k_over_N"});
        // 用字符串避免把 uint64 大事例数强转成有符号 long long。
        saveMetadata(TNamed{"requested_event_count_u64", std::to_string(config.totalEvents()).c_str()});
        const std::string audit =
            nlohmann::json{{"manifest", campaign.manifest}, {"software", software}, {"complete", true}}.dump();
        saveMetadata(TNamed{"campaign_metadata", audit.c_str()});
        ULong64_t index{}, emitted{}, valid{};
        Double_t efficiency{}, fraction{};
        TTree tree{"RawEfficiency", "Raw absolute efficiency: sum(k)/sum(N) * cone_fraction"};
        tree.Branch("cell_index", &index);
        tree.Branch("efficiency", &efficiency);
        tree.Branch("emitted_count", &emitted);
        tree.Branch("valid_count", &valid);
        tree.Branch("cone_solid_angle_fraction", &fraction);
        // 保留全天球索引；未模拟的后半球 N=0，与前半球 k=0 明确区分。
        for (std::uint64_t cell = 0; cell < config.fullCellCount(); ++cell)
        {
            index = cell;
            emitted = 0;
            valid = 0;
            fraction = 0;
            efficiency = 0;
            const auto found = counts.find(cell);
            if (found != counts.end())
            {
                emitted = found->second.emitted;
                valid = found->second.valid;
                fraction = found->second.coneFraction;
                efficiency = static_cast<double>(valid) / static_cast<double>(emitted) * fraction;
            }
            if (tree.Fill() < 0)
            {
                throw std::runtime_error{"Final Fill failed"};
            }
        }
        if (tree.Write() <= 0)
        {
            throw std::runtime_error{"Final tree write failed"};
        }
        checkWrite(file);
        tree.SetDirectory(nullptr);
        file.Close();
        if (file.TestBit(TFile::kWriteError))
        {
            throw std::runtime_error{"Final close failed"};
        }
    }
    verifyFinal(temporary, campaign, counts, software);
    if (std::filesystem::exists(path))
    {
        throw std::runtime_error{"Concurrent final output detected"};
    }
    std::filesystem::rename(temporary, path);
}

void verifyFinal(const std::filesystem::path& path, const Campaign& campaign, const Counts& counts,
                 const nlohmann::json& software)
{
    std::unique_ptr<TFile> file{TFile::Open(path.string().c_str(), "READ")};
    if (!file || file->IsZombie() || file->TestBit(TFile::kRecovered))
    {
        throw std::runtime_error{"Final ROOT cannot be read: " + path.string()};
    }
    auto* metadata = file->Get<TNamed>("campaign_metadata");
    auto* tree = file->Get<TTree>("RawEfficiency");
    const nlohmann::json expected{{"manifest", campaign.manifest}, {"software", software}, {"complete", true}};
    if (!metadata || !tree || nlohmann::json::parse(metadata->GetTitle()) != expected)
    {
        throw std::runtime_error{"Final ROOT identity mismatch"};
    }
    const auto& config = campaign.config;
    checkParameter(*file, "healpix_nside", config.healpixNside());
    checkParameter(*file, "direction_count", static_cast<Long64_t>(config.directionCount()));
    checkParameter(*file, "energy_count", static_cast<Long64_t>(config.energyPointCount()));
    checkParameter(*file, "energy_min_MeV", config.energyMinMeV());
    checkParameter(*file, "energy_max_MeV", config.energyMaxMeV());
    checkParameter(*file, "source_radius_mm", config.hemisphereRadiusMm());
    const auto* ordering = file->Get<TNamed>("healpix_ordering");
    if (!ordering || std::string{ordering->GetTitle()} != "RING")
    {
        throw std::runtime_error{"Final ROOT ordering mismatch"};
    }
    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> index{reader, "cell_index"}, emitted{reader, "emitted_count"},
        valid{reader, "valid_count"};
    TTreeReaderValue<Double_t> fraction{reader, "cone_solid_angle_fraction"}, efficiency{reader, "efficiency"};
    std::uint64_t row = 0;
    while (reader.Next())
    {
        const auto found = counts.find(row);
        const CellCounts c = found == counts.end() ? CellCounts{} : found->second;
        const double value =
            c.emitted ? static_cast<double>(c.valid) / static_cast<double>(c.emitted) * c.coneFraction : 0;
        if (*index != row || *emitted != c.emitted || *valid != c.valid || *fraction != c.coneFraction ||
            *efficiency != value)
        {
            throw std::runtime_error{"Final ROOT values differ from verified chunk counts"};
        }
        ++row;
    }
    if (row != campaign.config.fullCellCount() || reader.GetEntryStatus() != TTreeReader::kEntryBeyondEnd)
    {
        throw std::runtime_error{"Final ROOT has missing rows or branch errors"};
    }
}
