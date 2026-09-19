#ifndef EIID_V8_RESPONSE_SAMPLE_H
#define EIID_V8_RESPONSE_SAMPLE_H

#include <cstdint>

struct ResponseSample
{
    std::int64_t eventId{};
    double incidentEnergyMeV{};
    double scatterAngleDegree{};
    double armDegree{};
};

#endif
