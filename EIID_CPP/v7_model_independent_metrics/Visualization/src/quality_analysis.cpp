#include "quality_analysis.h"

#include <TF1.h>
#include <TF2.h>
#include <TFitResultPtr.h>
#include <TGraph2D.h>
#include <TH1D.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace
{
constexpr double pi = 3.141592653589793238462643383279502884;

double toDegree(double radian)
{
    return radian * 180.0 / pi;
}

double toRadian(double degree)
{
    return degree * pi / 180.0;
}

double dot(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
)
{
    return left[0] * right[0] +
           left[1] * right[1] +
           left[2] * right[2];
}

std::array<double, 3> cross(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
)
{
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0]
    };
}

std::array<double, 3> normalized(const std::array<double, 3>& value)
{
    const double length = std::sqrt(dot(value, value));

    if (!(length > std::numeric_limits<double>::epsilon()))
    {
        throw std::runtime_error{"Cannot normalize a zero direction."};
    }

    return {value[0] / length, value[1] / length, value[2] / length};
}

std::array<double, 3> cellDirection(const ImageCell& cell)
{
    return normalized({cell.directionX, cell.directionY, cell.directionZ});
}

std::array<double, 3> pixelDirection(const SkyPixel& pixel)
{
    return normalized({pixel.directionX, pixel.directionY, pixel.directionZ});
}

double separationDegree(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
)
{
    return toDegree(std::acos(std::clamp(dot(left, right), -1.0, 1.0)));
}

struct DirectionAngles
{
    double thetaDegree{};
    double phiDegree{};
};

DirectionAngles directionAngles(const std::array<double, 3>& direction)
{
    const std::array<double, 3> unit = normalized(direction);
    const double theta = toDegree(std::acos(std::clamp(unit[2], -1.0, 1.0)));
    double phi = toDegree(std::atan2(unit[1], unit[0]));

    if (phi < 0.0)
    {
        phi += 360.0;
    }

    return DirectionAngles{theta, phi};
}

struct TangentFrame
{
    std::array<double, 3> center;
    std::array<double, 3> uAxis;
    std::array<double, 3> vAxis;
};

TangentFrame makeTangentFrame(const std::array<double, 3>& center)
{
    const std::array<double, 3> reference = std::abs(center[2]) < 0.9
        ? std::array<double, 3>{0.0, 0.0, 1.0}
        : std::array<double, 3>{1.0, 0.0, 0.0};
    const std::array<double, 3> uAxis = normalized(cross(reference, center));
    const std::array<double, 3> vAxis = normalized(cross(center, uAxis));
    return TangentFrame{center, uAxis, vAxis};
}

std::array<double, 2> projectToTangent(
    const TangentFrame& frame,
    const std::array<double, 3>& direction
)
{
    const double cosine = std::clamp(dot(frame.center, direction), -1.0, 1.0);
    const double angle = std::acos(cosine);

    if (angle <= 1.0e-14)
    {
        return {0.0, 0.0};
    }

    const double sine = std::sin(angle);

    if (std::abs(sine) <= 1.0e-14)
    {
        throw std::runtime_error{
            "An antipodal direction has no unique local tangent coordinate."
        };
    }

    const std::array<double, 3> tangent{
        (direction[0] - cosine * frame.center[0]) / sine,
        (direction[1] - cosine * frame.center[1]) / sine,
        (direction[2] - cosine * frame.center[2]) / sine
    };
    return {
        toDegree(angle * dot(tangent, frame.uAxis)),
        toDegree(angle * dot(tangent, frame.vAxis))
    };
}

std::array<double, 3> directionFromTangent(
    const TangentFrame& frame,
    double uDegree,
    double vDegree
)
{
    const double u = toRadian(uDegree);
    const double v = toRadian(vDegree);
    const double angle = std::hypot(u, v);

    if (angle <= 1.0e-14)
    {
        return frame.center;
    }

    const std::array<double, 3> tangent = normalized({
        u * frame.uAxis[0] + v * frame.vAxis[0],
        u * frame.uAxis[1] + v * frame.vAxis[1],
        u * frame.uAxis[2] + v * frame.vAxis[2]
    });
    return normalized({
        std::cos(angle) * frame.center[0] + std::sin(angle) * tangent[0],
        std::cos(angle) * frame.center[1] + std::sin(angle) * tangent[1],
        std::cos(angle) * frame.center[2] + std::sin(angle) * tangent[2]
    });
}

