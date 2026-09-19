#ifndef EIID_V7_ENERGY_ANGLE_PLOTTER_H
#define EIID_V7_ENERGY_ANGLE_PLOTTER_H

#include "quality_analysis.h"
#include "iplotter.h"

#include <memory>

class EnergyAnglePlotter final : public IPlotter
{
public:
    explicit EnergyAnglePlotter(
        std::shared_ptr<const QualityAnalysisResult> analysis
    );

    std::string name() const override;
    void plot(
        const ReconstructionData& data,
        const VisConfig& config
    ) const override;

private:
    std::shared_ptr<const QualityAnalysisResult> analysis_;
};

#endif
