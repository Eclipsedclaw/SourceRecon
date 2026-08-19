#include "include/eiid.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <stdexcept>

namespace
{
Decimal dot(const Vec3& a, const Vec3& b)
{
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

Vec3 unitVector(const Vec3& vector)
{
    const Decimal length = std::sqrt(dot(vector, vector));

    if (length <= DENOMINATOR_FLOOR)
    {
        throw std::runtime_error{"A direction vector has zero length."};
    }

    return {vector.x / length, vector.y / length, vector.z / length};
}
}

Decimal calculateResponse(const Event& event, const Cell& cell, const Parameter& parameter)
{
    const Decimal incidentEnergy = cell.energyMeV;
    const Decimal energyAfterFirstHit = incidentEnergy - event.e1MeV;

    // 候选入射能量必须大于第一次沉积能量。
    if (energyAfterFirstHit <= static_cast<Decimal>(0.0L))
    {
        return static_cast<Decimal>(0.0L);
    }

    // 候选能量给出一个康普顿散射角。
    const Decimal cosThetaFromEnergy = static_cast<Decimal>(1.0L) - ELECTRON_MASS_MEV * (static_cast<Decimal>(1.0L) / energyAfterFirstHit - static_cast<Decimal>(1.0L) / incidentEnergy);

    if (cosThetaFromEnergy < static_cast<Decimal>(-1.0L) || cosThetaFromEnergy > static_cast<Decimal>(1.0L))
    {
        return static_cast<Decimal>(0.0L);
    }

    const Decimal thetaFromEnergy = std::acos(cosThetaFromEnergy);

    // r1 指向 r2 的方向，就是散射后光子的传播方向。
    const Vec3 hitDifference{event.r2.x - event.r1.x, event.r2.y - event.r1.y, event.r2.z - event.r1.z};
    const Vec3 scatteredDirection = unitVector(hitDifference);

    // sourceDirection 指向天空中的源，所以 gamma 的入射传播方向与它相反。
    const Vec3 sourceDirection = unitVector(cell.sourceDirection);
    const Vec3 incidentDirection{-sourceDirection.x, -sourceDirection.y, -sourceDirection.z};

    // 候选来源方向与两个 hit 的位置给出另一个散射角。
    const Decimal cosThetaFromGeometry = std::clamp(dot(incidentDirection, scatteredDirection), static_cast<Decimal>(-1.0L), static_cast<Decimal>(1.0L));
    const Decimal thetaFromGeometry = std::acos(cosThetaFromGeometry);

    // 两个散射角越接近，当前方向—能量 cell 对事件的解释能力越强。
    const Decimal sigmaRadian = parameter.responseSigmaDegree * PI / static_cast<Decimal>(180.0L);
    const Decimal angleDifference = thetaFromGeometry - thetaFromEnergy;
    return std::exp(static_cast<Decimal>(-0.5L) * angleDifference * angleDifference / (sigmaRadian * sigmaRadian));
}

std::vector<Decimal> runEiid(const std::vector<Event>& events, const Grid& grid, const Parameter& parameter)
{
    const std::vector<Cell>& cells = grid.cells();

    // 所有可能 cell 都用正数初始化。乘法更新无法把一个初始值为 0 的 cell 重新变成正数。
    std::vector<Decimal> image(cells.size(), static_cast<Decimal>(1.0L));

    for (int iteration = 0; iteration < parameter.iterationCount; ++iteration)
    {
        std::vector<Decimal> update(cells.size(), static_cast<Decimal>(0.0L));

        for (const Event& event : events)
        {
            std::vector<Decimal> eventResponse(cells.size(), static_cast<Decimal>(0.0L));
            Decimal lambda = static_cast<Decimal>(0.0L);

            // 先计算当前联合图对这个事件的总解释能力 lambda。
            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                eventResponse[cell] = calculateResponse(event, cells[cell], parameter);
                lambda += eventResponse[cell] * image[cell];
            }

            if (lambda <= DENOMINATOR_FLOOR)
            {
                throw std::runtime_error{"An event cannot be explained by the grid."};
            }

            // 当前事件按照 response / lambda 给所有方向—能量 cell 投票。
            for (std::size_t cell = 0; cell < cells.size(); ++cell)
            {
                update[cell] += eventResponse[cell] / lambda;
            }
        }

        // 汇总所有事件的票，并用每个 cell 的灵敏度修正，得到下一轮联合图。
        for (std::size_t cell = 0; cell < cells.size(); ++cell)
        {
            if (cells[cell].sensitivity > static_cast<Decimal>(0.0L))
            {
                image[cell] *= update[cell] / cells[cell].sensitivity;
            }
            else
            {
                image[cell] = static_cast<Decimal>(0.0L);
            }
        }
    }

    return image;
}

std::vector<Event> makeToyEvents(const Parameter& parameter)
{
    const Decimal trueEnergy = parameter.toyTrueEnergyMeV;
    const Decimal scatterAngle = parameter.toyScatterAngleDegree * PI / static_cast<Decimal>(180.0L);

    // 由康普顿公式反算教学事件在第一次 hit 中应沉积的能量。
    const Decimal energyAfterScatter = static_cast<Decimal>(1.0L) / (static_cast<Decimal>(1.0L) / trueEnergy + (static_cast<Decimal>(1.0L) - std::cos(scatterAngle)) / ELECTRON_MASS_MEV);
    const Decimal firstDeposit = trueEnergy - energyAfterScatter;

    std::vector<Event> events;

    // 不同事件拥有不同方位角，但都来自相机正前方，且真实能量相同。
    for (int eventIndex = 0; eventIndex < parameter.toyEventCount; ++eventIndex)
    {
        const Decimal phi = static_cast<Decimal>(2.0L) * PI * static_cast<Decimal>(eventIndex) / static_cast<Decimal>(parameter.toyEventCount);
        const Vec3 secondHit{std::sin(scatterAngle) * std::cos(phi), std::sin(scatterAngle) * std::sin(phi), std::cos(scatterAngle)};
        const Event event{{static_cast<Decimal>(0.0L), static_cast<Decimal>(0.0L), static_cast<Decimal>(0.0L)}, secondHit, firstDeposit};
        events.push_back(event);
    }

    return events;
}

void printResult(const std::vector<Decimal>& image, const Grid& grid)
{
    const std::vector<Cell>& cells = grid.cells();

    if (image.size() != cells.size() || image.empty())
    {
        throw std::runtime_error{"The result size does not match the grid."};
    }

    std::cout << std::fixed << std::setprecision(6);

    for (std::size_t cell = 0; cell < cells.size(); ++cell)
    {
        std::cout << "direction " << cells[cell].directionAngleDegree << " deg, energy " << cells[cell].energyMeV << " MeV: " << image[cell] << '\n';
    }

    const auto peak = std::max_element(image.begin(), image.end());
    const std::size_t peakCell = static_cast<std::size_t>(std::distance(image.begin(), peak));

    std::cout << "\nPeak: direction " << cells[peakCell].directionAngleDegree << " deg, energy " << cells[peakCell].energyMeV << " MeV\n";
}
