#include "containment_plotter.h"
#include "direction_fit_plotter.h"
#include "energy_angle_plotter.h"
#include "energy_fit_plotter.h"
#include "fit_analysis.h"
#include "fit_summary_writer.h"
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
            : std::filesystem::path{"config/plot_config.json"};

        const VisConfig config{configPath};

        std::filesystem::create_directories(config.outputDirectory());

        // 绘图程序不需要打开 X11 窗口，直接在批处理模式下生成 PNG。
        gROOT->SetBatch(kTRUE);
        gStyle->SetOptStat(0);
        gStyle->SetTitleFontSize(0.035);

        // result.root 只读取一次，之后所有 Plotter 共享同一份只读数据。
        const ReconstructionData data = ReconstructionDataReader::read(config);

        // 三张拟合图和 JSON 摘要依赖同一组拟合参数。
        // 这里统一计算一次，然后以 shared_ptr 只读共享，避免重复执行 ROOT 拟合。
        const bool needsFitAnalysis =
            config.drawEnergyFit() ||
            config.drawDirectionFit() ||
            config.drawEnergyAngleMap() ||
            config.writeFitSummary();
        std::shared_ptr<const FitAnalysisResult> fitAnalysis;

        if (needsFitAnalysis)
        {
            fitAnalysis = std::make_shared<const FitAnalysisResult>(
                FitAnalyzer::analyze(data, config)
            );
        }

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

        if (config.drawEnergyFit())
        {
            plotters.push_back(
                std::make_unique<EnergyFitPlotter>(fitAnalysis)
            );
        }

        if (config.drawDirectionFit())
        {
            plotters.push_back(
                std::make_unique<DirectionFitPlotter>(fitAnalysis)
            );
        }

        if (config.drawEnergyAngleMap())
        {
            plotters.push_back(
                std::make_unique<EnergyAnglePlotter>(fitAnalysis)
            );
        }

        if (plotters.empty() && !config.writeFitSummary())
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

        if (config.writeFitSummary())
        {
            FitSummaryWriter::write(*fitAnalysis, config);
            std::cout << "Generated fit summary in "
                      << config.outputDirectory().string() << '\n';
        }
    }
    catch (const std::exception& error)
    {
        std::cerr << "Visualization error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
