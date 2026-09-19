#include "plot_efficiency_map.C"

void run_efficiency_map()
{
    // 这里只需要修改下面几个参数，不需要编译，也不会修改 V10 的任何文件。
    const char* inputRootFile =
        "../v10_pixel_integrated_response/runs/latest/efficiency/absolute_efficiency_master.root";
    const char* treeName = "AbsoluteEfficiency";
    const double targetEnergyMeV = 0.662;
    const char* outputDirectory = "figures";

    // 当前模拟只覆盖相机前半球，因此默认把后半球标成“未模拟”。
    // 如果以后输入的是全天球效率图，把这里改为 false 即可。
    const bool frontHemisphereOnly = true;

    plot_efficiency_map(
        inputRootFile,
        treeName,
        targetEnergyMeV,
        outputDirectory,
        frontHemisphereOnly
    );
}
