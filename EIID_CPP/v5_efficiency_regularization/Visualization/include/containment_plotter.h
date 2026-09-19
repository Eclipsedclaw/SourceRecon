#ifndef EIID_CONTAINMENT_PLOTTER_H
#define EIID_CONTAINMENT_PLOTTER_H

#include "iplotter.h"

class ContainmentPlotter final : public IPlotter
{
public:
    std::string name() const override;
    void plot(const ReconstructionData& data, const VisConfig& config) const override;
};

#endif
