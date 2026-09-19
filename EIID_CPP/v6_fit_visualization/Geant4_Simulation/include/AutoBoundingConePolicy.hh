#ifndef EIID_V6_AUTO_BOUNDING_CONE_POLICY_HH
#define EIID_V6_AUTO_BOUNDING_CONE_POLICY_HH

#include "IEmissionConePolicy.hh"

class DetectorGeometryInfo;

class AutoBoundingConePolicy final : public IEmissionConePolicy
{
public:
    AutoBoundingConePolicy(
        const DetectorGeometryInfo& geometry,
        double safetyMarginDegree
    );
    EmissionCone coneFor(
        const G4ThreeVector& sourcePosition
    ) const override;

private:
    const DetectorGeometryInfo* geometry_{};
    G4double safetyMargin_{};
};

#endif
