#include <RtypesCore.h>
#include <TBox.h>
#include <TCanvas.h>
#include <TColor.h>
#include <TFile.h>
#include <TGraph.h>
#include <TH2D.h>
#include <TLatex.h>
#include <TLine.h>
#include <TNamed.h>
#include <TPad.h>
#include <TParameter.h>
#include <TROOT.h>
#include <TStyle.h>
#include <TSystem.h>
#include <TString.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
constexpr double PI = 3.141592653589793238462643383279502884;

void saveFigure(TCanvas& canvas, const std::string& pngPath)
{
    canvas.SaveAs(pngPath.c_str());
    if (pngPath.size() >= 4 && pngPath.substr(pngPath.size() - 4) == ".png")
        canvas.SaveAs((pngPath.substr(0, pngPath.size() - 4) + ".pdf").c_str());
}

struct EfficiencyMetadata
{
    int nside{};
    std::size_t directionCount{};
    std::size_t energyCount{};
    double energyMinMeV{};
    double energyMaxMeV{};
};

struct EnergyInterpolation
{
    std::size_t lowerIndex{};
    std::size_t upperIndex{};
    double lowerEnergyMeV{};
    double upperEnergyMeV{};
    double upperWeight{};
};

struct AitoffCoordinate
{
    double x{};
    double y{};
};

AitoffCoordinate projectAitoff(double longitudeDegree, double latitudeDegree)
{
    // 与 ROOT THistPainter::ProjectAitoff2xy() 使用同一个 Hammer-Aitoff 公式。
    const double halfLongitude = 0.5 * longitudeDegree * PI / 180.0;
    const double latitude = latitudeDegree * PI / 180.0;
    const double squareRootTwo = std::sqrt(2.0);
    const double scale = 2.0 * squareRootTwo / PI;
    const double cosineLatitude = std::cos(latitude);
    const double denominator = std::sqrt(
        1.0 + cosineLatitude * std::cos(halfLongitude)
    );
    double x = cosineLatitude * std::sin(halfLongitude) *
        2.0 * squareRootTwo / denominator;
    double y = std::sin(latitude) * squareRootTwo / denominator;

    x *= (180.0 / PI) / scale;
    y *= (180.0 / PI) / scale;
    return AitoffCoordinate{x, y};
}

template <typename T>
const T& requireObject(TFile& file, const char* objectName)
{
    const T* object = file.Get<T>(objectName);

    if (object == nullptr)
    {
        throw std::runtime_error{
            "Cannot find required ROOT object: " + std::string{objectName}
        };
    }

    return *object;
}

