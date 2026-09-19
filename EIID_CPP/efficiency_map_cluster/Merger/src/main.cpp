#include "CountMerger.h"
#include <exception>
#include <iostream>

int main(int argc, char** argv)
{
    try
    {
        if (argc < 2 || argc > 3 || (argc == 3 && std::string{argv[2]} != "--check-only"))
        {
            throw std::runtime_error{"Usage: efficiency_merge manifest.json [--check-only]"};
        }
        CountMerger{}.run(Campaign{argv[1]}, argc == 3);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Merge error: " << error.what() << std::endl;
        return 1;
    }
}
