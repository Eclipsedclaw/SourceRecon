#include "ConfigManager.hh"
#include "DetectorConstruction.hh"
#include "ExperimentEventAction.hh"
#include "ExperimentPhysicsList.hh"
#include "ExperimentRunAction.hh"
#include "FixedPointSourceAction.hh"

#include "G4RunManager.hh"
#include "Randomize.hh"

#include <exception>
#include <filesystem>
#include <iostream>
#include <memory>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: doppler_experiment [path/to/experiment_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/livermore.json"};
        const ConfigManager config{configPath};

        CLHEP::HepRandom::setTheSeed(config.randomSeed());

        auto runManager = std::make_unique<G4RunManager>();
        auto* detector = new B2a::DetectorConstruction{config};

        // Geant4 11.2 要求先向 RunManager 注册探测器和 PhysicsList，
        // 然后才能构造任何 G4UserRunAction/G4UserEventAction。
        // 注意：要求的是“构造顺序”，所以不能只把 SetUserAction() 往后移动；
        // new ExperimentRunAction 本身也必须出现在 PhysicsList 注册之后。
        runManager->SetUserInitialization(detector);
        runManager->SetUserInitialization(new ExperimentPhysicsList{config});

        auto* runAction = new ExperimentRunAction{config};
        runManager->SetUserAction(
            new FixedPointSourceAction{config, detector->GeometryInfo()}
        );
        runManager->SetUserAction(runAction);
        runManager->SetUserAction(
            new ExperimentEventAction{config, *runAction}
        );

        runManager->Initialize();
        runManager->BeamOn(config.numberOfEvents());
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Doppler experiment error: " << error.what() << '\n';
        return 1;
    }
}
