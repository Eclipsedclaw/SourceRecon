#ifndef EIID_V9_ROOT_SAMPLE_READER_H
#define EIID_V9_ROOT_SAMPLE_READER_H

#include "CalibrationConfig.h"
#include "ResponseSample.h"

#include <vector>

class RootSampleReader
{
public:
    static std::vector<ResponseSample> read(const CalibrationInput& input);
};

#endif
