#include "GridAdapter.h"
#include "ResamplerConfig.h"
#include "ResamplerIO.h"
#include "SensitivityMatrix.h"

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

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"GridResampler/config/resampler_config.json"};

        const ResamplerConfig config{configPath};
        const GridAdapter adapter{
            config.masterGrid(),
            config.targetGrid(),
            config.polygonSubdivisionFactor(),
            config.requireFullCoverage()
        };

        const SensitivityMatrix master = ResamplerIO::read(
            config.inputSensitivityFile(),
            config.inputSensitivityTree(),
            adapter.masterGrid()
        );

        const SensitivityMatrix target = adapter.resample(
            master,
            config.interpolation()
        );

        if (!config.outputSensitivityFile().parent_path().empty())
        {
            std::filesystem::create_directories(
                config.outputSensitivityFile().parent_path()
            );
        }

        ResamplerIO::write(
            config.outputSensitivityFile(),
            config.outputSensitivityTree(),
            adapter.targetGrid(),
            target
        );

        std::cout << "Grid resampling completed.\n"
                  << "  method: " << config.interpolation() << '\n'
                  << "  Master cells: " << master.size() << '\n'
                  << "  Target cells: " << target.size() << '\n'
                  << "  output: " << config.outputSensitivityFile().string() << '\n';
    }
    catch (const std::exception& error)
    {
        std::cerr << "Grid Resampler error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
