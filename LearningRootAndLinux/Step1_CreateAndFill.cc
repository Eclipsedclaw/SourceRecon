// Step1_CreateAndFill.C
//
// 本宏只做一件事：创建 kinematics.root，并向其中的 Events 树写入 px、py 两列。
// 直接运行：root Step1_CreateAndFill.C

#include <TFile.h>
#include <TTree.h>

#include <cmath>
#include <iostream>
#include <memory>
#include <random>

// --------------------------- 本步的对象生命周期 ---------------------------
// outputFile：unique_ptr 管理的堆对象，函数结束时自动释放。
// tree：普通栈对象，离开函数作用域时自动析构。
// px、py：普通栈变量，地址在本函数执行期间稳定。
// Branch：只借用 px、py 的地址，不取得这两个变量的所有权。
// 磁盘文件：由 TFile 打开，由 Write() 写入，并由 Close() 明确关闭。
// --------------------------------------------------------------------------

void Step1_CreateAndFill()
{
    // TFile 是 ROOT 文件在内存中的 C++ 管理对象，负责打开、写入和关闭磁盘上的 .root 文件。
    // TFile::Open 返回裸指针；立即交给 unique_ptr 后，即使中途 return，也会自动调用析构函数，
    // 因而不会因为遗漏 delete 而泄漏这块堆内存。
    auto outputFile = std::unique_ptr<TFile>{TFile::Open("kinematics.root", "RECREATE")};

    // 指针非空并不等价于文件成功打开；ROOT 可能返回一个处于 zombie 状态的 TFile 对象。
    // 所以这里同时检查空指针与 IsZombie()，避免随后对无效文件继续写入。
    if (!outputFile || outputFile->IsZombie()) {
        std::cerr << "Error: cannot create kinematics.root\n";
        return;
    }

    // TTree 是 ROOT 的列式事件数据容器：每个 Branch 是一列，每次 Fill() 追加一行事件。
    // 创建 TFile 后，它会成为当前 gDirectory，因此随后创建的 tree 会自动挂到这个文件上。
    TTree tree{"Events", "Simple transverse-momentum events"};

    // px 和 py 是普通的栈变量，此时只在本函数的栈帧中占据两个 double 的空间。
    // 它们在整个 Fill 循环期间地址保持不变，这正是 Branch 地址绑定所要求的生命周期。
    double px{0.0};
    double py{0.0};

    // 这里不能把某次计算产生的临时量地址交给 Branch。
    // 临时量会在完整表达式结束时销毁，之后 Branch 保存的地址就会悬空。
    // px、py 则一直活到函数末尾，覆盖整个 Fill 循环，因而满足要求。

    // Branch 不会复制一个永久的 px 变量；它只保存“到哪里取当前值”的地址 &px。
    // 每次调用 Fill() 时，TTree 都沿这个地址读取当时的 double，并复制到自己的 Basket 缓冲区。
    // 这个模板重载能从 double* 推导叶子的类型，避免手写易错的 "px/D" 叶子描述字符串。
    tree.Branch("px", &px);
    tree.Branch("py", &py);

    // 以下随机数工具都来自 C++ 标准库，不是新的 ROOT 类。
    // 固定种子使每次运行都得到相同样本，便于学习时复现实验结果。
    std::mt19937_64 randomEngine{20260812};

    // 我们先生成近似高斯分布的 pT，再用均匀分布的 phi 分解成 px、py。
    // 这样第三步用高斯函数拟合 pT 是一个有意义、容易观察的入门案例。
    // std::normal_distribution 是 C++ 标准库中的随机数分布模板类，用于生成服从高斯（正态）分布的随机数。
    // <double> 指定生成的数据类型为双精度浮点数。
    // ptDistribution 是这个分布对象的变量名。
    // {3.0, 0.55} 是现代 C++ 推荐的“列表初始化（大括号初始化）”语法。
    // 这里传入了两个核心参数：
    //   1. 3.0 是均值（Mean，对应高斯分布的中心点），代表我们模拟的粒子的平均横向动量 pT 为 3.0 GeV。
    //   2. 0.55 是标准差（Standard Deviation，即分布的宽度）。
    std::normal_distribution<double> ptDistribution{3.0, 0.55};

    // constexpr 是现代 C++ 强烈推荐的关键字，意思是“常量表达式”。
    // 它告诉编译器：“这个值在编译时就已经完全确定了，运行时绝对不会改变，请直接在编译阶段把它替换进机器码。”
    // 这比古老的 #define 宏更安全（有严格的类型检查），比普通的 const 性能更极致。
    // 这里定义了一个双精度浮点数 twoPi，值为 2π 的高精度展开，代表一个完整的圆（弧度制）。
    constexpr double twoPi{6.28318530717958647692};

    // std::uniform_real_distribution 是用于生成“均匀分布”实数的模板类。
    // 它的特点是：在指定的区间内，每一个数值被抽中的概率是完全相等的。
    // {0.0, twoPi} 指定了分布的下限是 0，上限是 2π。
    // 物理意义：用来模拟粒子在横向平面（x-y平面）飞出时，其方位角 phi 是完全随机且 360 度各向同性的。
    std::uniform_real_distribution<double> phiDistribution{0.0, twoPi};

    // 同样使用 constexpr 定义一个编译期常量。
    // 设置要模拟的物理事件（Event）总数为 2000。
    // 这意味着我们在接下来的 for 循环中，要执行 2000 次 TTree 的 Fill() 操作，
    // 凭空“捏造”出 2000 个碰撞后飞出的粒子数据，存入我们的 .root 文件中。
    constexpr int numberOfEvents{2000};

    // constexpr 表示数值可在编译阶段确定，并且运行时不可修改。
    // 这既表达“事件数是配置常量”，也防止循环中意外改变上限。

    // 同一对内存变量可以反复赋新值，因为 Branch 绑定的是地址，而不是最初的数值。
    for (int eventIndex{0}; eventIndex < numberOfEvents; ++eventIndex) {
        double pt{0.0};

        // 物理上的横向动量大小不能为负；若高斯尾部偶然产生负数，就重新抽样。
        // 当前均值远大于标准差，所以此循环通常只执行一次。
        do {
            pt = ptDistribution(randomEngine);
        } while (pt <= 0.0);

        const double phi{phiDistribution(randomEngine)};
        px = pt * std::cos(phi);
        py = pt * std::sin(phi);

        // 注意：给 px、py 赋值不会改变它们的地址。
        // 因此无需也不应该在每次循环中重新调用 Branch。

        // Fill() 此刻读取 &px 和 &py 指向的值，并把这一事件追加到内存 Basket。
        // 它不负责最终关闭文件，也不替代下面显式的 Write()。
        tree.Fill();
    }

    // Write() 把树的元数据和尚未落盘的 Basket 写入当前 TFile。
    // 返回值是写入的字节数；小于等于零说明写入没有成功完成。
    if (tree.Write() <= 0) {
        std::cerr << "Error: failed to write Events tree\n";
        outputFile->Close();
        return;
    }

    // 显式 Close() 让“写入完成”的时刻清晰可见，并立即刷新文件目录信息。
    // 即使忘记此行，unique_ptr 最终析构 TFile 时也会兜底关闭文件。
    outputFile->Close();

    // Close() 只关闭底层文件资源，并不会让 unique_ptr 本身立刻变成空指针。
    // 函数结束时 unique_ptr 仍会 delete TFile C++ 对象；关闭操作本身是可重复防护的。

    std::cout << "Created kinematics.root with "
              << numberOfEvents << " events.\n";
}
