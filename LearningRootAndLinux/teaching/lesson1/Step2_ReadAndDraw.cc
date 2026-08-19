// Step2_ReadAndDraw.C
//
// 本宏安全读取第一步的数据，逐事件计算 pT，并绘制带误差棒的直方图。
// 先运行第一步，再运行：root Step2_ReadAndDraw.C

#include <TCanvas.h>
#include <TFile.h>
#include <TH1D.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <cmath>
#include <cstddef>
#include <iostream>
#include <memory>

// --------------------------- 本步的数据流 ---------------------------------
// 磁盘中的 px/py Branch
//          ↓ TTreeReaderValue<double> 按当前事件提供只读值
// std::hypot(px, py) 计算一个 pT
//          ↓ TH1D::Fill 把该数值累计到对应 bin
// TH1D::Draw("E") 把 bin 内容和误差棒交给 TCanvas 显示
// --------------------------------------------------------------------------
// 读取过程中不会把整棵树一次性装入一个巨大数组；reader 逐事件推进，
// ROOT 在底层按需解压 Basket，因此这种写法也适用于远大于内存的数据集。

void Step2_ReadAndDraw()
{
    // TH1D 是“一维、每个 bin 内容用 double 保存”的直方图，负责统计 pT 的频数分布。
    // TCanvas 是 ROOT 的绘图窗口/画布，所有可视对象最终都画在它或它的子区域上。
    // static unique_ptr 让对象在函数返回后继续存在，所以 X11 窗口不会立刻随局部变量析构而消失；
    // 同时进程退出时仍由 C++ 自动清理，避免使用无人管理的裸 new。
    static std::unique_ptr<TH1D> histogram;
    static std::unique_ptr<TCanvas> canvas;

    // 如果在同一个 ROOT 会话中再次运行本宏，先销毁旧画布，再销毁被它引用的旧直方图。
    // 这个顺序避免画布在短暂时间里还保存着一个已经析构的直方图地址。
    canvas.reset();
    histogram.reset();

    // reset() 会对旧对象执行 delete，然后把 unique_ptr 置为 nullptr。
    // 第一次运行时两个指针本来就是 nullptr，所以这两个调用也是安全的空操作。

    // 用 unique_ptr 接管 TFile::Open 返回的指针，使所有提前 return 路径都能自动关闭文件。

    // ----------------------------------------------------------------------------------------------------
    // TFile::Open 的第二个参数指定文件的打开模式（Option），常用选项如下：
    //
    // 1. "READ" （默认模式，最安全）：
    //    以纯只读（Read-Only）方式打开已存在的文件。
    //    绝不会修改文件内容，如果文件不存在，TFile::Open 会返回 nullptr，提示打开失败。
    //    适用场景：分析数据、画图、拟合等不需要写入数据的阶段。
    //
    // 2. "RECREATE" （覆盖新建，最常用）：
    //    如果文件不存在，则创建新文件；如果文件已存在，则【直接清空覆盖】旧文件！
    //    适用场景：生成假数据、保存模拟结果等需要“重新造一份文件”的阶段（如 Step1）。
    //
    // 3. "UPDATE" （追加/修改）：
    //    打开一个已存在的文件以供写入，原文件的已有内容（TTree、直方图等）全都会被保留。
    //    你可以在原文件里追加新的 TTree、往已有的 TTree 填入新数据，或者覆盖更新里面的某个直方图。
    //    如果文件不存在，它会自动创建一个新的。
    //    适用场景：向已有数据文件里追加计算好的新特征（如加一列 Branch），或者合并多个分析结果。
    //
    // 4. "NEW" / "CREATE" （强制新建，防误删）：
    //    强制要求必须创建一个【全新的】文件。
    //    如果文件不存在，创建成功；如果文件【已经存在】，直接抛错拒绝打开！
    //    适用场景：防御性编程，防止手滑把之前跑了几个小时算好的重要数据给覆盖掉。
    //
    // 5. "NET" 或网络协议（如 "http://", "root://"）：
    //    ROOT 极具特色的一点，支持通过网络协议直接远程只读打开 CERN 或远端服务器上的 .root 文件，无需全量下载。
    // ----------------------------------------------------------------------------------------------------
    auto inputFile = std::unique_ptr<TFile>{TFile::Open("kinematics.root", "READ")};

    // READ 模式只允许读取已有内容，不会像 RECREATE 那样覆盖第一步生成的文件。
    // 这里没有显式 Close()：本函数结束时 inputFile 的析构会可靠地完成关闭。
    if (!inputFile || inputFile->IsZombie()) {
        std::cerr << "Error: cannot open kinematics.root; run Step1 first.\n";
        return;
    }

    // Get<TTree> 同时完成按名字查找和类型检查，比 C 风格强制转换更安全、更清楚。
    // tree 是“借用指针”：对象所有权仍属于 inputFile，所以 inputFile 必须比 reader 活得更久。
    TTree* const tree{inputFile->Get<TTree>("Events")};
    // const 修饰的是指针本身（TTree* const），表示随后不能让 tree 改指向另一棵树。
    // 它并不表示 TTree 内容是 const；reader 仍可调用读取所需的非 const ROOT 接口。

    if (tree == nullptr) {
        std::cerr << "Error: Events tree was not found.\n";
        return;
    }

    // TTreeReader 是按事件顺序安全推进 TTree 的读取器，替代手动 SetBranchAddress/GetEntry。
    TTreeReader reader{tree};

    // reader 是栈对象，不拥有 tree；析构 reader 不会 delete tree。
    // 当前声明顺序保证 reader 会先析构，inputFile 随后才析构并释放 tree。

    // TTreeReaderValue<double> 是一列 double 数据的类型安全访问器。
    // 它内部保存读取状态；解引用 *pxReader 得到“当前事件”的 px，而不是一个拥有所有事件的数组。
    TTreeReaderValue<double> pxReader{reader, "px"};
    TTreeReaderValue<double> pyReader{reader, "py"};

    // 模板参数 double 必须与第一步 Branch 的真实类型一致。
    // 如果误写成 int，ROOT 会报告类型不匹配，而不会默默做危险的按位解释。

    // 60 个等宽 bin 覆盖 0 到 6；标题中的两个分号依次分隔主标题、x 轴标题和 y 轴标题。
    histogram = std::make_unique<TH1D>(
        "ptHistogramStep2",
        "Transverse momentum;p_{T};Events",
        60,
        0.0,
        6.0);

    // 直方图拥有 60 个普通 bin，宽度为 (6-0)/60 = 0.1。
    // ROOT 还会自动维护一个 underflow bin 和一个 overflow bin，
    // 它们分别接收小于 0 和大于等于 6 的数值，但默认绘图范围不显示它们。

    // 默认情况下，TH1 会挂到当前 gDirectory；当前目录是刚打开的输入文件。
    // SetDirectory(nullptr) 将其分离，使 inputFile 关闭后直方图仍由 unique_ptr 独立拥有。
    histogram->SetDirectory(nullptr);

    // Sumw2() 为每个 bin 分配平方权重和，用来保存统计误差。
    // 当前每个事件权重都是 1，因此误差等价于熟悉的 sqrt(N)，但显式调用更能表达意图。
    histogram->Sumw2();

    // unique_ptr 使用 ->，因为它的行为像“拥有对象的指针”。
    // pxReader 使用 *，则是因为我们要取得它所代理的当前 double 值。

    std::size_t acceptedEvents{0};

    // size_t 是标准库用于计数和大小的无符号整数类型。
    // 用它记录事件数，避免在很大数据集上受普通 int 范围限制。

    // Next() 成功时，reader 会把所有 ReaderValue 同步到同一个新事件；到树尾时返回 false。
    while (reader.Next()) {
        // std::hypot 在数值上比手写 sqrt(px*px + py*py) 更稳健，并直接表达二维模长。
        const double pt{std::hypot(*pxReader, *pyReader)};

        // Fill(value) 找到 value 所属的 bin，并把该 bin 内容增加 1。
        histogram->Fill(pt);
        ++acceptedEvents;
    }

    // 循环结束后 reader 已到树尾，但 histogram 已拥有所有累计的 bin 内容。
    // 它保存的是统计结果，不保存指向 pxReader 或 pyReader 当前值的地址。

    //0U是无符号的0，避免和acceptedEvents的类型不匹配
    if (acceptedEvents == 0U) {
        std::cerr << "Error: Events tree contains no readable entries.\n";
        return;
    }

    // ----------------------------------------------------------------------------------------------------
    // std::make_unique<TCanvas> 创建一个 ROOT 绘图画布对象，各参数含义如下：
    //
    // 参数 1 ("ptCanvasStep2")：
    //    画布的内部系统名称（Name）。在 ROOT 内部用来唯一标识这个画布对象，不能重复。
    //
    // 参数 2 ("Step 2: transverse momentum")：
    //    画布的窗口标题（Title）。会直接显示在弹出的图形窗口最顶部的标题栏上。
    //
    // 参数 3 (900)：
    //    窗口的宽度（Width），单位为像素（Pixel）。
    //
    // 参数 4 (650)：
    //    窗口的高度（Height），单位为像素（Pixel）。
    //
    // 内存管理说明：
    //    这里使用 std::make_unique<TCanvas>(...) 在堆上开辟画布，并用 unique_ptr 托管，
    //    避免了老式 ROOT 代码中手动写 delete canvas 的麻烦，同时也防止了局部变量出作用域被提前销毁。
    // ----------------------------------------------------------------------------------------------------
    canvas = std::make_unique<TCanvas>(
        "ptCanvasStep2",
        "Step 2: transverse momentum",
        900,
        650);

    // 画布和直方图都位于堆上；各自的 unique_ptr 是唯一所有者。
    // static 只延长 unique_ptr 的寿命，不改变 unique_ptr 的唯一所有权语义。

    // Draw("E") 中的 E 要求 ROOT 按每个 bin 的统计不确定度绘制误差棒。
    histogram->Draw("E");

    // Draw 不会复制整份直方图数据；画布保存一个指向 histogram 的引用来完成重绘。
    // 这正是 histogram 也必须与 canvas 一样在函数返回后继续存活的原因。

    // Modified/Update 让 ROOT 立即重新布局并把绘图命令发送到 X11 窗口，
    // 而不是等到下一次 GUI 事件发生时才刷新。
    canvas->Modified();
    canvas->Update();

    // inputFile 很快会随函数返回而关闭，但 histogram 已经 SetDirectory(nullptr)。
    // 所以 GUI 后续重绘只依赖内存中的 histogram，不再依赖磁盘文件或 tree。

    // ----------------------------------------------------------------------------------------------------
    // 图形渲染与对象生命周期机制：
    //
    // 1. 引用式绘制（Non-copying Draw）：
    //    canvas 绘制直方图时不会复制数据，仅持有 histogram 的指针。
    //    因此 histogram 的生命周期必须覆盖 canvas 的整个生命周期（即只要窗口还在，histogram 就必须活在内存里）。
    //
    // 2. 强制实时刷新机制：
    //    canvas->Modified();  标记画布内容已更新，通知图形系统重绘。
    //    canvas->Update();    立即将绘图命令推送到 Linux X11 窗口，无需等待 GUI 事件循环，实现即时渲染。
    //
    // 3. 数据独立性与析构时机：
    //    先前调用过 histogram->SetDirectory(nullptr)，即使输入文件/TTree 已关闭，GUI 重绘依然安全。
    //    由于使用 static unique_ptr 托管，关闭本地 X11 窗口仅关闭显示界面，内存中的对象不会立刻析构；
    //    它们会在下一次运行本函数重置（reset）时、或整个 ROOT 会话退出（.q）时统一进行析构释放。
    // ----------------------------------------------------------------------------------------------------

    std::cout << "Read and plotted " << acceptedEvents << " events.\n";
    canvas->SaveAs("output.png");
}