double interpolateCrossing(
    double xLeft,
    double yLeft,
    double xRight,
    double yRight,
    double target
)
{
    const double difference = yRight - yLeft;

    if (std::abs(difference) <= std::numeric_limits<double>::epsilon())
    {
        return 0.5 * (xLeft + xRight);
    }

    const double fraction = std::clamp(
        (target - yLeft) / difference,
        0.0,
        1.0
    );
    return xLeft + fraction * (xRight - xLeft);
}

struct ShortestInterval
{
    double low{};
    double high{};
};

ShortestInterval shortestEnergyInterval(
    const std::vector<EnergyPoint>& spectrum,
    const std::vector<double>& edges,
    double fraction,
    double totalWeight
)
{
    const double targetWeight = fraction * totalWeight;
    std::size_t right = 0;
    double windowWeight = 0.0;
    double bestWidth = std::numeric_limits<double>::infinity();
    ShortestInterval best{edges.front(), edges.back()};

    for (std::size_t left = 0; left < spectrum.size(); ++left)
    {
        while (right < spectrum.size() && windowWeight < targetWeight)
        {
            windowWeight += spectrum[right].weight;
            ++right;
        }

        if (windowWeight >= targetWeight)
        {
            const double width = edges[right] - edges[left];

            if (width < bestWidth)
            {
                bestWidth = width;
                best = ShortestInterval{edges[left], edges[right]};
            }
        }

        if (right > left)
        {
            windowWeight -= spectrum[left].weight;
        }
        else
        {
            right = left + 1;
        }
    }

    return best;
}

GaussianEnergyFit attemptGaussianEnergyFit(
    const std::vector<EnergyPoint>& spectrum,
    const std::vector<double>& edges,
    const EnergyMetrics& metrics,
    const AnalysisConfig& config,
    const char* objectName
)
{
    GaussianEnergyFit result;
    result.enabled = config.gaussianFitEnabled;

    if (!result.enabled)
    {
        result.status = -1;
        return result;
    }

    result.fitMinMeV = std::max(
        edges.front(),
        metrics.peakEnergyMeV - config.gaussianFitHalfWidthMeV
    );
    result.fitMaxMeV = std::min(
        edges.back(),
        metrics.peakEnergyMeV + config.gaussianFitHalfWidthMeV
    );
    TH1D histogram{
        objectName,
        objectName,
        static_cast<int>(spectrum.size()),
        edges.data()
    };
    histogram.SetDirectory(nullptr);

    for (std::size_t index = 0; index < spectrum.size(); ++index)
    {
        histogram.SetBinContent(
            static_cast<int>(index + 1),
            spectrum[index].weight
        );
    }

    const double energyStep = std::abs(
        spectrum[1].energyMeV - spectrum[0].energyMeV
    );
    const double initialSigma = metrics.directFwhmAvailable
        ? metrics.directFwhmMeV / 2.354820045
        : std::max(2.0 * energyStep, config.gaussianFitHalfWidthMeV / 4.0);
    TF1 function{
        (std::string{objectName} + "_function").c_str(),
        "[0]*exp(-0.5*((x-[1])/[2])^2)+[3]",
        result.fitMinMeV,
        result.fitMaxMeV
    };
    function.SetParNames("Amplitude", "Mean", "Sigma", "Background");
    function.SetParameters(
        std::max(
            metrics.peakIntensity - metrics.baselineIntensity,
            metrics.peakIntensity * 0.5
        ),
        metrics.peakEnergyMeV,
        std::max(initialSigma, energyStep * 0.20),
        metrics.baselineIntensity
    );
    function.SetParLimits(0, 0.0, metrics.peakIntensity * 20.0);
    function.SetParLimits(1, result.fitMinMeV, result.fitMaxMeV);
    function.SetParLimits(
        2,
        std::max(energyStep * 0.20, 1.0e-8),
        config.gaussianFitHalfWidthMeV
    );
    function.SetParLimits(3, 0.0, metrics.peakIntensity * 2.0);

    const TFitResultPtr fitResult = histogram.Fit(
        &function,
        "QSNW",
        "",
        result.fitMinMeV,
        result.fitMaxMeV
    );
    result.status = static_cast<int>(fitResult);
    result.amplitude = function.GetParameter(0);
    result.meanMeV = function.GetParameter(1);
    result.sigmaMeV = std::abs(function.GetParameter(2));
    result.background = function.GetParameter(3);
    result.converged = result.status == 0 &&
        std::isfinite(result.meanMeV) &&
        std::isfinite(result.sigmaMeV) &&
        result.sigmaMeV > 0.0;
    return result;
}

