// v3_json_architecture/io/root_simulation_translator.cpp

#include "root_simulation_translator.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <cmath>
#include <cstddef>
#include <filesystem>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
// RawStep 只保留本次 ETL 真正需要的六项数据。
// 其他真值和过程信息仍安全保存在原始 ROOT 文件中，不会被覆盖。
struct RawStep
{
    Int_t chamberId;
    Double_t x;
    Double_t y;
    Double_t z;
    Double_t energyMeV;
};

// 一个 DigitizedHit 代表实验硬件在某一个 chamber 上看到的宏观结果。
struct DigitizedHit
{
    Double_t x;
    Double_t y;
    Double_t z;
    Double_t energyMeV;
};

using DigitizedEvent = std::map<Int_t, DigitizedHit>;

struct ChamberAccumulator
{
    Double_t weightedX = 0.0;
    Double_t weightedY = 0.0;
    Double_t weightedZ = 0.0;
    Double_t totalEnergyMeV = 0.0;
};

// Branch 绑定要求变量地址在整个 Fill() 期间保持有效。
// 因此把所有输出变量集中放在一个生命周期足够长的对象中。
struct TranslatedRow
{
    Int_t eventId = -1;
    Double_t r1X = 0.0;
    Double_t r1Y = 0.0;
    Double_t r1Z = 0.0;
    Double_t r2X = 0.0;
    Double_t r2Y = 0.0;
    Double_t r2Z = 0.0;
    Double_t e1MeV = 0.0;
};

void requireBranch(TTree* tree, const std::string& branchName)
{
    if (tree->GetBranch(branchName.c_str()) == nullptr)
    {
        throw std::runtime_error{"Raw Geant4 tree is missing branch: " + branchName};
    }
}

void requireDifferentInputAndOutputPaths(const IoConfig& config)
{
    namespace fs = std::filesystem;

    // RECREATE 会覆盖已有文件，所以必须在打开输出文件之前完成这项保护。
    const fs::path rawPath = fs::absolute(config.rawGeant4FilePath).lexically_normal();
    const fs::path translatedPath = fs::absolute(config.inputRootFilePath).lexically_normal();

    if (rawPath == translatedPath)
    {
        throw std::runtime_error{"Raw input and translated output must be different files."};
    }
}

// Digitizer：把同一个 eventID 中属于同一 chamber 的所有正能量 Step 合并。
// 总能量是直接求和；位置是以每条 Step 的沉积能量为权重的三维质心。
DigitizedEvent digitize(const std::vector<RawStep>& steps)
{
    std::map<Int_t, ChamberAccumulator> accumulators;

    for (const RawStep& step : steps)
    {
        // Geant4 文件中存在 eDep = 0 的过程记录；它们不代表硬件可见沉积。
        if (step.energyMeV <= 0.0)
        {
            continue;
        }

        if (!std::isfinite(step.energyMeV) || !std::isfinite(step.x) || !std::isfinite(step.y) || !std::isfinite(step.z))
        {
            throw std::runtime_error{"A positive-energy raw Step contains a non-finite value."};
        }

        ChamberAccumulator& accumulator = accumulators[step.chamberId];
        accumulator.weightedX += step.energyMeV * step.x;
        accumulator.weightedY += step.energyMeV * step.y;
        accumulator.weightedZ += step.energyMeV * step.z;
        accumulator.totalEnergyMeV += step.energyMeV;
    }

    DigitizedEvent event;

    for (const auto& [chamberId, accumulator] : accumulators)
    {
        if (accumulator.totalEnergyMeV <= 0.0 || !std::isfinite(accumulator.totalEnergyMeV))
        {
            continue;
        }

        const DigitizedHit hit{
            accumulator.weightedX / accumulator.totalEnergyMeV,
            accumulator.weightedY / accumulator.totalEnergyMeV,
            accumulator.weightedZ / accumulator.totalEnergyMeV,
            accumulator.totalEnergyMeV};

        event.emplace(chamberId, hit);
    }

    return event;
}

// TriggerPolicy：ch2 和 ch1 都必须具有正沉积。
// ch0 是否存在不会影响当前触发判定。
bool passesTrigger(const DigitizedEvent& event, const IoConfig& config)
{
    const auto ch2 = event.find(config.frontChamberId);
    const auto ch1 = event.find(config.rearChamberId);

    return ch2 != event.end() &&
           ch1 != event.end() &&
           ch2->second.energyMeV > config.minimumLayerEnergyMeV &&
           ch1->second.energyMeV > config.minimumLayerEnergyMeV;
}

bool transformAndWriteEvent(
    Int_t eventId,
    const std::vector<RawStep>& steps,
    const IoConfig& config,
    TranslatedRow& row,
    TTree& outputTree
)
{
    const DigitizedEvent event = digitize(steps);

    if (!passesTrigger(event, config))
    {
        return false;
    }

    // 经过 TriggerPolicy 后，这两个 key 一定存在；at() 同时保留运行时边界检查。
    const DigitizedHit& ch2 = event.at(config.frontChamberId);
    const DigitizedHit& ch1 = event.at(config.rearChamberId);

    // 固定采用 ch2 → ch1：r1/e1 来自 ch2，r2 来自 ch1。
    row.eventId = eventId;
    row.r1X = ch2.x;
    row.r1Y = ch2.y;
    row.r1Z = ch2.z;
    row.r2X = ch1.x;
    row.r2Y = ch1.y;
    row.r2Z = ch1.z;
    row.e1MeV = ch2.energyMeV;

    if (outputTree.Fill() < 0)
    {
        throw std::runtime_error{"Failed while filling the translated event tree."};
    }

    return true;
}
}

