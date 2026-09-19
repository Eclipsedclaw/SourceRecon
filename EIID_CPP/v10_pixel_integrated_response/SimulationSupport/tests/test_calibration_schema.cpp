#include "CalibrationSchema.h"

#include <cassert>

int main()
{
    assert(!CalibrationSchema::eventId.empty());
    assert(!CalibrationSchema::description().empty());
    return 0;
}
