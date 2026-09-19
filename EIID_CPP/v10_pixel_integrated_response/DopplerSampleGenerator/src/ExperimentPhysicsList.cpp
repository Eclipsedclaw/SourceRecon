#include "ExperimentPhysicsList.hh"

#include "ConfigManager.hh"

#include "G4ComptonScattering.hh"
#include "G4Electron.hh"
#include "G4EmParameters.hh"
#include "G4Gamma.hh"
#include "G4GammaConversion.hh"
#include "G4KleinNishinaCompton.hh"
#include "G4LivermoreComptonModel.hh"
#include "G4LivermorePhotoElectricModel.hh"
#include "G4Neutron.hh"
#include "G4PhotoElectricEffect.hh"
#include "G4Positron.hh"
#include "G4ProcessManager.hh"
#include "G4Proton.hh"
#include "G4SystemOfUnits.hh"
#include "G4eBremsstrahlung.hh"
#include "G4eIonisation.hh"
#include "G4eMultipleScattering.hh"
#include "G4eplusAnnihilation.hh"
#include "G4hIonisation.hh"

#if __has_include("G4LowEPComptonModel.hh")
#include "G4LowEPComptonModel.hh"
#define DOPPLER_EXPERIMENT_HAS_LOWEP 1
#else
#define DOPPLER_EXPERIMENT_HAS_LOWEP 0
#endif

#include <stdexcept>

ExperimentPhysicsList::ExperimentPhysicsList(const ConfigManager& config)
    : config_{&config}
{
    defaultCutValue = 0.1 * mm;

    G4EmParameters* parameters = G4EmParameters::Instance();
    parameters->SetVerbose(1);
    parameters->SetMinEnergy(100.0 * eV);
    parameters->SetMaxEnergy(10.0 * GeV);
    parameters->SetNumberOfBinsPerDecade(20);
    parameters->SetMscStepLimitType(fUseDistanceToBoundary);

    // 三组实验必须使用同一套原子退激发设置，否则比较中会混入第二个变量。
    parameters->SetFluo(config.atomicRelaxation());
    parameters->SetAuger(config.atomicRelaxation());
    parameters->SetPixe(config.atomicRelaxation());
}

void ExperimentPhysicsList::ConstructParticle()
{
    G4Gamma::GammaDefinition();
    G4Electron::ElectronDefinition();
    G4Positron::PositronDefinition();
    G4Proton::ProtonDefinition();
    G4Neutron::NeutronDefinition();
}

void ExperimentPhysicsList::ConstructProcess()
{
    AddTransportation();
    addElectromagneticPhysics();
}

void ExperimentPhysicsList::addElectromagneticPhysics()
{
    auto iterator = GetParticleIterator();
    iterator->reset();

    while ((*iterator)())
    {
        G4ParticleDefinition* particle = iterator->value();
        G4ProcessManager* manager = particle->GetProcessManager();
        const G4String name = particle->GetParticleName();

        if (name == "gamma")
        {
            auto* compton = new G4ComptonScattering();

            if (config_->comptonModel() == "free")
            {
                // Klein-Nishina 自由静止电子近似：作为“没有束缚电子动量”的参考组。
                compton->SetEmModel(new G4KleinNishinaCompton());
            }
            else if (config_->comptonModel() == "livermore")
            {
                // 当前正式工程所用模型：包含低能束缚电子/散射函数处理。
                compton->SetEmModel(new G4LivermoreComptonModel());
            }
            else if (config_->comptonModel() == "lowep")
            {
#if DOPPLER_EXPERIMENT_HAS_LOWEP
                // LowEP 使用更完整的低能电子动量处理，作为可选的第三组。
                compton->SetEmModel(new G4LowEPComptonModel());
#else
                throw std::runtime_error{
                    "This Geant4 installation does not provide G4LowEPComptonModel."
                };
#endif
            }

            manager->AddDiscreteProcess(compton);

            auto* photoelectric = new G4PhotoElectricEffect();
            photoelectric->SetEmModel(new G4LivermorePhotoElectricModel());
            manager->AddDiscreteProcess(photoelectric);
            manager->AddDiscreteProcess(new G4GammaConversion());
        }
        else if (name == "e-")
        {
            manager->AddProcess(new G4eMultipleScattering(), -1, -1, 1);
            manager->AddProcess(new G4eIonisation(), -1, 1, 2);
            manager->AddProcess(new G4eBremsstrahlung(), -1, -1, 3);
        }
        else if (name == "e+")
        {
            manager->AddProcess(new G4eIonisation(), -1, 1, 1);
            manager->AddProcess(new G4eBremsstrahlung(), -1, -1, 2);
            manager->AddProcess(new G4eplusAnnihilation(), 0, -1, 3);
        }
        else if (name == "proton")
        {
            manager->AddProcess(new G4hIonisation(), -1, 1, 1);
        }
    }
}

void ExperimentPhysicsList::SetCuts()
{
    SetCutsWithDefault();
    SetCutValue(0.01 * mm, "gamma");
    SetCutValue(0.01 * mm, "e-");
    SetCutValue(0.01 * mm, "e+");
    SetCutValue(0.1 * mm, "proton");

    if (verboseLevel > 0)
    {
        DumpCutValuesTable();
    }
}
