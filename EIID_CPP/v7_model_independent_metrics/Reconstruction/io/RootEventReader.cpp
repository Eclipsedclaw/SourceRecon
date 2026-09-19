#include "RootEventReader.h"

#include "ReconConfig.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <cmath>
#include <memory>
#include <stdexcept>

namespace
{
void requireBranch(TTree& tree, const std::string& name)
{
    if (tree.GetBranch(name.c_str()) == nullptr)
    {
        throw std::runtime_error{"Missing event branch: " + name};
    }
}
}

std::vector<Event> RootEventReader::read(const ReconConfig& config)
{
    std::unique_ptr<TFile> file{
        TFile::Open(config.inputEventsFile().string().c_str(), "READ")
    };

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{
            "Cannot open event file: " + config.inputEventsFile().string()
        };
    }

    TTree* tree = file->Get<TTree>(config.inputEventsTree().c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find event tree: " + config.inputEventsTree()};
    }

    const EventBranchNames& names = config.eventBranches();
    requireBranch(*tree, names.r1X);
    requireBranch(*tree, names.r1Y);
    requireBranch(*tree, names.r1Z);
    requireBranch(*tree, names.r2X);
    requireBranch(*tree, names.r2Y);
    requireBranch(*tree, names.r2Z);
    requireBranch(*tree, names.e1MeV);

    TTreeReader reader{tree};
    TTreeReaderValue<Double_t> r1X{reader, names.r1X.c_str()};
    TTreeReaderValue<Double_t> r1Y{reader, names.r1Y.c_str()};
    TTreeReaderValue<Double_t> r1Z{reader, names.r1Z.c_str()};
    TTreeReaderValue<Double_t> r2X{reader, names.r2X.c_str()};
    TTreeReaderValue<Double_t> r2Y{reader, names.r2Y.c_str()};
    TTreeReaderValue<Double_t> r2Z{reader, names.r2Z.c_str()};
    TTreeReaderValue<Double_t> e1{reader, names.e1MeV.c_str()};
    std::vector<Event> events;
    events.reserve(static_cast<std::size_t>(tree->GetEntries()));

    while (reader.Next())
    {
        if (!std::isfinite(*r1X) || !std::isfinite(*r1Y) ||
            !std::isfinite(*r1Z) || !std::isfinite(*r2X) ||
            !std::isfinite(*r2Y) || !std::isfinite(*r2Z) ||
            !std::isfinite(*e1) || *e1 <= 0.0)
        {
            throw std::runtime_error{"The event tree contains an invalid row."};
        }

        events.push_back(
            Event{
                Vec3{*r1X, *r1Y, *r1Z},
                Vec3{*r2X, *r2Y, *r2Z},
                *e1
            }
        );
    }

    if (events.empty())
    {
        throw std::runtime_error{"The event tree contains no events."};
    }

    return events;
}
