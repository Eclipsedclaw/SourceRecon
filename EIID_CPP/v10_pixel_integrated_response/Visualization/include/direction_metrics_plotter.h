#ifndef EIID_V7_DIRECTION_METRICS_PLOTTER_H
#define EIID_V7_DIRECTION_METRICS_PLOTTER_H

#include "iplotter.h"
#include "quality_analysis.h"

#include <memory>
#include <string>

class DirectionMetricsPlotter final : public IPlotter
{
public:
    explicit DirectionMetricsPlotter(
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
