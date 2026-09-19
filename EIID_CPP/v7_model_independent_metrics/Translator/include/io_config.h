// v3_json_architecture/include/io_config.h

#ifndef EIID_IO_CONFIG_H
#define EIID_IO_CONFIG_H

#include <filesystem>
#include <string>

// IoConfig 是整个 ETL 和重建流程的路径及 ROOT schema 配置中心。
// Translator 和重建器共享同一个对象，因此二者不会各自写死另一套文件名。
class IoConfig
{
public:
    // Translator 的原始输入：Geant4 每行一个 step 的大 ROOT 文件。
    std::string rawGeant4FilePath;
    std::string rawGeant4TreeName;
    std::string rawEventIdBranchName;
    std::string rawChamberIdBranchName;
    std::string rawXBranchName;
    std::string rawYBranchName;
    std::string rawZBranchName;
    std::string rawEnergyDepositBranchName;

    int frontChamberId;
    int rearChamberId;
    double minimumLayerEnergyMeV;

    // Translator 的输出，同时也是重建器的输入。
    std::string inputRootFilePath;
    std::string inputTreeName;

    // 精简事件树中组成 Event 的七个分支名称。
    std::string r1XBranchName;
    std::string r1YBranchName;
    std::string r1ZBranchName;
    std::string r2XBranchName;
    std::string r2YBranchName;
    std::string r2ZBranchName;
    std::string e1MeVBranchName;

    // 重建结果文件及结果树的名称。
    std::string outputResultPath;
    std::string outputTreeName;
    std::string outputCellIndexBranchName;
    std::string outputWeightBranchName;

    explicit IoConfig(
        const std::filesystem::path& configPath =
            "config/translator_config.json"
    );
};

#endif
