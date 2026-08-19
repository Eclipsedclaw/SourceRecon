// D:\CodexForSR\EIID_CPP\io_translator_version\core\grid.cpp

#include "grid.h"

#include <healpix_base.h>

#include <stdexcept>

Grid::Grid(const Parameter& parameter)
{
    parameter_ = &parameter;

    if (parameter_->healpixNside <= 0 || parameter_->energyPointCount <= 0)
    {
        throw std::runtime_error{"HEALPix Nside and energy point count must be positive."};
    }

    buildDirections();
    buildEnergies();
    buildCells();
}

void Grid::buildDirections()
{
    const int nside = parameter_->healpixNside;
    const int pixelCount = 12 * nside * nside;

    // RING 表示使用 HEALPix 的环形像素编号；SET_NSIDE 表示构造函数收到的是 Nside，而不是 order。
    const Healpix_Base healpixBase(nside, RING, SET_NSIDE);

    directions_.reserve(static_cast<std::size_t>(pixelCount));
    healpixPixelIds_.reserve(static_cast<std::size_t>(pixelCount));
    directionAnglesDegree_.reserve(static_cast<std::size_t>(pixelCount));
    directionPhiDegree_.reserve(static_cast<std::size_t>(pixelCount));

    for (int pixelId = 0; pixelId < pixelCount; ++pixelId)
    {
        // pix2vec() 返回当前像素中心的三维单位向量。
        // pix2ang() 返回同一中心的极角 theta 和方位角 phi，二者单位都是弧度。
        const vec3 healpixDirection = healpixBase.pix2vec(pixelId);
        const pointing healpixAngle = healpixBase.pix2ang(pixelId);

        const Vec3 direction{static_cast<Decimal>(healpixDirection.x), static_cast<Decimal>(healpixDirection.y), static_cast<Decimal>(healpixDirection.z)};
        const Decimal thetaDegree = static_cast<Decimal>(healpixAngle.theta) * static_cast<Decimal>(180.0L) / PI;
        const Decimal phiDegree = static_cast<Decimal>(healpixAngle.phi) * static_cast<Decimal>(180.0L) / PI;

        directions_.push_back(direction);
        healpixPixelIds_.push_back(static_cast<std::size_t>(pixelId));
        directionAnglesDegree_.push_back(thetaDegree);
        directionPhiDegree_.push_back(phiDegree);
    }

    // 同时检查我们使用的像素数公式与 HEALPix 对象报告的数量完全一致。
    if (static_cast<int>(directions_.size()) != healpixBase.Npix())
    {
        throw std::runtime_error{"HEALPix pixel count does not match 12 * Nside * Nside."};
    }
}

void Grid::buildEnergies()
{
    const int pointCount = parameter_->energyPointCount;
    const Decimal step = pointCount == 1 ? static_cast<Decimal>(0.0L) : (parameter_->energyMaxMeV - parameter_->energyMinMeV) / static_cast<Decimal>(pointCount - 1);

    for (int index = 0; index < pointCount; ++index)
    {
        const Decimal energyMeV = parameter_->energyMinMeV + static_cast<Decimal>(index) * step;
        energiesMeV_.push_back(energyMeV);
    }
}

void Grid::buildCells()
{
    for (std::size_t directionIndex = 0; directionIndex < directions_.size(); ++directionIndex)
    {
        for (std::size_t energyIndex = 0; energyIndex < energiesMeV_.size(); ++energyIndex)
        {
            const Cell cell{directionIndex, energyIndex, healpixPixelIds_[directionIndex], directionAnglesDegree_[directionIndex], directionPhiDegree_[directionIndex], directions_[directionIndex], energiesMeV_[energyIndex], parameter_->defaultSensitivity};
            cells_.push_back(cell);
        }
    }
}

const std::vector<Cell>& Grid::cells() const
{
    return cells_;
}

std::size_t Grid::directionCount() const
{
    return directions_.size();
}

std::size_t Grid::energyCount() const
{
    return energiesMeV_.size();
}