std::uint64_t angleToRingPixel(int nside, double theta, double phi)
{
    // 这是 HEALPix RING ordering 的标准 ang2pix 关系。
    // 小工具直接实现这段几何换算，因此运行时只需要 ROOT，不需要再链接 healpix_cxx。
    const std::uint64_t nside64 = static_cast<std::uint64_t>(nside);
    const std::uint64_t pixelCount = 12ULL * nside64 * nside64;
    const std::uint64_t northCapCount = 2ULL * nside64 * (nside64 - 1ULL);
    const std::uint64_t pixelsPerRing = 4ULL * nside64;

    const double z = std::cos(theta);
    const double absoluteZ = std::abs(z);

    phi = std::fmod(phi, 2.0 * PI);

    if (phi < 0.0)
    {
        phi += 2.0 * PI;
    }

    const double tt = phi / (0.5 * PI);

    if (absoluteZ <= 2.0 / 3.0)
    {
        const double ascending = static_cast<double>(nside) * (0.5 + tt - 0.75 * z);
        const double descending = static_cast<double>(nside) * (0.5 + tt + 0.75 * z);
        const std::int64_t jp = static_cast<std::int64_t>(std::floor(ascending));
        const std::int64_t jm = static_cast<std::int64_t>(std::floor(descending));
        const std::int64_t ring = static_cast<std::int64_t>(nside) + 1 + jp - jm;
        const std::int64_t shift = 1 - (ring & 1);
        std::int64_t pixelInRing =
            (jp + jm - static_cast<std::int64_t>(nside) + shift + 1) / 2 + 1;

        if (pixelInRing > static_cast<std::int64_t>(pixelsPerRing))
        {
            pixelInRing -= static_cast<std::int64_t>(pixelsPerRing);
        }

        if (pixelInRing < 1)
        {
            pixelInRing += static_cast<std::int64_t>(pixelsPerRing);
        }

        return northCapCount +
            static_cast<std::uint64_t>(ring - 1) * pixelsPerRing +
            static_cast<std::uint64_t>(pixelInRing - 1);
    }

    const double sectorPosition = tt - std::floor(tt);
    const double polarScale = static_cast<double>(nside) *
        std::sqrt(3.0 * (1.0 - absoluteZ));
    const std::int64_t jp = static_cast<std::int64_t>(
        std::floor(sectorPosition * polarScale)
    );
    const std::int64_t jm = static_cast<std::int64_t>(
        std::floor((1.0 - sectorPosition) * polarScale)
    );
    const std::int64_t ring = jp + jm + 1;
    std::int64_t pixelInRing = static_cast<std::int64_t>(
        std::floor(tt * static_cast<double>(ring))
    ) + 1;

    if (pixelInRing > 4 * ring)
    {
        pixelInRing -= 4 * ring;
    }

    if (z > 0.0)
    {
        return static_cast<std::uint64_t>(
            2 * ring * (ring - 1) + pixelInRing - 1
        );
    }

    return pixelCount - static_cast<std::uint64_t>(
        2 * ring * (ring + 1) - pixelInRing + 1
    );
}

EnergyInterpolation makeEnergyInterpolation(
    const EfficiencyMetadata& metadata,
    double targetEnergyMeV
)
{
    if (metadata.energyCount == 0)
    {
        throw std::runtime_error{"The efficiency file contains no energy points."};
    }

    if (targetEnergyMeV < metadata.energyMinMeV ||
        targetEnergyMeV > metadata.energyMaxMeV)
    {
        throw std::runtime_error{"The requested energy is outside the efficiency grid."};
    }

    if (metadata.energyCount == 1)
    {
        return EnergyInterpolation{
            0,
            0,
            metadata.energyMinMeV,
            metadata.energyMinMeV,
            0.0
        };
    }

    const double spacing = (metadata.energyMaxMeV - metadata.energyMinMeV) /
        static_cast<double>(metadata.energyCount - 1);
    const double floatingIndex = (targetEnergyMeV - metadata.energyMinMeV) / spacing;
    const std::size_t lowerIndex = std::min(
        static_cast<std::size_t>(std::floor(floatingIndex)),
        metadata.energyCount - 1
    );
    const std::size_t upperIndex = std::min(
        lowerIndex + 1,
        metadata.energyCount - 1
    );
    const double lowerEnergyMeV = metadata.energyMinMeV +
        spacing * static_cast<double>(lowerIndex);
    const double upperEnergyMeV = metadata.energyMinMeV +
        spacing * static_cast<double>(upperIndex);
    const double upperWeight = upperIndex == lowerIndex
        ? 0.0
        : (targetEnergyMeV - lowerEnergyMeV) /
            (upperEnergyMeV - lowerEnergyMeV);

    return EnergyInterpolation{
        lowerIndex,
        upperIndex,
        lowerEnergyMeV,
        upperEnergyMeV,
        std::clamp(upperWeight, 0.0, 1.0)
    };
}

std::string energyTag(double energyMeV)
{
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(3) << energyMeV;
    std::string tag = stream.str();
    std::replace(tag.begin(), tag.end(), '.', 'p');
    return tag;
}

