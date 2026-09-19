#include "RunAction.hh"
#include "RootSchema.h"
#include <G4ios.hh>
#include <cmath>
#include <stdexcept>

RunAction::RunAction(const Campaign& campaign, const SimulationGrid& grid, const RunContext& context,
                     std::shared_ptr<const ISourceGeometry> source, std::shared_ptr<const IEmissionConePolicy> cone,
                     const nlohmann::json& software)
    : campaign_{campaign}, grid_{grid}, context_{context}, source_{std::move(source)}, cone_{std::move(cone)},
      software_{software}
{
}

G4Run* RunAction::GenerateRun()
{
    current_ = new EfficiencyRun;
    return current_;
}

void RunAction::recordEvent(std::uint64_t cell, bool front, bool rear, bool hit)
{
    if (!current_)
    {
        throw std::runtime_error{"Missing thread-local run"};
    }
    auto& c = current_->counts[cell];
    ++c.emitted;
    c.valid += front && rear ? 1 : 0;
    c.front += front ? 1 : 0;
    c.rear += rear ? 1 : 0;
    c.hits += hit ? 1 : 0;
}

void RunAction::EndOfRunAction(const G4Run* run)
{
    // 工作线程绝不创建 ROOT 输出；只有主线程看到所有 worker 合并后的计数。
    if (!IsMaster())
    {
        return;
    }
    const auto& complete = static_cast<const EfficiencyRun&>(*run);
    ChunkData data;
    data.counts = complete.counts;
    std::uint64_t valid = 0, front = 0, rear = 0, hits = 0;
    for (auto& [cell, c] : data.counts)
    {
        const auto position = source_->position(grid_.fullCell(static_cast<std::size_t>(cell)));
        const auto cone = cone_->coneFor(position);
        c.coneFraction = (1.0 - std::cos(cone.halfAngle)) / 2.0;
        valid += c.valid;
        front += c.front;
        rear += c.rear;
        hits += c.hits;
    }
    // Aborted run 或丢失事件都会在此失败，绝不能写成“已完成”的块。
    validateCounts(data.counts, context_.task, campaign_.config);
    data.metadata = {{"identity", campaign_.identity(context_.task)}, {"software", software_}, {"complete", true}};
    writeChunk(campaign_.chunkPath(context_.task), data);
    G4cout << "Chunk " << context_.task.id << " completed: emitted=" << context_.task.eventCount << " hits=" << hits
           << " ch2=" << front << " ch1=" << rear << " valid=" << valid << G4endl;
}
