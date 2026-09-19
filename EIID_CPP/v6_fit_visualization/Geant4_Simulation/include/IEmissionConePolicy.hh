#ifndef EIID_V6_I_EMISSION_CONE_POLICY_HH
#define EIID_V6_I_EMISSION_CONE_POLICY_HH

#include "G4ThreeVector.hh"
#include "globals.hh"

struct EmissionCone
{
    G4ThreeVector axis;
    G4double halfAngle{};
};

class IEmissionConePolicy
{
public:
    virtual ~IEmissionConePolicy() = default;
    virtual EmissionCone coneFor(
        const G4ThreeVector& sourcePosition
    ) const = 0;
};

#endif
