#include "CalibrationPipeline.h"

#include "CalibrationConfig.h"
#include "DoubleGaussianFitter.h"
#include "KernelParameterTable.h"
#include "RootSampleReader.h"
#include "VoigtFitter.h"

#include "TCanvas.h"
#include "TColor.h"
#include "TFile.h"
#include "TGraph.h"
#include "TH1D.h"
#include "TH3D.h"
#include "TLegend.h"
#include "TNamed.h"
#include "TTree.h"

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
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
struct ModelMetric
{
    ResponseFitResult fit;
    double trainingNegativeLogLikelihood{};
    double testNegativeLogLikelihood{};
    double aic{};
    double bic{};
};

struct CalibratedBin
{
    KernelParameters parameters;
    ModelMetric voigt;
    ModelMetric doubleGaussian;
    std::size_t trainingCount{};
    std::size_t testCount{};
    double empiricalR68Degree{};
    double empiricalR90Degree{};
    double empiricalTailFraction{};
};

std::vector<double> uniqueEnergies(const std::vector<ResponseSample>& samples)
{
    std::vector<double> energies;
    energies.reserve(samples.size());

    for (const ResponseSample& sample : samples)
    {
        energies.push_back(sample.incidentEnergyMeV);
    }

    std::sort(energies.begin(), energies.end());
    energies.erase(
        std::unique(
            energies.begin(),
            energies.end(),
            [](double left, double right)
            {
                return std::abs(left - right) < 1.0e-9;
            }
        ),
        energies.end()
    );
    return energies;
}

std::vector<double> centerEdges(const std::vector<double>& centers)
{
    if (centers.empty())
    {
        throw std::runtime_error{"No calibration energies were read."};
    }

    if (centers.size() == 1)
    {
        const double halfWidth = std::max(0.005, 0.025 * centers.front());
        return {centers.front() - halfWidth, centers.front() + halfWidth};
    }

    std::vector<double> edges(centers.size() + 1);

    for (std::size_t index = 1; index < centers.size(); ++index)
    {
        edges[index] = 0.5 * (centers[index - 1] + centers[index]);
    }

    edges.front() = centers.front() - (edges[1] - centers.front());
    edges.back() = centers.back() + (centers.back() - edges[centers.size() - 1]);
    return edges;
}

void reportSampleCoverage(
    const std::vector<ResponseSample>& samples,
    const std::vector<double>& energies
)
{
    std::cout << "Response-calibration sample coverage:\n";

    for (const double energy : energies)
    {
        std::size_t count = 0;
        double minimumAngle = std::numeric_limits<double>::infinity();
        double maximumAngle = -std::numeric_limits<double>::infinity();

        for (const ResponseSample& sample : samples)
        {
            if (std::abs(sample.incidentEnergyMeV - energy) >= 1.0e-9)
            {
                continue;
            }

            ++count;
            minimumAngle = std::min(minimumAngle, sample.scatterAngleDegree);
            maximumAngle = std::max(maximumAngle, sample.scatterAngleDegree);
        }

        std::cout << "  E=" << energy << " MeV: " << count
                  << " valid events";

        if (count > 0)
        {
            std::cout << ", scatter-angle range=[" << minimumAngle
                      << ", " << maximumAngle << "] degree";
        }

        std::cout << '\n';
    }
}

bool belongsToTest(std::int64_t eventId, double fraction)
{
    // A deterministic integer hash makes the train/test split reproducible
    // without depending on the order in which ROOT files are supplied.
    const std::uint64_t value = static_cast<std::uint64_t>(eventId);
    const std::uint64_t hash = value * 11400714819323198485ull;
    return hash % 10000ull < static_cast<std::uint64_t>(fraction * 10000.0);
}

double quantileOfAbsolute(std::vector<double> values, double probability)
{
    if (values.empty())
    {
        return std::numeric_limits<double>::quiet_NaN();
    }

    for (double& value : values)
    {
        value = std::abs(value);
    }

    std::sort(values.begin(), values.end());
    const std::size_t index = static_cast<std::size_t>(
        std::ceil(probability * static_cast<double>(values.size())) - 1.0
    );
    return values[std::min(index, values.size() - 1)];
}

