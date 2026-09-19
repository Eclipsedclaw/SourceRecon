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

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: EIID_Recon_V8 [path/to/recon_config.json]\n";
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

        std::cout << "EIID V8 reconstruction completed.\n"
                  << "  events: " << events.size() << '\n'
                  << "  cells: " << grid.cells().size() << '\n'
                  << "  response kernel: "
                  << responseKernel->name() << '\n'
                  << "  result: " << config.outputResultFile().string() << '\n';
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "EIID V8 error: " << error.what() << '\n';
        return 1;
    }
}
