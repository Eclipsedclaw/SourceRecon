#include <algorithm>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>

constexpr double electronMassMeV{0.511};
constexpr double pi{3.14159265358979323846};

// 三维向量这里只用来保存方向和两个 hit 的位置。
struct Vec3
{
    double x;
    double y;
    double z;
};

// 一个两次相互作用事件：r1/e1 是第一次 hit，r2 是第二次 hit。
struct Event
{
    Vec3 r1;
    Vec3 r2;
    double e1MeV;
};

// EIID 的一个 cell 不是普通图像像素，而是“一个来源方向 + 一个入射能量”。
struct Cell
{
    Vec3 sourceDirection;
    double energyMeV;
};

//点乘
double dot(const Vec3& a, const Vec3& b)
{
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

//归一化
Vec3 unitVector(const Vec3& v)
{
    const double length{std::sqrt(dot(v, v))};
    if (length <= 1.0e-12) {
        throw std::runtime_error{"A direction vector has zero length."};
    }
    return {v.x / length, v.y / length, v.z / length};
}

// 计算“这个方向和能量的 cell”解释当前事件的能力。
double response(const Event& event, const Cell& cell)
{
    const double incidentEnergy{cell.energyMeV};
    const double energyAfterFirstHit{incidentEnergy - event.e1MeV};

    // 候选入射能量必须大于第一次沉积能量。
    if (energyAfterFirstHit <= 0.0) {
        return 0.0;
    }

    // 候选能量给出的康普顿散射角。
    const double cosThetaFromEnergy{
        1.0 - electronMassMeV
                  * (1.0 / energyAfterFirstHit - 1.0 / incidentEnergy)
    };

    if (cosThetaFromEnergy < -1.0 || cosThetaFromEnergy > 1.0) {
        return 0.0;
    }

    const double thetaFromEnergy{std::acos(cosThetaFromEnergy)};

    // r1 -> r2 给出散射后光子的传播方向。
    const Vec3 scatteredDirection{unitVector({
        event.r2.x - event.r1.x,
        event.r2.y - event.r1.y,
        event.r2.z - event.r1.z
    })};

    // sourceDirection 指向天空中的源；gamma 传播方向与它相反。
    const Vec3 source{unitVector(cell.sourceDirection)};
    const Vec3 incidentDirection{-source.x, -source.y, -source.z};

    // 候选来源方向和两个 hit 位置给出的几何散射角。
    const double cosThetaFromGeometry{
        std::clamp(dot(incidentDirection, scatteredDirection), -1.0, 1.0)
    };
    const double thetaFromGeometry{std::acos(cosThetaFromGeometry)};

    // 两个角越接近，当前 cell 越能解释这个事件。
    // 这里暂用 6 度宽的高斯；以后再替换成 Geant4 给出的真实响应。
    const double sigma{6.0 * pi / 180.0};
    const double difference{thetaFromGeometry - thetaFromEnergy};

    return std::exp(-0.5 * difference * difference / (sigma * sigma));
}

// 在“方向 × 能量”联合图上执行 EIID 的 LM-MLEM 迭代。
std::vector<double> runEiid(
    const std::vector<Event>& events,
    const std::vector<Cell>& cells,
    const std::vector<double>& sensitivity,
    int iterationCount)
{
    // 所有可能 cell 都必须用正数初始化；从 0 开始的 cell 永远无法被乘法更新救活。
    std::vector<double> image(cells.size(), 1.0);

    for (int iteration{0}; iteration < iterationCount; ++iteration) {
        std::vector<double> update(cells.size(), 0.0);

        for (const Event& event : events) {
            std::vector<double> eventResponse(cells.size(), 0.0);
            double lambda{0.0};

            // 先算当前图像对这个事件的总解释能力 lambda。
            for (std::size_t cell{0}; cell < cells.size(); ++cell) {
                eventResponse[cell] = response(event, cells[cell]);
                lambda += eventResponse[cell] * image[cell];
            }

            if (lambda <= 1.0e-12) {
                throw std::runtime_error{"An event cannot be explained by the grid."};
            }

            // 当前事件按照 response / lambda 给所有方向—能量 cell 投票。
            for (std::size_t cell{0}; cell < cells.size(); ++cell) {
                update[cell] += eventResponse[cell] / lambda;
            }
        }

        // 汇总所有事件的票，并用灵敏度修正，得到下一轮联合图。
        for (std::size_t cell{0}; cell < cells.size(); ++cell) {
            if (sensitivity[cell] > 0.0) {
                image[cell] *= update[cell] / sensitivity[cell];
            } else {
                image[cell] = 0.0;
            }
        }
    }

    return image;
}

// 生成几个教学事件。只有这里知道真值；runEiid() 不接收真值。
std::vector<Event> makeToyEvents()
{
    const double trueEnergy{1.0};
    const double scatterAngle{45.0 * pi / 180.0};

    // 由康普顿公式反算第一次 hit 应沉积的能量。
    const double energyAfterScatter{
        1.0 / (1.0 / trueEnergy
               + (1.0 - std::cos(scatterAngle)) / electronMassMeV)
    };
    const double firstDeposit{trueEnergy - energyAfterScatter};

    std::vector<Event> events;

    // 四个事件具有不同方位角，但都来自相机正前方、能量都是 1 MeV。
    for (double phi : {0.0, 0.5 * pi, pi, 1.5 * pi}) {
        const Vec3 secondHit{
            std::sin(scatterAngle) * std::cos(phi),
            std::sin(scatterAngle) * std::sin(phi),
            std::cos(scatterAngle)
        };
        events.push_back({{0.0, 0.0, 0.0}, secondHit, firstDeposit});
    }

    return events;
}

int main()
{
    const double tilt{20.0 * pi / 180.0};

    // 三个候选天空方向。第 0 个方向 (-Z) 是教学数据的真实来源方向。
    const std::vector<Vec3> directions{
        {0.0, 0.0, -1.0},
        {std::sin(tilt), 0.0, -std::cos(tilt)},
        {-std::sin(tilt), 0.0, -std::cos(tilt)}
    };

    // 三个候选入射能量。1.0 MeV 是教学数据的真实能量。
    const std::vector<double> energies{0.8, 1.0, 1.2};

    std::vector<Cell> cells;
    for (const Vec3& direction : directions) {
        for (double energy : energies) {
            cells.push_back({direction, energy});
        }
    }

    // 教学例子先假设每个 cell 的探测效率相同。
    // 正式版本必须换成 Geant4 统计出的方向—能量灵敏度。
    const std::vector<double> sensitivity(cells.size(), 1.0);
    const std::vector<Event> events{makeToyEvents()};
    const std::vector<double> image{runEiid(events, cells, sensitivity, 10)};

    std::cout << std::fixed << std::setprecision(6);
    for (std::size_t cell{0}; cell < cells.size(); ++cell) {
        const std::size_t directionIndex{cell / energies.size()};
        const std::size_t energyIndex{cell % energies.size()};

        std::cout << "direction " << directionIndex
                  << ", energy " << energies[energyIndex]
                  << " MeV: " << image[cell] << '\n';
    }

    const auto peak{std::max_element(image.begin(), image.end())};
    const std::size_t peakCell{
        static_cast<std::size_t>(std::distance(image.begin(), peak))
    };

    std::cout << "\nPeak: direction " << peakCell / energies.size()
              << ", energy " << energies[peakCell % energies.size()]
              << " MeV\n";
}
