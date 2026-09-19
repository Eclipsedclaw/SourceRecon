#ifndef EIID_V7_HEALPIX_GRID_H
#define EIID_V7_HEALPIX_GRID_H

#include "IGrid.h"

#include <vector>

class HealpixGrid final : public IGrid
{
public:
    HealpixGrid(
        int healpixNside,
        int energyPointCount,
        Decimal energyMinMeV,
        Decimal energyMaxMeV
    );

    const std::vector<Cell>& cells() const override;
    const Cell& cell(
        std::size_t directionIndex,
        std::size_t energyIndex
    ) const override;
    const Vec3& direction(std::size_t directionIndex) const override;
    Decimal energy(std::size_t energyIndex) const override;
    int healpixNside() const override;
    std::size_t directionCount() const override;
    std::size_t energyCount() const override;

private:
    int healpixNside_{};
    int energyPointCount_{};
    Decimal energyMinMeV_{};
    Decimal energyMaxMeV_{};
    std::vector<Vec3> directions_;
    std::vector<Decimal> energiesMeV_;
    std::vector<Cell> cells_;

    void buildDirections();
    void buildEnergies();
    void buildCells();
};

#endif
