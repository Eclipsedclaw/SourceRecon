#include "BenchmarkRunner.h"

#include "BenchmarkConfig.h"

#include "TCanvas.h"
#include "TColor.h"
#include "TFile.h"
#include "TGraph.h"
#include "TLegend.h"
#include "TMultiGraph.h"
#include "TNamed.h"
#include "TParameter.h"
#include "TTree.h"
#include "TTreeReader.h"
#include "TTreeReaderValue.h"

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <numbers>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace
{
struct ImageCell
{
    double weight{};
    double thetaDegree{};
    double phiDegree{};
    double x{};
    double y{};
    double z{};
    double energyMeV{};
};

struct EvaluatedResult
{
    BenchmarkInput input;
    std::vector<std::pair<double, double>> spectrum;
    std::vector<std::pair<double, double>> containment;
    double totalWeight{};
    double peakAngularErrorDegree{};
    double peakEnergyMeV{};
    double energyMeanMeV{};
    double energySigmaMeV{};
    double r50Degree{};
    double r68Degree{};
    double r90Degree{};
    double calibrationTestNllPerEvent{};
    double calibrationTotalAic{};
    double calibrationTotalBic{};
};

struct CalibrationScore
{
    std::size_t testEvents{};
    double testNll{};
    double aic{};
    double bic{};
};

std::map<std::string, CalibrationScore> readCalibrationScores(
    const std::filesystem::path& path,
    const std::vector<BenchmarkInput>& inputs
)
{
    std::ifstream input{path};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open calibration comparison: " + path.string()
        };
    }

    nlohmann::json document;
    input >> document;
    std::map<std::string, CalibrationScore> scores;

    for (const BenchmarkInput& benchmarkInput : inputs)
    {
        scores.emplace(benchmarkInput.kernelType, CalibrationScore{});
    }

    for (const auto& row : document.at("rows"))
    {
        const std::size_t testEvents =
            row.at("test_events").get<std::size_t>();

        for (auto& [kernelType, score] : scores)
        {
            const auto& metric = row.at(kernelType);

            if (!metric.at("converged").get<bool>())
            {
                throw std::runtime_error{
                    "Model status and calibration comparison disagree for " +
                    kernelType
                };
            }

            score.testEvents += testEvents;
            score.testNll += metric.at("test_nll").get<double>();
            score.aic += metric.at("aic").get<double>();
            score.bic += metric.at("bic").get<double>();
        }
    }

    for (const auto& [kernelType, score] : scores)
    {
        if (score.testEvents == 0)
        {
            throw std::runtime_error{
                "Calibration comparison has no test events for " + kernelType
            };
        }
    }

    return scores;
}

std::vector<ImageCell> readImage(const BenchmarkInput& input)
{
    TFile file{input.file.string().c_str(), "READ"};

    if (file.IsZombie())
    {
        throw std::runtime_error{"Cannot open benchmark result: " + input.file.string()};
    }

    TTree* tree = file.Get<TTree>(input.tree.c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find benchmark result tree: " + input.tree};
    }

    const auto* nside = file.Get<TParameter<int>>("healpix_nside");
    const auto* integrationNside =
        file.Get<TParameter<int>>("integration_nside");
    const auto* samples =
        file.Get<TParameter<Long64_t>>("samples_per_pixel");
    const auto* iterations = file.Get<TParameter<int>>("iteration_count");
    const auto* strategy = file.Get<TNamed>("pixel_integration_strategy");

    if (nside == nullptr || integrationNside == nullptr || samples == nullptr ||
        iterations == nullptr || strategy == nullptr)
    {
        throw std::runtime_error{
            "Benchmark result lacks V10 pixel-integration metadata: " +
            input.file.string()
        };
    }

    if (nside->GetVal() != input.reconstructionNside ||
        integrationNside->GetVal() != input.integrationNside ||
        static_cast<std::size_t>(samples->GetVal()) != input.samplesPerPixel ||
        iterations->GetVal() != input.iterationCount ||
        input.pixelIntegrationStrategy != strategy->GetTitle())
    {
        throw std::runtime_error{
            "Benchmark result metadata does not match its JSON entry: " +
            input.file.string()
        };
    }

    TTreeReader reader{tree};
    TTreeReaderValue<Double_t> weight{reader, "weight"};
    TTreeReaderValue<Double_t> theta{reader, "theta_degree"};
    TTreeReaderValue<Double_t> phi{reader, "phi_degree"};
    TTreeReaderValue<Double_t> x{reader, "direction_x"};
    TTreeReaderValue<Double_t> y{reader, "direction_y"};
    TTreeReaderValue<Double_t> z{reader, "direction_z"};
    TTreeReaderValue<Double_t> energy{reader, "energy_MeV"};
    std::vector<ImageCell> cells;
    cells.reserve(static_cast<std::size_t>(tree->GetEntries()));

    while (reader.Next())
    {
        cells.push_back(ImageCell{*weight, *theta, *phi, *x, *y, *z, *energy});
    }

    return cells;
}

