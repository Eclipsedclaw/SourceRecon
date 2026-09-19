#ifndef EIID_V7_QUALITY_ANALYSIS_H
#define EIID_V7_QUALITY_ANALYSIS_H

#include "plot_utils.h"
#include "reconstruction_data.h"
#include "vis_config.h"

#include <array>
#include <cstddef>
#include <vector>

struct GaussianEnergyFit
{
    bool enabled{};
    bool converged{};
    int status{};
    double amplitude{};
    double meanMeV{};
    double sigmaMeV{};
    double background{};
    double fitMinMeV{};
    double fitMaxMeV{};
};

struct EnergyMetrics
{
    std::vector<EnergyPoint> spectrum;

    double peakEnergyMeV{};
    double peakIntensity{};
    double peakBiasMeV{};
    double baselineIntensity{};
    double halfMaximumIntensity{};

    bool directFwhmAvailable{};
    double leftHalfMaximumMeV{};
    double rightHalfMaximumMeV{};
    double directFwhmMeV{};
    double relativeDirectFwhm{};

    double intervalFraction{};
    double intervalLowMeV{};
    double intervalHighMeV{};
    double intervalWidthMeV{};

    double momentMeanMeV{};
    double momentSigmaMeV{};
    double momentMeanBiasMeV{};
    double directionGateRadiusDegree{};

    GaussianEnergyFit gaussian;
};

struct LocalDirectionPoint
{
    double uDegree{};
    double vDegree{};
    double weight{};
};

struct GaussianDirectionFit
{
    bool enabled{};
    bool converged{};
    int status{};
    double centerUDegree{};
    double centerVDegree{};
    double sigmaMajorDegree{};
    double sigmaMinorDegree{};
    double ellipseAngleDegree{};
    double thetaDegree{};
    double phiDegree{};
    double angularBiasDegree{};
};

struct DirectionMetrics
{
    std::size_t healpixNside{};
    double pixelScaleDegree{};
    double localRadiusDegree{};
    double energyGateLowMeV{};
    double energyGateHighMeV{};

    double centroidUDegree{};
    double centroidVDegree{};
    double rmsMajorDegree{};
    double rmsMinorDegree{};
    double ellipseAngleDegree{};
    double centroidThetaDegree{};
    double centroidPhiDegree{};
    double angularBiasDegree{};
    bool underResolved{};

    bool truthInsideLocalView{};
    double truthUDegree{};
    double truthVDegree{};
    std::array<double, 3> centroidDirection{};
    std::vector<LocalDirectionPoint> points;
    GaussianDirectionFit gaussian;
};

struct ContainmentMetrics
{
    double r50Degree{};
    double r68Degree{};
    double r90Degree{};
};

struct QualityAnalysisResult
{
    EnergyMetrics fullSkyEnergy;
    DirectionMetrics direction;
    EnergyMetrics directionGatedEnergy;
    ContainmentMetrics containment;
};

// QualityAnalyzer 只计算普通 C++ 数值，不负责画图。
// 所有主指标均不要求数据服从 Gaussian 分布。
class QualityAnalyzer
{
public:
    static QualityAnalysisResult analyze(
        const ReconstructionData& data,
        const VisConfig& config
    );
};

#endif
