#ifndef EIID_IPLOTTER_H
#define EIID_IPLOTTER_H

#include "reconstruction_data.h"
#include "vis_config.h"

#include <string>

// 所有绘图器都遵循同一个接口。
// 新增图表时，只需继承 IPlotter 并在 vis_main.cpp 中按配置注册。
class IPlotter
{
public:
    virtual ~IPlotter() = default;

    virtual std::string name() const = 0;
    virtual void plot(const ReconstructionData& data, const VisConfig& config) const = 0;
};

#endif
