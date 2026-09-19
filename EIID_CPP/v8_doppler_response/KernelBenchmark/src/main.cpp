#include "BenchmarkConfig.h"
#include "BenchmarkRunner.h"

#include "TROOT.h"

#include <exception>
#include <filesystem>
#include <iostream>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: kernel_benchmark [path/to/benchmark_config.json]\n";
            return 1;
        }

        gROOT->SetBatch(kTRUE);
        const std::filesystem::path path = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/benchmark_config.json"};
        const BenchmarkConfig config{path};
        BenchmarkRunner::run(config);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Kernel benchmark error: " << error.what() << '\n';
        return 1;
    }
}
