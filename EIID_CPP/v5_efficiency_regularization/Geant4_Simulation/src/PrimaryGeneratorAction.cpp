#include "PrimaryGeneratorAction.hh"

#include "ConfigManager.hh"
#include "IEmissionConePolicy.hh"
#include "ISourceGeometry.hh"
#include "SimulationGrid.hh"

#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4SystemOfUnits.hh"
#include "Randomize.hh"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <utility>

namespace
{
G4ThreeVector sampleInsideCone(const EmissionCone& cone)
{
    const G4ThreeVector axis = cone.axis.unit();
    const G4double cosMinimum = std::cos(cone.halfAngle);
    const G4double cosAlpha =
        cosMinimum + (1.0 - cosMinimum) * G4UniformRand();
    const G4double sinAlpha =
        std::sqrt(std::max(0.0, 1.0 - cosAlpha * cosAlpha));
    const G4double azimuth = twopi * G4UniformRand();
    const G4ThreeVector helper = std::abs(axis.z()) < 0.9
        ? G4ThreeVector{0.0, 0.0, 1.0}
        : G4ThreeVector{1.0, 0.0, 0.0};
    const G4ThreeVector u = axis.cross(helper).unit();
    const G4ThreeVector v = axis.cross(u).unit();
    return (
        cosAlpha * axis +
        sinAlpha * std::cos(azimuth) * u +
        sinAlpha * std::sin(azimuth) * v
    ).unit();
}
}

PrimaryGeneratorAction::PrimaryGeneratorAction(
    const ConfigManager& config,
    const SimulationGrid& grid,
    std::shared_ptr<const ISourceGeometry> sourceGeometry,
    std::shared_ptr<const IEmissionConePolicy> conePolicy
)
    : config_{&config},
      grid_{&grid},
      sourceGeometry_{std::move(sourceGeometry)},
      conePolicy_{std::move(conePolicy)},
      particleGun_{std::make_unique<G4ParticleGun>(1)}
{
    if (!sourceGeometry_ || !conePolicy_)
    {
        throw std::invalid_argument{"Source geometry and cone policy are required."};
    }
}

PrimaryGeneratorAction::~PrimaryGeneratorAction() = default;

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"GeneratePrimaries received a null event."};
    }

    if (particleGun_->GetParticleDefinition() == nullptr)
    {
        G4ParticleDefinition* particle =
            G4ParticleTable::GetParticleTable()->FindParticle(
                config_->particleName()
            );

        if (particle == nullptr)
        {
            throw std::runtime_error{"Unknown Geant4 particle: " + config_->particleName()};
        }

        particleGun_->SetParticleDefinition(particle);
    }

    const SimulationCell& cell = grid_->cellForEvent(
        static_cast<std::uint64_t>(event->GetEventID())
    );
    const G4ThreeVector sourcePosition = sourceGeometry_->position(cell);
    const EmissionCone cone = conePolicy_->coneFor(sourcePosition);
    particleGun_->SetParticlePosition(sourcePosition);
    particleGun_->SetParticleMomentumDirection(sampleInsideCone(cone));
    particleGun_->SetParticleEnergy(cell.energyMeV * MeV);
    particleGun_->GeneratePrimaryVertex(event);
}
