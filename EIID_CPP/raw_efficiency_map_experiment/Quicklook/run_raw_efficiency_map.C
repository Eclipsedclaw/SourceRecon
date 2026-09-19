#include "plot_raw_efficiency_map.C"

// 无参调用继续绘制完整效率图；小测试可以单独传入 ROOT 路径和图片目录。
void run_raw_efficiency_map(
    const char* inputRootFile = "../runs/raw_efficiency/raw_efficiency_master.root",
    const char* outputDirectory = "figures"
)
{
    // 这个文件读取本实验重新模拟得到的 raw efficiency。
    const char* treeName = "RawEfficiency";
    const double targetEnergyMeV = 0.662;

    // 当前模拟只覆盖相机前半球，因此默认把后半球标成“未模拟”。
    // 如果以后输入的是全天球效率图，把这里改为 false 即可。
    const bool frontHemisphereOnly = true;

    plot_raw_efficiency_map(
        inputRootFile,
        treeName,
        targetEnergyMeV,
        outputDirectory,
        frontHemisphereOnly
    );
}
