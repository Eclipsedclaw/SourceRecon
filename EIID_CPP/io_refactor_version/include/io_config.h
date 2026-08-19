#ifndef EIID_IO_CONFIG_H
#define EIID_IO_CONFIG_H

#include <string>

// IoConfig 是文件接口的配置中心。
// 修改输入文件、树名或分支名时，不需要修改算法核心和 ROOT 读写代码。
class IoConfig
{
public:
    std::string inputRootFilePath;
    std::string inputTreeName;

    // 输入树中组成 Event 的七个分支名称。
    std::string r1XBranchName;
    std::string r1YBranchName;
    std::string r1ZBranchName;
    std::string r2XBranchName;
    std::string r2YBranchName;
    std::string r2ZBranchName;
    std::string e1MeVBranchName;

    std::string outputResultPath;
    std::string outputTreeName;
    std::string outputCellIndexBranchName;
    std::string outputWeightBranchName;

    IoConfig();
};

#endif
