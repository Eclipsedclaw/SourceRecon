#include "data_input.h"

#include <RtypesCore.h>
#include <TFile.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>

namespace
{
void requireBranch(TTree& tree, const std::string& branchName)
{
    if (tree.GetBranch(branchName.c_str()) == nullptr)
    {
        throw std::runtime_error{"Missing event ROOT branch: " + branchName};
    }
}
}

std::vector<Event> readEventsFromRoot(const ReconConfig& config)
{
    std::unique_ptr<TFile> inputFile{
        TFile::Open(config.inputEventsFile().string().c_str(), "READ")
    };

    if (!inputFile || inputFile->IsZombie())
    {
        throw std::runtime_error{"Cannot open translated event file: " + config.inputEventsFile().string()};
    }

    TTree* tree = inputFile->Get<TTree>(config.inputEventsTree().c_str());

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find translated event tree: " + config.inputEventsTree()};
    }

    const EventBranchNames& branches = config.eventBranches();
    requireBranch(*tree, branches.r1X);
    requireBranch(*tree, branches.r1Y);
    requireBranch(*tree, branches.r1Z);
    requireBranch(*tree, branches.r2X);
    requireBranch(*tree, branches.r2Y);
    requireBranch(*tree, branches.r2Z);
    requireBranch(*tree, branches.e1MeV);

    TTreeReader reader{tree};
    TTreeReaderValue<Double_t> r1X{reader, branches.r1X.c_str()};
    TTreeReaderValue<Double_t> r1Y{reader, branches.r1Y.c_str()};
    TTreeReaderValue<Double_t> r1Z{reader, branches.r1Z.c_str()};
    TTreeReaderValue<Double_t> r2X{reader, branches.r2X.c_str()};
    TTreeReaderValue<Double_t> r2Y{reader, branches.r2Y.c_str()};
    TTreeReaderValue<Double_t> r2Z{reader, branches.r2Z.c_str()};
    TTreeReaderValue<Double_t> e1MeV{reader, branches.e1MeV.c_str()};

    std::vector<Event> events;
    events.reserve(static_cast<std::size_t>(tree->GetEntries()));

    while (reader.Next())
    {
        if (!std::isfinite(*r1X) || !std::isfinite(*r1Y) ||
            !std::isfinite(*r1Z) || !std::isfinite(*r2X) ||
            !std::isfinite(*r2Y) || !std::isfinite(*r2Z) ||
            !std::isfinite(*e1MeV) || *e1MeV <= 0.0)
        {
            throw std::runtime_error{
                "Translated event tree contains an invalid event row."
            };
        }

        events.push_back(
            Event{
                Vec3{
                    static_cast<Decimal>(*r1X),
                    static_cast<Decimal>(*r1Y),
                    static_cast<Decimal>(*r1Z)
                },
                Vec3{
                    static_cast<Decimal>(*r2X),
                    static_cast<Decimal>(*r2Y),
                    static_cast<Decimal>(*r2Z)
                },
                static_cast<Decimal>(*e1MeV)
            }
        );
    }

    if (events.empty())
    {
        throw std::runtime_error{"The translated event tree contains no events."};
    }

    return events;
}
