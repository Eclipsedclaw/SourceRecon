#include "Ch2CenteredHemisphereSource.hh"

#include "DetectorGeometryInfo.hh"
#include "SimulationGrid.hh"

#include "G4SystemOfUnits.hh"

#include <cmath>
#include <stdexcept>

Ch2CenteredHemisphereSource::Ch2CenteredHemisphereSource(
    const DetectorGeometryInfo& geometry,
    double radiusMm
)
    : geometry_{&geometry}, radiusMm_{radiusMm}
{
    if (!std::isfinite(radiusMm_) || radiusMm_ <= 0.0)
    {
        throw std::runtime_error{"Source hemisphere radius must be positive."};
    }
}

G4ThreeVector Ch2CenteredHemisphereSource::position(
    const SimulationCell& cell
) const
{
    const G4ThreeVector direction{
        cell.directionX,
        cell.directionY,
        cell.directionZ
    };
    return geometry_->ch2Center() + radiusMm_ * mm * direction.unit();
}

double Ch2CenteredHemisphereSource::radiusMm() const { return radiusMm_; }
