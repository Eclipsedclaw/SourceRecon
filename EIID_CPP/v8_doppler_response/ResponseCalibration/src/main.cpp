#include "CalibrationConfig.h"
#include "CalibrationPipeline.h"

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
            std::cerr << "Usage: response_calibrator [path/to/calibration_config.json]\n";
            return 1;
        }

        gROOT->SetBatch(kTRUE);
        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/calibration_config.json"};
        const CalibrationConfig config{configPath};
        CalibrationPipeline::run(config);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Response calibration error: " << error.what() << '\n';
        return 1;
    }
}