void translateRawData(const IoConfig& config)
{
    requireDifferentInputAndOutputPaths(config);

    auto rawFile = std::unique_ptr<TFile>{TFile::Open(config.rawGeant4FilePath.c_str(), "READ")};

    if (!rawFile || rawFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open raw Geant4 ROOT file: " + config.rawGeant4FilePath};
    }

    TTree* const rawTree = rawFile->Get<TTree>(config.rawGeant4TreeName.c_str());

    if (rawTree == nullptr)
    {
        throw std::runtime_error{"Cannot find raw Geant4 ROOT tree: " + config.rawGeant4TreeName};
    }

    requireBranch(rawTree, config.rawEventIdBranchName);
    requireBranch(rawTree, config.rawChamberIdBranchName);
    requireBranch(rawTree, config.rawXBranchName);
    requireBranch(rawTree, config.rawYBranchName);
    requireBranch(rawTree, config.rawZBranchName);
    requireBranch(rawTree, config.rawEnergyDepositBranchName);

    TTreeReader reader{rawTree};
    TTreeReaderValue<Int_t> eventId{
        reader,
        config.rawEventIdBranchName.c_str()
    };
    TTreeReaderValue<Int_t> chamberId{
        reader,
        config.rawChamberIdBranchName.c_str()
    };
    TTreeReaderValue<Double_t> x{reader, config.rawXBranchName.c_str()};
    TTreeReaderValue<Double_t> y{reader, config.rawYBranchName.c_str()};
    TTreeReaderValue<Double_t> z{reader, config.rawZBranchName.c_str()};
    TTreeReaderValue<Double_t> energyMeV{
        reader,
        config.rawEnergyDepositBranchName.c_str()
    };

    const std::filesystem::path translatedPath{config.inputRootFilePath};

    if (!translatedPath.parent_path().empty())
    {
        std::filesystem::create_directories(
            translatedPath.parent_path()
        );
    }

    TFile translatedFile{config.inputRootFilePath.c_str(), "RECREATE"};

    if (translatedFile.IsZombie())
    {
        throw std::runtime_error{"Cannot create translated ROOT file: " + config.inputRootFilePath};
    }

    TTree outputTree{config.inputTreeName.c_str(), "Digitized two-hit Compton events"};
    outputTree.SetDirectory(&translatedFile);

    TranslatedRow row;

    // eventID 不是重建必需量，但保留它可以把精简事件追溯到原始模拟事件。
    outputTree.Branch("eventID", &row.eventId);
    outputTree.Branch(config.r1XBranchName.c_str(), &row.r1X);
    outputTree.Branch(config.r1YBranchName.c_str(), &row.r1Y);
    outputTree.Branch(config.r1ZBranchName.c_str(), &row.r1Z);
    outputTree.Branch(config.r2XBranchName.c_str(), &row.r2X);
    outputTree.Branch(config.r2YBranchName.c_str(), &row.r2Y);
    outputTree.Branch(config.r2ZBranchName.c_str(), &row.r2Z);
    outputTree.Branch(config.e1MeVBranchName.c_str(), &row.e1MeV);

    bool hasBufferedEvent = false;
    Int_t bufferedEventId = -1;
    std::vector<RawStep> eventBuffer;
    eventBuffer.reserve(32);

    std::size_t rawRowCount = 0;
    std::size_t observedEventCount = 0;
    std::size_t acceptedEventCount = 0;

    // 每次 eventID 改变时，旧 Buffer 已经收齐，可以立即数字化并写盘。
    // 因而峰值内存只与单个 Geant4 事件的 Step 数有关，而不是与 1284 万行总量有关。
    while (reader.Next())
    {
        ++rawRowCount;

        if (!hasBufferedEvent)
        {
            bufferedEventId = *eventId;
            hasBufferedEvent = true;
        }
        else if (*eventId != bufferedEventId)
        {
            // 状态机要求相同 eventID 连续排列；倒序时立即失败，不能悄悄拆错事件。
            if (*eventId < bufferedEventId)
            {
                throw std::runtime_error{"Raw Tree1 eventID is not monotonically non-decreasing."};
            }

            ++observedEventCount;

            if (transformAndWriteEvent(
                    bufferedEventId,
                    eventBuffer,
                    config,
                    row,
                    outputTree
                ))
            {
                ++acceptedEventCount;
            }

            eventBuffer.clear();
            bufferedEventId = *eventId;
        }

        const RawStep step{*chamberId, *x, *y, *z, *energyMeV};
        eventBuffer.push_back(step);
    }

    // ROOT 文件结束不会再出现新的 eventID，因此必须手动处理最后一个 Buffer。
    if (hasBufferedEvent)
    {
        ++observedEventCount;

        if (transformAndWriteEvent(
                bufferedEventId,
                eventBuffer,
                config,
                row,
                outputTree
            ))
        {
            ++acceptedEventCount;
        }
    }

    if (outputTree.Write() <= 0)
    {
        throw std::runtime_error{"Failed to write the translated ROOT tree."};
    }

    translatedFile.Close();

    std::cout << "Raw rows: " << rawRowCount << '\n';
    std::cout << "Observed eventID groups: " << observedEventCount << '\n';
    std::cout << "Accepted ch2+ch1 events: " << acceptedEventCount << '\n';
    std::cout << "Rejected events: " << observedEventCount - acceptedEventCount << '\n';
    std::cout << "Translated file: " << config.inputRootFilePath << '\n';
}