EnergyMetrics calculateEnergyMetrics(
    const std::vector<EnergyPoint>& spectrum,
    const VisConfig& config,
    const char* objectName
)
{
    if (spectrum.size() < 3)
    {
        throw std::runtime_error{
            "Energy quality analysis requires at least three grid points."
        };
    }

    double totalWeight = 0.0;

    for (std::size_t index = 0; index < spectrum.size(); ++index)
    {
        if (!std::isfinite(spectrum[index].energyMeV) ||
            !std::isfinite(spectrum[index].weight) ||
            spectrum[index].weight < 0.0)
        {
            throw std::runtime_error{
                "Energy quality analysis requires finite non-negative weights."
            };
        }

        if (index > 0 &&
            !(spectrum[index].energyMeV > spectrum[index - 1].energyMeV))
        {
            throw std::runtime_error{
                "Energy grid points must be strictly increasing."
            };
        }

        totalWeight += spectrum[index].weight;
    }

    if (!(totalWeight > 0.0))
    {
        throw std::runtime_error{"Energy spectrum has no positive intensity."};
    }

    const std::vector<double> edges = makeEnergyBinEdges(spectrum);
    const auto peakIterator = std::max_element(
        spectrum.begin(),
        spectrum.end(),
        [](const EnergyPoint& left, const EnergyPoint& right)
        {
            return left.weight < right.weight;
        }
    );
    const std::size_t peakIndex = static_cast<std::size_t>(
        std::distance(spectrum.begin(), peakIterator)
    );
    EnergyMetrics metrics;
    metrics.spectrum = spectrum;
    metrics.peakEnergyMeV = peakIterator->energyMeV;
    metrics.peakIntensity = peakIterator->weight;
    metrics.baselineIntensity = std::min_element(
        spectrum.begin(),
        spectrum.end(),
        [](const EnergyPoint& left, const EnergyPoint& right)
        {
            return left.weight < right.weight;
        }
    )->weight;

    // 三点抛物线插值只细化峰位置，不改变原始直方图或半高交点。
    if (peakIndex > 0 && peakIndex + 1 < spectrum.size())
    {
        const double left = spectrum[peakIndex - 1].weight;
        const double middle = spectrum[peakIndex].weight;
        const double right = spectrum[peakIndex + 1].weight;
        const double denominator = left - 2.0 * middle + right;

        if (denominator < 0.0)
        {
            const double offset = 0.5 * (left - right) / denominator;

            if (std::isfinite(offset) && std::abs(offset) <= 1.0)
            {
                const double step = 0.5 * (
                    spectrum[peakIndex + 1].energyMeV -
                    spectrum[peakIndex - 1].energyMeV
                );
                metrics.peakEnergyMeV += offset * step;
                metrics.peakIntensity = middle -
                    0.25 * (left - right) * offset;
            }
        }
    }

    metrics.peakBiasMeV = metrics.peakEnergyMeV - config.truth().energyMeV;
    metrics.halfMaximumIntensity = metrics.baselineIntensity + 0.5 * (
        metrics.peakIntensity - metrics.baselineIntensity
    );
    bool foundLeft = false;
    bool foundRight = false;

    for (std::size_t index = peakIndex; index > 0; --index)
    {
        if (spectrum[index - 1].weight <= metrics.halfMaximumIntensity &&
            spectrum[index].weight >= metrics.halfMaximumIntensity)
        {
            metrics.leftHalfMaximumMeV = interpolateCrossing(
                spectrum[index - 1].energyMeV,
                spectrum[index - 1].weight,
                spectrum[index].energyMeV,
                spectrum[index].weight,
                metrics.halfMaximumIntensity
            );
            foundLeft = true;
            break;
        }
    }

    for (std::size_t index = peakIndex; index + 1 < spectrum.size(); ++index)
    {
        if (spectrum[index].weight >= metrics.halfMaximumIntensity &&
            spectrum[index + 1].weight <= metrics.halfMaximumIntensity)
        {
            metrics.rightHalfMaximumMeV = interpolateCrossing(
                spectrum[index].energyMeV,
                spectrum[index].weight,
                spectrum[index + 1].energyMeV,
                spectrum[index + 1].weight,
                metrics.halfMaximumIntensity
            );
            foundRight = true;
            break;
        }
    }

    metrics.directFwhmAvailable = foundLeft && foundRight &&
        metrics.rightHalfMaximumMeV > metrics.leftHalfMaximumMeV;

    if (metrics.directFwhmAvailable)
    {
        metrics.directFwhmMeV =
            metrics.rightHalfMaximumMeV - metrics.leftHalfMaximumMeV;
        metrics.relativeDirectFwhm =
            metrics.directFwhmMeV / metrics.peakEnergyMeV;
    }

    metrics.intervalFraction = config.analysis().energyIntervalFraction;
    const ShortestInterval interval = shortestEnergyInterval(
        spectrum,
        edges,
        metrics.intervalFraction,
        totalWeight
    );
    metrics.intervalLowMeV = interval.low;
    metrics.intervalHighMeV = interval.high;
    metrics.intervalWidthMeV = interval.high - interval.low;

    double weightedEnergy = 0.0;
    double weightedEnergySquared = 0.0;

    for (const EnergyPoint& point : spectrum)
    {
        weightedEnergy += point.weight * point.energyMeV;
        weightedEnergySquared +=
            point.weight * point.energyMeV * point.energyMeV;
    }

    metrics.momentMeanMeV = weightedEnergy / totalWeight;
    metrics.momentSigmaMeV = std::sqrt(std::max(
        0.0,
        weightedEnergySquared / totalWeight -
            metrics.momentMeanMeV * metrics.momentMeanMeV
    ));
    metrics.momentMeanBiasMeV =
        metrics.momentMeanMeV - config.truth().energyMeV;
    metrics.gaussian = attemptGaussianEnergyFit(
        spectrum,
        edges,
        metrics,
        config.analysis(),
        objectName
    );
    return metrics;
}