ModelMetric evaluateModel(
    const IResponseFitter& fitter,
    const ResponseFitResult& fit,
    const std::vector<double>& training,
    const std::vector<double>& test
)
{
    const auto calculateNll = [&fitter, &fit](const std::vector<double>& values)
    {
        double value = 0.0;

        for (const double arm : values)
        {
            const double density = std::max(
                fitter.density(arm, fit),
                1.0e-300
            );
            value -= std::log(density);
        }

        return value;
    };

    const double trainingNll = calculateNll(training);
    const double testNll = calculateNll(test);
    const double parameterCount = static_cast<double>(fitter.parameterCount());
    const double sampleCount = static_cast<double>(
        std::max<std::size_t>(1, training.size())
    );
    return ModelMetric{
        fit,
        trainingNll,
        testNll,
        2.0 * parameterCount + 2.0 * trainingNll,
        parameterCount * std::log(sampleCount) + 2.0 * trainingNll
    };
}

void drawComparison(
    TH1D& histogram,
    const IResponseFitter& voigtFitter,
    const ModelMetric& voigt,
    const IResponseFitter& doubleFitter,
    const ModelMetric& doubleGaussian,
    const std::filesystem::path& output
)
{
    histogram.SetDirectory(nullptr);

    if (histogram.Integral() > 0.0)
    {
        histogram.Scale(1.0 / histogram.Integral(), "width");
    }

    histogram.SetLineColor(kBlack);
    histogram.SetMarkerStyle(20);
    histogram.SetMarkerSize(0.55);
    histogram.SetTitle("ARM response calibration;ARM (degree);probability density (degree^{-1})");

    constexpr int pointCount = 600;
    TGraph voigtGraph{pointCount};
    TGraph doubleGraph{pointCount};
    const double minimum = histogram.GetXaxis()->GetXmin();
    const double maximum = histogram.GetXaxis()->GetXmax();

    for (int point = 0; point < pointCount; ++point)
    {
        const double x = minimum + (maximum - minimum) *
            static_cast<double>(point) / static_cast<double>(pointCount - 1);
        voigtGraph.SetPoint(point, x, voigtFitter.density(x, voigt.fit));
        doubleGraph.SetPoint(point, x, doubleFitter.density(x, doubleGaussian.fit));
    }

    voigtGraph.SetLineColor(kBlue + 1);
    voigtGraph.SetLineWidth(3);
    doubleGraph.SetLineColor(kRed + 1);
    doubleGraph.SetLineWidth(3);
    doubleGraph.SetLineStyle(2);

    TCanvas canvas{"response_calibration_canvas", "response calibration", 1000, 720};
    canvas.SetGrid();
    histogram.Draw("E");
    voigtGraph.Draw("L SAME");
    doubleGraph.Draw("L SAME");

    TLegend legend{0.59, 0.70, 0.88, 0.88};
    legend.AddEntry(&histogram, "training sample", "lep");
    legend.AddEntry(&voigtGraph, "Voigt", "l");
    legend.AddEntry(&doubleGraph, "double Gaussian", "l");
    legend.Draw();
    canvas.SaveAs(output.string().c_str());
}

void normalizeHistogramSlices(TH3D& histogram)
{
    for (int energyBin = 1; energyBin <= histogram.GetNbinsX(); ++energyBin)
    {
        for (int angleBin = 1; angleBin <= histogram.GetNbinsY(); ++angleBin)
        {
            double integral = 0.0;

            for (int armBin = 1; armBin <= histogram.GetNbinsZ(); ++armBin)
            {
                integral += histogram.GetBinContent(energyBin, angleBin, armBin) *
                    histogram.GetZaxis()->GetBinWidth(armBin);
            }

            if (integral <= 0.0)
            {
                continue;
            }

            for (int armBin = 1; armBin <= histogram.GetNbinsZ(); ++armBin)
            {
                histogram.SetBinContent(
                    energyBin,
                    angleBin,
                    armBin,
                    histogram.GetBinContent(energyBin, angleBin, armBin) /
                        integral
                );
            }
        }
    }
}
}

