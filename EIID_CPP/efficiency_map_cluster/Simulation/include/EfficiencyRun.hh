#pragma once
#include "CellCounts.h"
#include <G4Run.hh>

// G4Run 是“一次 BeamOn 的结果容器”。每个工作线程有自己的实例。
// 事件热循环不加全局锁；Geant4 在结束时调用 Merge 汇总。
class EfficiencyRun final : public G4Run
{
  public:
    Counts counts;
    void Merge(const G4Run* other) override;
};
