#include "data_output.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>

#include <cstdint>
#include <stdexcept>

void saveImageToFile(const std::vector<Decimal>& image, const IoConfig& config)
{
    if (image.empty())
    {
        throw std::runtime_error{"Cannot save an empty EIID image."};
    }

    TFile outputFile{config.outputResultPath.c_str(), "RECREATE"};

    if (outputFile.IsZombie())
    {
        throw std::runtime_error{"Cannot create ROOT output file: " + config.outputResultPath};
    }

    // 每一行保存一个联合 cell 的一维索引和最终权重。
    // directionIndex 与 energyIndex 的还原规则仍由 Grid 统一定义。
    TTree resultTree{config.outputTreeName.c_str(), "EIID direction-energy image"};

    ULong64_t cellIndex = 0;
    Decimal weight = static_cast<Decimal>(0.0L);

    // 模板版 Branch 会从变量地址推导实际类型，不需要手写 leaflist 字符串。
    resultTree.Branch(config.outputCellIndexBranchName.c_str(), &cellIndex);
    resultTree.Branch(config.outputWeightBranchName.c_str(), &weight);

    for (std::size_t index = 0; index < image.size(); ++index)
    {
        cellIndex = static_cast<ULong64_t>(index);
        weight = image[index];

        if (resultTree.Fill() < 0)
        {
            throw std::runtime_error{"Failed while filling the ROOT output tree."};
        }
    }

    if (resultTree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write the EIID image tree."};
    }

    outputFile.Close();
}