void drawMap(
    TH2D& map,
    const EfficiencyMetadata& metadata,
    const EnergyInterpolation& interpolation,
    double targetEnergyMeV,
    double minimumPositive,
    double maximum,
    const std::string& outputPath,
    bool frontHemisphereOnly,
    bool logarithmic
)
{
    const bool hasPositiveValues = maximum > 0.0;
    const bool useLogarithmicScale = logarithmic && hasPositiveValues;
    TCanvas canvas{
        logarithmic ? "efficiency_log_canvas" : "efficiency_linear_canvas",
        "Raw absolute efficiency quick-look",
        1500,
        850
    };

    canvas.SetLeftMargin(0.09);
    canvas.SetRightMargin(0.16);
    canvas.SetBottomMargin(0.12);
    canvas.SetTopMargin(0.18);
    canvas.SetLogz(useLogarithmicScale);

    // 全零也必须能画：只画坐标框和未模拟区域，保留白色的零值区域。
    // 1.0 仅是空框的显示范围，不写入任何像素，也不显示虚构的效率色标。
    map.SetMinimum(useLogarithmicScale ? minimumPositive : 0.0);
    const double displayMaximum = useLogarithmicScale && maximum <= minimumPositive ? maximum * 10.0 : maximum;
    map.SetMaximum(hasPositiveValues ? displayMaximum : 1.0);
    map.GetZaxis()->SetMoreLogLabels(true);
    map.GetZaxis()->SetLabelSize(0.030);
    map.GetZaxis()->SetTitleSize(0.034);
    map.GetZaxis()->SetTitleOffset(1.45);
    map.Draw(hasPositiveValues ? "COLZ" : "AXIS");

    // 前半球模拟使用 z <= 0。投影后，它对应图中央的 |longitude| <= 90 度。
    // 灰色区域明确表示“没有模拟”，而不是把它误画成物理效率等于零。
    TBox leftMask{-180.0, -90.0, -90.0, 90.0};
    TBox rightMask{90.0, -90.0, 180.0, 90.0};

    if (frontHemisphereOnly)
    {
        leftMask.SetFillColorAlpha(kGray + 1, 0.72);
        rightMask.SetFillColorAlpha(kGray + 1, 0.72);
        leftMask.SetLineColor(kGray + 2);
        rightMask.SetLineColor(kGray + 2);
        leftMask.Draw("SAME");
        rightMask.Draw("SAME");
    }

    TLine leftBoundary{-90.0, -90.0, -90.0, 90.0};
    TLine rightBoundary{90.0, -90.0, 90.0, 90.0};

    if (frontHemisphereOnly)
    {
        leftBoundary.SetLineStyle(2);
        rightBoundary.SetLineStyle(2);
        leftBoundary.SetLineColor(kGray + 3);
        rightBoundary.SetLineColor(kGray + 3);
        leftBoundary.Draw("SAME");
        rightBoundary.Draw("SAME");
    }

    TLatex text;
    text.SetNDC(true);
    text.SetTextAlign(22);
    text.SetTextSize(0.040);
    text.SetTextColor(kBlack);
    text.DrawLatex(0.50, 0.965, "Raw absolute detection efficiency (no pseudo-count)");

    text.SetTextAlign(12);
    text.SetTextSize(0.029);
    text.DrawLatex(
        0.11,
        0.925,
        Form(
            "E = %.3f MeV; HEALPix Nside = %d; camera front (-Z) at map centre",
            targetEnergyMeV,
            metadata.nside
        )
    );

    text.SetTextSize(0.025);

    if (interpolation.lowerIndex == interpolation.upperIndex)
    {
        text.DrawLatex(
            0.11,
            0.885,
            Form("Exact energy layer: %.6f MeV", interpolation.lowerEnergyMeV)
        );
    }
    else
    {
        text.DrawLatex(
            0.11,
            0.885,
            Form(
                "Linear interpolation: %.6f MeV (%.4f) + %.6f MeV (%.4f)",
                interpolation.lowerEnergyMeV,
                1.0 - interpolation.upperWeight,
                interpolation.upperEnergyMeV,
                interpolation.upperWeight
            )
        );
    }

    if (frontHemisphereOnly)
    {
        text.SetTextColor(kGray + 3);
        text.SetTextAlign(22);
        text.DrawLatex(0.19, 0.50, "not simulated");
        text.DrawLatex(0.75, 0.50, "not simulated");
    }

    if (!hasPositiveValues)
    {
        text.SetTextAlign(12);
        text.SetTextColor(kRed + 1);
        text.DrawLatex(0.11, 0.845, "All simulated pixels = 0; logarithmic scale is undefined.");
    }
    else if (logarithmic)
    {
        text.SetTextAlign(12);
        text.SetTextColor(kBlack);
        text.DrawLatex(0.11, 0.845, "Unpainted active bins: raw efficiency exactly zero");
    }

    canvas.Modified();
    canvas.Update();
    saveFigure(canvas, outputPath);
}

