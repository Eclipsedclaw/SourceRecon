#include "DetectorGeometryInfo.hh"

#include "G4SystemOfUnits.hh"

#include <array>

DetectorGeometryInfo::DetectorGeometryInfo(G4double gap1, G4double gap2)
{
    constexpr G4int pixelCount = 14;
    const G4double ysoPixelSize = 3.0 * mm;
    const G4double reflectorThickness = 0.18 * mm;
    const G4double pitch = ysoPixelSize + 2.0 * reflectorThickness;
    const G4double arrayHalfXY = pixelCount * pitch / 2.0;
    const G4double ysoHalfZ = 1.5 * mm;
    const G4double lysoHalfZ = 3.0 * mm;
    const G4double siHalfZ = 0.5 * um;
    const G4double fr4HalfZ = 0.8 * mm;
    const G4double yso1Z = -30.0 * mm;
    const G4double si1Z = yso1Z + ysoHalfZ + siHalfZ;
    const G4double fr41Z = si1Z + siHalfZ + fr4HalfZ;
    const G4double layer1End = fr41Z + fr4HalfZ;
    const G4double yso2Z = layer1End + gap1 + ysoHalfZ;
    const G4double si2Z = yso2Z + ysoHalfZ + siHalfZ;
    const G4double fr42Z = si2Z + siHalfZ + fr4HalfZ;
    const G4double layer2End = fr42Z + fr4HalfZ;
    const G4double lysoZ = layer2End + gap2 + lysoHalfZ;
    const G4double si3Z = lysoZ + lysoHalfZ + siHalfZ;
    const G4double fr43Z = si3Z + siHalfZ + fr4HalfZ;

    ch2Center_ = G4ThreeVector{0.0, 0.0, yso1Z};
    detectorHalfXY_ = arrayHalfXY;
    detectorMinimumZ_ = yso1Z - ysoHalfZ;
    detectorMaximumZ_ = fr43Z + fr4HalfZ;

    const G4double triggerMinZ = yso1Z - ysoHalfZ;
    const G4double triggerMaxZ = yso2Z + ysoHalfZ;

    const std::array<G4double, 2> transverse{-arrayHalfXY, arrayHalfXY};
    const std::array<G4double, 2> longitudinal{triggerMinZ, triggerMaxZ};

    for (const G4double x : transverse)
    {
        for (const G4double y : transverse)
        {
            for (const G4double z : longitudinal)
            {
                triggerEnvelopeCorners_.emplace_back(x, y, z);
            }
        }
    }
}

const G4ThreeVector& DetectorGeometryInfo::ch2Center() const { return ch2Center_; }
const std::vector<G4ThreeVector>& DetectorGeometryInfo::triggerEnvelopeCorners() const
{
    return triggerEnvelopeCorners_;
}
G4double DetectorGeometryInfo::detectorHalfXY() const { return detectorHalfXY_; }
G4double DetectorGeometryInfo::detectorMinimumZ() const { return detectorMinimumZ_; }
G4double DetectorGeometryInfo::detectorMaximumZ() const { return detectorMaximumZ_; }
