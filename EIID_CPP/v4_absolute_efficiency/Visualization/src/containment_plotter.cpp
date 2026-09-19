#include "containment_plotter.h"

#include "plot_utils.h"

#include <TAxis.h>
#include <TCanvas.h>
#include <TColor.h>
#include <TGraph.h>
#include <TLegend.h>
#include <TLine.h>

#include <algorithm>
#include <array>
#include <filesystem>
#include <iomanip>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace
{
struct AngularWeight
{
    double angleDegree;
    double weight;
};

double containmentRadius(
    const std::vector<AngularWeight>& angularWeights,
    double totalWeight,
    double targetFraction
)
{
    double cumulativeWeight = 0.0;

    for (const AngularWeight& point : angularWeights)
    {
        cumulativeWeight += point.weight;

        if (cumulativeWeight / totalWeight >= targetFraction)
        {
            return point.angleDegree;
        }
    }

    return angularWeights.back().angleDegree;
}
}

std::string ContainmentPlotter::name() const
{
    return "containment";
}

void ContainmentPlotter::plot(
    const ReconstructionData& data,
    const VisConfig& config
) const
{
    const std::vector<SkyPixel> pixels = marginalizeDirections(data);
    const std::array<double, 3> trueDirection = truthDirection(config.truth());

    std::vector<AngularWeight> angularWeights;
    angularWeights.reserve(pixels.size());

    for (const SkyPixel& pixel : pixels)
    {
        if (pixel.weight < 0.0)
        {
            throw std::runtime_error{"Containment requires non-negative reconstructed weights."};
        }

        angularWeights.push_back(
            AngularWeight{
                angularSeparationDegree(pixel, trueDirection),
                pixel.weight
            }
        );
    }

    std::sort(
        angularWeights.begin(),
        angularWeights.end(),
        [](const AngularWeight& left, const AngularWeight& right)
        {
            return left.angleDegree < right.angleDegree;
        }
    );

    const double totalWeight = std::accumulate(
        angularWeights.begin(),
        angularWeights.end(),
        0.0,
        [](double sum, const AngularWeight& point)
        {
            return sum + point.weight;
        }
    );

    if (!(totalWeight > 0.0))
    {
        throw std::runtime_error{"Containment requires a positive total reconstructed weight."};
    }

    std::vector<double> angles;
    std::vector<double> fractions;
    angles.reserve(angularWeights.size() + 1);
    fractions.reserve(angularWeights.size() + 1);

    angles.push_back(0.0);
    fractions.push_back(0.0);

    double cumulativeWeight = 0.0;

    for (const AngularWeight& point : angularWeights)
    {
        cumulativeWeight += point.weight;
        angles.push_back(point.angleDegree);
        fractions.push_back(cumulativeWeight / totalWeight);
    }

    const double r50 = containmentRadius(angularWeights, totalWeight, 0.50);
    const double r68 = containmentRadius(angularWeights, totalWeight, 0.68);
    const double r90 = containmentRadius(angularWeights, totalWeight, 0.90);

    const std::size_t nside = inferHealpixNside(pixels.size());
    const double pixelScaleDegree = meanHealpixPixelScaleDegree(pixels.size());

    std::ostringstream title;
    title << "Directional containment"
          << " (HEALPix Nside=" << nside
          << ", mean pixel scale ~ "
          << std::fixed << std::setprecision(2)
          << pixelScaleDegree << " deg)"
          << ";Angular distance from truth (degree)"
          << ";Cumulative intensity fraction";

    TGraph graph{
        static_cast<int>(angles.size()),
        angles.data(),
        fractions.data()
    };

    graph.SetName("eiid_containment");
    graph.SetTitle(title.str().c_str());
    graph.SetLineColor(kAzure + 2);
    graph.SetLineWidth(3);
    graph.SetMarkerColor(kAzure + 2);
    graph.SetMarkerStyle(20);
    graph.SetMarkerSize(0.55);
    graph.SetMinimum(0.0);
    graph.SetMaximum(1.05);

    TCanvas canvas{"containment_canvas", "EIID containment", 1100, 760};
    canvas.SetLeftMargin(0.12);
    canvas.SetRightMargin(0.05);
    canvas.SetBottomMargin(0.12);
    canvas.SetGrid();

    graph.Draw("ALP");
    graph.GetXaxis()->SetLimits(0.0, 180.0);

    TLine r50Line{r50, 0.0, r50, 1.0};
    TLine r68Line{r68, 0.0, r68, 1.0};
    TLine r90Line{r90, 0.0, r90, 1.0};

    r50Line.SetLineColor(kOrange + 7);
    r68Line.SetLineColor(kGreen + 2);
    r90Line.SetLineColor(kMagenta + 1);

    for (TLine* line : {&r50Line, &r68Line, &r90Line})
    {
        line->SetLineStyle(2);
        line->SetLineWidth(2);
        line->Draw("SAME");
    }

    std::ostringstream gridLabel;
    gridLabel << "GRID WARNING: Nside=" << nside
              << ", mean pixel scale ~ "
              << std::fixed << std::setprecision(2)
              << pixelScaleDegree << " deg";

    std::ostringstream r50Label;
    std::ostringstream r68Label;
    std::ostringstream r90Label;

    r50Label << "R50 = " << std::fixed << std::setprecision(2) << r50 << " deg";
    r68Label << "R68 = " << std::fixed << std::setprecision(2) << r68 << " deg";
    r90Label << "R90 = " << std::fixed << std::setprecision(2) << r90 << " deg";

    TLegend legend{0.48, 0.18, 0.90, 0.40};
    legend.SetHeader(gridLabel.str().c_str(), "C");
    legend.SetBorderSize(1);
    legend.SetFillColorAlpha(kWhite, 0.90);
    legend.AddEntry(&r50Line, r50Label.str().c_str(), "L");
    legend.AddEntry(&r68Line, r68Label.str().c_str(), "L");
    legend.AddEntry(&r90Line, r90Label.str().c_str(), "L");
    legend.Draw();

    canvas.Modified();
    canvas.Update();

    const std::filesystem::path outputPath =
        config.outputDirectory() / "containment.png";

    canvas.SaveAs(outputPath.string().c_str());
}