void CalibrationPipeline::run(const CalibrationConfig& config)
{
    std::vector<ResponseSample> samples;

    for (const CalibrationInput& input : config.inputs())
    {
        std::vector<ResponseSample> current = RootSampleReader::read(input);
        samples.insert(samples.end(), current.begin(), current.end());
    }

    if (samples.empty())
    {
        throw std::runtime_error{"No valid response-calibration samples were read."};
    }

    const std::vector<double> energies = uniqueEnergies(samples);
    reportSampleCoverage(samples, energies);
    const std::vector<double> energyEdges = centerEdges(energies);
    const std::vector<double>& angleEdges = config.scatterAngleEdgesDegree();
    std::vector<double> armEdges(static_cast<std::size_t>(config.armBinCount()) + 1);

    for (int bin = 0; bin <= config.armBinCount(); ++bin)
    {
        armEdges[static_cast<std::size_t>(bin)] = config.armMinimumDegree() +
            (config.armMaximumDegree() - config.armMinimumDegree()) *
            static_cast<double>(bin) / static_cast<double>(config.armBinCount());
    }

    TH3D empirical{
        config.histogramName().c_str(),
        "Empirical detector ARM PDF;incident energy (MeV);scatter angle (degree);ARM (degree)",
        static_cast<int>(energies.size()),
        energyEdges.data(),
        static_cast<int>(angleEdges.size() - 1),
        angleEdges.data(),
        config.armBinCount(),
        armEdges.data()
    };
    empirical.SetDirectory(nullptr);

    for (const ResponseSample& sample : samples)
    {
        empirical.Fill(
            sample.incidentEnergyMeV,
            sample.scatterAngleDegree,
            sample.armDegree
        );
    }

    normalizeHistogramSlices(empirical);
    const VoigtFitter voigtFitter;
    const DoubleGaussianFitter doubleFitter;
    std::vector<CalibratedBin> calibrated;
    std::filesystem::create_directories(config.figuresDirectory());

    for (std::size_t energyIndex = 0; energyIndex < energies.size(); ++energyIndex)
    {
        for (std::size_t angleIndex = 0;
             angleIndex + 1 < angleEdges.size();
             ++angleIndex)
        {
            std::vector<double> training;
            std::vector<double> testing;
            const double lowAngle = angleEdges[angleIndex];
            const double highAngle = angleEdges[angleIndex + 1];

            for (const ResponseSample& sample : samples)
            {
                const bool energyMatch =
                    std::abs(sample.incidentEnergyMeV - energies[energyIndex]) < 1.0e-9;
                const bool angleMatch = sample.scatterAngleDegree >= lowAngle &&
                    (sample.scatterAngleDegree < highAngle ||
                     (angleIndex + 2 == angleEdges.size() &&
                      sample.scatterAngleDegree <= highAngle));

                if (!energyMatch || !angleMatch ||
                    sample.armDegree < config.armMinimumDegree() ||
                    sample.armDegree > config.armMaximumDegree())
                {
                    continue;
                }

                (belongsToTest(sample.eventId, config.testFraction())
                    ? testing
                    : training).push_back(sample.armDegree);
            }

            if (training.size() < config.minimumEventsPerBin())
            {
                std::ostringstream message;
                message << "Calibration bin E=" << energies[energyIndex]
                        << " MeV, angle=[" << lowAngle << ',' << highAngle
                        << "] degree contains only " << training.size()
                        << " training events; minimum is "
                        << config.minimumEventsPerBin() << '.';
                throw std::runtime_error{message.str()};
            }

            if (testing.size() < config.minimumTestEventsPerBin())
            {
                std::ostringstream message;
                message << "Calibration bin E=" << energies[energyIndex]
                        << " MeV, angle=[" << lowAngle << ',' << highAngle
                        << "] degree contains only " << testing.size()
                        << " held-out events; minimum is "
                        << config.minimumTestEventsPerBin() << '.';
                throw std::runtime_error{message.str()};
            }

            const std::string histogramName =
                "arm_training_e" + std::to_string(energyIndex) +
                "_a" + std::to_string(angleIndex);
            TH1D histogram{
                histogramName.c_str(),
                histogramName.c_str(),
                config.armBinCount(),
                config.armMinimumDegree(),
                config.armMaximumDegree()
            };
            histogram.SetDirectory(nullptr);

            for (const double arm : training)
            {
                histogram.Fill(arm);
            }

            const ResponseFitResult voigtFit = voigtFitter.fit(histogram);
            const ResponseFitResult doubleFit = doubleFitter.fit(histogram);
            const ModelMetric voigt = evaluateModel(
                voigtFitter,
                voigtFit,
                training,
                testing
            );
            const ModelMetric doubleGaussian = evaluateModel(
                doubleFitter,
                doubleFit,
                training,
                testing
            );
            const double centerAngle = 0.5 * (lowAngle + highAngle);
            const auto tailCount = std::count_if(
                testing.begin(),
                testing.end(),
                [](double value) { return std::abs(value) > 3.0; }
            );

            calibrated.push_back(CalibratedBin{
                KernelParameters{
                    energies[energyIndex],
                    centerAngle,
                    voigtFit.meanDegree,
                    voigtFit.gaussianSigmaDegree,
                    voigtFit.lorentzFwhmDegree,
                    doubleFit.meanDegree,
                    doubleFit.coreSigmaDegree,
                    doubleFit.tailSigmaDegree,
                    doubleFit.coreWeight
                },
                voigt,
                doubleGaussian,
                training.size(),
                testing.size(),
                quantileOfAbsolute(testing, 0.68),
                quantileOfAbsolute(testing, 0.90),
                static_cast<double>(tailCount) / static_cast<double>(testing.size())
            });

            drawComparison(
                histogram,
                voigtFitter,
                voigt,
                doubleFitter,
                doubleGaussian,
                config.figuresDirectory() /
                    ("response_e" + std::to_string(energyIndex) +
                     "_a" + std::to_string(angleIndex) + ".png")
            );
        }
    }

    if (!config.outputRootFile().parent_path().empty())
    {
        std::filesystem::create_directories(
            config.outputRootFile().parent_path()
        );
    }

    TFile output{config.outputRootFile().string().c_str(), "RECREATE"};

    if (output.IsZombie())
    {
        throw std::runtime_error{
            "Cannot create response calibration ROOT file: " +
            config.outputRootFile().string()
        };
    }

    double energyMeV{};
    double angleDegree{};
    double voigtMean{};
    double voigtSigma{};
    double voigtLorentzFwhm{};
    double doubleMean{};
    double doubleCoreSigma{};
    double doubleTailSigma{};
    double doubleCoreWeight{};
    double voigtNll{};
    double voigtAic{};
    double voigtBic{};
    double doubleNll{};
    double doubleAic{};
    double doubleBic{};
    double empiricalR68{};
    double empiricalR90{};
    double empiricalTailFraction{};
    Long64_t trainingEvents{};
    Long64_t testEvents{};
    Bool_t voigtConverged{};
    Bool_t doubleConverged{};
    TTree parameterTree{
        config.parameterTree().c_str(),
        "Energy- and scatter-angle-dependent ARM response parameters"
    };
    parameterTree.Branch("energy_MeV", &energyMeV);
    parameterTree.Branch("scatter_angle_degree", &angleDegree);
    parameterTree.Branch("voigt_mean_degree", &voigtMean);
    parameterTree.Branch("voigt_gaussian_sigma_degree", &voigtSigma);
    parameterTree.Branch("voigt_lorentz_fwhm_degree", &voigtLorentzFwhm);
    parameterTree.Branch("double_gaussian_mean_degree", &doubleMean);
    parameterTree.Branch("double_gaussian_core_sigma_degree", &doubleCoreSigma);
    parameterTree.Branch("double_gaussian_tail_sigma_degree", &doubleTailSigma);
    parameterTree.Branch("double_gaussian_core_weight", &doubleCoreWeight);
    parameterTree.Branch("voigt_test_nll", &voigtNll);
    parameterTree.Branch("voigt_aic", &voigtAic);
    parameterTree.Branch("voigt_bic", &voigtBic);
    parameterTree.Branch("double_gaussian_test_nll", &doubleNll);
    parameterTree.Branch("double_gaussian_aic", &doubleAic);
    parameterTree.Branch("double_gaussian_bic", &doubleBic);
    parameterTree.Branch("empirical_r68_degree", &empiricalR68);
    parameterTree.Branch("empirical_r90_degree", &empiricalR90);
    parameterTree.Branch("empirical_tail_fraction_abs_gt_3_degree", &empiricalTailFraction);
    parameterTree.Branch("training_events", &trainingEvents);
    parameterTree.Branch("test_events", &testEvents);
    parameterTree.Branch("voigt_converged", &voigtConverged);
    parameterTree.Branch("double_gaussian_converged", &doubleConverged);

    nlohmann::json jsonRows = nlohmann::json::array();

    for (const CalibratedBin& item : calibrated)
    {
        energyMeV = item.parameters.energyMeV;
        angleDegree = item.parameters.scatterAngleDegree;
        voigtMean = item.parameters.voigtMeanDegree;
        voigtSigma = item.parameters.voigtGaussianSigmaDegree;
        voigtLorentzFwhm = item.parameters.voigtLorentzFwhmDegree;
        doubleMean = item.parameters.doubleGaussianMeanDegree;
        doubleCoreSigma = item.parameters.doubleGaussianCoreSigmaDegree;
        doubleTailSigma = item.parameters.doubleGaussianTailSigmaDegree;
        doubleCoreWeight = item.parameters.doubleGaussianCoreWeight;
        voigtNll = item.voigt.testNegativeLogLikelihood;
        voigtAic = item.voigt.aic;
        voigtBic = item.voigt.bic;
        doubleNll = item.doubleGaussian.testNegativeLogLikelihood;
        doubleAic = item.doubleGaussian.aic;
        doubleBic = item.doubleGaussian.bic;
        empiricalR68 = item.empiricalR68Degree;
        empiricalR90 = item.empiricalR90Degree;
        empiricalTailFraction = item.empiricalTailFraction;
        trainingEvents = static_cast<Long64_t>(item.trainingCount);
        testEvents = static_cast<Long64_t>(item.testCount);
        voigtConverged = item.voigt.fit.converged;
        doubleConverged = item.doubleGaussian.fit.converged;
        parameterTree.Fill();

        jsonRows.push_back({
            {"energy_MeV", energyMeV},
            {"scatter_angle_degree", angleDegree},
            {"training_events", trainingEvents},
            {"test_events", testEvents},
            {"empirical_r68_degree", empiricalR68},
            {"empirical_r90_degree", empiricalR90},
            {"empirical_tail_fraction_abs_gt_3_degree", empiricalTailFraction},
            {"voigt", {
                {"converged", static_cast<bool>(voigtConverged)},
                {"test_nll", voigtNll}, {"aic", voigtAic}, {"bic", voigtBic},
                {"mean_degree", voigtMean},
                {"gaussian_sigma_degree", voigtSigma},
                {"lorentz_fwhm_degree", voigtLorentzFwhm}
            }},
            {"double_gaussian", {
                {"converged", static_cast<bool>(doubleConverged)},
                {"test_nll", doubleNll}, {"aic", doubleAic}, {"bic", doubleBic},
                {"mean_degree", doubleMean},
                {"core_sigma_degree", doubleCoreSigma},
                {"tail_sigma_degree", doubleTailSigma},
                {"core_weight", doubleCoreWeight}
            }},
            {"preferred_by_bic", voigtBic <= doubleBic ? "voigt" : "double_gaussian"}
        });
    }

    output.cd();
    TNamed schema{
        "response_kernel_schema",
        "EIID V8 response kernel calibration, ARM density in inverse degrees"
    };
    schema.Write();
    parameterTree.Write();
    empirical.Write();
    output.Write();
    output.Close();

    if (!config.comparisonJson().parent_path().empty())
    {
        std::filesystem::create_directories(
            config.comparisonJson().parent_path()
        );
    }

    std::ofstream jsonOutput{config.comparisonJson()};

    if (!jsonOutput)
    {
        throw std::runtime_error{
            "Cannot create model-comparison JSON: " +
            config.comparisonJson().string()
        };
    }

    jsonOutput << nlohmann::json{
        {"schema", "eiid_v8_response_model_comparison"},
        {"total_samples", samples.size()},
        {"rows", jsonRows}
    }.dump(2) << '\n';

    std::cout << "Response calibration completed.\n"
              << "  samples: " << samples.size() << '\n'
              << "  parameter rows: " << calibrated.size() << '\n'
              << "  ROOT: " << config.outputRootFile().string() << '\n'
              << "  comparison: " << config.comparisonJson().string() << '\n';
}
