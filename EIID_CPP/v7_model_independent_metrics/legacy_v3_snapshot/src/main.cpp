#include "ReconConfig.h"
#include "SensitivityMatrix.h"
#include "data_input.h"
#include "data_output.h"
#include "eiid_core.h"
#include "grid.h"
#include "mlem_core.h"
#include "sensitivity_reader.h"

#include <exception>
#include <filesystem>
#include <iostream>
#include <vector>

int main(int argc, char* argv[])
{
    try
    {
        if (argc > 2)
        {
            std::cerr << "Usage: EIID_Recon_V3 [path/to/recon_config.json]\n";
            return 1;
        }

        const std::filesystem::path configPath = argc == 2
            ? std::filesystem::path{argv[1]}
            : std::filesystem::path{"config/recon_config.json"};

        const ReconConfig config{configPath};
        const Grid grid{config};
        const std::vector<Event> events = readEventsFromRoot(config);
        const SensitivityMatrix sensitivity = readSensitivityFromRoot(config, grid);

        const LmMlemSolver solver{grid, sensitivity, config};
        const std::vector<Decimal> image = solver.solve(events);

        saveImageToFile(image, grid, config);

        std::cout << "EIID V3 reconstruction completed.\n"
                  << "  events: " << events.size() << '\n'
                  << "  cells: " << grid.cells().size() << '\n'
                  << "  result: " << config.outputResultFile().string() << '\n';
    }
    catch (const std::exception& error)
    {
        std::cerr << "EIID V3 error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
