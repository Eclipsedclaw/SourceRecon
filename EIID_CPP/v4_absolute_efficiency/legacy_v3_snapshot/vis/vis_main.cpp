#include "containment_plotter.h"
#include "iplotter.h"
#include "reconstruction_data.h"
#include "skymap_plotter.h"
#include "spectrum_plotter.h"
#include "vis_config.h"

#include <TROOT.h>
#include <TStyle.h>

#include <exception>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: eiid_plotter [path/to/plot_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"vis/plot_config.json"};

        const VisConfig config{configPath};

        std::filesystem::create_directories(config.outputDirectory());

        // 绘图程序不需要打开 X11 窗口，直接在批处理模式下生成 PNG。
        gROOT->SetBatch(kTRUE);
        gStyle->SetOptStat(0);
        gStyle->SetTitleFontSize(0.035);

        // result.root 只读取一次，之后所有 Plotter 共享同一份只读数据。
        const ReconstructionData data = ReconstructionDataReader::read(config);

        std::vector<std::unique_ptr<IPlotter>> plotters;

        if (config.drawSkymap())
        {
            plotters.push_back(std::make_unique<SkymapPlotter>());
        }

        if (config.drawSpectrum())
        {
            plotters.push_back(std::make_unique<SpectrumPlotter>());
        }

        if (config.drawContainment())
        {
            plotters.push_back(std::make_unique<ContainmentPlotter>());
        }

        if (plotters.empty())
        {
            std::cout << "All visualization switches are disabled.\n";
            return 0;
        }

        for (const std::unique_ptr<IPlotter>& plotter : plotters)
        {
            plotter->plot(data, config);
            std::cout << "Generated " << plotter->name()
                      << " in " << config.outputDirectory().string() << '\n';
        }
    }
    catch (const std::exception& error)
    {
        std::cerr << "Visualization error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
