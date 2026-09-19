#ifndef EIID_V6_ENERGY_ANGLE_PLOTTER_H
#define EIID_V6_ENERGY_ANGLE_PLOTTER_H

#include "fit_analysis.h"
#include "iplotter.h"

#include <memory>

class EnergyAnglePlotter final : public IPlotter
{
public:
    explicit EnergyAnglePlotter(
        std::shared_ptr<const FitAnalysisResult> analysis
    );

    std::string name() const override;
    void plot(
        const ReconstructionData& data,
        const VisConfig& config
    ) const override;

private:
    std::shared_ptr<const FitAnalysisResult> analysis_;
};

#endif
