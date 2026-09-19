#ifndef EIID_V6_ENERGY_FIT_PLOTTER_H
#define EIID_V6_ENERGY_FIT_PLOTTER_H

#include "fit_analysis.h"
#include "iplotter.h"

#include <memory>

class EnergyFitPlotter final : public IPlotter
{
public:
    explicit EnergyFitPlotter(
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
