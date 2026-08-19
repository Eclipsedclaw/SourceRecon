#include "include/eiid.h"
#include "include/grid.h"
#include "include/parameter.h"

#include <exception>
#include <iostream>

int main()
{
    try
    {
        // main() 只负责按顺序组织程序，不负责保存参数、划分网格或实现公式。
        const Parameter parameter;
        const Grid grid(parameter);
        const std::vector<Event> events = makeToyEvents(parameter);
        const std::vector<Decimal> image = runEiid(events, grid, parameter);

        printResult(image, grid);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
