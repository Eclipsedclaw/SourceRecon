// Step3_AddFit.C
//
// 本宏重复第二步的安全读取，然后用一维高斯函数拟合 pT 直方图。
// 先运行第一步，再运行：root Step3_AddFit.C

#include <TCanvas.h>
#include <TFile.h>
#include <TF1.h>
#include <TFitResultPtr.h>
#include <TH1D.h>
#include <TStyle.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <cmath>
#include <cstddef>
#include <iostream>
#include <memory>

// --------------------------- 本步比第二步新增什么 -------------------------
// 1. 用 TF1 表示“带三个可调参数的一维高斯函数”。
// 2. 用 TH1D::Fit 比较每个 bin 的观测值与函数预测值并优化参数。
// 3. 用 TFitResultPtr 检查数值优化是否成功。
// 4. 从 TF1 中提取最终参数及其不确定度。
// 5. 用 gStyle 控制拟合统计框的显示内容。
// --------------------------------------------------------------------------
// 拟合不是“画一条看起来顺眼的线”：优化器会利用 bin 内容和统计误差，
// 寻找使目标函数最小的参数；因此 Sumw2() 和收敛状态检查都很重要。
//
// --------------------------- 三个高斯参数的直观意义 -----------------------
// amplitude：峰顶附近的高度，主要反映总事件数和 bin 宽度。
// mean：分布中心，本例生成时设为约 3.0。
// sigma：分布宽度，本例生成时设为约 0.55，并且按定义应取正值。
// 参数误差：有限样本导致的拟合不确定度，不是原始分布本身的 sigma。
// chi-square：数据与模型偏差相对于 bin 误差的综合度量。
// probability：在模型成立时得到当前或更大偏差的概率指标之一。
// 这些量会同时显示在统计框中，其中三个参数还会明确打印到终端。
// --------------------------------------------------------------------------

