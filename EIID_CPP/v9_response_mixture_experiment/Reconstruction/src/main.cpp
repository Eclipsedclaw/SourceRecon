#include "HealpixGrid.h"
#include "IResponseKernel.h"
#include "LmMlemSolver.h"
#include "ReconConfig.h"
#include "ResponseKernelFactory.h"
#include "RootEfficiencyReader.h"
#include "RootEventReader.h"
#include "RootImageWriter.h"

#include <exception>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char* argv[])
{
    try
    {
        const bool validateEventsOnly = argc == 3 &&
            std::string{argv[1]} == "--validate-events-only";

        if ((!validateEventsOnly && argc > 2) ||
            (validateEventsOnly && argc != 3))
        {
            std::cerr
                << "Usage:\n"
                << "  EIID_Recon_V9 [path/to/recon_config.json]\n"
                << "  EIID_Recon_V9 --validate-events-only path/to/recon_config.json\n";
            return 1;
        }

        const std::filesystem::path configPath = validateEventsOnly
            ? std::filesystem::path{argv[2]}
            : argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/recon_config.json"};
        const ReconConfig config{configPath};
        const std::vector<Event> events = RootEventReader::read(config);

        if (validateEventsOnly)
        {
            std::cout << "External event input is valid.\n"
                      << "  file: " << config.inputEventsFile().string() << '\n'
                      << "  tree: " << config.inputEventsTree() << '\n'
                      << "  events: " << events.size() << '\n';
            return 0;
        }

        const HealpixGrid grid{
            config.healpixNside(),
            config.energyPointCount(),
            config.energyMinMeV(),
            config.energyMaxMeV()
        };
        const AbsoluteEfficiencyMap efficiency =
            RootEfficiencyReader::read(config, grid);
        const std::unique_ptr<IResponseKernel> responseKernel =
            ResponseKernelFactory::create(config.responseKernel());
        const LmMlemSolver solver{
            grid,
            efficiency,
            config,
            *responseKernel
        };
        const std::vector<Decimal> image = solver.solve(events);
        RootImageWriter::write(image, grid, config);

        std::cout << "EIID V9 reconstruction completed.\n"
                  << "  events: " << events.size() << '\n'
                  << "  cells: " << grid.cells().size() << '\n'
                  << "  response kernel: "
                  << responseKernel->name() << '\n'
                  << "  result: " << config.outputResultFile().string() << '\n';
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "EIID V9 error: " << error.what() << '\n';
        return 1;
    }
}
