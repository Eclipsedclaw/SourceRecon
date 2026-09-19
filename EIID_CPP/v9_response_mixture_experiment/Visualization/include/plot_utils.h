#ifndef EIID_PLOT_UTILS_H
#define EIID_PLOT_UTILS_H

#include "reconstruction_data.h"
#include "vis_config.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

struct SkyPixel
{
    std::uint64_t healpixPixelId;
    double thetaDegree;
    double phiDegree;
    double directionX;
    double directionY;
    double directionZ;
    double weight;
};

struct EnergyPoint
{
    double energyMeV;
    double weight;
};

struct DisplayCoordinate
{
    double longitudeDegree;
    double latitudeDegree;
};

std::vector<SkyPixel> marginalizeDirections(const ReconstructionData& data);
std::vector<EnergyPoint> marginalizeEnergies(const ReconstructionData& data);
std::vector<double> makeEnergyBinEdges(const std::vector<EnergyPoint>& spectrum);

std::array<double, 3> truthDirection(const TruthInfo& truth);
DisplayCoordinate cameraCenteredCoordinate(double x, double y, double z);
double angularSeparationDegree(const SkyPixel& pixel, const std::array<double, 3>& truthDirection);

std::size_t inferHealpixNside(std::size_t pixelCount);
double meanHealpixPixelScaleDegree(std::size_t pixelCount);

#endif
