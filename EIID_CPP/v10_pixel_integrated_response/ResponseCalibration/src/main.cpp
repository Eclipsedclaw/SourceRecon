#include "CalibrationConfig.h"
#include "CalibrationPipeline.h"

#include "TROOT.h"
#include "TStyle.h"

#include <nlohmann/json.hpp>

#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
int reportModelUsability(
    const std::filesystem::path& statusPath,
    const std::string& model
)
{
    std::ifstream input{statusPath};

    if (!input)
    {
        throw std::runtime_error{
            "Cannot open model-status JSON: " + statusPath.string()
        };
    }

    nlohmann::json document;
    input >> document;
    const auto& status = document.at("models").at(model);
    const bool usable = status.at("usable").get<bool>();
    std::cout << model << ": " << (usable ? "USABLE" : "SKIPPED")
              << " (" << status.at("converged_bins").get<std::size_t>()
              << '/' << status.at("total_bins").get<std::size_t>()
              << " calibration bins converged)\n";
    return usable ? 0 : 2;
}
}

int main(int argc, char* argv[])
{
    try
    {
        if (argc == 4 && std::string{argv[1]} == "--model-usable")
        {
            return reportModelUsability(argv[2], argv[3]);
        }

        if (argc > 2)
        {
            std::cerr
                << "Usage:\n"
                << "  response_calibrator [path/to/calibration_config.json]\n"
                << "  response_calibrator --model-usable status.json model\n";
            return 1;
        }

        gROOT->SetBatch(kTRUE);
        gStyle->SetOptStat(0);
        gStyle->SetOptFit(0);
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
