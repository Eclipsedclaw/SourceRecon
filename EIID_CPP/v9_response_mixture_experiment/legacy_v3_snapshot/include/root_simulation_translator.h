// v3_json_architecture/include/root_simulation_translator.h

#ifndef EIID_ROOT_SIMULATION_TRANSLATOR_H
#define EIID_ROOT_SIMULATION_TRANSLATOR_H

#include "io_config.h"

// 将 Geant4 step 级 Tree1 翻译成每行一个有效宏观事件的精简 ROOT 文件。
// 这是 Translator 模块唯一对外暴露的函数。
void translateRawData(const IoConfig& config);

#endif
