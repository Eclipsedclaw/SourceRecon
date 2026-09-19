#include "fit_analysis.h"

#include <TF1.h>
#include <TF2.h>
#include <TFitResultPtr.h>
#include <TGraph2D.h>
#include <TH1D.h>

#include <algorithm>
#include <array>
#include <cmath>
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
            "A direction opposite the local fit centre has no unique tangent coordinate."
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

EnergyFitResult fitEnergySpectrum(
    const std::vector<EnergyPoint>& spectrum,
    double halfWidthMeV,
    double truthEnergyMeV,
    const char* objectName
)
{
    if (spectrum.size() < 5)
    {
        throw std::runtime_error{"Energy fitting requires at least five grid points."};
    }

    const std::vector<double> edges = makeEnergyBinEdges(spectrum);
    TH1D histogram{
        objectName,
        objectName,
        static_cast<int>(spectrum.size()),
        edges.data()
    };
    histogram.SetDirectory(nullptr);

    for (std::size_t index = 0; index < spectrum.size(); ++index)
    {
        if (!std::isfinite(spectrum[index].weight) || spectrum[index].weight < 0.0)
        {
            throw std::runtime_error{
                "Energy fitting requires finite non-negative image weights."
            };
        }

        histogram.SetBinContent(
            static_cast<int>(index + 1),
            spectrum[index].weight
        );
    }

    const auto peakIterator = std::max_element(
        spectrum.begin(),
        spectrum.end(),
        [](const EnergyPoint& left, const EnergyPoint& right)
        {
            return left.weight < right.weight;
        }
    );
    const double peakEnergy = peakIterator->energyMeV;
    const double maximum = peakIterator->weight;
    const double fitMin = std::max(edges.front(), peakEnergy - halfWidthMeV);
    const double fitMax = std::min(edges.back(), peakEnergy + halfWidthMeV);

    if (!(maximum > 0.0) || !(fitMax > fitMin))
    {
        throw std::runtime_error{"Energy spectrum has no positive fit peak."};
    }

    double localMinimum = maximum;

    for (const EnergyPoint& point : spectrum)
    {
        if (point.energyMeV >= fitMin && point.energyMeV <= fitMax)
        {
            localMinimum = std::min(localMinimum, point.weight);
        }
    }

    const double energyStep = std::abs(
        spectrum[1].energyMeV - spectrum[0].energyMeV
    );

    // ROOT 数值拟合失败时，局部加权矩给出一个可解释的退路。
    // 先减去窗口内最低值作为常数背景估计；若信号和为零，再退回原权重。
    double momentWeight = 0.0;
    double momentEnergy = 0.0;
    double momentEnergySquared = 0.0;

    for (const EnergyPoint& point : spectrum)
    {
        if (point.energyMeV < fitMin || point.energyMeV > fitMax)
        {
            continue;
        }

        const double signal = std::max(0.0, point.weight - localMinimum);
        momentWeight += signal;
        momentEnergy += signal * point.energyMeV;
        momentEnergySquared += signal * point.energyMeV * point.energyMeV;
    }

    if (!(momentWeight > 0.0))
    {
        for (const EnergyPoint& point : spectrum)
        {
            if (point.energyMeV >= fitMin && point.energyMeV <= fitMax)
            {
                momentWeight += point.weight;
                momentEnergy += point.weight * point.energyMeV;
                momentEnergySquared +=
                    point.weight * point.energyMeV * point.energyMeV;
            }
        }
    }

    if (!(momentWeight > 0.0))
    {
        throw std::runtime_error{
            "Energy fit window contains no positive reconstructed intensity."
        };
    }

    const double momentMean = momentEnergy / momentWeight;
    const double momentVariance = std::max(
        0.0,
        momentEnergySquared / momentWeight - momentMean * momentMean
    );
    const double momentSigma = std::max(
        std::sqrt(momentVariance),
        std::max(energyStep * 0.20, 1.0e-8)
    );
    TF1 function{
        (std::string{objectName} + "_function").c_str(),
        "[0]*exp(-0.5*((x-[1])/[2])^2)+[3]",
        fitMin,
        fitMax
    };
    function.SetParNames("Amplitude", "Mean", "Sigma", "Background");
    function.SetParameters(
        std::max(maximum - localMinimum, maximum * 0.5),
        peakEnergy,
        std::max(2.0 * energyStep, halfWidthMeV / 4.0),
        localMinimum
    );
    function.SetParLimits(0, 0.0, maximum * 20.0);
    function.SetParLimits(1, fitMin, fitMax);
    function.SetParLimits(2, std::max(energyStep * 0.20, 1.0e-8), halfWidthMeV);
    function.SetParLimits(3, 0.0, maximum * 2.0);

    const TFitResultPtr fitResult = histogram.Fit(
        &function,
        "QSNW",
        "",
        fitMin,
        fitMax
    );
    const int fitStatus = static_cast<int>(fitResult);
    const double fittedMean = function.GetParameter(1);
    const double fittedSigma = std::abs(function.GetParameter(2));
    const bool converged = fitStatus == 0 &&
        std::isfinite(fittedMean) &&
        std::isfinite(fittedSigma) &&
        fittedSigma > 0.0;
    const double mean = converged ? fittedMean : momentMean;
    const double sigma = converged ? fittedSigma : momentSigma;
    const double amplitude = converged
        ? function.GetParameter(0)
        : std::max(maximum - localMinimum, maximum * 0.5);
    const double background = converged
        ? function.GetParameter(3)
        : localMinimum;

    return EnergyFitResult{
        converged,
        fitStatus,
        amplitude,
        mean,
        sigma,
        background,
        fitMin,
        fitMax,
        mean - truthEnergyMeV,
        2.354820045 * sigma,
        2.354820045 * sigma / mean,
        0.0,
        spectrum
    };
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

DirectionFitResult fitDirection(
    const std::vector<SkyPixel>& pixels,
    const VisConfig& config,
    std::size_t fullSkyPixelCount
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
        throw std::runtime_error{"The energy-gated direction map has no positive peak."};
    }

    const std::array<double, 3> peakDirection = pixelDirection(*peakIterator);
    const TangentFrame frame = makeTangentFrame(peakDirection);
    const double fitRadius = config.fit().directionFitRadiusDegree;
    // 分辨率属于原始 HEALPix 网格，不能用能量门控后偶然保留下来的
    // 像素数量估算，否则稀疏结果会被误判为更粗的网格。
    const double pixelScale =
        meanHealpixPixelScaleDegree(fullSkyPixelCount);
    std::vector<LocalDirectionPoint> points;

    for (const SkyPixel& pixel : pixels)
    {
        const std::array<double, 3> direction = pixelDirection(pixel);
        const double separation = separationDegree(peakDirection, direction);

        if (separation <= fitRadius)
        {
            const std::array<double, 2> local = projectToTangent(frame, direction);
            points.push_back(LocalDirectionPoint{local[0], local[1], pixel.weight});
        }
    }

    if (points.size() < 9)
    {
        throw std::runtime_error{
            "The local direction fit contains fewer than nine HEALPix pixels."
        };
    }

    TGraph2D graph{static_cast<int>(points.size())};
    double minimum = points.front().weight;
    double maximum = points.front().weight;

    for (std::size_t index = 0; index < points.size(); ++index)
    {
        graph.SetPoint(
            static_cast<int>(index),
            points[index].uDegree,
            points[index].vDegree,
            points[index].weight
        );
        minimum = std::min(minimum, points[index].weight);
        maximum = std::max(maximum, points[index].weight);
    }

    TF2 function{
        "direction_gaussian_fit_function",
        ellipticalGaussian,
        -fitRadius,
        fitRadius,
        -fitRadius,
        fitRadius,
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
        0.0,
        0.0,
        std::max(2.0 * pixelScale, fitRadius / 4.0),
        std::max(pixelScale, fitRadius / 6.0),
        0.0,
        minimum
    );
    function.SetParLimits(0, 0.0, maximum * 20.0);
    function.SetParLimits(1, -fitRadius * 0.5, fitRadius * 0.5);
    function.SetParLimits(2, -fitRadius * 0.5, fitRadius * 0.5);
    function.SetParLimits(3, pixelScale * 0.20, fitRadius);
    function.SetParLimits(4, pixelScale * 0.20, fitRadius);
    function.SetParLimits(5, -0.5 * pi, 0.5 * pi);
    function.SetParLimits(6, 0.0, maximum * 2.0);

    const TFitResultPtr fitResult = graph.Fit(&function, "QSN");
    const int fitStatus = static_cast<int>(fitResult);
    const double fittedCenterU = function.GetParameter(1);
    const double fittedCenterV = function.GetParameter(2);
    const double fittedSigmaMajor = std::abs(function.GetParameter(3));
    const double fittedSigmaMinor = std::abs(function.GetParameter(4));
    const bool converged = fitStatus == 0 &&
        std::isfinite(fittedCenterU) &&
        std::isfinite(fittedCenterV) &&
        std::isfinite(fittedSigmaMajor) &&
        std::isfinite(fittedSigmaMinor) &&
        fittedSigmaMajor > 0.0 &&
        fittedSigmaMinor > 0.0;

    // 与能量拟合相同，二维拟合失败时使用局部峰的加权协方差。
    // 这不会冒充成功拟合：fitConverged 会保持 false，并写入输出警告。
    double momentWeight = 0.0;
    double momentU = 0.0;
    double momentV = 0.0;

    for (const LocalDirectionPoint& point : points)
    {
        const double signal = std::max(0.0, point.weight - minimum);
        momentWeight += signal;
        momentU += signal * point.uDegree;
        momentV += signal * point.vDegree;
    }

    if (!(momentWeight > 0.0))
    {
        throw std::runtime_error{
            "Direction fit window contains no positive peak above background."
        };
    }

    const double fallbackCenterU = momentU / momentWeight;
    const double fallbackCenterV = momentV / momentWeight;
    double covarianceUU = 0.0;
    double covarianceVV = 0.0;
    double covarianceUV = 0.0;

    for (const LocalDirectionPoint& point : points)
    {
        const double signal = std::max(0.0, point.weight - minimum);
        const double deltaU = point.uDegree - fallbackCenterU;
        const double deltaV = point.vDegree - fallbackCenterV;
        covarianceUU += signal * deltaU * deltaU;
        covarianceVV += signal * deltaV * deltaV;
        covarianceUV += signal * deltaU * deltaV;
    }

    covarianceUU /= momentWeight;
    covarianceVV /= momentWeight;
    covarianceUV /= momentWeight;
    const double covarianceDiscriminant = std::sqrt(std::max(
        0.0,
        (covarianceUU - covarianceVV) *
            (covarianceUU - covarianceVV) +
        4.0 * covarianceUV * covarianceUV
    ));
    const double fallbackMajor = std::sqrt(std::max(
        0.5 * (covarianceUU + covarianceVV + covarianceDiscriminant),
        pixelScale * pixelScale * 0.04
    ));
    const double fallbackMinor = std::sqrt(std::max(
        0.5 * (covarianceUU + covarianceVV - covarianceDiscriminant),
        pixelScale * pixelScale * 0.04
    ));
    const double fallbackAngle = 0.5 * std::atan2(
        2.0 * covarianceUV,
        covarianceUU - covarianceVV
    );

    const double centerU = converged ? fittedCenterU : fallbackCenterU;
    const double centerV = converged ? fittedCenterV : fallbackCenterV;
    double sigmaMajor = converged ? fittedSigmaMajor : fallbackMajor;
    double sigmaMinor = converged ? fittedSigmaMinor : fallbackMinor;
    double angleRadian = converged
        ? function.GetParameter(5)
        : fallbackAngle;

    if (sigmaMinor > sigmaMajor)
    {
        std::swap(sigmaMajor, sigmaMinor);
        angleRadian += 0.5 * pi;
    }

    const std::array<double, 3> fittedDirection = directionFromTangent(
        frame,
        centerU,
        centerV
    );
    const std::array<double, 3> trueDirection = truthDirection(config.truth());
    const double theta = toDegree(std::acos(std::clamp(
        fittedDirection[2],
        -1.0,
        1.0
    )));
    double phi = toDegree(std::atan2(fittedDirection[1], fittedDirection[0]));

    if (phi < 0.0)
    {
        phi += 360.0;
    }

    bool truthInside = false;
    double truthU = 0.0;
    double truthV = 0.0;
    const double truthDistanceFromPeak = separationDegree(peakDirection, trueDirection);

    if (truthDistanceFromPeak < 179.999)
    {
        const std::array<double, 2> truthLocal =
            projectToTangent(frame, trueDirection);
        truthU = truthLocal[0];
        truthV = truthLocal[1];
        truthInside = std::hypot(truthU, truthV) <= fitRadius;
    }

    return DirectionFitResult{
        converged,
        sigmaMinor < pixelScale,
        fitStatus,
        inferHealpixNside(fullSkyPixelCount),
        pixelScale,
        fitRadius,
        converged
            ? function.GetParameter(0)
            : std::max(maximum - minimum, maximum * 0.5),
        centerU,
        centerV,
        sigmaMajor,
        sigmaMinor,
        toDegree(angleRadian),
        converged ? function.GetParameter(6) : minimum,
        theta,
        phi,
        separationDegree(fittedDirection, trueDirection),
        truthInside,
        truthU,
        truthV,
        fittedDirection,
        std::move(points)
    };
}

