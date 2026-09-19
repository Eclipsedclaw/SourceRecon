#ifndef EIID_V4_ROOT_EVENT_READER_H
#define EIID_V4_ROOT_EVENT_READER_H

#include "PhysicsTypes.h"

#include <vector>

class ReconConfig;

class RootEventReader
{
public:
    static std::vector<Event> read(const ReconConfig& config);
};

#endif
