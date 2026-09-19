#include "HealpixGrid.h"
#include "LmMlemSolver.h"
#include "ReconConfig.h"
#include "RootEfficiencyReader.h"
#include "RootEventReader.h"
#include "RootImageWriter.h"

#include <exception>
#include <filesystem>
#include <iostream>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: EIID_Recon_V4 [path/to/recon_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/recon_config.json"};
        const ReconConfig config{configPath};
        const HealpixGrid grid{
            config.healpixNside(),
            config.energyPointCount(),
            config.energyMinMeV(),
            config.energyMaxMeV()
        };
        const std::vector<Event> events = RootEventReader::read(config);
        const AbsoluteEfficiencyMap efficiency =
            RootEfficiencyReader::read(config, grid);
        const LmMlemSolver solver{grid, efficiency, config};
        const std::vector<Decimal> image = solver.solve(events);
        RootImageWriter::write(image, grid, config);

        std::cout << "EIID V4 reconstruction completed.\n"
                  << "  events: " << events.size() << '\n'
                  << "  cells: " << grid.cells().size() << '\n'
                  << "  result: " << config.outputResultFile().string() << '\n';
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "EIID V4 error: " << error.what() << '\n';
        return 1;
    }
}
