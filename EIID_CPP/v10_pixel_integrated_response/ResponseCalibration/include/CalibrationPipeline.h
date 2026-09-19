#ifndef EIID_V10_CALIBRATION_PIPELINE_H
#define EIID_V10_CALIBRATION_PIPELINE_H

class CalibrationConfig;

class CalibrationPipeline
{
public:
    static void run(const CalibrationConfig& config);
};

#endif
