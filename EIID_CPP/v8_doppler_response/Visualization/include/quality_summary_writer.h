#ifndef EIID_V7_QUALITY_SUMMARY_WRITER_H
#define EIID_V7_QUALITY_SUMMARY_WRITER_H

#include "quality_analysis.h"
#include "vis_config.h"

// QualitySummaryWriter 只负责把已经算好的质量指标写成 JSON。
// 它不重新读取 ROOT 文件，也不重新执行任何拟合或统计计算。
class QualitySummaryWriter
{
public:
    static void write(
        const QualityAnalysisResult& analysis,
        const VisConfig& config
    );
};

#endif
