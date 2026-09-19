#include "direction_metrics_plotter.h"

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
#include <memory>
#include <sstream>
#include <stdexcept>
#include <utility>

DirectionMetricsPlotter::DirectionMetricsPlotter(
    std::shared_ptr<const QualityAnalysisResult> analysis
)
    : analysis_{std::move(analysis)}
{
    if (!analysis_)
    {
        throw std::invalid_argument{
            "DirectionMetricsPlotter requires quality analysis."
        };
    }
}

std::string DirectionMetricsPlotter::name() const
{
    return "model-independent direction metrics";
}

void DirectionMetricsPlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    static_cast<void>(data);
    const DirectionMetrics& result = analysis_->direction;
    const int bins = std::max(
        20,
        static_cast<int>(std::ceil(
            2.0 * result.localRadiusDegree / result.pixelScaleDegree
        ))
    );
    TH2D histogram{
        "v7_local_direction_metrics",
        "Model-independent local direction metrics;Local tangent u (degree);Local tangent v (degree);Intensity",
        bins,
        -result.localRadiusDegree,
        result.localRadiusDegree,
        bins,
        -result.localRadiusDegree,
        result.localRadiusDegree
    };
    histogram.SetDirectory(nullptr);
    histogram.SetStats(false);

    for (const LocalDirectionPoint& point : result.points)
    {
        histogram.Fill(point.uDegree, point.vDegree, point.weight);
    }

    TCanvas canvas{"v7_direction_metrics_canvas", "Direction metrics", 1250, 900};
    canvas.SetLeftMargin(0.10);
    canvas.SetRightMargin(0.16);
    canvas.SetBottomMargin(0.11);
    canvas.SetGrid();
    gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(255);
    histogram.Draw("COLZ");

    TEllipse oneRms{
        result.centroidUDegree,
        result.centroidVDegree,
        result.rmsMajorDegree,
        result.rmsMinorDegree,
        0.0,
        360.0,
        result.ellipseAngleDegree
    };
    TEllipse twoRms{
        result.centroidUDegree,
        result.centroidVDegree,
        2.0 * result.rmsMajorDegree,
        2.0 * result.rmsMinorDegree,
        0.0,
        360.0,
        result.ellipseAngleDegree
    };

    for (TEllipse* ellipse : {&oneRms, &twoRms})
    {
        ellipse->SetFillStyle(0);
        ellipse->SetLineColor(kOrange + 7);
        ellipse->SetLineWidth(3);
    }

    twoRms.SetLineStyle(2);
    oneRms.Draw("SAME");
    twoRms.Draw("SAME");

    TMarker centroidMarker{
        result.centroidUDegree,
        result.centroidVDegree,
        34
    };
    centroidMarker.SetMarkerColor(kOrange + 7);
    centroidMarker.SetMarkerSize(2.1);
    centroidMarker.Draw("SAME");

    TMarker truthMarker{result.truthUDegree, result.truthVDegree, 29};
    truthMarker.SetMarkerColor(kRed + 1);
    truthMarker.SetMarkerSize(2.2);

    if (config.showTruthMarkers() && result.truthInsideLocalView)
    {
        truthMarker.Draw("SAME");
    }

    std::unique_ptr<TEllipse> gaussianEllipse;

    if (result.gaussian.converged)
    {
        gaussianEllipse = std::make_unique<TEllipse>(
            result.gaussian.centerUDegree,
            result.gaussian.centerVDegree,
            result.gaussian.sigmaMajorDegree,
            result.gaussian.sigmaMinorDegree,
            0.0,
            360.0,
            result.gaussian.ellipseAngleDegree
        );
        gaussianEllipse->SetFillStyle(0);
        gaussianEllipse->SetLineColor(kCyan + 2);
        gaussianEllipse->SetLineStyle(3);
        gaussianEllipse->SetLineWidth(3);
        gaussianEllipse->Draw("SAME");
    }

    TLegend legend{0.12, 0.70, 0.39, 0.89};
    legend.SetBorderSize(1);
    legend.SetFillColorAlpha(kWhite, 0.92);
    legend.AddEntry(&centroidMarker, "Weighted centroid", "P");
    legend.AddEntry(&oneRms, "1 RMS covariance ellipse", "L");
    legend.AddEntry(&twoRms, "2 RMS covariance ellipse", "L");

    if (result.gaussian.converged)
    {
        legend.AddEntry(
            gaussianEllipse.get(),
            "Optional Gaussian ellipse",
            "L"
        );
    }

    if (config.showTruthMarkers() && result.truthInsideLocalView)
    {
        legend.AddEntry(&truthMarker, "Truth direction", "P");
    }

    legend.Draw();

    TPaveText metrics{0.50, 0.62, 0.84, 0.89, "NDC"};
    metrics.SetBorderSize(1);
    metrics.SetFillColorAlpha(kWhite, 0.92);
    metrics.SetTextAlign(12);
    metrics.SetTextSize(0.027);
    std::ostringstream line;
    line << std::fixed << std::setprecision(3)
         << "centroid theta = " << result.centroidThetaDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "centroid phi = " << result.centroidPhiDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "angular bias = " << result.angularBiasDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "RMS major/minor = "
         << result.rmsMajorDegree << " / "
         << result.rmsMinorDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "Nside = " << result.healpixNside
         << ", pixel scale = " << result.pixelScaleDegree << " deg";
    metrics.AddText(line.str().c_str());
    line.str("");
    line.clear();
    line << "energy gate = [" << result.energyGateLowMeV
         << ", " << result.energyGateHighMeV << "] MeV";
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

    if (result.underResolved)
    {
        metrics.AddText("CAUTION: minor RMS is below the HEALPix pixel scale");
    }

    if (config.showTruthMarkers() && !result.truthInsideLocalView)
    {
        metrics.AddText("CAUTION: truth lies outside this local view");
    }

    metrics.Draw();
    canvas.Modified();
    canvas.Update();
    const std::filesystem::path outputPath =
        config.outputDirectory() / "direction_resolution.png";
    canvas.SaveAs(outputPath.string().c_str());
}
