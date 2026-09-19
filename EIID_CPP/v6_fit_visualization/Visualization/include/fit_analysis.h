#ifndef EIID_V6_FIT_ANALYSIS_H
#define EIID_V6_FIT_ANALYSIS_H

#include "plot_utils.h"
#include "reconstruction_data.h"
#include "vis_config.h"

#include <array>
#include <vector>

struct EnergyFitResult
{
    bool fitConverged{};
    int fitStatus{};
    double amplitude{};
    double meanMeV{};
    double sigmaMeV{};
    double background{};
    double fitMinMeV{};
    double fitMaxMeV{};
    double truthBiasMeV{};
    double fwhmMeV{};
    double relativeFwhm{};
    double directionGateRadiusDegree{};
    std::vector<EnergyPoint> spectrum;
};

struct LocalDirectionPoint
{
    double uDegree{};
    double vDegree{};
    double weight{};
};

struct DirectionFitResult
{
    bool fitConverged{};
    bool underResolved{};
    int fitStatus{};
    std::size_t healpixNside{};
    double pixelScaleDegree{};
    double fitRadiusDegree{};
    double amplitude{};
    double centerUDegree{};
    double centerVDegree{};
    double sigmaMajorDegree{};
    double sigmaMinorDegree{};
    double ellipseAngleDegree{};
    double background{};
    double fittedThetaDegree{};
    double fittedPhiDegree{};
    double angularBiasDegree{};
    bool truthInsideLocalView{};
    double truthUDegree{};
    double truthVDegree{};
    std::array<double, 3> fittedDirection{};
    std::vector<LocalDirectionPoint> points;
};

struct ContainmentMetrics
{
    double r50Degree{};
    double r68Degree{};
    double r90Degree{};
};

struct FitAnalysisResult
{
    EnergyFitResult preliminaryEnergy;
    DirectionFitResult direction;
    EnergyFitResult finalEnergy;
    ContainmentMetrics containment;
};

// FitAnalyzer performs numerical analysis only.  Plotter classes consume the
// returned plain C++ values and are not responsible for choosing fit windows.
class FitAnalyzer
{
public:
    static FitAnalysisResult analyze(
        const ReconstructionData& data,
        const VisConfig& config
    );
};

#endif