std::vector<SkyPixel> energyGatedPixels(
    const ReconstructionData& data,
    double minimumEnergy,
    double maximumEnergy
)
{
    std::map<std::uint64_t, SkyPixel> pixels;

    for (const ImageCell& cell : data.cells)
    {
        if (cell.energyMeV < minimumEnergy || cell.energyMeV > maximumEnergy)
        {
            continue;
        }

        auto [iterator, inserted] = pixels.try_emplace(
            cell.healpixPixelId,
            SkyPixel{
                cell.healpixPixelId,
                cell.thetaDegree,
                cell.phiDegree,
                cell.directionX,
                cell.directionY,
                cell.directionZ,
                0.0
            }
        );
        static_cast<void>(inserted);
        iterator->second.weight += cell.weight;
    }

    std::vector<SkyPixel> result;
    result.reserve(pixels.size());

    for (const auto& [pixelId, pixel] : pixels)
    {
        static_cast<void>(pixelId);
        result.push_back(pixel);
    }

    return result;
}

double ellipticalGaussian(double* coordinate, double* parameter)
{
    const double cosine = std::cos(parameter[5]);
    const double sine = std::sin(parameter[5]);
    const double deltaU = coordinate[0] - parameter[1];
    const double deltaV = coordinate[1] - parameter[2];
    const double majorCoordinate = deltaU * cosine + deltaV * sine;
    const double minorCoordinate = -deltaU * sine + deltaV * cosine;
    const double exponent = -0.5 * (
        majorCoordinate * majorCoordinate / (parameter[3] * parameter[3]) +
        minorCoordinate * minorCoordinate / (parameter[4] * parameter[4])
    );
    return parameter[0] * std::exp(exponent) + parameter[6];
}

