#include "AutoBoundingConePolicy.hh"

#include "DetectorGeometryInfo.hh"

#include "G4PhysicalConstants.hh"
#include "G4SystemOfUnits.hh"

#include <algorithm>
#include <cmath>
#include <stdexcept>

AutoBoundingConePolicy::AutoBoundingConePolicy(
    const DetectorGeometryInfo& geometry,
    double safetyMarginDegree
)
    : geometry_{&geometry}, safetyMargin_{safetyMarginDegree * degree}
{
    if (!std::isfinite(safetyMarginDegree) || safetyMarginDegree < 0.0)
    {
        throw std::runtime_error{"Cone safety margin must be finite and non-negative."};
    }
}

EmissionCone AutoBoundingConePolicy::coneFor(
    const G4ThreeVector& sourcePosition
) const
{
    const G4ThreeVector toCenter = geometry_->ch2Center() - sourcePosition;

    if (toCenter.mag2() == 0.0)
    {
        throw std::runtime_error{"Source position coincides with the ch2 center."};
    }

    const G4ThreeVector axis = toCenter.unit();
    G4double maximumAngle = 0.0;

    for (const G4ThreeVector& corner : geometry_->triggerEnvelopeCorners())
    {
        const G4ThreeVector ray = corner - sourcePosition;

        if (ray.mag2() == 0.0)
        {
            throw std::runtime_error{"Source position lies on the trigger envelope."};
        }

        const G4double cosine = std::clamp(axis.dot(ray.unit()), -1.0, 1.0);
        maximumAngle = std::max(maximumAngle, std::acos(cosine));
    }

    const G4double halfAngle = maximumAngle + safetyMargin_;

    if (!(halfAngle > 0.0) || halfAngle >= pi)
    {
        throw std::runtime_error{"Automatically calculated cone angle is invalid."};
    }

    return EmissionCone{axis, halfAngle};
}
