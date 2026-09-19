#include "RootSampleReader.h"
#include "CalibrationSchema.h"

#include "TFile.h"
#include "TNamed.h"
#include "TParameter.h"
#include "TTree.h"
#include "TTreeReader.h"
#include "TTreeReaderValue.h"

#include <cmath>
#include <cstdint>
#include <stdexcept>

std::vector<ResponseSample> RootSampleReader::read(
    const CalibrationInput& input
)
{
    TFile file{input.file.string().c_str(), "READ"};

    if (file.IsZombie())
    {
        throw std::runtime_error{
            "Cannot open calibration sample: " + input.file.string()
        };
    }

    TTree* tree = file.Get<TTree>(input.tree.c_str());
    auto* sourceEnergy = file.Get<TParameter<double>>(
        CalibrationSchema::sourceEnergyMetadata.data()
    );
    auto* model = file.Get<TNamed>("compton_model");

    if (tree == nullptr || sourceEnergy == nullptr || model == nullptr)
    {
        throw std::runtime_error{
            "Calibration file lacks its event tree or source_energy_MeV: " +
            input.file.string()
        };
    }

    if (input.comptonModel != model->GetTitle())
    {
        throw std::runtime_error{
            "Calibration sample has Compton model '" +
            std::string{model->GetTitle()} + "', expected '" +
            input.comptonModel + "': " + input.file.string()
        };
    }

    const bool detector = input.level == "detector";
    TTreeReader reader{tree};
    // The writer stores ExperimentRecord::eventId as std::int64_t.  On
    // 64-bit Linux that typedef is `long`, while ROOT's Long64_t is
    // `long long`.  They have the same width but ROOT deliberately requires
    // the C++ types to match exactly, so read with the writer's actual type.
    TTreeReaderValue<std::int64_t> eventId{
        reader,
        CalibrationSchema::eventId.data()
    };
    TTreeReaderValue<Int_t> detectorValid{
        reader,
        CalibrationSchema::detectorKinematicsValid.data()
    };
    TTreeReaderValue<Double_t> angle{
        reader,
        detector
            ? CalibrationSchema::detectorScatterAngle.data()
            : CalibrationSchema::truthScatterAngle.data()
    };
    TTreeReaderValue<Double_t> arm{
        reader,
        detector
            ? CalibrationSchema::detectorArm.data()
            : CalibrationSchema::truthArm.data()
    };

    std::vector<ResponseSample> samples;
    samples.reserve(static_cast<std::size_t>(tree->GetEntries()));

    while (reader.Next())
    {
        if (detector && *detectorValid == 0)
        {
            continue;
        }

        if (!std::isfinite(*angle) || !std::isfinite(*arm))
        {
            continue;
        }

        samples.push_back(ResponseSample{
            static_cast<std::int64_t>(*eventId),
            sourceEnergy->GetVal(),
            *angle,
            *arm
        });
    }

    return samples;
}