void drawAitoffSkyMap(
    TH2D& map,
    const EfficiencyMetadata& metadata,
    const EnergyInterpolation& interpolation,
    double targetEnergyMeV,
    double minimumPositive,
    double maximum,
    const std::string& outputPath,
    bool frontHemisphereOnly
)
{
    const bool hasPositiveValues = maximum > 0.0;
    TCanvas canvas{
        "raw_efficiency_aitoff_canvas",
        "Raw absolute efficiency Aitoff skymap",
        1500,
        900
    };

    TPad mapPad{"efficiency_aitoff_map_pad", "", 0.0, 0.0, 0.86, 1.0};
    mapPad.SetLeftMargin(0.115);
    mapPad.SetRightMargin(0.02);
    mapPad.SetBottomMargin(0.10);
    mapPad.SetTopMargin(0.18);
    // 像素内容在下面已经取过 log10，这里不能再开启第二次对数变换。
    mapPad.SetLogz(false);
    mapPad.Draw();
    mapPad.cd();

    // Do not use TH2::Draw("AITOFF") here. ROOT implements that option as a
    // filled-contour projection, so it does not necessarily preserve COLZ
    // colour levels. Every display pixel is instead inverse-projected to the
    // same longitude-latitude map used by the rectangular figure.
    TH2D frame{
        "raw_efficiency_aitoff_frame",
        ";Projected camera-centred longitude (degree);Projected latitude (degree)",
        360,
        -180.0,
        180.0,
        180,
        -90.0,
        90.0
    };
    frame.SetDirectory(nullptr);
    frame.SetStats(false);
    frame.Draw("AXIS");

    constexpr int boundarySamples = 361;
    TGraph skyBoundary{boundarySamples};

    for (int index = 0; index < boundarySamples; ++index)
    {
        const double angle = 2.0 * PI * static_cast<double>(index) /
            static_cast<double>(boundarySamples - 1);
        skyBoundary.SetPoint(index, 180.0 * std::cos(angle), 90.0 * std::sin(angle));
    }

    skyBoundary.SetFillColor(frontHemisphereOnly ? kGray + 1 : kWhite);
    skyBoundary.SetLineColor(kGray + 2);
    skyBoundary.Draw("F SAME");
    skyBoundary.Draw("L SAME");

    // The simulated z <= 0 hemisphere is the central lens bounded by
    // longitude = -90 and +90 degrees. White inside that lens means a real
    // raw zero (k == 0); gray means that the direction was not simulated.
    TGraph activeHemisphere{2 * boundarySamples + 1};

    for (int index = 0; index < boundarySamples; ++index)
    {
        const double latitude = -90.0 + 180.0 * static_cast<double>(index) /
            static_cast<double>(boundarySamples - 1);
        const AitoffCoordinate point = projectAitoff(-90.0, latitude);
        activeHemisphere.SetPoint(index, point.x, point.y);
    }

    for (int index = 0; index < boundarySamples; ++index)
    {
        const double latitude = 90.0 - 180.0 * static_cast<double>(index) /
            static_cast<double>(boundarySamples - 1);
        const AitoffCoordinate point = projectAitoff(90.0, latitude);
        activeHemisphere.SetPoint(boundarySamples + index, point.x, point.y);
    }

    double firstX{};
    double firstY{};
    activeHemisphere.GetPoint(0, firstX, firstY);
    activeHemisphere.SetPoint(2 * boundarySamples, firstX, firstY);
    activeHemisphere.SetFillColor(kWhite);
    activeHemisphere.SetLineColor(kGray + 2);

    if (frontHemisphereOnly)
    {
        activeHemisphere.Draw("F SAME");
        activeHemisphere.Draw("L SAME");
    }

    TH2D projected{
        "raw_efficiency_aitoff_raster",
        "",
        720,
        -180.0,
        180.0,
        360,
        -90.0,
        90.0
    };
    projected.SetDirectory(nullptr);
    projected.SetStats(false);

    // 与矩形对数图使用同一效率范围。若所有正值相同，只扩展显示上限，
    // 不改变效率数据；右侧手画的色标也必须使用这个显示上限。
    const double displayMaximum = hasPositiveValues && maximum <= minimumPositive ? maximum * 10.0 : maximum;
    // 全零时不取 log(0)；下面仍可绘制白色的有效半球和灰色未模拟区。
    const double logarithmicMinimum = hasPositiveValues ? std::log10(minimumPositive) : 0.0;
    const double logarithmicMaximum = hasPositiveValues ? std::log10(displayMaximum) : 1.0;
    const double logarithmicRange = std::max(
        logarithmicMaximum - logarithmicMinimum,
        1.0e-12
    );

    for (int xBin = 1; xBin <= projected.GetNbinsX(); ++xBin)
    {
        const double projectedX = projected.GetXaxis()->GetBinCenter(xBin);

        for (int yBin = 1; yBin <= projected.GetNbinsY(); ++yBin)
        {
            const double projectedY = projected.GetYaxis()->GetBinCenter(yBin);
            const double ellipse =
                projectedX * projectedX / (180.0 * 180.0) +
                projectedY * projectedY / (90.0 * 90.0);

            if (ellipse > 1.0)
            {
                continue;
            }

            const double hammerX = projectedX * std::sqrt(2.0) / 90.0;
            const double hammerY = projectedY * std::sqrt(2.0) / 90.0;
            const double inverseFactor = std::sqrt(std::max(
                0.0,
                1.0 - hammerX * hammerX / 16.0 - hammerY * hammerY / 4.0
            ));
            const double longitude = 2.0 * std::atan2(
                inverseFactor * hammerX,
                2.0 * (2.0 * inverseFactor * inverseFactor - 1.0)
            );
            const double latitude = std::asin(std::clamp(
                inverseFactor * hammerY,
                -1.0,
                1.0
            ));
            const double physicalZ = -std::cos(latitude) * std::cos(longitude);

            if (frontHemisphereOnly && physicalZ > 0.0)
            {
                continue;
            }

            const int longitudeBin = map.GetXaxis()->FindBin(longitude * 180.0 / PI);
            const int latitudeBin = map.GetYaxis()->FindBin(latitude * 180.0 / PI);
            const double value = map.GetBinContent(longitudeBin, latitudeBin);

            if (value <= 0.0)
            {
                continue;
            }

            // Shift log10(efficiency) above zero so COL1 can leave raw-zero
            // bins unpainted while preserving an exact logarithmic palette.
            projected.SetBinContent(
                xBin,
                yBin,
                1.0 + std::log10(value) - logarithmicMinimum
            );
        }
    }

    projected.SetMinimum(1.0);
    projected.SetMaximum(1.0 + logarithmicRange);
    projected.SetContour(255);
    if (hasPositiveValues)
    {
        // SAME 会沿用前面空 frame 的 Z 范围，导致不同效率挤成同一种颜色。
        // SAME0 仍叠加到原坐标框，但使用 projected 自己的颜色范围。
        // COL1 保留零值区域不着色；这只修复显示，不修改任何 ROOT 数据。
        projected.Draw("COL1 SAME0");
    }
    skyBoundary.Draw("L SAME");
    frame.Draw("AXIS SAME");

    TLatex text;
    text.SetNDC(true);
    text.SetTextAlign(22);
    text.SetTextSize(0.040);
    text.DrawLatex(0.48, 0.965, "Raw absolute-efficiency skymap (Hammer-Aitoff)");

    text.SetTextAlign(12);
    text.SetTextSize(0.028);
    text.DrawLatex(
        0.09,
        0.925,
        Form(
            "E = %.3f MeV; HEALPix Nside = %d; camera front (-Z) at map centre",
            targetEnergyMeV,
            metadata.nside
        )
    );

    text.SetTextSize(0.024);

    if (interpolation.lowerIndex == interpolation.upperIndex)
    {
        text.DrawLatex(
            0.09,
            0.888,
            Form("Exact energy layer: %.6f MeV", interpolation.lowerEnergyMeV)
        );
    }
    else
    {
        text.DrawLatex(
            0.09,
            0.888,
            Form(
                "Interpolated from %.6f MeV and %.6f MeV",
                interpolation.lowerEnergyMeV,
                interpolation.upperEnergyMeV
            )
        );
    }

    if (frontHemisphereOnly)
    {
        text.SetTextAlign(32);
        text.SetTextColor(kGray + 2);
        text.DrawLatex(0.88, 0.888, "Rear hemisphere not simulated");
    }

    text.SetTextAlign(12);
    text.SetTextColor(kBlack);
    if (hasPositiveValues)
    {
        text.DrawLatex(0.09, 0.852, "White active pixels: raw efficiency exactly zero");
    }
    else
    {
        text.SetTextColor(kRed + 1);
        text.DrawLatex(0.09, 0.852, "All simulated pixels = 0; logarithmic scale is undefined.");
        // 没有正值时不画对数色标；依然输出可读的 skymap。
        canvas.Modified();
        canvas.Update();
        saveFigure(canvas, outputPath);
        return;
    }

    // AITOFF 本身不会稳定地产生可用的 Z 色条，所以在右侧独立画一个
    // 与对数调色完全一致的小色标。这仍然全部使用 ROOT 图元。
    canvas.cd();
    TPad palettePad{"efficiency_aitoff_palette_pad", "", 0.86, 0.16, 0.995, 0.82};
    palettePad.SetMargin(0.0, 0.0, 0.0, 0.0);
    palettePad.Draw();
    palettePad.cd();
    palettePad.Range(0.0, 0.0, 1.0, 1.0);

    const int paletteColors = std::max(2, gStyle->GetNumberOfColors());
    std::vector<std::unique_ptr<TBox>> colorBoxes;
    colorBoxes.reserve(static_cast<std::size_t>(paletteColors));

    for (int index = 0; index < paletteColors; ++index)
    {
        const double low = static_cast<double>(index) /
            static_cast<double>(paletteColors);
        const double high = static_cast<double>(index + 1) /
            static_cast<double>(paletteColors);
        const int color = TColor::GetColorPalette(index);
        auto box = std::make_unique<TBox>(0.08, 0.10 + 0.80 * low, 0.34, 0.10 + 0.80 * high);
        box->SetFillColor(color);
        box->SetLineColor(color);
        box->Draw("SAME");
        colorBoxes.push_back(std::move(box));
    }

    TLatex paletteText;
    paletteText.SetTextSize(0.105);
    paletteText.SetTextAlign(12);

    constexpr int labelCount = 5;

    for (int index = 0; index < labelCount; ++index)
    {
        const double fraction = static_cast<double>(index) /
            static_cast<double>(labelCount - 1);
        const double value = minimumPositive * std::pow(
            displayMaximum / minimumPositive,
            fraction
        );
        paletteText.DrawLatex(
            0.39,
            0.10 + 0.80 * fraction,
            Form("%.2e", value)
        );
    }

    paletteText.SetTextAlign(22);
    paletteText.SetTextAngle(90.0);
    paletteText.SetTextSize(0.105);
    paletteText.DrawLatex(0.92, 0.50, "Raw absolute detection efficiency");

    canvas.Modified();
    canvas.Update();
    saveFigure(canvas, outputPath);
}
}