void Step3_AddFit()
{
    // TH1D 保存一维 pT 频数分布；TCanvas 提供实际显示直方图和拟合曲线的 GUI 画布。
    // 与第二步相同，static unique_ptr 兼顾“函数返回后窗口仍存在”和“进程退出时自动释放”。
    static std::unique_ptr<TH1D> histogram;
    static std::unique_ptr<TCanvas> canvas;

    // 支持在同一 ROOT 会话中重复运行：先移除引用直方图的画布，再释放直方图。
    canvas.reset();
    histogram.reset();

    // reset 的销毁顺序有意与依赖方向相反：canvas 引用 histogram，
    // 所以先销毁引用者 canvas，再销毁被引用者 histogram。
    // 这是 C++ 管理对象依赖关系时常见的“逆序释放”原则。

    auto inputFile = std::unique_ptr<TFile>{TFile::Open("kinematics.root", "READ")};

    // TFile::Open 必须返回堆对象，是 ROOT 接口的历史设计；
    // unique_ptr 在接口边界立即接管所有权，把后续代码恢复为 RAII 风格。
    if (!inputFile || inputFile->IsZombie()) {
        std::cerr << "Error: cannot open kinematics.root; run Step1 first.\n";
        return;
    }

    // Get<TTree> 不需要 C 风格强转；失败时明确返回 nullptr。
    // 这个借用指针只在 inputFile 存活期间有效，所以下面的读取全部在本函数返回之前完成。
    TTree* const tree{inputFile->Get<TTree>("Events")};

    // Get 返回的 tree 由文件拥有，因此这里只借用，不再套一层 unique_ptr。
    // 若两个 unique_ptr 同时声称拥有同一对象，最终会发生两次 delete，属于未定义行为。
    if (tree == nullptr) {
        std::cerr << "Error: Events tree was not found.\n";
        return;
    }

    // TTreeReader 管理逐事件推进；两个 TTreeReaderValue<double> 类型安全地读取 px、py 列。
    TTreeReader reader{tree};
    TTreeReaderValue<double> pxReader{reader, "px"};
    TTreeReaderValue<double> pyReader{reader, "py"};

    // 三个读取对象都是局部栈对象，声明顺序也决定逆序析构顺序：
    // pyReader、pxReader 先离开，reader 后离开，最后 inputFile 才关闭。
    // 因而没有访问已经被释放的 tree 的机会。

    histogram = std::make_unique<TH1D>(
        "ptHistogramStep3",
        "Gaussian fit to transverse momentum;p_{T};Events",
        60,
        0.0,
        6.0);

    // 这里使用不同于第二步的 ROOT 对象名 ptHistogramStep3。
    // ROOT 会按名字登记许多对象；在同一会话使用唯一名字可避免同名警告和歧义。

    // 把直方图从输入文件目录中分离；否则输入文件析构时可能连带删除它。
    histogram->SetDirectory(nullptr);

    // nullptr 是现代 C++ 的专用空指针字面量，类型安全地表示“不属于任何目录”。
    // 不使用整数 0 或旧式 NULL，避免重载解析时产生整数/指针歧义。

    // 为每个 bin 显式保存统计误差，既用于 E 选项的误差棒，也会被拟合用于计算 chi-square。
    histogram->Sumw2();

    // 对无权计数，某 bin 内容为 N，标准差近似 sqrt(N)。
    // 拟合会用这个误差判断偏差的相对严重程度：高统计 bin 通常约束更强。

    std::size_t acceptedEvents{0};
    while (reader.Next()) {
        const double pt{std::hypot(*pxReader, *pyReader)};
        histogram->Fill(pt);
        ++acceptedEvents;
    }

    // pt 是每次循环新建的 const 栈变量，循环体末尾就被销毁。
    // 这没有问题，因为 Fill 立即复制其数值；TH1D 不保存 &pt。

    if (acceptedEvents == 0U) {
        std::cerr << "Error: Events tree contains no readable entries.\n";
        return;
    }

    // TF1 是 ROOT 的一维函数对象：它既能计算函数值，也能作为 Fit() 要优化的模型。
    // "gaus" 是 ROOT 内建的高斯模型，三个参数依次为幅度 [0]、均值 [1]、标准差 [2]。
    // 最后两个数把拟合范围限制为 0.5 到 5.5，避开直方图边界。
    TF1 gaussianFit{"gaussianFit", "gaus", 0.5, 5.5};

    // gaussianFit 是栈对象；本函数执行拟合和参数读取期间它始终存活。
    // Fit 会把用于绘图的函数副本关联到直方图，因此函数返回后画布仍能显示拟合曲线。
    // 对入门宏而言，栈对象避免了手动 new/delete，也清晰界定了计算对象的生命周期。

    // 合理初值能帮助数值最小化器更快、更稳定地收敛。
    // GetMaximum/Mean/StdDev 都从已经填好的直方图估算，不需要手工猜测本次样本。
    gaussianFit.SetParameters(
        histogram->GetMaximum(),
        histogram->GetMean(),
        histogram->GetStdDev());

    // 参数顺序必须与 "gaus" 的定义一致：
    // 参数 0 主要控制峰高，参数 1 控制峰中心，参数 2 控制峰宽。
    // 初值不是最终结果；Fit 会在这些值附近开始迭代并不断更新它们。

    // TStyle 控制 ROOT 图形的全局显示风格；gStyle 是 ROOT 提供的当前 TStyle 对象指针。
    // SetOptFit(1111) 要求统计框显示拟合参数、参数误差、chi-square 和拟合概率。
    gStyle->SetOptFit(1111);

    // gStyle 是 ROOT 管理的全局非拥有指针，不应对它调用 delete。
    // 这里修改的是当前进程的显示设置，不改变直方图的 bin 内容或拟合数值。
    // 统计框只是一种结果展示，终端中显式打印参数仍便于保存日志和后续脚本处理。

    canvas = std::make_unique<TCanvas>(
        "ptCanvasStep3",
        "Step 3: Gaussian fit",
        900,
        650);

    // Fit 前先创建画布并 Draw，可以明确指定拟合结果应该显示在哪个 pad 上。
    // 如果一个会话中存在多个画布，依赖“当前画布”的隐式状态容易把曲线画错位置。

    // 先用 E 选项画出数据误差棒；随后 Fit() 会把拟合曲线关联到同一幅直方图上。
    histogram->Draw("E");

    // TFitResultPtr 是 ROOT 的拟合结果智能句柄：既保存详细结果，也能转换成整数状态码。
    // Fit 的 S 选项要求 ROOT 返回并保存完整结果，便于显式检查拟合是否收敛。
    const TFitResultPtr fitResult{histogram->Fit(&gaussianFit, "S")};
    const int fitStatus{static_cast<int>(fitResult)};

    // &gaussianFit 是地址，因为 Fit 需要访问并修改同一个 TF1 对象中的参数。
    // 若按值传递，优化器只能修改副本，调用者随后就无法从原对象取得结果。
    // static_cast<int> 是显式、可搜索的 C++ 转换，避免旧式 (int) 强转。
    // 此转换调用 TFitResultPtr 为状态码专门提供的转换接口，并非重新解释内存位模式。

    // ROOT 约定状态码 0 表示成功；失败时不把不可靠参数伪装成有效物理结果。
    if (fitStatus != 0) {
        // 非零状态不一定意味着程序崩溃；它表示优化器没有按成功标准结束。
        // 常见原因包括样本为空、初值不合理、拟合区间不合适或模型不匹配。
        std::cerr << "Warning: fit did not converge; status = "
                  << fitStatus << '\n';
    } else {
        // GetParameter(i) 提取最佳拟合值，GetParError(i) 提取相应的一标准差不确定度。
        const double amplitude{gaussianFit.GetParameter(0)};
        const double mean{gaussianFit.GetParameter(1)};
        const double sigma{gaussianFit.GetParameter(2)};

        const double amplitudeError{gaussianFit.GetParError(0)};
        const double meanError{gaussianFit.GetParError(1)};
        const double sigmaError{gaussianFit.GetParError(2)};

        // 六个结果都按值复制到普通 double 中。
        // 它们不借用 TF1 内部地址，所以之后可安全传给其他计算或输出代码。
        // “value +/- error” 是参数估计值与一标准差不确定度的常见书写方式。

        std::cout << "Fit succeeded for " << acceptedEvents << " events:\n"
                  << "  amplitude = " << amplitude << " +/- " << amplitudeError << '\n'
                  << "  mean      = " << mean << " +/- " << meanError << '\n'
                  << "  sigma     = " << sigma << " +/- " << sigmaError << '\n';
    }

    // Fit() 改变了画布内容；显式刷新后，拟合曲线和统计框会立即出现在 X11 窗口中。
    canvas->Modified();
    canvas->Update();

    // 函数返回时，局部 gaussianFit 和 fitResult 会析构；输入文件也会自动关闭。
    // static histogram 保存了 bin 内容和 Fit 关联的绘图函数副本，static canvas 保存显示窗口。
    // 因此关闭 ROOT 进程之前，X11 窗口仍可重绘、缩放并查看统计框。
}
