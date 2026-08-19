#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>

// 完成“一轮”MLEM 更新。
//
// response[event][cell]：
//   某个 cell 对某个事件的解释能力。数值越大，说明越匹配。
//
// sensitivity[cell]：
//   探测器看到该 cell 的相对能力。等于 0 表示这个 cell 无法被探测。
//
// oldImage[cell]：
//   本轮更新前，我们认为各个 cell 分别有多强。
std::vector<double> oneMlemIteration(
    const std::vector<std::vector<double>>& response,
    const std::vector<double>& sensitivity,
    const std::vector<double>& oldImage)
{
    const std::size_t cellCount{oldImage.size()};

    // update[cell] 用来累计所有事件投给该 cell 的票。
    std::vector<double> update(cellCount, 0.0);

    // 一次处理一个事件。
    for (const std::vector<double>& eventResponse : response) {
        // lambda 表示：当前整张图对这个事件的总解释能力。
        // 公式：lambda = sum(response[cell] * oldImage[cell])
        double lambda{0.0};

        for (std::size_t cell{0}; cell < cellCount; ++cell) {
            lambda += eventResponse[cell] * oldImage[cell];
        }

        // lambda 为 0 意味着没有任何 cell 能解释这个事件，继续除法会出错。
        if (lambda <= 1.0e-12) {
            throw std::runtime_error{"An event cannot be explained by any cell."};
        }

        // 当前事件按照 response / lambda 的比例，给各个 cell 投票。
        for (std::size_t cell{0}; cell < cellCount; ++cell) {
            update[cell] += eventResponse[cell] / lambda;
        }
    }

    std::vector<double> newImage(cellCount, 0.0);

    // 把旧强度、累计票数和探测灵敏度合并，得到新强度。
    // 公式：new = old * update / sensitivity
    for (std::size_t cell{0}; cell < cellCount; ++cell) {
        if (sensitivity[cell] > 0.0) {
            newImage[cell] =
                oldImage[cell] * update[cell] / sensitivity[cell];
        }
        // sensitivity 为 0 时，newImage 保持初始化时的 0，不进行除法。
    }

    return newImage;
}

int main()
{
    // 这是一个可以手算的例子：2 个事件，3 个候选 cell。
    // 每一行属于一个事件，每一列属于一个 cell。
    const std::vector<std::vector<double>> response{
        {1.0, 0.5, 0.0},
        {0.2, 0.5, 1.0}
    };

    // 为了先看清算法，暂时假设三个 cell 的探测灵敏度相同。
    const std::vector<double> sensitivity{1.0, 1.0, 1.0};

    // MLEM 不能把可能存在信号的 cell 初始化为 0，
    // 因为乘法更新会让 0 永远保持为 0。这里统一从 1 开始。
    const std::vector<double> oldImage{1.0, 1.0, 1.0};

    const std::vector<double> newImage{
        oneMlemIteration(response, sensitivity, oldImage)
    };

    // 正确输出应约为：0.784314  0.627451  0.588235
    std::cout << std::fixed << std::setprecision(6);
    for (std::size_t cell{0}; cell < newImage.size(); ++cell) {
        std::cout << "cell " << cell << ": " << newImage[cell] << '\n';
    }

    return 0;
}
