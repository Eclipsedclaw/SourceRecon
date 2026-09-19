#ifndef EIID_SKYMAP_PLOTTER_H
#define EIID_SKYMAP_PLOTTER_H

#include "iplotter.h"

class SkymapPlotter final : public IPlotter
{
public:
    std::string name() const override;
    void plot(const ReconstructionData& data, const VisConfig& config) const override;
};

#endif
