// v3_json_architecture/include/data_output.h

#ifndef EIID_DATA_OUTPUT_H
#define EIID_DATA_OUTPUT_H

#include "ReconConfig.h"
#include "common.h"

#include <vector>

class Grid;

// 把最终联合图逐 cell 保存到 ROOT TTree。
// Grid 用于把 image 的一维下标重新解释为方向、能量等物理坐标。
void saveImageToFile(
    const std::vector<Decimal>& image,
    const Grid& grid,
    const ReconConfig& config
);

#endif