GaussianDirectionFit attemptGaussianDirectionFit(
    const std::vector<LocalDirectionPoint>& points,
    double minimum,
    double maximum,
    const DirectionMetrics& metrics,
    const TangentFrame& frame,
    const std::array<double, 3>& trueDirection,
    const AnalysisConfig& config
)
{
    GaussianDirectionFit result;
    result.enabled = config.gaussianFitEnabled;

    if (!result.enabled)
    {
        result.status = -1;
        return result;
    }

    TGraph2D graph{static_cast<int>(points.size())};

    for (std::size_t index = 0; index < points.size(); ++index)
    {
        graph.SetPoint(
            static_cast<int>(index),
            points[index].uDegree,
            points[index].vDegree,
            points[index].weight
        );
    }

    TF2 function{
        "v7_optional_direction_gaussian",
        ellipticalGaussian,
        -metrics.localRadiusDegree,
        metrics.localRadiusDegree,
        -metrics.localRadiusDegree,
        metrics.localRadiusDegree,
        7
    };
    function.SetParNames(
        "Amplitude",
        "CenterU",
        "CenterV",
        "SigmaMajor",
        "SigmaMinor",
        "Angle",
        "Background"
    );
    function.SetParameters(
        std::max(maximum - minimum, maximum * 0.5),
        metrics.centroidUDegree,
        metrics.centroidVDegree,
        metrics.rmsMajorDegree,
        metrics.rmsMinorDegree,
        toRadian(metrics.ellipseAngleDegree),
        minimum
    );
    function.SetParLimits(0, 0.0, maximum * 20.0);
    function.SetParLimits(
        1,
        -metrics.localRadiusDegree * 0.75,
        metrics.localRadiusDegree * 0.75
    );
    function.SetParLimits(
        2,
        -metrics.localRadiusDegree * 0.75,
        metrics.localRadiusDegree * 0.75
    );
    function.SetParLimits(
        3,
        metrics.pixelScaleDegree * 0.20,
        metrics.localRadiusDegree
    );
    function.SetParLimits(
        4,
        metrics.pixelScaleDegree * 0.20,
        metrics.localRadiusDegree
    );
    function.SetParLimits(5, -0.5 * pi, 0.5 * pi);
    function.SetParLimits(6, 0.0, maximum * 2.0);

    const TFitResultPtr fitResult = graph.Fit(&function, "QSN");
    result.status = static_cast<int>(fitResult);
    result.centerUDegree = function.GetParameter(1);
    result.centerVDegree = function.GetParameter(2);
    result.sigmaMajorDegree = std::abs(function.GetParameter(3));
    result.sigmaMinorDegree = std::abs(function.GetParameter(4));
    double angleRadian = function.GetParameter(5);

    if (result.sigmaMinorDegree > result.sigmaMajorDegree)
    {
        std::swap(result.sigmaMajorDegree, result.sigmaMinorDegree);
        angleRadian += 0.5 * pi;
    }

    result.ellipseAngleDegree = toDegree(angleRadian);
    result.converged = result.status == 0 &&
        std::isfinite(result.centerUDegree) &&
        std::isfinite(result.centerVDegree) &&
        std::isfinite(result.sigmaMajorDegree) &&
        std::isfinite(result.sigmaMinorDegree) &&
        result.sigmaMajorDegree > 0.0 &&
        result.sigmaMinorDegree > 0.0;

    if (result.converged)
    {
        const std::array<double, 3> direction = directionFromTangent(
            frame,
            result.centerUDegree,
            result.centerVDegree
        );
        const DirectionAngles angles = directionAngles(direction);
        result.thetaDegree = angles.thetaDegree;
        result.phiDegree = angles.phiDegree;
        result.angularBiasDegree = separationDegree(direction, trueDirection);
    }

    return result;
}

