#ifndef EIID_V4_PHYSICS_TYPES_H
#define EIID_V4_PHYSICS_TYPES_H

#include "Common.h"

#include <cstddef>

struct Vec3
{
    Decimal x{};
    Decimal y{};
    Decimal z{};
};

struct Event
{
    Vec3 r1;
    Vec3 r2;
    Decimal e1MeV{};
};

struct Cell
{
    std::size_t directionIndex{};
    std::size_t energyIndex{};
    std::size_t healpixPixelId{};
    Decimal thetaDegree{};
    Decimal phiDegree{};
    Vec3 sourceDirection;
    Decimal energyMeV{};
};

#endif