std::vector<EnergyPoint> directionGatedSpectrum(
    const ReconstructionData& data,
    const std::array<double, 3>& fittedDirection,
    double radiusDegree
)
{
    std::map<double, double> weights;

    for (const ImageCell& cell : data.cells)
    {
        if (separationDegree(cellDirection(cell), fittedDirection) <= radiusDegree)
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
        throw std::runtime_error{"Containment requires positive total intensity."};
    }

    return ContainmentMetrics{
        radiusAtFraction(values, total, 0.50),
        radiusAtFraction(values, total, 0.68),
        radiusAtFraction(values, total, 0.90)
    };
}
}

FitAnalysisResult FitAnalyzer::analyze(
    const ReconstructionData& data,
    const VisConfig& config
)
{
    EnergyFitResult preliminary = fitEnergySpectrum(
        marginalizeEnergies(data),
        config.fit().energyFitHalfWidthMeV,
        config.truth().energyMeV,
        "preliminary_energy_fit"
    );
    const double gateHalfWidth =
        config.fit().directionEnergyGateSigma * preliminary.sigmaMeV;
    const std::vector<SkyPixel> gatedPixels = energyGatedPixels(
        data,
        preliminary.meanMeV - gateHalfWidth,
        preliminary.meanMeV + gateHalfWidth
    );
    const std::size_t fullSkyPixelCount = marginalizeDirections(data).size();
    DirectionFitResult direction = fitDirection(
        gatedPixels,
        config,
        fullSkyPixelCount
    );
    EnergyFitResult finalEnergy = fitEnergySpectrum(
        directionGatedSpectrum(
            data,
            direction.fittedDirection,
            config.fit().directionSpectrumRadiusDegree
        ),
        config.fit().energyFitHalfWidthMeV,
        config.truth().energyMeV,
        "final_energy_fit"
    );
    finalEnergy.directionGateRadiusDegree =
        config.fit().directionSpectrumRadiusDegree;

    return FitAnalysisResult{
        std::move(preliminary),
        std::move(direction),
        std::move(finalEnergy),
        calculateContainment(data, config.truth())
    };
}
