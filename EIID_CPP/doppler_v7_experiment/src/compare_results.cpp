#include "TCanvas.h"
#include "TFile.h"
#include "TGraph.h"
#include "TH1D.h"
#include "TLegend.h"
#include "TROOT.h"
#include "TStyle.h"
#include "TTree.h"
#include "TTreeReader.h"
#include "TTreeReaderValue.h"
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
enum class Level
{
    truth,
    detector
};

struct InputDefinition
{
    std::string label;
    std::filesystem::path rootFile;
    int color{};
};

struct ComparisonConfig
{
    std::string treeName;
    double sourceEnergyMeV{};
    int histogramBins{};
    double armMinimum{};
    double armMaximum{};
    double energyMinimum{};
    double energyMaximum{};
    double armTailThreshold{};
    double relativeEnergyTailThreshold{};
    std::filesystem::path figuresDirectory;
    std::filesystem::path summaryJson;
    std::vector<InputDefinition> inputs;
};

struct ModelData
{
    InputDefinition definition;
    std::vector<double> truthArm;
    std::vector<double> detectorArm;
    std::vector<double> truthEnergyResidual;
    std::vector<double> detectorEnergyResidual;
    std::vector<double> truthRelativeEnergyResidual;
    std::vector<double> detectorRelativeEnergyResidual;
};

struct DistributionView
{
    const std::vector<double>& arm;
    const std::vector<double>& energyResidual;
    const std::vector<double>& relativeEnergyResidual;
};

struct Metrics
{
    std::size_t eventCount{};
    double armFwhmDegree{};
    double armR68Degree{};
    double armR90Degree{};
    double armTailFraction{};
    double energyFwhmMeV{};
    double energyFwhmPercent{};
    double energyR68MeV{};
    double energyR90MeV{};
    double energyTailFraction{};
};

std::filesystem::path resolve(
    const std::filesystem::path& configPath,
    const std::string& value
)
{
    const std::filesystem::path path{value};
    return (path.is_absolute() ? path : configPath.parent_path() / path)
        .lexically_normal();
}

ComparisonConfig readConfig(const std::filesystem::path& requestedPath)
{
    const std::filesystem::path path =
        std::filesystem::absolute(requestedPath).lexically_normal();
    std::ifstream input{path};

    if (!input)
    {
        throw std::runtime_error{"Cannot open comparison config: " + path.string()};
    }

    nlohmann::json document;
    input >> document;
    ComparisonConfig config;
    config.treeName = document.at("tree_name").get<std::string>();
    config.sourceEnergyMeV = document.at("source_energy_MeV").get<double>();
    config.histogramBins = document.at("histogram_bins").get<int>();
    config.armMinimum = document.at("arm_range_degree").at(0).get<double>();
    config.armMaximum = document.at("arm_range_degree").at(1).get<double>();
    config.energyMinimum = document.at("energy_residual_range_MeV").at(0).get<double>();
    config.energyMaximum = document.at("energy_residual_range_MeV").at(1).get<double>();
    config.armTailThreshold = document.at("arm_tail_threshold_degree").get<double>();
    config.relativeEnergyTailThreshold =
        document.at("relative_energy_tail_threshold").get<double>();
    config.figuresDirectory = resolve(
        path,
        document.at("figures_directory").get<std::string>()
    );
    config.summaryJson = resolve(
        path,
        document.at("summary_json").get<std::string>()
    );

    for (const auto& item : document.at("inputs"))
    {
        config.inputs.push_back(
            InputDefinition{
                item.at("label").get<std::string>(),
                resolve(path, item.at("root_file").get<std::string>()),
                item.at("root_color").get<int>()
            }
        );
    }

    if (config.treeName.empty() || config.sourceEnergyMeV <= 0.0 ||
        config.histogramBins <= 0 || config.armMaximum <= config.armMinimum ||
        config.energyMaximum <= config.energyMinimum || config.inputs.empty())
    {
        throw std::runtime_error{"Comparison configuration contains invalid values."};
    }

    return config;
}

void appendIfFinite(std::vector<double>& values, double value)
{
    if (std::isfinite(value))
    {
        values.push_back(value);
    }
}

