#include "AutoBoundingConePolicy.hh"
#include "Ch2CenteredHemisphereSource.hh"
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
        if (argc > 2)
        {
            std::cerr << "Usage: geant4_simulator [path/to/sim_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/sim_config.json"};
        const ConfigManager config{configPath};
        const SimulationGrid grid{config};

        if (grid.totalEventCount() >
            static_cast<std::uint64_t>(std::numeric_limits<int>::max()))
        {
            throw std::runtime_error{
                "Requested event count exceeds G4RunManager::BeamOn(int)."
            };
        }

        CLHEP::HepRandom::setTheSeed(config.randomSeed());
        auto runManager = std::make_unique<G4RunManager>();
        auto* detector = new B2a::DetectorConstruction{config};
        runManager->SetUserInitialization(detector);
        runManager->SetUserInitialization(new MyPhysicsList{});

        auto sourceGeometry = std::make_shared<Ch2CenteredHemisphereSource>(
            detector->GeometryInfo(),
            config.hemisphereRadiusMm()
        );
        auto conePolicy = std::make_shared<AutoBoundingConePolicy>(
            detector->GeometryInfo(),
            config.emissionConeSafetyMarginDegree()
        );
        auto* runAction = new RunAction{
            config,
            grid,
            sourceGeometry,
            conePolicy
        };
        runManager->SetUserAction(
            new PrimaryGeneratorAction{
                config,
                grid,
                sourceGeometry,
                conePolicy
            }
        );
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
