#include "data_input.h"
#include "data_output.h"
#include "eiid.h"
#include "grid.h"
#include "io_config.h"
#include "parameter.h"

#include <exception>
#include <iostream>
#include <vector>

int main()
{
    try
    {
        // main() 只负责组织执行顺序；计算、网格和 ROOT 读写分别位于独立模块。
        const Parameter parameter;
        const IoConfig ioConfig;
        const Grid grid{parameter};
        const std::vector<Event> events = readEventsFromRoot(ioConfig);
        const std::vector<Decimal> image = runEiid(events, grid, parameter);

        saveImageToFile(image, ioConfig);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
