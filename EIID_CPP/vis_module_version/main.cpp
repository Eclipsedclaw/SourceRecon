// D:\CodexForSR\EIID_CPP\io_translator_version\main.cpp

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
        // 重建入口只面对 Translator 的精简输出，不读取 Geant4 Step。
        const Parameter parameter;
        const IoConfig ioConfig;
        const Grid grid{parameter};
        const std::vector<Event> events = readEventsFromRoot(ioConfig);
        const std::vector<Decimal> image = runEiid(events, grid, parameter);

        saveImageToFile(image, grid, ioConfig);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
