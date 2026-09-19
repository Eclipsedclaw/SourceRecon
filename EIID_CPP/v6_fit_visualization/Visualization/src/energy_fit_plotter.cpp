#include "energy_fit_plotter.h"

#include "plot_utils.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TF1.h>
#include <TH1D.h>
#include <TLegend.h>
#include <TLine.h>
#include <TPad.h>
#include <TPaveText.h>

#include <algorithm>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

EnergyFitPlotter::EnergyFitPlotter(
    std::shared_ptr<const FitAnalysisResult> analysis
)
    : analysis_{std::move(analysis)}
{
    if (!analysis_)
    {
        throw std::invalid_argument{"EnergyFitPlotter requires fit analysis."};
    }
}

std::string EnergyFitPlotter::name() const
{
    return "energy fit";
}

void EnergyFitPlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    static_cast<void>(data);
    const EnergyFitResult& result = analysis_->finalEnergy;
    const std::vector<double> edges = makeEnergyBinEdges(result.spectrum);
    TH1D histogram{
        "eiid_direction_gated_energy_fit",
        "Direction-gated energy peak;Energy (MeV);Reconstructed intensity",
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

    TF1 fitFunction{
        "display_energy_fit_function",
        "[0]*exp(-0.5*((x-[1])/[2])^2)+[3]",
        result.fitMinMeV,
        result.fitMaxMeV
    };
    fitFunction.SetParameters(
        result.amplitude,
        result.meanMeV,
        result.sigmaMeV,
        result.background
    );
    fitFunction.SetLineColor(kOrange + 7);
    fitFunction.SetLineWidth(3);

    TCanvas canvas{"energy_fit_canvas", "Energy fit", 1150, 880};
    TPad upperPad{"energy_fit_upper", "Energy fit", 0.0, 0.28, 1.0, 1.0};
    TPad lowerPad{"energy_fit_lower", "Fit residual", 0.0, 0.0, 1.0, 0.28};
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
    histogram.SetMaximum(histogram.GetMaximum() * 1.28);
    histogram.Draw("HIST");
    fitFunction.Draw("SAME");

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

    std::ostringstream fitLabel;
    fitLabel << "Local Gaussian fit ["
             << std::fixed << std::setprecision(3)
             << result.fitMinMeV << ", " << result.fitMaxMeV << "] MeV";
    TLegend legend{0.56, 0.72, 0.91, 0.89};
    legend.SetBorderSize(0);
    legend.SetFillStyle(0);
    legend.AddEntry(&histogram, "Direction-gated spectrum", "LF");
    legend.AddEntry(&fitFunction, fitLabel.str().c_str(), "L");

    if (config.showTruthMarkers())
    {
        legend.AddEntry(&truthLine, "Truth energy", "L");
    }

    legend.Draw();

    TPaveText metrics{0.14, 0.60, 0.48, 0.88, "NDC"};
    metrics.SetBorderSize(1);
    metrics.SetFillColorAlpha(kWhite, 0.90);
    metrics.SetTextAlign(12);
    metrics.SetTextSize(0.032);
    std::ostringstream line;
    line << std::fixed << std::setprecision(5)
         << "#mu_{E} = " << result.meanMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "bias = " << result.truthBiasMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "#sigma_{E} = " << result.sigmaMeV << " MeV";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "FWHM/#mu_{E} = "
         << 100.0 * result.relativeFwhm << " %";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "direction gate = "
         << result.directionGateRadiusDegree << " deg";
    metrics.AddText(line.str().c_str());

    if (!result.fitConverged)
    {
        metrics.AddText("WARNING: ROOT fit failed; showing moment fallback");
    }

    metrics.Draw();

    lowerPad.cd();
    TH1D residual{
        "eiid_energy_fit_residual",
        ";Energy (MeV);Residual / peak",
        static_cast<int>(result.spectrum.size()),
        edges.data()
    };
    residual.SetDirectory(nullptr);
    residual.SetStats(false);
    residual.SetLineColor(kAzure + 2);
    residual.SetLineWidth(2);
    residual.SetMarkerColor(kAzure + 2);
    residual.SetMarkerStyle(20);
    residual.SetMarkerSize(0.75);
    residual.GetXaxis()->SetTitleSize(0.11);
    residual.GetXaxis()->SetLabelSize(0.09);
    residual.GetYaxis()->SetTitleSize(0.09);
    residual.GetYaxis()->SetLabelSize(0.075);
    residual.GetYaxis()->SetTitleOffset(0.48);
    residual.GetYaxis()->SetNdivisions(505);
    const double peak = histogram.GetMaximum();

    for (std::size_t index = 0; index < result.spectrum.size(); ++index)
    {
        const double energy = result.spectrum[index].energyMeV;

        if (energy >= result.fitMinMeV && energy <= result.fitMaxMeV)
        {
            residual.SetBinContent(
                static_cast<int>(index + 1),
                (result.spectrum[index].weight - fitFunction.Eval(energy)) / peak
            );
        }
    }

    residual.Draw("HIST P");
    TLine zeroLine{edges.front(), 0.0, edges.back(), 0.0};
    zeroLine.SetLineStyle(2);
    zeroLine.Draw("SAME");

    canvas.cd();
    canvas.Modified();
    canvas.Update();
    const std::filesystem::path outputPath =
        config.outputDirectory() / "energy_fit.png";
    canvas.SaveAs(outputPath.string().c_str());
}
