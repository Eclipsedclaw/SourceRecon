#include "data_input.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <memory>
#include <stdexcept>
#include <string>

namespace
{
void requireBranch(TTree* tree, const std::string& branchName)
{
    if (tree->GetBranch(branchName.c_str()) == nullptr)
    {
        throw std::runtime_error{"Required ROOT branch was not found: " + branchName};
    }
}
}

std::vector<Event> readEventsFromRoot(const IoConfig& config)
{
    // TFile::Open 返回裸指针；交给 unique_ptr 后，所有提前退出路径都会自动关闭文件。
    auto inputFile = std::unique_ptr<TFile>{TFile::Open(config.inputRootFilePath.c_str(), "READ")};

    if (!inputFile || inputFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open ROOT input file: " + config.inputRootFilePath};
    }

    // tree 是由 inputFile 拥有的借用指针；inputFile 在整个读取过程中保持存活。
    TTree* const tree = inputFile->Get<TTree>(config.inputTreeName.c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find ROOT tree: " + config.inputTreeName};
    }

    // 在开始遍历前一次性检查合同要求的全部分支，缺少分支时给出明确名称。
    requireBranch(tree, config.r1XBranchName);
    requireBranch(tree, config.r1YBranchName);
    requireBranch(tree, config.r1ZBranchName);
    requireBranch(tree, config.r2XBranchName);
    requireBranch(tree, config.r2YBranchName);
    requireBranch(tree, config.r2ZBranchName);
    requireBranch(tree, config.e1MeVBranchName);

    TTreeReader reader{tree};

    // 这里假设 ROOT 文件中的坐标和能量分支以 Double_t 保存。
    // 读出后立即转换为 Decimal，因此 ROOT 文件格式与算法内部精度彼此独立。
    TTreeReaderValue<Double_t> r1X{reader, config.r1XBranchName.c_str()};
    TTreeReaderValue<Double_t> r1Y{reader, config.r1YBranchName.c_str()};
    TTreeReaderValue<Double_t> r1Z{reader, config.r1ZBranchName.c_str()};
    TTreeReaderValue<Double_t> r2X{reader, config.r2XBranchName.c_str()};
    TTreeReaderValue<Double_t> r2Y{reader, config.r2YBranchName.c_str()};
    TTreeReaderValue<Double_t> r2Z{reader, config.r2ZBranchName.c_str()};
    TTreeReaderValue<Double_t> e1MeV{reader, config.e1MeVBranchName.c_str()};

    std::vector<Event> events;
    events.reserve(static_cast<std::size_t>(tree->GetEntries()));

    while (reader.Next())
    {
        const Vec3 r1{static_cast<Decimal>(*r1X), static_cast<Decimal>(*r1Y), static_cast<Decimal>(*r1Z)};
        const Vec3 r2{static_cast<Decimal>(*r2X), static_cast<Decimal>(*r2Y), static_cast<Decimal>(*r2Z)};
        const Event event{r1, r2, static_cast<Decimal>(*e1MeV)};
        events.push_back(event);
    }

    if (events.empty())
    {
        throw std::runtime_error{"The ROOT input tree contains no readable events."};
    }

    return events;
}
