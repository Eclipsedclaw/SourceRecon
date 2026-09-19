#include "direction_fit_plotter.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TEllipse.h>
#include <TH2D.h>
#include <TLegend.h>
#include <TMarker.h>
#include <TPaveText.h>
#include <TStyle.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>

DirectionFitPlotter::DirectionFitPlotter(
    std::shared_ptr<const FitAnalysisResult> analysis
)
    : analysis_{std::move(analysis)}
{
    if (!analysis_)
    {
        throw std::invalid_argument{"DirectionFitPlotter requires fit analysis."};
    }
}

std::string DirectionFitPlotter::name() const
{
    return "direction fit";
}

void DirectionFitPlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    static_cast<void>(data);
    const DirectionFitResult& result = analysis_->direction;
    const int bins = std::max(
        20,
        static_cast<int>(std::ceil(
            2.0 * result.fitRadiusDegree / result.pixelScaleDegree
        ))
    );
    TH2D histogram{
        "eiid_local_direction_fit",
        "Energy-gated local direction fit;Local tangent u (degree);Local tangent v (degree);Intensity",
        bins,
        -result.fitRadiusDegree,
        result.fitRadiusDegree,
        bins,
        -result.fitRadiusDegree,
        result.fitRadiusDegree
    };
    histogram.SetDirectory(nullptr);
    histogram.SetStats(false);

    for (const LocalDirectionPoint& point : result.points)
    {
        histogram.Fill(point.uDegree, point.vDegree, point.weight);
    }

    TCanvas canvas{"direction_fit_canvas", "Direction fit", 1050, 880};
    canvas.SetLeftMargin(0.11);
    canvas.SetRightMargin(0.16);
    canvas.SetBottomMargin(0.11);
    canvas.SetGrid();
    gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(255);
    histogram.Draw("COLZ");

    TEllipse oneSigma{
        result.centerUDegree,
        result.centerVDegree,
        result.sigmaMajorDegree,
        result.sigmaMinorDegree,
        0.0,
        360.0,
        result.ellipseAngleDegree
    };
    TEllipse twoSigma{
        result.centerUDegree,
        result.centerVDegree,
        2.0 * result.sigmaMajorDegree,
        2.0 * result.sigmaMinorDegree,
        0.0,
        360.0,
        result.ellipseAngleDegree
    };

    for (TEllipse* ellipse : {&oneSigma, &twoSigma})
    {
        ellipse->SetFillStyle(0);
        ellipse->SetLineColor(kOrange + 7);
        ellipse->SetLineWidth(3);
    }

    twoSigma.SetLineStyle(2);
    oneSigma.Draw("SAME");
    twoSigma.Draw("SAME");

    TMarker fittedMarker{result.centerUDegree, result.centerVDegree, 34};
    fittedMarker.SetMarkerColor(kOrange + 7);
    fittedMarker.SetMarkerSize(2.1);
    fittedMarker.Draw("SAME");

    TMarker truthMarker{result.truthUDegree, result.truthVDegree, 29};
    truthMarker.SetMarkerColor(kRed + 1);
    truthMarker.SetMarkerSize(2.2);

    if (config.showTruthMarkers() && result.truthInsideLocalView)
    {
        truthMarker.Draw("SAME");
    }

    TLegend legend{0.13, 0.73, 0.40, 0.89};
    legend.SetBorderSize(1);
    legend.SetFillColorAlpha(kWhite, 0.90);
    legend.AddEntry(&fittedMarker, "Fitted direction", "P");
    legend.AddEntry(&oneSigma, "1#sigma ellipse", "L");
    legend.AddEntry(&twoSigma, "2#sigma ellipse", "L");

    if (config.showTruthMarkers() && result.truthInsideLocalView)
    {
        legend.AddEntry(&truthMarker, "Truth direction", "P");
    }

    legend.Draw();

    TPaveText metrics{0.55, 0.64, 0.86, 0.89, "NDC"};
    metrics.SetBorderSize(1);
    metrics.SetFillColorAlpha(kWhite, 0.90);
    metrics.SetTextAlign(12);
    metrics.SetTextSize(0.029);
    std::ostringstream line;
    line << std::fixed << std::setprecision(3)
         << "theta = " << result.fittedThetaDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "phi = " << result.fittedPhiDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "angular bias = " << result.angularBiasDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "sigma major/minor = "
         << result.sigmaMajorDegree << " / "
         << result.sigmaMinorDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "Nside = " << result.healpixNside
         << ", pixel scale = " << result.pixelScaleDegree << " deg";
    metrics.AddText(line.str().c_str());

    if (result.underResolved)
    {
        metrics.AddText("WARNING: fitted width is below pixel scale");
    }

    if (!result.fitConverged)
    {
        metrics.AddText("WARNING: ROOT fit failed; showing moment fallback");
    }

    if (config.showTruthMarkers() && !result.truthInsideLocalView)
    {
        metrics.AddText("WARNING: truth lies outside local fit view");
    }

    metrics.Draw();
    canvas.Modified();
    canvas.Update();
    const std::filesystem::path outputPath =
        config.outputDirectory() / "direction_fit.png";
    canvas.SaveAs(outputPath.string().c_str());
}
