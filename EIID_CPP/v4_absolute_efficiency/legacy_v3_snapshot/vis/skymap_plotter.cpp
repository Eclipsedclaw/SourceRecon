#include "skymap_plotter.h"

#include "plot_utils.h"

#include <TCanvas.h>
#include <TColor.h>
#include <TH2D.h>
#include <TLegend.h>
#include <TMarker.h>
#include <TStyle.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <sstream>
#include <vector>

std::string SkymapPlotter::name() const
{
    return "skymap";
}

void SkymapPlotter::plot(const ReconstructionData& data, const VisConfig& config) const
{
    const std::vector<SkyPixel> pixels = marginalizeDirections(data);
    const std::size_t nside = inferHealpixNside(pixels.size());

    // 这里的 TH2D 只是全天球展示画布，不改变原始 HEALPix 权重。
    // 分箱数随 Nside 自动增长，因此更换网格分辨率时不需要修改绘图代码。
    const int longitudeBins = nside > 0
        ? std::max(36, static_cast<int>(6 * nside))
        : 72;

    const int latitudeBins = nside > 0
        ? std::max(18, static_cast<int>(3 * nside))
        : 36;

    TH2D skymap{
        "eiid_skymap",
        "EIID skymap centred on camera front (-Z);Camera-centred longitude (degree);Camera-centred latitude (degree);Marginal intensity",
        longitudeBins,
        -180.0,
        180.0,
        latitudeBins,
        -90.0,
        90.0
    };

    skymap.SetDirectory(nullptr);
    skymap.SetStats(false);

    for (const SkyPixel& pixel : pixels)
    {
        const DisplayCoordinate coordinate = cameraCenteredCoordinate(
            pixel.directionX,
            pixel.directionY,
            pixel.directionZ
        );

        skymap.Fill(
            coordinate.longitudeDegree,
            coordinate.latitudeDegree,
            pixel.weight
        );
    }

    TCanvas canvas{"skymap_canvas", "EIID skymap", 1400, 800};
    canvas.SetLeftMargin(0.09);
    canvas.SetRightMargin(0.14);
    canvas.SetBottomMargin(0.12);
    canvas.SetGrid();

    gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(255);

    skymap.Draw("COLZ");

    if (config.showTruthMarkers())
    {
        const std::array<double, 3> trueDirection = truthDirection(config.truth());
        const DisplayCoordinate truthCoordinate = cameraCenteredCoordinate(
            trueDirection[0],
            trueDirection[1],
            trueDirection[2]
        );

        TMarker truthMarker{
            truthCoordinate.longitudeDegree,
            truthCoordinate.latitudeDegree,
            29
        };

        truthMarker.SetMarkerColor(kRed + 1);
        truthMarker.SetMarkerSize(2.6);
        truthMarker.Draw("SAME");

        std::ostringstream label;
        label << "Truth: theta=" << config.truth().thetaDegree
              << " deg, phi=" << config.truth().phiDegree << " deg";

        TLegend legend{0.12, 0.82, 0.42, 0.90};
        legend.SetBorderSize(0);
        legend.SetFillStyle(0);
        legend.AddEntry(&truthMarker, label.str().c_str(), "P");
        legend.Draw();

        canvas.Modified();
        canvas.Update();

        const std::filesystem::path outputPath =
            config.outputDirectory() / "skymap.png";

        canvas.SaveAs(outputPath.string().c_str());
        return;
    }

    canvas.Modified();
    canvas.Update();

    const std::filesystem::path outputPath =
        config.outputDirectory() / "skymap.png";

    canvas.SaveAs(outputPath.string().c_str());
}
