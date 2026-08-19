#ifndef EIID_DATA_INPUT_H
#define EIID_DATA_INPUT_H

#include "eiid.h"
#include "io_config.h"

#include <vector>

// 从 ROOT 文件读取事件，并转换成算法只认识的 Event 对象。
// ROOT 的 TFile、TTree 和分支细节不会进入 core/ 模块。
std::vector<Event> readEventsFromRoot(const IoConfig& config);

#endif
