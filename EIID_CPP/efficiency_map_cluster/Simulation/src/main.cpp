#include "TaskRunner.hh"
#include <exception>
#include <iostream>

int main(int argc, char** argv)
{
    try
    {
        if (argc != 3)
        {
            throw std::runtime_error{"Usage: efficiency_simulator manifest.json job_id"};
        }
        const std::string id{argv[2]};
        if (id.empty() || id.find_first_not_of("0123456789") != std::string::npos)
        {
            throw std::runtime_error{"job_id must be a nonnegative integer"};
        }
        TaskRunner{}.run(Campaign{argv[1]}, std::stoull(id));
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "Simulation error: " << error.what() << std::endl;
        return 1;
    }
}
