// D:\CodexForSR\EIID_CPP\io_translator_version\include\data_output.h

#ifndef EIID_DATA_OUTPUT_H
#define EIID_DATA_OUTPUT_H

#include "common.h"
#include "io_config.h"

#include <vector>

// 把最终联合图逐 cell 保存到 ROOT TTree。
void saveImageToFile(const std::vector<Decimal>& image, const IoConfig& config);

#endif