ModelData readModel(const InputDefinition& definition, const std::string& treeName)
{
    std::unique_ptr<TFile> file{TFile::Open(definition.rootFile.string().c_str(), "READ")};

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{"Cannot open ROOT file: " + definition.rootFile.string()};
    }

    TTree* tree = file->Get<TTree>(treeName.c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{
            "Cannot find tree " + treeName + " in " + definition.rootFile.string()
        };
    }

    if (tree->GetEntries() == 0)
    {
        throw std::runtime_error{
            "Tree " + treeName + " contains zero selected events in " +
            definition.rootFile.string()
        };
    }

    TTreeReader reader{tree};
    TTreeReaderValue<std::int32_t> detectorValid{
        reader,
        "detector_kinematics_valid"
    };
    TTreeReaderValue<double> truthArm{reader, "truth_arm_degree"};
    TTreeReaderValue<double> detectorArm{reader, "detector_arm_degree"};
    TTreeReaderValue<double> truthEnergy{reader, "truth_energy_residual_MeV"};
    TTreeReaderValue<double> detectorEnergy{
        reader,
        "detector_energy_residual_MeV"
    };
    TTreeReaderValue<double> truthRelative{
        reader,
        "truth_relative_energy_residual"
    };
    TTreeReaderValue<double> detectorRelative{
        reader,
        "detector_relative_energy_residual"
    };
    ModelData result;
    result.definition = definition;
    const std::size_t entryCount = static_cast<std::size_t>(tree->GetEntries());
    result.truthArm.reserve(entryCount);
    result.truthEnergyResidual.reserve(entryCount);
    result.truthRelativeEnergyResidual.reserve(entryCount);
    result.detectorArm.reserve(entryCount);
    result.detectorEnergyResidual.reserve(entryCount);
    result.detectorRelativeEnergyResidual.reserve(entryCount);

    while (reader.Next())
    {
        appendIfFinite(result.truthArm, *truthArm);
        appendIfFinite(result.truthEnergyResidual, *truthEnergy);
        appendIfFinite(result.truthRelativeEnergyResidual, *truthRelative);

        if (*detectorValid != 0)
        {
            appendIfFinite(result.detectorArm, *detectorArm);
            appendIfFinite(result.detectorEnergyResidual, *detectorEnergy);
            appendIfFinite(result.detectorRelativeEnergyResidual, *detectorRelative);
        }
    }

    if (result.truthArm.empty() || result.detectorArm.empty())
    {
        throw std::runtime_error{
            "Selected tree has no finite truth-level or detector-level values for " +
            definition.label
        };
    }

    return result;
}

DistributionView view(const ModelData& model, Level level)
{
    if (level == Level::truth)
    {
        return {
            model.truthArm,
            model.truthEnergyResidual,
            model.truthRelativeEnergyResidual
        };
    }

    return {
        model.detectorArm,
        model.detectorEnergyResidual,
        model.detectorRelativeEnergyResidual
    };
}

double absoluteQuantile(const std::vector<double>& values, double probability)
{
    std::vector<double> absoluteValues;
    absoluteValues.reserve(values.size());

    for (const double value : values)
    {
        absoluteValues.push_back(std::abs(value));
    }

    std::sort(absoluteValues.begin(), absoluteValues.end());
    const double floatingIndex = probability * (absoluteValues.size() - 1);
    const std::size_t lower = static_cast<std::size_t>(std::floor(floatingIndex));
    const std::size_t upper = static_cast<std::size_t>(std::ceil(floatingIndex));
    const double fraction = floatingIndex - static_cast<double>(lower);
    return absoluteValues[lower] * (1.0 - fraction) + absoluteValues[upper] * fraction;
}

double fractionOutside(const std::vector<double>& values, double threshold)
{
    const std::size_t count = static_cast<std::size_t>(std::count_if(
        values.begin(),
        values.end(),
        [threshold](double value)
        {
            return std::abs(value) > threshold;
        }
    ));
    return static_cast<double>(count) / static_cast<double>(values.size());
}

double interpolateCrossing(
    double x1,
    double y1,
    double x2,
    double y2,
    double target
)
{
    return y2 == y1
        ? 0.5 * (x1 + x2)
        : x1 + (target - y1) * (x2 - x1) / (y2 - y1);
}

