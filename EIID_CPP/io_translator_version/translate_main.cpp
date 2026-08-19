// D:\CodexForSR\EIID_CPP\io_translator_version\translate_main.cpp

#include "io_config.h"
#include "root_simulation_translator.h"

#include <exception>
#include <iostream>

int main()
{
    try
    {
        // Translator 有独立入口，因此执行数据转换时不会启动任何重建计算。
        const IoConfig ioConfig;
        translateRawData(ioConfig);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Translator error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