DirectionMetrics calculateDirectionMetrics(
    const std::vector<SkyPixel>& pixels,
    const VisConfig& config,
    std::size_t fullSkyPixelCount,
    double energyGateLow,
    double energyGateHigh
)
{
    if (pixels.empty())
    {
        throw std::runtime_error{"The energy-gated direction map is empty."};
    }

    const auto peakIterator = std::max_element(
        pixels.begin(),
        pixels.end(),
        [](const SkyPixel& left, const SkyPixel& right)
        {
            return left.weight < right.weight;
        }
    );

    if (!(peakIterator->weight > 0.0))
    {
        throw std::runtime_error{"The direction map has no positive peak."};
    }

    const std::array<double, 3> peakDirection = pixelDirection(*peakIterator);
    const TangentFrame frame = makeTangentFrame(peakDirection);
    DirectionMetrics metrics;
    metrics.healpixNside = inferHealpixNside(fullSkyPixelCount);
    metrics.pixelScaleDegree =
        meanHealpixPixelScaleDegree(fullSkyPixelCount);
    metrics.localRadiusDegree = config.analysis().directionLocalRadiusDegree;
    metrics.energyGateLowMeV = energyGateLow;
    metrics.energyGateHighMeV = energyGateHigh;

    for (const SkyPixel& pixel : pixels)
    {
        const std::array<double, 3> direction = pixelDirection(pixel);

        if (separationDegree(peakDirection, direction) <=
            metrics.localRadiusDegree)
        {
            const std::array<double, 2> local =
                projectToTangent(frame, direction);
            metrics.points.push_back(LocalDirectionPoint{
                local[0],
                local[1],
                pixel.weight
            });
        }
    }

    if (metrics.points.size() < 9)
    {
        throw std::runtime_error{
            "Direction analysis contains fewer than nine local pixels."
        };
    }

    double minimum = metrics.points.front().weight;
    double maximum = metrics.points.front().weight;

    for (const LocalDirectionPoint& point : metrics.points)
    {
        minimum = std::min(minimum, point.weight);
        maximum = std::max(maximum, point.weight);
    }

    double totalSignal = 0.0;
    double weightedU = 0.0;
    double weightedV = 0.0;

    for (const LocalDirectionPoint& point : metrics.points)
    {
        const double signal = std::max(0.0, point.weight - minimum);
        totalSignal += signal;
        weightedU += signal * point.uDegree;
        weightedV += signal * point.vDegree;
    }

    if (!(totalSignal > 0.0))
    {
        throw std::runtime_error{
            "Direction window has no intensity above its local background."
        };
    }

    metrics.centroidUDegree = weightedU / totalSignal;
    metrics.centroidVDegree = weightedV / totalSignal;
    double covarianceUU = 0.0;
    double covarianceVV = 0.0;
    double covarianceUV = 0.0;

    for (const LocalDirectionPoint& point : metrics.points)
    {
        const double signal = std::max(0.0, point.weight - minimum);
        const double deltaU = point.uDegree - metrics.centroidUDegree;
        const double deltaV = point.vDegree - metrics.centroidVDegree;
        covarianceUU += signal * deltaU * deltaU;
        covarianceVV += signal * deltaV * deltaV;
        covarianceUV += signal * deltaU * deltaV;
    }

    covarianceUU /= totalSignal;
    covarianceVV /= totalSignal;
    covarianceUV /= totalSignal;
    const double discriminant = std::sqrt(std::max(
        0.0,
        (covarianceUU - covarianceVV) *
            (covarianceUU - covarianceVV) +
        4.0 * covarianceUV * covarianceUV
    ));
    metrics.rmsMajorDegree = std::sqrt(std::max(
        0.5 * (covarianceUU + covarianceVV + discriminant),
        0.0
    ));
    metrics.rmsMinorDegree = std::sqrt(std::max(
        0.5 * (covarianceUU + covarianceVV - discriminant),
        0.0
    ));
    metrics.ellipseAngleDegree = toDegree(0.5 * std::atan2(
        2.0 * covarianceUV,
        covarianceUU - covarianceVV
    ));
    metrics.centroidDirection = directionFromTangent(
        frame,
        metrics.centroidUDegree,
        metrics.centroidVDegree
    );
    const DirectionAngles centroidAngles =
        directionAngles(metrics.centroidDirection);
    metrics.centroidThetaDegree = centroidAngles.thetaDegree;
    metrics.centroidPhiDegree = centroidAngles.phiDegree;
    const std::array<double, 3> trueDirection = truthDirection(config.truth());
    metrics.angularBiasDegree = separationDegree(
        metrics.centroidDirection,
        trueDirection
    );
    metrics.underResolved =
        metrics.rmsMinorDegree < metrics.pixelScaleDegree;

    if (separationDegree(peakDirection, trueDirection) < 179.999)
    {
        const std::array<double, 2> truthLocal =
            projectToTangent(frame, trueDirection);
        metrics.truthUDegree = truthLocal[0];
        metrics.truthVDegree = truthLocal[1];
        metrics.truthInsideLocalView =
            std::hypot(truthLocal[0], truthLocal[1]) <=
            metrics.localRadiusDegree;
    }

    metrics.gaussian = attemptGaussianDirectionFit(
        metrics.points,
        minimum,
        maximum,
        metrics,
        frame,
        trueDirection,
        config.analysis()
    );
    return metrics;
}