double histogramFwhm(const TH1D& histogram)
{
    const int maximumBin = histogram.GetMaximumBin();
    const double halfMaximum = 0.5 * histogram.GetBinContent(maximumBin);
    int leftBelow = maximumBin;

    while (leftBelow > 1 && histogram.GetBinContent(leftBelow) >= halfMaximum)
    {
        --leftBelow;
    }

    int rightBelow = maximumBin;

    while (rightBelow < histogram.GetNbinsX() &&
           histogram.GetBinContent(rightBelow) >= halfMaximum)
    {
        ++rightBelow;
    }

    if (halfMaximum <= 0.0 || leftBelow == 1 ||
        rightBelow == histogram.GetNbinsX())
    {
        return std::numeric_limits<double>::quiet_NaN();
    }

    const double left = interpolateCrossing(
        histogram.GetBinCenter(leftBelow),
        histogram.GetBinContent(leftBelow),
        histogram.GetBinCenter(leftBelow + 1),
        histogram.GetBinContent(leftBelow + 1),
        halfMaximum
    );
    const double right = interpolateCrossing(
        histogram.GetBinCenter(rightBelow - 1),
        histogram.GetBinContent(rightBelow - 1),
        histogram.GetBinCenter(rightBelow),
        histogram.GetBinContent(rightBelow),
        halfMaximum
    );
    return right - left;
}

std::unique_ptr<TH1D> makeHistogram(
    const std::vector<double>& values,
    const std::string& name,
    int bins,
    double minimum,
    double maximum,
    int color
)
{
    auto histogram = std::make_unique<TH1D>(name.c_str(), "", bins, minimum, maximum);
    histogram->SetDirectory(nullptr);
    histogram->SetLineColor(color);
    histogram->SetLineWidth(3);
    histogram->SetStats(false);

    for (const double value : values)
    {
        histogram->Fill(value);
    }

    return histogram;
}

Metrics calculateMetrics(
    const DistributionView& values,
    const ComparisonConfig& config,
    const std::string& name
)
{
    auto armHistogram = makeHistogram(
        values.arm,
        name + "_arm",
        config.histogramBins,
        config.armMinimum,
        config.armMaximum,
        1
    );
    auto energyHistogram = makeHistogram(
        values.energyResidual,
        name + "_energy",
        config.histogramBins,
        config.energyMinimum,
        config.energyMaximum,
        1
    );
    const double energyFwhm = histogramFwhm(*energyHistogram);

    return {
        values.arm.size(),
        histogramFwhm(*armHistogram),
        absoluteQuantile(values.arm, 0.68),
        absoluteQuantile(values.arm, 0.90),
        fractionOutside(values.arm, config.armTailThreshold),
        energyFwhm,
        100.0 * energyFwhm / config.sourceEnergyMeV,
        absoluteQuantile(values.energyResidual, 0.68),
        absoluteQuantile(values.energyResidual, 0.90),
        fractionOutside(
            values.relativeEnergyResidual,
            config.relativeEnergyTailThreshold
        )
    };
}

std::string levelName(Level level)
{
    return level == Level::truth ? "truth" : "detector";
}

void drawHistogramOverlay(
    const std::vector<ModelData>& data,
    const ComparisonConfig& config,
    Level level,
    bool drawArm
)
{
    const std::string prefix = levelName(level);
    const std::string filename = prefix + (drawArm
        ? "_arm_overlay.png"
        : "_energy_residual_overlay.png");
    const std::string title = drawArm
        ? prefix + "-level ARM comparison;ARM (degree);normalized counts"
        : prefix + "-level EIID energy comparison;E_{EIID}-E_{true} (MeV);normalized counts";
    const double minimum = drawArm ? config.armMinimum : config.energyMinimum;
    const double maximum = drawArm ? config.armMaximum : config.energyMaximum;
    TCanvas canvas{"histogram_canvas", "histogram_canvas", 1200, 800};
    TLegend legend{0.62, 0.69, 0.89, 0.89};
    legend.SetBorderSize(0);
    std::vector<std::unique_ptr<TH1D>> histograms;

    for (std::size_t index = 0; index < data.size(); ++index)
    {
        const DistributionView values = view(data[index], level);
        const auto& selectedValues = drawArm ? values.arm : values.energyResidual;
        auto histogram = makeHistogram(
            selectedValues,
            "display_" + prefix + '_' + std::to_string(index) +
                (drawArm ? "_arm" : "_energy"),
            config.histogramBins,
            minimum,
            maximum,
            data[index].definition.color
        );
        histogram->SetTitle(title.c_str());

        if (histogram->Integral() > 0.0)
        {
            histogram->Scale(1.0 / histogram->Integral());
        }

        legend.AddEntry(histogram.get(), data[index].definition.label.c_str(), "l");
        histograms.push_back(std::move(histogram));
    }

    double displayMaximum = 0.0;

    for (const auto& histogram : histograms)
    {
        displayMaximum = std::max(displayMaximum, histogram->GetMaximum());
    }

    if (!(displayMaximum > 0.0))
    {
        throw std::runtime_error{"Refusing to draw an empty histogram: " + filename};
    }

    for (std::size_t index = 0; index < histograms.size(); ++index)
    {
        histograms[index]->SetMaximum(1.15 * displayMaximum);
        histograms[index]->Draw(index == 0 ? "HIST" : "HIST SAME");
    }

    legend.Draw();
    canvas.SetGrid();
    canvas.SaveAs((config.figuresDirectory / filename).string().c_str());
}

