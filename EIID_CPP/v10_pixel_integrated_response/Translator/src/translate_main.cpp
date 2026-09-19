// v3_json_architecture/translate_main.cpp

#include "io_config.h"
#include "root_simulation_translator.h"

#include <exception>
#include <filesystem>
#include <iostream>

int main(int argc, char* argv[])
{
    try
    {
        // Translator 有独立入口，因此执行数据转换时不会启动任何重建计算。
        const std::filesystem::path configPath = argc > 1
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/translator_config.json"};
        const IoConfig ioConfig{configPath};
        translateRawData(ioConfig);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Translator error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
