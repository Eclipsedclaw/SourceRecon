#ifndef EIID_VIS_CONFIG_H
#define EIID_VIS_CONFIG_H

#include <filesystem>
#include <string>

// TruthInfo 与重建算法完全独立，只描述模拟中已知的真实源参数。
struct TruthInfo
{
    double thetaDegree;
    double phiDegree;
    double energyMeV;
};

// FitConfig 只保存用户真正需要控制的拟合窗口。
// 分箱数量等显示细节由程序根据 HEALPix 和能量网格自动推导。
struct FitConfig
{
    double energyFitHalfWidthMeV;
    double directionEnergyGateSigma;
    double directionFitRadiusDegree;
    double directionSpectrumRadiusDegree;
};

// VisConfig 负责一次性读取绘图开关、输入输出路径和真值信息。
// 所有相对路径都以 plot_config.json 所在目录为基准，而不是以启动程序时的目录为基准。
class VisConfig
{
public:
    explicit VisConfig(const std::filesystem::path& plotConfigPath);

    const std::filesystem::path& inputRootFilePath() const;
    const std::filesystem::path& outputDirectory() const;
    const std::string& inputTreeName() const;
    const TruthInfo& truth() const;
    const FitConfig& fit() const;

    bool drawSkymap() const;
    bool drawSpectrum() const;
    bool drawContainment() const;
    bool drawEnergyFit() const;
    bool drawDirectionFit() const;
    bool drawEnergyAngleMap() const;
    bool writeFitSummary() const;
    bool showTruthMarkers() const;

private:
    std::filesystem::path inputRootFilePath_;
    std::filesystem::path outputDirectory_;
    std::string inputTreeName_;
    TruthInfo truth_{};
    FitConfig fit_{
        0.16,
        2.0,
        30.0,
        15.0
    };

    bool drawSkymap_ = false;
    bool drawSpectrum_ = false;
    bool drawContainment_ = false;
    bool drawEnergyFit_ = false;
    bool drawDirectionFit_ = false;
    bool drawEnergyAngleMap_ = false;
    bool writeFitSummary_ = false;
    bool showTruthMarkers_ = false;
};

#endif
