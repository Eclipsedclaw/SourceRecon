#include "TaskRunner.hh"
#include "ActionInitialization.hh"
#include "AutoBoundingConePolicy.hh"
#include "Ch2CenteredHemisphereSource.hh"
#include "DetectorConstruction.hh"
#include "MyPhysicsList.hh"
#include "RootSchema.h"
#include "BuildInfo.h"
#include <G4MTRunManager.hh>
#include <G4Version.hh>
#include <G4ios.hh>
#include <Randomize.hh>
#include <CLHEP/Random/RanecuEngine.h>
#include <RVersion.h>
#include <chrono>
#include <cstdlib>
#include <stdexcept>

void TaskRunner::run(const Campaign& campaign, std::uint64_t jobId) const
{
    if (jobId >= campaign.jobs)
    {
        throw std::runtime_error{"Job ID is outside manifest"};
    }
    nlohmann::json software{{"source_sha256", EFF_SOURCE_SHA256},
                            {"compiler", EFF_COMPILER},
                            {"geant4", G4Version},
                            {"root", ROOT_RELEASE},
                            {"seed_scheme", "global-event-ranecu-v1"}};
    for (const char* key :
         {"G4LEDATA", "G4ENSDFSTATEDATA", "G4LEVELGAMMADATA", "G4RADIOACTIVEDATA", "G4PARTICLEXSDATA",
          "G4NEUTRONHPDATA", "G4PIIDATA", "G4REALSURFACEDATA", "G4SAIDXSDATA", "G4ABLADATA", "G4INCLDATA"})
    {
        const char* value = std::getenv(key);
        software["datasets"][key] = value ? value : "";
    }
    for (const char* key : {"G4LEDATA", "G4ENSDFSTATEDATA"})
    {
        const auto path = software["datasets"][key].get<std::string>();
        if (path.empty() || !std::filesystem::is_directory(path))
        {
            throw std::runtime_error{std::string{"Missing physics dataset "} + key + "; run through setup_env.sh"};
        }
    }
    G4cout << "Software: " << software.dump() << "\nConfig: " << campaign.config.document().dump() << "\nJob=" << jobId
           << " threads=" << campaign.threads << " seed=" << campaign.seed << G4endl;
    std::vector<TaskSpec> pending;
    for (const auto& task : campaign.tasks)
    {
        if (task.jobId != jobId)
        {
            continue;
        }
        if (std::filesystem::exists(campaign.chunkPath(task)))
        {
            const auto data = readChunk(campaign.chunkPath(task));
            if (data.metadata.at("identity") != campaign.identity(task) || data.metadata.at("software") != software)
            {
                throw std::runtime_error{
                    "Existing chunk comes from different configuration/software; use a new run directory"};
            }
            validateCounts(data.counts, task, campaign.config);
            G4cout << "Skip verified chunk " << task.id << G4endl;
        }
        else
        {
            pending.push_back(task);
        }
    }
    if (pending.empty())
    {
        G4cout << "All job chunks are already complete." << G4endl;
        return;
    }
    const SimulationGrid grid{campaign.config};
    if (grid.totalEventCount() != campaign.config.totalEvents())
    {
        throw std::runtime_error{"HEALPix active-cell mapping mismatch"};
    }
    RunContext context{pending.front(), campaign.seed};
    // 引擎必须活得比 RunManager 久。worker 使用 Geant4 创建的线程独立副本。
    CLHEP::RanecuEngine randomEngine;
    CLHEP::HepRandom::setTheEngine(&randomEngine);
    auto manager = std::make_unique<G4MTRunManager>();
    manager->SetNumberOfThreads(campaign.threads);
    if (manager->GetNumberOfThreads() != campaign.threads)
    {
        throw std::runtime_error{"Effective worker count differs from the requested CPU allocation"};
    }
    auto* detector = new B2a::DetectorConstruction{campaign.config};
    manager->SetUserInitialization(detector);
    manager->SetUserInitialization(new MyPhysicsList);
    auto source =
        std::make_shared<Ch2CenteredHemisphereSource>(detector->GeometryInfo(), campaign.config.hemisphereRadiusMm());
    auto cone = std::make_shared<AutoBoundingConePolicy>(detector->GeometryInfo(),
                                                         campaign.config.emissionConeSafetyMarginDegree());
    manager->SetUserInitialization(new ActionInitialization{campaign, grid, context, source, cone, software});
    manager->Initialize();
    for (const auto& task : pending)
    {
        // BeamOn 返回时 worker 已汇总并停止访问本块；此时更新上下文没有数据竞争。
        context.task = task;
        G4cout << "Begin chunk " << task.id << ", global events [" << task.firstEvent << ", "
               << task.firstEvent + task.eventCount << ")" << G4endl;
        const auto start = std::chrono::steady_clock::now();
        manager->BeamOn(static_cast<int>(task.eventCount));
        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        G4cout << "Chunk " << task.id << " wall_seconds=" << seconds << G4endl;
    }
}
