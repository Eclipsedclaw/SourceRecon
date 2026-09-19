#ifndef EIID_V6_FIT_SUMMARY_WRITER_H
#define EIID_V6_FIT_SUMMARY_WRITER_H

#include "fit_analysis.h"
#include "vis_config.h"

class FitSummaryWriter
{
public:
    static void write(
        const FitAnalysisResult& analysis,
        const VisConfig& config
    );
};

#endif
