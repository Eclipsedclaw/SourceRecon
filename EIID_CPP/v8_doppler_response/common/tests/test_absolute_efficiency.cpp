#include "AbsoluteEfficiencyMap.h"

#include <cassert>
#include <stdexcept>

int main()
{
    AbsoluteEfficiencyMap map{2, 3};

    for (std::size_t index = 0; index < map.size(); ++index)
    {
        map.setFlat(index, static_cast<Decimal>(index) / 10.0);
    }

    map.requireComplete();
    assert(map.flatIndex(1, 2) == 5);
    assert(map.at(1, 2) == static_cast<Decimal>(0.5));

    bool duplicateRejected = false;

    try
    {
        map.setFlat(0, 0.1);
    }
    catch (const std::runtime_error&)
    {
        duplicateRejected = true;
    }

    assert(duplicateRejected);
    return 0;
}
