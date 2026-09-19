#ifndef EIID_V10_HISTOGRAM_KERNEL_H
#define EIID_V10_HISTOGRAM_KERNEL_H

#include "IResponseKernel.h"

#include <cstddef>
#include <vector>

// HistogramKernel is the non-parametric reference.  ROOT bin contents are
// copied into ordinary vectors by RootKernelReader, so evaluate() has no ROOT
// ownership or global-directory dependency inside the hot LM-MLEM loop.
class HistogramKernel final : public IResponseKernel
{
public:
    HistogramKernel(
        std::vector<Decimal> energyCenters,
        std::vector<Decimal> angleCenters,
        std::vector<Decimal> deltaCenters,
        std::vector<Decimal> density
    );

    Decimal evaluate(const ResponseQuery& query) const override;
    std::string_view name() const noexcept override;

private:
    std::size_t nearest(
        const std::vector<Decimal>& coordinates,
        Decimal value
    ) const;

    std::size_t flatIndex(
        std::size_t energy,
        std::size_t angle,
        std::size_t delta
    ) const;

    std::vector<Decimal> energyCenters_;
    std::vector<Decimal> angleCenters_;
    std::vector<Decimal> deltaCenters_;
    std::vector<Decimal> density_;
};

#endif