double angleDegree(
    double x,
    double y,
    double z,
    const BenchmarkTruth& truth
)
{
    const double theta = truth.thetaDegree * std::numbers::pi / 180.0;
    const double phi = truth.phiDegree * std::numbers::pi / 180.0;
    const double truthX = std::sin(theta) * std::cos(phi);
    const double truthY = std::sin(theta) * std::sin(phi);
    const double truthZ = std::cos(theta);
    const double norm = std::sqrt(x * x + y * y + z * z);

    if (!std::isfinite(norm) || norm <= 0.0)
    {
        throw std::runtime_error{
            "Benchmark result contains a non-finite or zero direction vector."
        };
    }

    const double cosine = std::clamp(
        (x * truthX + y * truthY + z * truthZ) / norm,
        -1.0,
        1.0
    );
    return std::acos(cosine) * 180.0 / std::numbers::pi;
}

double containmentRadius(
    const std::vector<std::pair<double, double>>& curve,
    double fraction
)
{
    const auto found = std::lower_bound(
        curve.begin(),
        curve.end(),
        fraction,
        [](const auto& point, double value)
        {
            return point.second < value;
        }
    );
    return found == curve.end() ? curve.back().first : found->first;
}

EvaluatedResult evaluate(
    const BenchmarkInput& input,
    const BenchmarkTruth& truth,
    const CalibrationScore& calibration
)
{
    const std::vector<ImageCell> cells = readImage(input);

    if (cells.empty())
    {
        throw std::runtime_error{"Benchmark result contains no image cells."};
    }

    std::map<double, double> spectrumMap;
    std::vector<std::pair<double, double>> angularWeights;
    const ImageCell* peak = &cells.front();
    double totalWeight = 0.0;

    for (const ImageCell& cell : cells)
    {
        const double positiveWeight = std::max(cell.weight, 0.0);
        totalWeight += positiveWeight;
        spectrumMap[cell.energyMeV] += positiveWeight;
        angularWeights.emplace_back(
            angleDegree(cell.x, cell.y, cell.z, truth),
            positiveWeight
        );

        if (cell.weight > peak->weight)
        {
            peak = &cell;
        }
    }

    if (totalWeight <= 0.0)
    {
        throw std::runtime_error{"Benchmark image has no positive weight."};
    }

    std::vector<std::pair<double, double>> spectrum(
        spectrumMap.begin(),
        spectrumMap.end()
    );
    double energyMean = 0.0;

    for (const auto& [energy, weight] : spectrum)
    {
        energyMean += energy * weight / totalWeight;
    }

    double energyVariance = 0.0;

    for (const auto& [energy, weight] : spectrum)
    {
        const double difference = energy - energyMean;
        energyVariance += difference * difference * weight / totalWeight;
    }

    std::sort(angularWeights.begin(), angularWeights.end());
    std::vector<std::pair<double, double>> containment;
    containment.reserve(angularWeights.size());
    double cumulative = 0.0;

    for (const auto& [angle, weight] : angularWeights)
    {
        cumulative += weight / totalWeight;
        containment.emplace_back(angle, cumulative);
    }

    const double r50 = containmentRadius(containment, 0.50);
    const double r68 = containmentRadius(containment, 0.68);
    const double r90 = containmentRadius(containment, 0.90);

    return EvaluatedResult{
        input,
        std::move(spectrum),
        std::move(containment),
        totalWeight,
        angleDegree(peak->x, peak->y, peak->z, truth),
        peak->energyMeV,
        energyMean,
        std::sqrt(std::max(energyVariance, 0.0)),
        r50,
        r68,
        r90,
        calibration.testNll / static_cast<double>(calibration.testEvents),
        calibration.aic,
        calibration.bic
    };
}

