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

// AnalysisConfig 控制模型无关质量指标和可选 Gaussian 拟合。
// 直接 FWHM、最短包含区间和方向矩指标不依赖 Gaussian 成功与否。
struct AnalysisConfig
{
    double energyIntervalFraction;
    bool gaussianFitEnabled;
    double gaussianFitHalfWidthMeV;
    double directionLocalRadiusDegree;
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
    const AnalysisConfig& analysis() const;

    bool drawSkymap() const;
    bool drawSpectrum() const;
    bool drawContainment() const;
    bool drawEnergyMetrics() const;
    bool drawDirectionMetrics() const;
    bool drawEnergyAngleMap() const;
    bool writeQualitySummary() const;
    bool showTruthMarkers() const;

private:
    std::filesystem::path inputRootFilePath_;
    std::filesystem::path outputDirectory_;
    std::string inputTreeName_;
    TruthInfo truth_{};
    AnalysisConfig analysis_{
        0.68,
        true,
        0.16,
        30.0,
        15.0
    };

    bool drawSkymap_ = false;
    bool drawSpectrum_ = false;
    bool drawContainment_ = false;
    bool drawEnergyMetrics_ = false;
    bool drawDirectionMetrics_ = false;
    bool drawEnergyAngleMap_ = false;
    bool writeQualitySummary_ = false;
    bool showTruthMarkers_ = false;
};

#endif
