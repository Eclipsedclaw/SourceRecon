#include "energy_angle_plotter.h"

#include "plot_utils.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TH2D.h>
#include <TLegend.h>
#include <TLine.h>
#include <TMarker.h>
#include <TStyle.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

EnergyAnglePlotter::EnergyAnglePlotter(
    std::shared_ptr<const QualityAnalysisResult> analysis
)
    : analysis_{std::move(analysis)}
{
    if (!analysis_)
    {
        throw std::invalid_argument{
            "EnergyAnglePlotter requires quality analysis."
        };
    }
}

std::string EnergyAnglePlotter::name() const
{
    return "energy-angle map";
}

void EnergyAnglePlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    const std::vector<EnergyPoint> energies = marginalizeEnergies(data);
    const std::vector<double> energyEdges = makeEnergyBinEdges(energies);
    const std::size_t pixelCount = marginalizeDirections(data).size();
    const std::size_t nside = inferHealpixNside(pixelCount);
    const int angleBins = nside > 0
        ? std::max(45, static_cast<int>(3 * nside))
        : 90;
    TH2D histogram{
        "eiid_energy_angle_map",
        "Direction-energy correlation;Energy (MeV);Angular distance from truth (degree);Reconstructed intensity",
        static_cast<int>(energies.size()),
        energyEdges.data(),
        angleBins,
        0.0,
        180.0
    };
    histogram.SetDirectory(nullptr);
    histogram.SetStats(false);
    const std::array<double, 3> reference = truthDirection(config.truth());
    double smallestPositive = std::numeric_limits<double>::max();

    for (const ImageCell& cell : data.cells)
    {
        if (cell.weight < 0.0 || !std::isfinite(cell.weight))
        {
            throw std::runtime_error{
                "Energy-angle plotting requires finite non-negative weights."
            };
        }

        const SkyPixel pixel{
            cell.healpixPixelId,
            cell.thetaDegree,
            cell.phiDegree,
            cell.directionX,
            cell.directionY,
            cell.directionZ,
            cell.weight
        };
        histogram.Fill(
            cell.energyMeV,
            angularSeparationDegree(pixel, reference),
            cell.weight
        );

        if (cell.weight > 0.0)
        {
            smallestPositive = std::min(smallestPositive, cell.weight);
        }
    }

    if (smallestPositive < std::numeric_limits<double>::max())
    {
        histogram.SetMinimum(std::max(
            smallestPositive,
            histogram.GetMaximum() * 1.0e-8
        ));
    }

    TCanvas canvas{"energy_angle_canvas", "Energy-angle map", 1200, 820};
    canvas.SetLeftMargin(0.10);
    canvas.SetRightMargin(0.15);
    canvas.SetBottomMargin(0.11);
    canvas.SetLogz();
    canvas.SetGrid();
    gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(255);
    histogram.Draw("COLZ");

    TLine fittedEnergy{
        analysis_->directionGatedEnergy.peakEnergyMeV,
        0.0,
        analysis_->directionGatedEnergy.peakEnergyMeV,
        180.0
    };
    fittedEnergy.SetLineColor(kOrange + 7);
    fittedEnergy.SetLineWidth(3);
    fittedEnergy.Draw("SAME");

    TLine r68Line{
        energyEdges.front(),
        analysis_->containment.r68Degree,
        energyEdges.back(),
        analysis_->containment.r68Degree
    };
    TLine r90Line{
        energyEdges.front(),
        analysis_->containment.r90Degree,
        energyEdges.back(),
        analysis_->containment.r90Degree
    };
    r68Line.SetLineColor(kGreen + 2);
    r68Line.SetLineStyle(2);
    r68Line.SetLineWidth(2);
    r90Line.SetLineColor(kMagenta + 1);
    r90Line.SetLineStyle(2);
    r90Line.SetLineWidth(2);
    r68Line.Draw("SAME");
    r90Line.Draw("SAME");

    TMarker truthMarker{config.truth().energyMeV, 0.8, 29};
    truthMarker.SetMarkerColor(kRed + 1);
    truthMarker.SetMarkerSize(2.0);

    if (config.showTruthMarkers())
    {
        truthMarker.Draw("SAME");
    }

    TLegend legend{0.57, 0.70, 0.88, 0.89};
    legend.SetBorderSize(1);
    legend.SetFillColorAlpha(kWhite, 0.90);
    legend.AddEntry(&fittedEnergy, "Interpolated data peak", "L");
    legend.AddEntry(&r68Line, "Directional R68", "L");
    legend.AddEntry(&r90Line, "Directional R90", "L");

    if (config.showTruthMarkers())
    {
        legend.AddEntry(&truthMarker, "Truth", "P");
    }

    legend.Draw();
    canvas.Modified();
    canvas.Update();
    const std::filesystem::path outputPath =
        config.outputDirectory() / "energy_angle_map.png";
    canvas.SaveAs(outputPath.string().c_str());
}
