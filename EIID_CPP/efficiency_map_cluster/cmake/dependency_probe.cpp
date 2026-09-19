#include <TROOT.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>
#include <cstdio>

#ifdef EFF_PROBE_SIMULATION
#include <G4RunManager.hh>
#include <healpix_base.h>
#endif

namespace
{
    // 配置程序会捕获输出，因此不能依赖 cout 的缓冲区在正常退出时刷新。
    // 每条消息立即写出；即使下一步卡住或被超时终止，也能知道最后执行到哪里。
    void stage(const char* message)
    {
        std::fprintf(stderr, "[dependency-probe] %s\n", message);
        std::fflush(stderr);
    }
}

// 配置检查：真正调用 TreePlayer；只使用内存中的树，不创建 .root 文件。
// 不建探测器、不调用 BeamOn，不会产生任何模拟事例。
int main()
{
    stage("01 main entered; starting ROOT initialization");
    gROOT->SetBatch(true);
    stage("02 ROOT initialized; constructing in-memory TTree");
    {
        int value = 7;
        TTree tree("DependencyProbe", "In-memory dependency check");
        tree.SetDirectory(nullptr);
        stage("03 TTree constructed; creating branch");
        if (!tree.Branch("value", &value))
        {
            stage("ERROR: Branch returned nullptr");
            return 1;
        }
        stage("04 branch created; filling tree");
        if (tree.Fill() < 0)
        {
            stage("ERROR: Fill failed");
            return 1;
        }
        stage("05 tree filled; constructing TTreeReader");
        TTreeReader reader(&tree);
        stage("06 reader constructed; constructing TTreeReaderValue");
        TTreeReaderValue<int> readValue(reader, "value");
        stage("07 reader value constructed; reading next entry");
        if (!reader.Next())
        {
            stage("ERROR: Next failed");
            return 2;
        }
        stage("08 entry available; accessing branch value");
        if (*readValue != value)
        {
            stage("ERROR: value mismatch");
            return 2;
        }
        stage("09 TreePlayer read passed; destroying ROOT test objects");
    }
    stage("10 ROOT test objects destroyed");
#ifdef EFF_PROBE_SIMULATION
    stage("11 constructing HEALPix grid");
    {
        Healpix_Base pixels(1, RING, SET_NSIDE);
        const auto direction = pixels.pix2vec(0);
        if (pixels.Npix() != 12 || direction.z <= 0)
        {
            stage("ERROR: HEALPix check failed");
            return 3;
        }
        stage("12 HEALPix passed; querying Geant4 run manager");
        // 这里只检查 Geant4 动态库可调用，不开始一次模拟。
        // GetRunManager() 是 G4run 库中实现的函数；管理器未创建时返回 nullptr。
        // 不能孤立创建 G4Run：11.2.2 的析构函数会访问当前管理器，导致空指针崩溃。
        // 也不通过泄漏 G4Run 或提前退出来掩盖错误；仍检查程序正常析构、退出。
        if (G4RunManager::GetRunManager() != nullptr)
        {
            stage("ERROR: unexpected Geant4 run manager in dependency probe");
            return 3;
        }
        stage("13 Geant4 library call passed; no run manager created");
        stage("14 destroying HEALPix grid");
    }
    stage("15 HEALPix grid destroyed");
#endif
    // 这不是最终的成功标记：退出时的全局析构仍须完成，父进程须收到退出码 0。
    stage("16 leaving main; waiting for normal process exit");
    return 0;
}
