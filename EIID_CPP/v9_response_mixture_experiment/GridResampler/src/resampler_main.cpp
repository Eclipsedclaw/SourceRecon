#include "GridAdapter.h"
#include "ResamplerConfig.h"
#include "ResamplerIO.h"

#include <exception>
#include <filesystem>
#include <iostream>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: grid_resampler [path/to/resampler_config.json]\n";
            return 1;
        }

        const std::filesystem::path path = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/resampler_config.json"};
        const ResamplerConfig config{path};
        const GridAdapter adapter{config};
        EfficiencyDataset master = ResamplerIO::read(
            config.inputFile(),
            config.inputTree(),
            adapter.masterGrid()
        );
        const AbsoluteEfficiencyMap target = adapter.resample(master.values);
        ResamplerIO::write(
            config.outputFile(),
            config.outputTree(),
            adapter.targetGrid(),
            target,
            master.sourceRadiusMm
        );

        std::cout << "Grid resampling completed.\n"
                  << "  strategy: " << adapter.strategyName() << '\n'
                  << "  Master cells: " << master.values.size() << '\n'
                  << "  Target cells: " << target.size() << '\n'
                  << "  output: " << config.outputFile().string() << '\n';
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Grid Resampler error: " << error.what() << '\n';
        return 1;
    }
}
