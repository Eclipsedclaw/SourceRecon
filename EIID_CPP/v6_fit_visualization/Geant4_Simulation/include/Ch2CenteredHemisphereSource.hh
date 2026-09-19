#ifndef EIID_V6_CH2_CENTERED_HEMISPHERE_SOURCE_HH
#define EIID_V6_CH2_CENTERED_HEMISPHERE_SOURCE_HH

#include "ISourceGeometry.hh"

class DetectorGeometryInfo;

class Ch2CenteredHemisphereSource final : public ISourceGeometry
{
public:
    Ch2CenteredHemisphereSource(
        const DetectorGeometryInfo& geometry,
        double radiusMm
    );
    G4ThreeVector position(const SimulationCell& cell) const override;
    double radiusMm() const override;

private:
    const DetectorGeometryInfo* geometry_{};
    double radiusMm_{};
};

#endif
