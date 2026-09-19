#pragma once
#include "TaskSpec.h"

class TaskRunner
{
  public:
    void run(const Campaign& campaign, std::uint64_t jobId) const;
};
