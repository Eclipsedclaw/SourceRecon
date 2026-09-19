// D:\CodexForSR\EIID_CPP\io_translator_version\io\io_config.cpp

#include "io_config.h"

IoConfig::IoConfig()
{
    // 默认从新版本目录的上一级读取现有 Geant4 原始文件。
    // 因此 raw 输入和 Translator 输出不会指向同一个 events.root。
    rawGeant4FilePath = "rawEvents.root";
    rawGeant4TreeName = "Tree1";

    // Translator 在当前工作目录生成精简文件；重建器读取同一个文件。
    inputRootFilePath = "events.root";
    inputTreeName = "Events";

    r1XBranchName = "r1_x";
    r1YBranchName = "r1_y";
    r1ZBranchName = "r1_z";
    r2XBranchName = "r2_x";
    r2YBranchName = "r2_y";
    r2ZBranchName = "r2_z";
    e1MeVBranchName = "e1_MeV";

    outputResultPath = "result.root";
    outputTreeName = "EiidImage";
    outputCellIndexBranchName = "cell_index";
    outputWeightBranchName = "weight";
}