std::vector<EnergyPoint> directionGatedSpectrum(
    const ReconstructionData& data,
    const std::array<double, 3>& center,
    double radiusDegree
)
{
    std::map<double, double> weights;

    for (const ImageCell& cell : data.cells)
    {
        if (separationDegree(cellDirection(cell), center) <= radiusDegree)
        {
            weights[cell.energyMeV] += cell.weight;
        }
    }

    std::vector<EnergyPoint> spectrum;
    spectrum.reserve(weights.size());

    for (const auto& [energy, weight] : weights)
    {
        spectrum.push_back(EnergyPoint{energy, weight});
    }

    return spectrum;
}

double radiusAtFraction(
    const std::vector<std::pair<double, double>>& sorted,
    double total,
    double fraction
)
{
    double cumulative = 0.0;

    for (const auto& [angle, weight] : sorted)
    {
        cumulative += weight;

        if (cumulative / total >= fraction)
        {
            return angle;
        }
    }

    return sorted.back().first;
}

ContainmentMetrics calculateContainment(
    const ReconstructionData& data,
    const TruthInfo& truth
)
{
    const std::vector<SkyPixel> pixels = marginalizeDirections(data);
    const std::array<double, 3> reference = truthDirection(truth);
    std::vector<std::pair<double, double>> values;
    values.reserve(pixels.size());

    for (const SkyPixel& pixel : pixels)
    {
        values.emplace_back(
            angularSeparationDegree(pixel, reference),
            pixel.weight
        );
    }

    std::sort(values.begin(), values.end());
    const double total = std::accumulate(
        values.begin(),
        values.end(),
        0.0,
        [](double sum, const auto& value)
        {
            return sum + value.second;
        }
    );

    if (!(total > 0.0))
    {
        throw std::runtime_error{"Containment requires positive intensity."};
    }

    return ContainmentMetrics{
        radiusAtFraction(values, total, 0.50),
        radiusAtFraction(values, total, 0.68),
        radiusAtFraction(values, total, 0.90)
    };
}
}

QualityAnalysisResult QualityAnalyzer::analyze(
    const ReconstructionData& data,
    const VisConfig& config
)
{
    EnergyMetrics fullSkyEnergy = calculateEnergyMetrics(
        marginalizeEnergies(data),
        config,
        "v7_full_sky_optional_gaussian"
    );
    const std::vector<SkyPixel> fullSkyPixels = marginalizeDirections(data);
    const std::vector<SkyPixel> gatedPixels = energyGatedPixels(
        data,
        fullSkyEnergy.intervalLowMeV,
        fullSkyEnergy.intervalHighMeV
    );
    DirectionMetrics direction = calculateDirectionMetrics(
        gatedPixels,
        config,
        fullSkyPixels.size(),
        fullSkyEnergy.intervalLowMeV,
        fullSkyEnergy.intervalHighMeV
    );
    EnergyMetrics directionGatedEnergy = calculateEnergyMetrics(
        directionGatedSpectrum(
            data,
            direction.centroidDirection,
            config.analysis().directionSpectrumRadiusDegree
        ),
        config,
        "v7_direction_gated_optional_gaussian"
    );
    directionGatedEnergy.directionGateRadiusDegree =
        config.analysis().directionSpectrumRadiusDegree;

    return QualityAnalysisResult{
        std::move(fullSkyEnergy),
        std::move(direction),
        std::move(directionGatedEnergy),
        calculateContainment(data, config.truth())
    };
}
