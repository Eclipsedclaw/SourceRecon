#ifndef EIID_SENSITIVITY_READER_H
#define EIID_SENSITIVITY_READER_H

#include "ReconConfig.h"
#include "SensitivityMatrix.h"
#include "grid.h"

SensitivityMatrix readSensitivityFromRoot(
    const ReconConfig& config,
    const Grid& grid
);

#endif
