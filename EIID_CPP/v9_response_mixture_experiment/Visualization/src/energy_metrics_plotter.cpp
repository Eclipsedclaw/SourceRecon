#include "energy_metrics_plotter.h"

#include "plot_utils.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TF1.h>
#include <TH1D.h>
#include <TLegend.h>
#include <TLine.h>
#include <TPad.h>
#include <TPaveText.h>

#include <filesystem>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

EnergyMetricsPlotter::EnergyMetricsPlotter(
    std::shared_ptr<const QualityAnalysisResult> analysis
)
    : analysis_{std::move(analysis)}
{
    if (!analysis_)
    {
        throw std::invalid_argument{
            "EnergyMetricsPlotter requires quality analysis."
        };
    }
}

std::string EnergyMetricsPlotter::name() const
{
    return "model-independent energy metrics";
}

void EnergyMetricsPlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    static_cast<void>(data);
    const EnergyMetrics& result = analysis_->directionGatedEnergy;
    const std::vector<double> edges = makeEnergyBinEdges(result.spectrum);
    TH1D histogram{
        "v7_direction_gated_energy",
        "Model-independent energy resolution;Energy (MeV);Reconstructed intensity",
        static_cast<int>(result.spectrum.size()),
        edges.data()
    };
    histogram.SetDirectory(nullptr);
    histogram.SetStats(false);
    histogram.SetLineColor(kAzure + 2);
    histogram.SetLineWidth(3);
    histogram.SetFillColorAlpha(kAzure - 9, 0.45);

    for (std::size_t index = 0; index < result.spectrum.size(); ++index)
    {
        histogram.SetBinContent(
            static_cast<int>(index + 1),
            result.spectrum[index].weight
        );
    }

    TCanvas canvas{"v7_energy_metrics_canvas", "Energy metrics", 1200, 900};
    TPad upperPad{"v7_energy_upper", "Energy metrics", 0.0, 0.30, 1.0, 1.0};
    TPad lowerPad{"v7_energy_lower", "Cumulative intensity", 0.0, 0.0, 1.0, 0.30};
    upperPad.SetLeftMargin(0.12);
    upperPad.SetRightMargin(0.05);
    upperPad.SetBottomMargin(0.03);
    upperPad.SetGridy();
    lowerPad.SetLeftMargin(0.12);
    lowerPad.SetRightMargin(0.05);
    lowerPad.SetTopMargin(0.04);
    lowerPad.SetBottomMargin(0.34);
    lowerPad.SetGridy();
    upperPad.Draw();
    lowerPad.Draw();

    upperPad.cd();
    histogram.GetXaxis()->SetLabelSize(0.0);
    histogram.SetMaximum(histogram.GetMaximum() * 1.32);
    histogram.Draw("HIST");

    TLine truthLine{
        config.truth().energyMeV,
        0.0,
        config.truth().energyMeV,
        histogram.GetMaximum()
    };
    truthLine.SetLineColor(kRed + 1);
    truthLine.SetLineStyle(2);
    truthLine.SetLineWidth(3);

    if (config.showTruthMarkers())
    {
        truthLine.Draw("SAME");
    }

    TLine peakLine{
        result.peakEnergyMeV,
        0.0,
        result.peakEnergyMeV,
        result.peakIntensity
    };
    peakLine.SetLineColor(kOrange + 7);
    peakLine.SetLineWidth(3);
    peakLine.Draw("SAME");

    std::unique_ptr<TLine> halfMaximumLine;
    std::unique_ptr<TLine> leftHalfMaximumLine;
    std::unique_ptr<TLine> rightHalfMaximumLine;

    if (result.directFwhmAvailable)
    {
        halfMaximumLine = std::make_unique<TLine>(
            result.leftHalfMaximumMeV,
            result.halfMaximumIntensity,
            result.rightHalfMaximumMeV,
            result.halfMaximumIntensity
        );
        leftHalfMaximumLine = std::make_unique<TLine>(
            result.leftHalfMaximumMeV,
            0.0,
            result.leftHalfMaximumMeV,
            result.halfMaximumIntensity
        );
        rightHalfMaximumLine = std::make_unique<TLine>(
            result.rightHalfMaximumMeV,
            0.0,
            result.rightHalfMaximumMeV,
            result.halfMaximumIntensity
        );

        for (TLine* line : {
            halfMaximumLine.get(),
            leftHalfMaximumLine.get(),
            rightHalfMaximumLine.get()
        })
        {
            line->SetLineColor(kGreen + 2);
            line->SetLineWidth(2);
            line->Draw("SAME");
        }
    }

    TLine intervalLowLine{
        result.intervalLowMeV,
        0.0,
        result.intervalLowMeV,
        histogram.GetMaximum()
    };
    TLine intervalHighLine{
        result.intervalHighMeV,
        0.0,
        result.intervalHighMeV,
        histogram.GetMaximum()
    };

    for (TLine* line : {&intervalLowLine, &intervalHighLine})
    {
        line->SetLineColor(kMagenta + 1);
        line->SetLineStyle(3);
        line->SetLineWidth(2);
        line->Draw("SAME");
    }

    std::unique_ptr<TF1> gaussianFunction;

    if (result.gaussian.converged)
    {
        gaussianFunction = std::make_unique<TF1>(
            "v7_display_optional_energy_gaussian",
            "[0]*exp(-0.5*((x-[1])/[2])^2)+[3]",
            result.gaussian.fitMinMeV,
            result.gaussian.fitMaxMeV
        );
        gaussianFunction->SetParameters(
            result.gaussian.amplitude,
            result.gaussian.meanMeV,
            result.gaussian.sigmaMeV,
            result.gaussian.background
        );
        gaussianFunction->SetLineColor(kCyan + 2);
        gaussianFunction->SetLineStyle(2);
        gaussianFunction->SetLineWidth(3);
        gaussianFunction->Draw("SAME");
    }

    TLegend legend{0.58, 0.68, 0.92, 0.90};
    legend.SetBorderSize(0);
    legend.SetFillStyle(0);
    legend.AddEntry(&histogram, "Direction-gated spectrum", "LF");
    legend.AddEntry(&peakLine, "Interpolated data peak", "L");

    if (result.directFwhmAvailable)
    {
        legend.AddEntry(
            halfMaximumLine.get(),
            "Direct half-maximum width",
            "L"
        );
    }

    legend.AddEntry(&intervalLowLine, "Shortest intensity interval", "L");

    if (result.gaussian.converged)
    {
        legend.AddEntry(
            gaussianFunction.get(),
            "Optional Gaussian fit",
            "L"
        );
    }

    if (config.showTruthMarkers())
    {
        legend.AddEntry(&truthLine, "Truth energy", "L");
    }

    legend.Draw();

    TPaveText metrics{0.14, 0.53, 0.53, 0.90, "NDC"};
    metrics.SetBorderSize(1);
    metrics.SetFillColorAlpha(kWhite, 0.92);
    metrics.SetTextAlign(12);
    metrics.SetTextSize(0.029);
    std::ostringstream line;
    line << std::fixed << std::setprecision(5)
         << "E_{peak} = " << result.peakEnergyMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "peak bias = " << result.peakBiasMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();

    if (result.directFwhmAvailable)
    {
        line << "direct FWHM = " << result.directFwhmMeV << " MeV";
        metrics.AddText(line.str().c_str());
        line.str("");
        line.clear();
        line << "FWHM/E_{peak} = "
             << 100.0 * result.relativeDirectFwhm << " %";
        metrics.AddText(line.str().c_str());
        line.str("");
        line.clear();
    }
    else
    {
        metrics.AddText("direct FWHM unavailable: missing half-height crossing");
    }

    line << 100.0 * result.intervalFraction << "% shortest interval = ["
         << result.intervalLowMeV << ", "
         << result.intervalHighMeV << "] MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "global moment mean/sigma = "
         << result.momentMeanMeV << " / "
         << result.momentSigmaMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "direction gate = "
         << result.directionGateRadiusDegree << " deg";
    metrics.AddText(line.str().c_str());

    if (result.gaussian.enabled)
    {
        line.str("");
        line.clear();
        line << "optional Gaussian: "
             << (result.gaussian.converged ? "converged" : "unavailable")
             << " (status " << result.gaussian.status << ")";
        metrics.AddText(line.str().c_str());
    }

    metrics.Draw();

    lowerPad.cd();
    TH1D cumulative{
        "v7_energy_cumulative",
        ";Energy (MeV);Cumulative intensity",
        static_cast<int>(result.spectrum.size()),
        edges.data()
    };
    cumulative.SetDirectory(nullptr);
    cumulative.SetStats(false);
    cumulative.SetLineColor(kAzure + 2);
    cumulative.SetLineWidth(3);
    cumulative.SetMinimum(0.0);
    cumulative.SetMaximum(1.05);
    cumulative.GetXaxis()->SetTitleSize(0.11);
    cumulative.GetXaxis()->SetLabelSize(0.09);
    cumulative.GetYaxis()->SetTitleSize(0.09);
    cumulative.GetYaxis()->SetLabelSize(0.075);
    cumulative.GetYaxis()->SetTitleOffset(0.52);
    cumulative.GetYaxis()->SetNdivisions(505);
    double total = 0.0;

    for (const EnergyPoint& point : result.spectrum)
    {
        total += point.weight;
    }

    double running = 0.0;

    for (std::size_t index = 0; index < result.spectrum.size(); ++index)
    {
        running += result.spectrum[index].weight;
        cumulative.SetBinContent(
            static_cast<int>(index + 1),
            running / total
        );
    }

    cumulative.Draw("HIST");
    TLine fractionLine{
        edges.front(),
        result.intervalFraction,
        edges.back(),
        result.intervalFraction
    };
    fractionLine.SetLineColor(kMagenta + 1);
    fractionLine.SetLineStyle(3);
    fractionLine.Draw("SAME");
    TLine lowerIntervalLow{
        result.intervalLowMeV,
        0.0,
        result.intervalLowMeV,
        1.0
    };
    TLine lowerIntervalHigh{
        result.intervalHighMeV,
        0.0,
        result.intervalHighMeV,
        1.0
    };

    for (TLine* intervalLine : {&lowerIntervalLow, &lowerIntervalHigh})
    {
        intervalLine->SetLineColor(kMagenta + 1);
        intervalLine->SetLineStyle(3);
        intervalLine->Draw("SAME");
    }

    canvas.cd();
    canvas.Modified();
    canvas.Update();
    const std::filesystem::path outputPath =
        config.outputDirectory() / "energy_resolution.png";
    canvas.SaveAs(outputPath.string().c_str());
}
