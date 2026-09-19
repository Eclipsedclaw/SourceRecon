#include "plot_utils.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>

namespace
{
constexpr double PI = 3.141592653589793238462643383279502884;

double degreeToRadian(double degree)
{
    return degree * PI / 180.0;
}

double radianToDegree(double radian)
{
    return radian * 180.0 / PI;
}
}

std::vector<SkyPixel> marginalizeDirections(const ReconstructionData& data)
{
    std::map<std::uint64_t, SkyPixel> pixels;

    for (const ImageCell& cell : data.cells)
    {
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

        if (!inserted)
        {
            // 同一个 HEALPix pixel 在不同能量 cell 中具有相同方向坐标。
            // 这里只累加权重，不重新计算方向。
        }

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

std::vector<EnergyPoint> marginalizeEnergies(const ReconstructionData& data)
{
    std::map<double, double> weights;

    for (const ImageCell& cell : data.cells)
    {
        weights[cell.energyMeV] += cell.weight;
    }

    std::vector<EnergyPoint> result;
    result.reserve(weights.size());

    for (const auto& [energyMeV, weight] : weights)
    {
        result.push_back(EnergyPoint{energyMeV, weight});
    }

    return result;
}

std::vector<double> makeEnergyBinEdges(const std::vector<EnergyPoint>& spectrum)
{
    if (spectrum.empty())
    {
        throw std::runtime_error{"Cannot construct energy bins from an empty spectrum."};
    }

    std::vector<double> edges(spectrum.size() + 1);

    if (spectrum.size() == 1)
    {
        const double halfWidth = std::max(0.05, std::abs(spectrum.front().energyMeV) * 0.05);
        edges[0] = spectrum.front().energyMeV - halfWidth;
        edges[1] = spectrum.front().energyMeV + halfWidth;
        return edges;
    }

    edges.front() = spectrum.front().energyMeV -
        0.5 * (spectrum[1].energyMeV - spectrum[0].energyMeV);

    for (std::size_t index = 1; index < spectrum.size(); ++index)
    {
        edges[index] = 0.5 * (
            spectrum[index - 1].energyMeV +
            spectrum[index].energyMeV
        );
    }

    edges.back() = spectrum.back().energyMeV +
        0.5 * (
            spectrum.back().energyMeV -
            spectrum[spectrum.size() - 2].energyMeV
        );

    return edges;
}

std::array<double, 3> truthDirection(const TruthInfo& truth)
{
    const double theta = degreeToRadian(truth.thetaDegree);
    const double phi = degreeToRadian(truth.phiDegree);

    return {
        std::sin(theta) * std::cos(phi),
        std::sin(theta) * std::sin(phi),
        std::cos(theta)
    };
}

DisplayCoordinate cameraCenteredCoordinate(double x, double y, double z)
{
    const double norm = std::sqrt(x * x + y * y + z * z);

    if (!(norm > std::numeric_limits<double>::epsilon()))
    {
        throw std::runtime_error{"Cannot project a zero-length direction vector."};
    }

    // 新坐标系把相机正前方 -Z 作为经纬度 (0, 0)，因此它位于二维图中心。
    const double longitude = std::atan2(x, -z);
    const double latitude = std::asin(std::clamp(y / norm, -1.0, 1.0));

    return DisplayCoordinate{
        radianToDegree(longitude),
        radianToDegree(latitude)
    };
}

double angularSeparationDegree(
    const SkyPixel& pixel,
    const std::array<double, 3>& trueDirection
)
{
    const double norm = std::sqrt(
        pixel.directionX * pixel.directionX +
        pixel.directionY * pixel.directionY +
        pixel.directionZ * pixel.directionZ
    );

    if (!(norm > std::numeric_limits<double>::epsilon()))
    {
        throw std::runtime_error{"Cannot calculate an angle from a zero-length direction vector."};
    }

    const double dot = (
        pixel.directionX * trueDirection[0] +
        pixel.directionY * trueDirection[1] +
        pixel.directionZ * trueDirection[2]
    ) / norm;

    return radianToDegree(std::acos(std::clamp(dot, -1.0, 1.0)));
}

std::size_t inferHealpixNside(std::size_t pixelCount)
{
    if (pixelCount == 0)
    {
        return 0;
    }

    const double estimate = std::sqrt(static_cast<double>(pixelCount) / 12.0);
    const std::size_t nside = static_cast<std::size_t>(std::llround(estimate));

    if (12 * nside * nside != pixelCount)
    {
        return 0;
    }

    return nside;
}

double meanHealpixPixelScaleDegree(std::size_t pixelCount)
{
    if (pixelCount == 0)
    {
        throw std::runtime_error{"Cannot estimate grid resolution from zero pixels."};
    }

    const double averageAreaSteradian = 4.0 * PI / static_cast<double>(pixelCount);
    return radianToDegree(std::sqrt(averageAreaSteradian));
}
