#include "io_config.h"

IoConfig::IoConfig()
{
    // 默认在程序工作目录中读取 events.root 的 Events 树。
    inputRootFilePath = "events.root";
    inputTreeName = "Events";

    // 这些默认分支名描述一个已经整理好相互作用顺序的两次 hit 事件树。
    // 如果真实 ROOT 文件采用其他名称，只修改这里或之后加入配置文件读取即可。
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
