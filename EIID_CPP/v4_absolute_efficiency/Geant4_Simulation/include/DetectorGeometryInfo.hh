#ifndef EIID_V4_DETECTOR_GEOMETRY_INFO_HH
#define EIID_V4_DETECTOR_GEOMETRY_INFO_HH

#include "G4ThreeVector.hh"
#include "globals.hh"

#include <vector>

// 探测器尺寸只在此处计算，几何构造、源位置和自动发射锥共享同一份结果。
class DetectorGeometryInfo
{
public:
    DetectorGeometryInfo(G4double gap1, G4double gap2);
    const G4ThreeVector& ch2Center() const;
    const std::vector<G4ThreeVector>& triggerEnvelopeCorners() const;
    G4double detectorHalfXY() const;
    G4double detectorMinimumZ() const;
    G4double detectorMaximumZ() const;

private:
    G4ThreeVector ch2Center_;
    std::vector<G4ThreeVector> triggerEnvelopeCorners_;
    G4double detectorHalfXY_{};
    G4double detectorMinimumZ_{};
    G4double detectorMaximumZ_{};
};

#endif
