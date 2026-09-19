#include "FixedPointSourceAction.hh"

#include "AutoBoundingConePolicy.hh"
#include "ConfigManager.hh"
#include "DetectorGeometryInfo.hh"
#include "IEmissionConePolicy.hh"

#include "G4Event.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4SystemOfUnits.hh"
#include "G4ios.hh"
#include "Randomize.hh"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace
{
G4ThreeVector directionFromAngles(double thetaDegree, double phiDegree)
{
    const G4double theta = thetaDegree * degree;
    const G4double phi = phiDegree * degree;
    return G4ThreeVector{
        std::sin(theta) * std::cos(phi),
        std::sin(theta) * std::sin(phi),
        std::cos(theta)
    }.unit();
}

G4ThreeVector sampleUniformlyInsideCone(const EmissionCone& cone)
{
    const G4ThreeVector axis = cone.axis.unit();
    const G4double minimumCosine = std::cos(cone.halfAngle);

    // 对 cos(alpha) 均匀采样，才是在立体角上均匀；直接均匀采 alpha 会偏向锥轴。
    const G4double cosine =
        minimumCosine + (1.0 - minimumCosine) * G4UniformRand();
    const G4double sine = std::sqrt(std::max(0.0, 1.0 - cosine * cosine));
    const G4double azimuth = twopi * G4UniformRand();

    const G4ThreeVector helper = std::abs(axis.z()) < 0.9
        ? G4ThreeVector{0.0, 0.0, 1.0}
        : G4ThreeVector{1.0, 0.0, 0.0};
    const G4ThreeVector u = axis.cross(helper).unit();
    const G4ThreeVector v = axis.cross(u).unit();

    return (
        cosine * axis +
        sine * std::cos(azimuth) * u +
        sine * std::sin(azimuth) * v
    ).unit();
}
}

FixedPointSourceAction::FixedPointSourceAction(
    const ConfigManager& config,
    const DetectorGeometryInfo& geometry
)
    : config_{&config},
      sourcePosition_{
          geometry.ch2Center() +
          config.hemisphereRadiusMm() * mm * directionFromAngles(
              config.sourceThetaDegree(),
              config.sourcePhiDegree()
          )
      },
      conePolicy_{std::make_unique<AutoBoundingConePolicy>(
          geometry,
          config.emissionConeSafetyMarginDegree()
      )},
      particleGun_{std::make_unique<G4ParticleGun>(1)}
{
}

FixedPointSourceAction::~FixedPointSourceAction() = default;

void FixedPointSourceAction::GeneratePrimaries(G4Event* event)
{
    if (event == nullptr)
    {
        throw std::invalid_argument{"GeneratePrimaries received a null event."};
    }

    // G4ParticleGun 的 messenger 会提供一个默认 geantino，因此不能用
    // “当前定义是否为空”判断我们是否已经设置了配置文件指定的粒子。
    // 第一次 GeneratePrimaries() 发生在 PhysicsList::ConstructParticle()
    // 之后，此时再查表并明确覆盖默认粒子最稳妥。
    if (!particleConfigured_)
    {
        G4ParticleDefinition* particle =
            G4ParticleTable::GetParticleTable()->FindParticle(config_->particleName());

        if (particle == nullptr)
        {
            throw std::runtime_error{"Unknown Geant4 particle: " + config_->particleName()};
        }

        particleGun_->SetParticleDefinition(particle);
        particleConfigured_ = true;

        if (particleGun_->GetParticleDefinition() == nullptr ||
            particleGun_->GetParticleDefinition()->GetParticleName() !=
                config_->particleName())
        {
            throw std::runtime_error{
                "Particle gun failed to select " + config_->particleName() + "."
            };
        }

        G4cout << "Primary particle configured: "
               << particleGun_->GetParticleDefinition()->GetParticleName()
               << ", energy = " << config_->sourceEnergyMeV() << " MeV"
               << G4endl;
    }

    const EmissionCone cone = conePolicy_->coneFor(sourcePosition_);
    particleGun_->SetParticlePosition(sourcePosition_);
    particleGun_->SetParticleMomentumDirection(sampleUniformlyInsideCone(cone));
    particleGun_->SetParticleEnergy(config_->sourceEnergyMeV() * MeV);
    particleGun_->GeneratePrimaryVertex(event);
}

const G4ThreeVector& FixedPointSourceAction::sourcePosition() const
{
    return sourcePosition_;
}
