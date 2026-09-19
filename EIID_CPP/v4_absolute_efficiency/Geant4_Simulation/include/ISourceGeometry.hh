#ifndef EIID_V4_I_SOURCE_GEOMETRY_HH
#define EIID_V4_I_SOURCE_GEOMETRY_HH

#include "G4ThreeVector.hh"

struct SimulationCell;

class ISourceGeometry
{
public:
    virtual ~ISourceGeometry() = default;
    virtual G4ThreeVector position(const SimulationCell& cell) const = 0;
    virtual double radiusMm() const = 0;
};

#endif
