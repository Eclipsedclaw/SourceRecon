#include "ConfigManager.hh"
#include "DetectorConstruction.hh"
#include "EventAction.hh"
#include "MyPhysicsList.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "SimulationGrid.hh"

#include "G4RunManager.hh"
#include "Randomize.hh"

#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>

int main(int argc, char* argv[])
{
    try
    {
        const std::filesystem::path configPath = argc > 1
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{
                  "Geant4_Simulation/config/sim_config.json"
              };
        const ConfigManager config{configPath};
        const SimulationGrid grid{config};

        if (grid.totalEventCount() >
            static_cast<std::uint64_t>(std::numeric_limits<int>::max()))
        {
            throw std::runtime_error{
                "Requested event count exceeds G4RunManager::BeamOn(int). "
                "Reduce particles_per_cell or split the job."
            };
        }

        CLHEP::HepRandom::setTheSeed(config.randomSeed());

        // 使用串行 RunManager：ROOT TFile/TTree 只由一个线程访问，结果可重复且清晰。
        auto runManager = std::make_unique<G4RunManager>();
        runManager->SetUserInitialization(new B2a::DetectorConstruction{});
        runManager->SetUserInitialization(new MyPhysicsList{});

        auto* runAction = new RunAction{config, grid};
        runManager->SetUserAction(new PrimaryGeneratorAction{config, grid});
        runManager->SetUserAction(runAction);
        runManager->SetUserAction(new EventAction{config, grid, *runAction});

        runManager->Initialize();
        runManager->BeamOn(static_cast<int>(grid.totalEventCount()));
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Geant4 simulator error: " << error.what() << '\n';
        return 1;
    }
}
