#ifndef EIID_V8_CALIBRATION_PIPELINE_H
#define EIID_V8_CALIBRATION_PIPELINE_H

class CalibrationConfig;

class CalibrationPipeline
{
public:
    static void run(const CalibrationConfig& config);
};

#endif
