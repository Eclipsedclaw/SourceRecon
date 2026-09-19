#include "EiidResponse.h"

#include "IResponseKernel.h"
#include "ReconConfig.h"
#include "ResponseQuery.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace
{
Decimal dot(const Vec3& left, const Vec3& right)
{
    return left.x * right.x + left.y * right.y + left.z * right.z;
}

Vec3 unitVector(const Vec3& value, Decimal floor)
{
    const Decimal length = std::sqrt(dot(value, value));

    if (length <= floor)
    {
        throw std::runtime_error{"A direction vector has zero length."};
    }

    return Vec3{value.x / length, value.y / length, value.z / length};
}
}

Decimal calculateResponse(
    const Event& event,
    const Cell& cell,
    const ReconConfig& config,
    const IResponseKernel& responseKernel
)
{
    return calculateDirectionalResponse(
        event,
        cell.energyMeV,
        cell.sourceDirection,
        config,
        responseKernel
    );
}

Decimal calculateDirectionalResponse(
    const Event& event,
    Decimal candidateEnergyMeV,
    const Vec3& sourceDirection,
    const ReconConfig& config,
    const IResponseKernel& responseKernel
)
{
    const Decimal energyAfterFirstHit = candidateEnergyMeV - event.e1MeV;

    if (energyAfterFirstHit <= static_cast<Decimal>(0.0))
    {
        return static_cast<Decimal>(0.0);
    }

    const Decimal cosEnergy = static_cast<Decimal>(1.0) -
        ELECTRON_MASS_MEV *
        (static_cast<Decimal>(1.0) / energyAfterFirstHit -
         static_cast<Decimal>(1.0) / candidateEnergyMeV);

    if (cosEnergy < static_cast<Decimal>(-1.0) ||
        cosEnergy > static_cast<Decimal>(1.0))
    {
        return static_cast<Decimal>(0.0);
    }

    const Vec3 scattered = unitVector(
        Vec3{
            event.r2.x - event.r1.x,
            event.r2.y - event.r1.y,
            event.r2.z - event.r1.z
        },
        config.denominatorFloor()
    );
    const Vec3 source = unitVector(
        sourceDirection,
        config.denominatorFloor()
    );
    const Vec3 incident{-source.x, -source.y, -source.z};
    const Decimal thetaGeometry = std::acos(
        std::clamp(
            dot(incident, scattered),
            static_cast<Decimal>(-1.0),
            static_cast<Decimal>(1.0)
        )
    );
    const Decimal thetaEnergy = std::acos(cosEnergy);
    constexpr Decimal radianToDegree =
        static_cast<Decimal>(180.0) / PI;

    return responseKernel.evaluate(
        ResponseQuery{
            (thetaGeometry - thetaEnergy) * radianToDegree,
            candidateEnergyMeV,
            thetaEnergy * radianToDegree
        }
    );
}