std::unique_ptr<TGraph> makeAbsoluteCdf(
    const std::vector<double>& values,
    int color
)
{
    std::vector<double> sorted;
    sorted.reserve(values.size());

    for (const double value : values)
    {
        sorted.push_back(std::abs(value));
    }

    std::sort(sorted.begin(), sorted.end());
    auto graph = std::make_unique<TGraph>(static_cast<int>(sorted.size() + 1));
    graph->SetPoint(0, 0.0, 0.0);

    for (std::size_t index = 0; index < sorted.size(); ++index)
    {
        graph->SetPoint(
            static_cast<int>(index + 1),
            sorted[index],
            static_cast<double>(index + 1) / static_cast<double>(sorted.size())
        );
    }

    graph->SetLineColor(color);
    graph->SetLineWidth(3);
    return graph;
}

void drawCdfOverlay(
    const std::vector<ModelData>& data,
    const ComparisonConfig& config,
    Level level,
    bool drawArm
)
{
    const std::string prefix = levelName(level);
    const std::string filename = prefix + (drawArm
        ? "_absolute_arm_cdf.png"
        : "_absolute_energy_residual_cdf.png");
    const std::string title = drawArm
        ? prefix + "-level absolute ARM;|ARM| (degree);cumulative fraction"
        : prefix + "-level absolute energy residual;|E_{EIID}-E_{true}| (MeV);cumulative fraction";
    TCanvas canvas{"cdf_canvas", "cdf_canvas", 1200, 800};
    TLegend legend{0.62, 0.18, 0.89, 0.38};
    legend.SetBorderSize(0);
    std::vector<std::unique_ptr<TGraph>> graphs;
    double commonXMaximum = 0.0;

    for (const ModelData& model : data)
    {
        const DistributionView values = view(model, level);
        const auto& selectedValues = drawArm ? values.arm : values.energyResidual;

        // TGraph 在第一次以 "AL" 绘制时，会根据第一条曲线自动确定坐标轴。
        // Free-electron 的 truth-level 残差接近机器精度；如果它恰好是第一条
        // 曲线，ROOT 就会把横轴缩小到约 1e-13，随后 Livermore 的有限宽度
        // 曲线全部落到画框之外。因此必须在绘图前扫描所有模型，并为它们
        // 计算同一个横轴上限，不能让绘制顺序决定最终的显示范围。
        for (const double value : selectedValues)
        {
            if (std::isfinite(value))
            {
                commonXMaximum = std::max(commonXMaximum, std::abs(value));
            }
        }

        auto graph = makeAbsoluteCdf(selectedValues, model.definition.color);
        legend.AddEntry(graph.get(), model.definition.label.c_str(), "l");
        graphs.push_back(std::move(graph));
    }

    // 给最大数据点右侧留出 5% 的空白。如果所有值都严格为零，则使用一个
    // 很小但正常的正范围，避免 ROOT 创建退化坐标轴。
    const double displayedXMaximum = commonXMaximum > 0.0
        ? 1.05 * commonXMaximum
        : 1.0;

    for (std::size_t index = 0; index < graphs.size(); ++index)
    {
        if (index == 0)
        {
            graphs[index]->SetTitle(title.c_str());
            graphs[index]->SetMinimum(0.0);
            graphs[index]->SetMaximum(1.02);
            graphs[index]->Draw("AL");
            graphs[index]->GetXaxis()->SetLimits(0.0, displayedXMaximum);
        }
        else
        {
            graphs[index]->Draw("L SAME");
        }
    }

    legend.Draw();
    canvas.SetGrid();
    canvas.SaveAs((config.figuresDirectory / filename).string().c_str());
}

