#include "spectrum_plotter.h"

#include "plot_utils.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TH1D.h>
#include <TLegend.h>
#include <TLine.h>

#include <algorithm>
#include <filesystem>
#include <sstream>
#include <vector>

std::string SpectrumPlotter::name() const
{
    return "spectrum";
}

void SpectrumPlotter::plot(const ReconstructionData& data, const VisConfig& config) const
{
    const std::vector<EnergyPoint> spectrum = marginalizeEnergies(data);
    const std::vector<double> binEdges = makeEnergyBinEdges(spectrum);

    TH1D histogram{
        "eiid_spectrum",
        "Direction-marginalized EIID spectrum;Energy (MeV);Marginal intensity",
        static_cast<int>(spectrum.size()),
        binEdges.data()
    };

    histogram.SetDirectory(nullptr);
    histogram.SetStats(false);
    histogram.SetLineColor(kAzure + 2);
    histogram.SetLineWidth(3);
    histogram.SetFillColorAlpha(kAzure - 9, 0.45);

    for (std::size_t index = 0; index < spectrum.size(); ++index)
    {
        histogram.SetBinContent(
            static_cast<int>(index + 1),
            spectrum[index].weight
        );
    }

    TCanvas canvas{"spectrum_canvas", "EIID spectrum", 1100, 760};
    canvas.SetLeftMargin(0.12);
    canvas.SetRightMargin(0.05);
    canvas.SetBottomMargin(0.12);
    canvas.SetGridy();

    histogram.SetMaximum(histogram.GetMaximum() * 1.18);
    histogram.Draw("HIST");

    if (config.showTruthMarkers())
    {
        TLine truthLine{
            config.truth().energyMeV,
            0.0,
            config.truth().energyMeV,
            histogram.GetMaximum()
        };

        truthLine.SetLineColor(kRed + 1);
        truthLine.SetLineStyle(2);
        truthLine.SetLineWidth(3);
        truthLine.Draw("SAME");

        std::ostringstream label;
        label << "Truth energy = " << config.truth().energyMeV << " MeV";

        TLegend legend{0.60, 0.77, 0.89, 0.88};
        legend.SetBorderSize(0);
        legend.SetFillStyle(0);
        legend.AddEntry(&histogram, "Reconstructed spectrum", "LF");
        legend.AddEntry(&truthLine, label.str().c_str(), "L");
        legend.Draw();

        canvas.Modified();
        canvas.Update();

        const std::filesystem::path outputPath =
            config.outputDirectory() / "spectrum.png";

        canvas.SaveAs(outputPath.string().c_str());
        return;
    }

    canvas.Modified();
    canvas.Update();

    const std::filesystem::path outputPath =
        config.outputDirectory() / "spectrum.png";

    canvas.SaveAs(outputPath.string().c_str());
}