void drawCurves(
    const std::vector<EvaluatedResult>& results,
    const std::filesystem::path& figures
)
{
    TCanvas spectrumCanvas{"benchmark_spectrum", "kernel spectra", 1000, 720};
    TMultiGraph spectra;
    TLegend spectrumLegend{0.62, 0.72, 0.88, 0.88};
    std::vector<TGraph> spectrumGraphs;
    spectrumGraphs.reserve(results.size());

    for (std::size_t index = 0; index < results.size(); ++index)
    {
        spectrumGraphs.emplace_back(static_cast<int>(results[index].spectrum.size()));
        TGraph& graph = spectrumGraphs.back();

        for (std::size_t point = 0; point < results[index].spectrum.size(); ++point)
        {
            graph.SetPoint(
                static_cast<int>(point),
                results[index].spectrum[point].first,
                results[index].spectrum[point].second / results[index].totalWeight
            );
        }

        graph.SetLineColor(static_cast<int>(kBlue + 2 * index));
        graph.SetLineWidth(3);
        spectra.Add(&graph, "L");
        spectrumLegend.AddEntry(&graph, results[index].input.label.c_str(), "l");
    }

    spectra.SetTitle("Pixel-integration energy comparison;energy (MeV);normalized intensity");
    spectra.Draw("A");
    spectrumLegend.Draw();
    spectrumCanvas.SetGrid();
    spectrumCanvas.SaveAs((figures / "kernel_energy_comparison.png").string().c_str());

    TCanvas containmentCanvas{"benchmark_containment", "kernel containment", 1000, 720};
    TMultiGraph containments;
    TLegend containmentLegend{0.62, 0.20, 0.88, 0.36};
    std::vector<TGraph> containmentGraphs;
    containmentGraphs.reserve(results.size());

    for (std::size_t index = 0; index < results.size(); ++index)
    {
        containmentGraphs.emplace_back(
            static_cast<int>(results[index].containment.size())
        );
        TGraph& graph = containmentGraphs.back();

        for (std::size_t point = 0;
             point < results[index].containment.size();
             ++point)
        {
            graph.SetPoint(
                static_cast<int>(point),
                results[index].containment[point].first,
                results[index].containment[point].second
            );
        }

        graph.SetLineColor(static_cast<int>(kBlue + 2 * index));
        graph.SetLineWidth(3);
        containments.Add(&graph, "L");
        containmentLegend.AddEntry(&graph, results[index].input.label.c_str(), "l");
    }

    containments.SetTitle("Pixel-integration direction comparison;angular distance to truth (degree);containment");
    containments.Draw("A");
    containmentLegend.Draw();
    containmentCanvas.SetGrid();
    containmentCanvas.SaveAs(
        (figures / "kernel_direction_comparison.png").string().c_str()
    );
}
}

void BenchmarkRunner::run(const BenchmarkConfig& config)
{
    std::vector<EvaluatedResult> results;
    const std::map<std::string, CalibrationScore> calibrationScores =
        readCalibrationScores(
            config.calibrationComparisonJson(),
            config.inputs()
        );

    for (const BenchmarkInput& input : config.inputs())
    {
        results.push_back(evaluate(
            input,
            config.truth(),
            calibrationScores.at(input.kernelType)
        ));
    }

    std::filesystem::create_directories(config.figuresDirectory());
    drawCurves(results, config.figuresDirectory());

    nlohmann::json rows = nlohmann::json::array();
    nlohmann::json skippedRows = nlohmann::json::array();

    for (const EvaluatedResult& result : results)
    {
        rows.push_back({
            {"label", result.input.label},
            {"kernel_type", result.input.kernelType},
            {"result_file", result.input.file.string()},
            {"pixel_integration_strategy",
             result.input.pixelIntegrationStrategy},
            {"reconstruction_nside", result.input.reconstructionNside},
            {"integration_nside", result.input.integrationNside},
            {"samples_per_pixel", result.input.samplesPerPixel},
            {"iteration_count", result.input.iterationCount},
            {"peak_angular_error_degree", result.peakAngularErrorDegree},
            {"peak_energy_MeV", result.peakEnergyMeV},
            {"peak_energy_residual_MeV", result.peakEnergyMeV - config.truth().energyMeV},
            {"energy_mean_MeV", result.energyMeanMeV},
            {"energy_sigma_MeV", result.energySigmaMeV},
            {"r50_degree", result.r50Degree},
            {"r68_degree", result.r68Degree},
            {"r90_degree", result.r90Degree},
            {"calibration_test_nll_per_event",
             result.calibrationTestNllPerEvent},
            {"calibration_total_aic", result.calibrationTotalAic},
            {"calibration_total_bic", result.calibrationTotalBic}
        });
    }

    for (const SkippedBenchmarkInput& skipped : config.skippedInputs())
    {
        skippedRows.push_back({
            {"label", skipped.label},
            {"kernel_type", skipped.kernelType},
            {"reason", skipped.reason}
        });
    }

    if (!config.outputJson().parent_path().empty())
    {
        std::filesystem::create_directories(config.outputJson().parent_path());
    }

    std::ofstream output{config.outputJson()};

    if (!output)
    {
        throw std::runtime_error{
            "Cannot create kernel-benchmark JSON: " + config.outputJson().string()
        };
    }

    output << nlohmann::json{
        {"schema", "eiid_v10_pixel_integration_benchmark"},
        {"multi_model_comparison_performed", results.size() >= 2},
        {"truth", {
            {"theta_degree", config.truth().thetaDegree},
            {"phi_degree", config.truth().phiDegree},
            {"energy_MeV", config.truth().energyMeV}
        }},
        {"results", rows},
        {"skipped_models", skippedRows}
    }.dump(2) << '\n';

    std::cout << "Pixel-integration benchmark completed.\n"
              << "  configurations: " << results.size() << '\n'
              << "  skipped configurations: " << config.skippedInputs().size() << '\n'
              << "  summary: " << config.outputJson().string() << '\n';

    if (results.size() == 1)
    {
        std::cout << "  comparison: only absolute metrics were produced because "
                  << "one model is usable.\n";
    }
}
