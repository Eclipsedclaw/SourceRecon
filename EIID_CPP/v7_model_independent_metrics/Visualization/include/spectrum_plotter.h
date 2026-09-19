#ifndef EIID_SPECTRUM_PLOTTER_H
#define EIID_SPECTRUM_PLOTTER_H

#include "iplotter.h"

class SpectrumPlotter final : public IPlotter
{
public:
    std::string name() const override;
    void plot(const ReconstructionData& data, const VisConfig& config) const override;
};

#endif
