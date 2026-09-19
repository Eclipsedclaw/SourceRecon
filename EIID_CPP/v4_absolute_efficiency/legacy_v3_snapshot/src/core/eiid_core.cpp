#include "eiid_core.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace
{
Decimal dot(const Vec3& left, const Vec3& right)
{
    return left.x * right.x + left.y * right.y + left.z * right.z;
}

Vec3 unitVector(const Vec3& vector, Decimal denominatorFloor)
{
    const Decimal length = std::sqrt(dot(vector, vector));

    if (length <= denominatorFloor)
    {
        throw std::runtime_error{"A direction vector has zero length."};
    }

    return Vec3{
        vector.x / length,
        vector.y / length,
        vector.z / length
    };
}
}

Decimal calculateResponse(
    const Event& event,
    const Cell& cell,
    const ReconConfig& config
)
{
    const Decimal incidentEnergy = cell.energyMeV;
    const Decimal energyAfterFirstHit = incidentEnergy - event.e1MeV;

    if (energyAfterFirstHit <= static_cast<Decimal>(0.0L))
    {
        return static_cast<Decimal>(0.0L);
    }

    const Decimal cosThetaFromEnergy =
        static_cast<Decimal>(1.0L) - ELECTRON_MASS_MEV *
        (
            static_cast<Decimal>(1.0L) / energyAfterFirstHit -
            static_cast<Decimal>(1.0L) / incidentEnergy
        );

    if (cosThetaFromEnergy < static_cast<Decimal>(-1.0L) ||
        cosThetaFromEnergy > static_cast<Decimal>(1.0L))
    {
        return static_cast<Decimal>(0.0L);
    }

    const Decimal thetaFromEnergy = std::acos(cosThetaFromEnergy);

    const Vec3 hitDifference{
        event.r2.x - event.r1.x,
        event.r2.y - event.r1.y,
        event.r2.z - event.r1.z
    };

    const Vec3 scatteredDirection = unitVector(
        hitDifference,
        config.denominatorFloor()
    );

    const Vec3 sourceDirection = unitVector(
        cell.sourceDirection,
        config.denominatorFloor()
    );

    const Vec3 incidentDirection{
        -sourceDirection.x,
        -sourceDirection.y,
        -sourceDirection.z
    };

    const Decimal cosThetaFromGeometry = std::clamp(
        dot(incidentDirection, scatteredDirection),
        static_cast<Decimal>(-1.0L),
        static_cast<Decimal>(1.0L)
    );

    const Decimal thetaFromGeometry = std::acos(cosThetaFromGeometry);
    const Decimal sigmaRadian = config.responseSigmaDegree() * PI /
        static_cast<Decimal>(180.0L);

    const Decimal angleDifference = thetaFromGeometry - thetaFromEnergy;

    return std::exp(
        static_cast<Decimal>(-0.5L) *
        angleDifference * angleDifference /
        (sigmaRadian * sigmaRadian)
    );
}
