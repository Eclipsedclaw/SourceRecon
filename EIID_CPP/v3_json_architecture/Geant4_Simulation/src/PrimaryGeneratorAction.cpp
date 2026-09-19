#include "PrimaryGeneratorAction.hh"

#include "ConfigManager.hh"
#include "SimulationGrid.hh"

#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "Randomize.hh"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace
{
G4ThreeVector sampleDirectionInsideCone(
    const G4ThreeVector& coneAxis,
    G4double halfAngle
)
{
    const G4ThreeVector axis = coneAxis.unit();

    // cos(alpha) 均匀，才能让发射方向在立体角上均匀，而不是让 alpha 均匀。
    const G4double cosMinimum = std::cos(halfAngle);
    const G4double cosAlpha =
        cosMinimum + (1.0 - cosMinimum) * G4UniformRand();
    const G4double sinAlpha =
        std::sqrt(std::max(0.0, 1.0 - cosAlpha * cosAlpha));
    const G4double beta = twopi * G4UniformRand();

    const G4ThreeVector helper = std::abs(axis.z()) < 0.9
        ? G4ThreeVector{0.0, 0.0, 1.0}
        : G4ThreeVector{1.0, 0.0, 0.0};
    const G4ThreeVector basisU = axis.cross(helper).unit();
    const G4ThreeVector basisV = axis.cross(basisU).unit();

    return (
        cosAlpha * axis +
        sinAlpha * std::cos(beta) * basisU +
        sinAlpha * std::sin(beta) * basisV
    ).unit();
}
}

PrimaryGeneratorAction::PrimaryGeneratorAction(
    const ConfigManager& config,
    const SimulationGrid& grid
)
    : config_{&config},
      grid_{&grid},
      particleGun_{std::make_unique<G4ParticleGun>(1)}
{
}

PrimaryGeneratorAction::~PrimaryGeneratorAction() = default;

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"GeneratePrimaries received a null G4Event."};
    }

    // PhysicsList::ConstructParticle() 在 RunManager::Initialize() 中执行。
    // GeneratePrimaries() 发生在其后，因此此处查询粒子表不会遇到初始化时序问题。
    if (particleGun_->GetParticleDefinition() == nullptr)
    {
        G4ParticleDefinition* particle =
            G4ParticleTable::GetParticleTable()->FindParticle(
                config_->particleName()
            );

        if (particle == nullptr)
        {
            throw std::runtime_error{
                "Geant4 cannot find particle: " + config_->particleName()
            };
        }

        particleGun_->SetParticleDefinition(particle);
    }

    const SimulationCell& cell = grid_->cellForEvent(
        static_cast<std::uint64_t>(event->GetEventID())
    );
    const G4ThreeVector sourceDirection{
        cell.directionX,
        cell.directionY,
        cell.directionZ
    };
    const G4ThreeVector sourcePosition =
        config_->hemisphereRadiusMm() * mm * sourceDirection;

    // 源位于半球面上，因此指向相机原点的中心轴恰好是 -sourceDirection。
    const G4ThreeVector momentumDirection = sampleDirectionInsideCone(
        -sourceDirection,
        config_->emissionConeHalfAngleDegree() * degree
    );

    particleGun_->SetParticlePosition(sourcePosition);
    particleGun_->SetParticleMomentumDirection(momentumDirection);
    particleGun_->SetParticleEnergy(cell.energyMeV * MeV);
    particleGun_->GeneratePrimaryVertex(event);
}