void plot_raw_efficiency_map(
    const char* inputRootFile,
    const char* treeName = "RawEfficiency",
    double targetEnergyMeV = 0.662,
    const char* outputDirectory = "figures",
    bool frontHemisphereOnly = true
)
{
    gROOT->SetBatch(kTRUE);

    std::unique_ptr<TFile> file{TFile::Open(inputRootFile, "READ")};

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{
            "Cannot open efficiency ROOT file: " + std::string{inputRootFile}
        };
    }

    TTree* tree = file->Get<TTree>(treeName);

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find efficiency TTree: " + std::string{treeName}};
    }

    const auto& nsideObject = requireObject<TParameter<int>>(*file, "healpix_nside");
    const auto& orderingObject = requireObject<TNamed>(*file, "healpix_ordering");
    const auto& directionCountObject = requireObject<TParameter<Long64_t>>(
        *file,
        "direction_count"
    );
    const auto& energyCountObject = requireObject<TParameter<Long64_t>>(
        *file,
        "energy_count"
    );
    const auto& energyMinObject = requireObject<TParameter<double>>(
        *file,
        "energy_min_MeV"
    );
    const auto& energyMaxObject = requireObject<TParameter<double>>(
        *file,
        "energy_max_MeV"
    );

    if (std::string{orderingObject.GetTitle()} != "RING")
    {
        throw std::runtime_error{"This quick-look tool currently requires HEALPix RING ordering."};
    }

    const EfficiencyMetadata metadata{
        nsideObject.GetVal(),
        static_cast<std::size_t>(directionCountObject.GetVal()),
        static_cast<std::size_t>(energyCountObject.GetVal()),
        energyMinObject.GetVal(),
        energyMaxObject.GetVal()
    };

    const std::size_t expectedDirectionCount = 12ULL *
        static_cast<std::size_t>(metadata.nside) *
        static_cast<std::size_t>(metadata.nside);

    if (metadata.nside <= 0 ||
        metadata.directionCount != expectedDirectionCount ||
        metadata.energyCount == 0)
    {
        throw std::runtime_error{"The efficiency grid metadata is inconsistent."};
    }

    const std::size_t valueCount = metadata.directionCount * metadata.energyCount;
    std::vector<double> efficiencies(
        valueCount,
        std::numeric_limits<double>::quiet_NaN()
    );

    TTreeReader reader{tree};
    TTreeReaderValue<ULong64_t> cellIndex{reader, "cell_index"};
    TTreeReaderValue<Double_t> efficiency{reader, "efficiency"};

    while (reader.Next())
    {
        const std::size_t index = static_cast<std::size_t>(*cellIndex);

        if (index >= efficiencies.size())
        {
            throw std::runtime_error{"A cell_index is outside the metadata-defined grid."};
        }

        if (std::isfinite(efficiencies[index]))
        {
            throw std::runtime_error{"The efficiency TTree contains a duplicate cell_index."};
        }

        if (!std::isfinite(*efficiency) || *efficiency < 0.0)
        {
            throw std::runtime_error{"An efficiency value is negative or non-finite."};
        }
        efficiencies[index] = static_cast<double>(*efficiency);
    }

    if (std::any_of(
        efficiencies.begin(),
        efficiencies.end(),
        [](double value)
        {
            return !std::isfinite(value);
        }
    ))
    {
        throw std::runtime_error{"The efficiency TTree does not contain every grid cell."};
    }

    const EnergyInterpolation interpolation = makeEnergyInterpolation(
        metadata,
        targetEnergyMeV
    );
    std::vector<double> directionSlice(metadata.directionCount, 0.0);

    for (std::size_t direction = 0; direction < metadata.directionCount; ++direction)
    {
        const std::size_t lowerFlatIndex =
            direction * metadata.energyCount + interpolation.lowerIndex;
        const std::size_t upperFlatIndex =
            direction * metadata.energyCount + interpolation.upperIndex;
        directionSlice[direction] =
            (1.0 - interpolation.upperWeight) * efficiencies[lowerFlatIndex] +
            interpolation.upperWeight * efficiencies[upperFlatIndex];
    }

    // 720 x 360 只是显示用的经纬度光栅。每个显示格点都反查所属的
    // HEALPix pixel，因此不会改变原始效率，也不会用平滑制造虚假分辨率。
    TH2D map{
        "absolute_efficiency_map",
        ";Camera-centred longitude (degree);Camera-centred latitude (degree);Raw absolute detection efficiency",
        720,
        -180.0,
        180.0,
        360,
        -90.0,
        90.0
    };

    map.SetDirectory(nullptr);
    map.SetStats(false);

    double minimumPositive = std::numeric_limits<double>::infinity();
    double maximum = 0.0;

    for (int xBin = 1; xBin <= map.GetNbinsX(); ++xBin)
    {
        const double longitude = map.GetXaxis()->GetBinCenter(xBin) * PI / 180.0;

        for (int yBin = 1; yBin <= map.GetNbinsY(); ++yBin)
        {
            const double latitude = map.GetYaxis()->GetBinCenter(yBin) * PI / 180.0;

            // 这是现有项目 cameraCenteredCoordinate() 的逆变换。
            const double x = std::cos(latitude) * std::sin(longitude);
            const double y = std::sin(latitude);
            const double z = -std::cos(latitude) * std::cos(longitude);

            if (frontHemisphereOnly && z > 0.0)
            {
                map.SetBinContent(xBin, yBin, 0.0);
                continue;
            }

            const double theta = std::acos(std::clamp(z, -1.0, 1.0));
            const double phi = std::atan2(y, x);
            const std::uint64_t pixel = angleToRingPixel(metadata.nside, theta, phi);
            const double value = directionSlice.at(static_cast<std::size_t>(pixel));

            map.SetBinContent(xBin, yBin, value);
            maximum = std::max(maximum, value);

            if (value > 0.0)
            {
                minimumPositive = std::min(minimumPositive, value);
            }
        }
    }

    if (!(maximum > 0.0) || !std::isfinite(minimumPositive))
    {
        // 零计数是可显示的数据，不应阻止线性图和 skymap 输出。
        // 所有绘图函数会关闭对数处理并明确标注全零，不向数据中添加 baseline。
        std::cout << "WARNING: selected slice has no positive values; drawing zero maps without a logarithmic scale.\n";
    }

    if (gSystem->mkdir(outputDirectory, kTRUE) != 0 &&
        gSystem->AccessPathName(outputDirectory))
    {
        throw std::runtime_error{
            "Cannot create output directory: " + std::string{outputDirectory}
        };
    }

    gStyle->SetOptStat(0);
    gStyle->SetPalette(kViridis);
    gStyle->SetNumberContours(255);

    const std::string tag = energyTag(targetEnergyMeV);
    const std::string basePath = std::string{outputDirectory} +
        "/raw_efficiency_map_E" + tag;

    drawMap(
        map,
        metadata,
        interpolation,
        targetEnergyMeV,
        minimumPositive,
        maximum,
        basePath + "_linear.png",
        frontHemisphereOnly,
        false
    );

    drawMap(
        map,
        metadata,
        interpolation,
        targetEnergyMeV,
        minimumPositive,
        maximum,
        basePath + "_log.png",
        frontHemisphereOnly,
        true
    );

    drawAitoffSkyMap(
        map,
        metadata,
        interpolation,
        targetEnergyMeV,
        minimumPositive,
        maximum,
        basePath + "_skymap_aitoff_log.png",
        frontHemisphereOnly
    );

    std::cout << "Raw-efficiency quick-look completed.\n"
              << "  input: " << inputRootFile << '\n'
              << "  tree: " << treeName << '\n'
              << "  target energy: " << targetEnergyMeV << " MeV\n"
              << "  lower layer: " << interpolation.lowerEnergyMeV
              << " MeV, weight = " << 1.0 - interpolation.upperWeight << '\n'
              << "  upper layer: " << interpolation.upperEnergyMeV
              << " MeV, weight = " << interpolation.upperWeight << '\n'
              << "  output: " << basePath << "_linear.png\n"
              << "  output: " << basePath << "_log.png\n"
              << "  output: " << basePath << "_skymap_aitoff_log.png\n";
}