nlohmann::json metricsJson(const Metrics& metrics)
{
    return {
        {"events", metrics.eventCount},
        {"arm_fwhm_degree", metrics.armFwhmDegree},
        {"arm_R68_degree", metrics.armR68Degree},
        {"arm_R90_degree", metrics.armR90Degree},
        {"arm_tail_fraction", metrics.armTailFraction},
        {"energy_fwhm_MeV", metrics.energyFwhmMeV},
        {"energy_fwhm_percent", metrics.energyFwhmPercent},
        {"energy_R68_MeV", metrics.energyR68MeV},
        {"energy_R90_MeV", metrics.energyR90MeV},
        {"energy_tail_fraction", metrics.energyTailFraction}
    };
}
}

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: doppler_compare [path/to/comparison_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/comparison.json"};
        const ComparisonConfig config = readConfig(configPath);
        std::filesystem::create_directories(config.figuresDirectory);
        std::filesystem::create_directories(config.summaryJson.parent_path());
        std::vector<ModelData> data;

        for (const InputDefinition& input : config.inputs)
        {
            if (!std::filesystem::exists(input.rootFile))
            {
                std::cerr << "Warning: skipping missing optional result: "
                          << input.rootFile << '\n';
                continue;
            }

            data.push_back(readModel(input, config.treeName));
        }

        if (data.size() < 2)
        {
            throw std::runtime_error{"At least two non-empty model results are required."};
        }

        gROOT->SetBatch(kTRUE);
        gStyle->SetOptStat(0);
        gStyle->SetLineWidth(2);

        for (const Level level : {Level::truth, Level::detector})
        {
            drawHistogramOverlay(data, config, level, true);
            drawHistogramOverlay(data, config, level, false);
            drawCdfOverlay(data, config, level, true);
            drawCdfOverlay(data, config, level, false);
        }

        nlohmann::json summary;
        summary["source_energy_MeV"] = config.sourceEnergyMeV;
        summary["arm_tail_threshold_degree"] = config.armTailThreshold;
        summary["relative_energy_tail_threshold"] =
            config.relativeEnergyTailThreshold;
        summary["models"] = nlohmann::json::array();

        std::cout << std::left << std::setw(20) << "model"
                  << std::setw(12) << "level"
                  << std::right << std::setw(12) << "events"
                  << std::setw(14) << "ARM R68"
                  << std::setw(14) << "ARM R90"
                  << std::setw(16) << "E FWHM(%)" << '\n';

        for (std::size_t index = 0; index < data.size(); ++index)
        {
            nlohmann::json modelSummary{
                {"label", data[index].definition.label},
                {"root_file", data[index].definition.rootFile.string()}
            };

            for (const Level level : {Level::truth, Level::detector})
            {
                const Metrics metrics = calculateMetrics(
                    view(data[index], level),
                    config,
                    "metric_" + std::to_string(index) + '_' + levelName(level)
                );
                modelSummary[levelName(level) + "_level"] = metricsJson(metrics);
                std::cout << std::left << std::setw(20) << data[index].definition.label
                          << std::setw(12) << levelName(level)
                          << std::right << std::setw(12) << metrics.eventCount
                          << std::setw(14) << metrics.armR68Degree
                          << std::setw(14) << metrics.armR90Degree
                          << std::setw(16) << metrics.energyFwhmPercent << '\n';
            }

            summary["models"].push_back(std::move(modelSummary));
        }

        std::ofstream output{config.summaryJson};

        if (!output)
        {
            throw std::runtime_error{"Cannot create comparison JSON summary."};
        }

        output << summary.dump(2) << '\n';
        std::cout << "Figures: " << config.figuresDirectory << '\n'
                  << "Summary: " << config.summaryJson << '\n';
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Doppler comparison error: " << error.what() << '\n';
        return 1;
    }
}
