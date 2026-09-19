// v3_json_architecture/include/data_input.h

#ifndef EIID_DATA_INPUT_H
#define EIID_DATA_INPUT_H

#include "ReconConfig.h"
#include "eiid_core.h"

#include <vector>

// 这里只读取 Translator 已经整理好的精简事件树。
// Geant4 step 分组、数字化和触发逻辑绝不能进入这个函数。
std::vector<Event> readEventsFromRoot(const ReconConfig& config);

#endif
