#include "ExperimentRootWriter.hh"

#include "ConfigManager.hh"

#include "TFile.h"
#include "TH1D.h"
#include "TNamed.h"
#include "TParameter.h"
#include "TTree.h"
#include <nlohmann/json.hpp>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace
{
void createParentDirectory(const std::filesystem::path& path)
{
    if (!path.parent_path().empty())
    {
        std::filesystem::create_directories(path.parent_path());
    }
}
}

ExperimentRootWriter::ExperimentRootWriter(const ConfigManager& config)
    : config_{&config}
{
}

ExperimentRootWriter::~ExperimentRootWriter() = default;

void ExperimentRootWriter::open()
{
    createParentDirectory(config_->outputRootFile());
    file_.reset(TFile::Open(config_->outputRootFile().string().c_str(), "RECREATE"));

    if (!file_ || file_->IsZombie())
    {
        throw std::runtime_error{
            "Cannot create ROOT output: " + config_->outputRootFile().string()
        };
    }

    file_->cd();
    tree_ = new TTree(
        config_->outputTreeName().c_str(),
        "Two-layer escape-Compton events for the Doppler experiment"
    );

    tree_->Branch("event_id", &buffer_.eventId);
    tree_->Branch("primary_interaction_count", &buffer_.primaryInteractionCount);
    tree_->Branch("second_interaction_code", &buffer_.secondInteractionCode);
    tree_->Branch("detector_kinematics_valid", &buffer_.detectorKinematicsValid);

    tree_->Branch("truth_e1_MeV", &buffer_.truthE1MeV);
    tree_->Branch("detector_e1_MeV", &buffer_.detectorE1MeV);
    tree_->Branch("detector_e2_MeV", &buffer_.detectorE2MeV);

    tree_->Branch("truth_r1_x_mm", &buffer_.truthR1Xmm);
    tree_->Branch("truth_r1_y_mm", &buffer_.truthR1Ymm);
    tree_->Branch("truth_r1_z_mm", &buffer_.truthR1Zmm);
    tree_->Branch("truth_r2_x_mm", &buffer_.truthR2Xmm);
    tree_->Branch("truth_r2_y_mm", &buffer_.truthR2Ymm);
    tree_->Branch("truth_r2_z_mm", &buffer_.truthR2Zmm);
    tree_->Branch("detector_r1_x_mm", &buffer_.detectorR1Xmm);
    tree_->Branch("detector_r1_y_mm", &buffer_.detectorR1Ymm);
    tree_->Branch("detector_r1_z_mm", &buffer_.detectorR1Zmm);
    tree_->Branch("detector_r2_x_mm", &buffer_.detectorR2Xmm);
    tree_->Branch("detector_r2_y_mm", &buffer_.detectorR2Ymm);
    tree_->Branch("detector_r2_z_mm", &buffer_.detectorR2Zmm);

    tree_->Branch("incoming_x", &buffer_.incomingX);
    tree_->Branch("incoming_y", &buffer_.incomingY);
    tree_->Branch("incoming_z", &buffer_.incomingZ);
    tree_->Branch("outgoing_x", &buffer_.outgoingX);
    tree_->Branch("outgoing_y", &buffer_.outgoingY);
    tree_->Branch("outgoing_z", &buffer_.outgoingZ);

    tree_->Branch("truth_theta_geo_degree", &buffer_.truthThetaGeoDegree);
    tree_->Branch("truth_theta_kin_degree", &buffer_.truthThetaKinDegree);
    tree_->Branch("truth_arm_degree", &buffer_.truthArmDegree);
    tree_->Branch(
        "truth_reconstructed_energy_MeV",
        &buffer_.truthReconstructedEnergyMeV
    );
    tree_->Branch("truth_energy_residual_MeV", &buffer_.truthEnergyResidualMeV);
    tree_->Branch(
        "truth_relative_energy_residual",
        &buffer_.truthRelativeEnergyResidual
    );

    tree_->Branch("detector_theta_geo_degree", &buffer_.detectorThetaGeoDegree);
    tree_->Branch("detector_theta_kin_degree", &buffer_.detectorThetaKinDegree);
    tree_->Branch("detector_arm_degree", &buffer_.detectorArmDegree);
    tree_->Branch(
        "detector_reconstructed_energy_MeV",
        &buffer_.detectorReconstructedEnergyMeV
    );
    tree_->Branch(
        "detector_energy_residual_MeV",
        &buffer_.detectorEnergyResidualMeV
    );
    tree_->Branch(
        "detector_relative_energy_residual",
        &buffer_.detectorRelativeEnergyResidual
    );

    truthArmHistogram_ = new TH1D(
        "TruthArmDistribution",
        "Truth-level ARM;ARM (degree);selected events",
        800,
        -40.0,
        40.0
    );
    detectorArmHistogram_ = new TH1D(
        "DetectorArmDistribution",
        "Detector-level ARM;ARM (degree);valid detector events",
        800,
        -40.0,
        40.0
    );
    truthEnergyResidualHistogram_ = new TH1D(
        "TruthEnergyResidualDistribution",
        "Truth-level EIID residual;E_{EIID}-E_{true} (MeV);selected events",
        1000,
        -0.5,
        0.5
    );
    detectorEnergyResidualHistogram_ = new TH1D(
        "DetectorEnergyResidualDistribution",
        "Detector-level EIID residual;E_{EIID}-E_{true} (MeV);valid detector events",
        1000,
        -0.5,
        0.5
    );
}

void ExperimentRootWriter::write(const ExperimentRecord& record)
{
    if (tree_ == nullptr)
    {
        throw std::logic_error{"ExperimentRootWriter::open must be called first."};
    }

    buffer_ = record;
    tree_->Fill();
    truthArmHistogram_->Fill(record.truthArmDegree);
    truthEnergyResidualHistogram_->Fill(record.truthEnergyResidualMeV);

    if (record.detectorKinematicsValid != 0 &&
        std::isfinite(record.detectorArmDegree) &&
        std::isfinite(record.detectorEnergyResidualMeV))
    {
        detectorArmHistogram_->Fill(record.detectorArmDegree);
        detectorEnergyResidualHistogram_->Fill(record.detectorEnergyResidualMeV);
    }
}

void ExperimentRootWriter::finish(const ExperimentCounters& counters)
{
    if (!file_ || tree_ == nullptr)
    {
        throw std::logic_error{"Experiment ROOT output is not open."};
    }

    file_->cd();
    TNamed model{"compton_model", config_->comptonModel().c_str()};
    TNamed experiment{"experiment_name", config_->experimentName().c_str()};
    TParameter<double> sourceEnergy{"source_energy_MeV", config_->sourceEnergyMeV()};
    TParameter<double> sourceTheta{"source_theta_degree", config_->sourceThetaDegree()};
    TParameter<double> sourcePhi{"source_phi_degree", config_->sourcePhiDegree()};
    TParameter<Long64_t> emitted{
        "emitted_events",
        static_cast<Long64_t>(counters.emitted)
    };
    TParameter<Long64_t> selected{
        "selected_truth_events",
        static_cast<Long64_t>(counters.selectedTruth)
    };

    model.Write();
    experiment.Write();
    sourceEnergy.Write();
    sourceTheta.Write();
    sourcePhi.Write();
    emitted.Write();
    selected.Write();
    tree_->Write();
    truthArmHistogram_->Write();
    detectorArmHistogram_->Write();
    truthEnergyResidualHistogram_->Write();
    detectorEnergyResidualHistogram_->Write();
    file_->Write();
    file_->Close();

    createParentDirectory(config_->summaryJsonFile());
    const double selectedFraction = counters.emitted == 0
        ? 0.0
        : static_cast<double>(counters.selectedTruth) /
            static_cast<double>(counters.emitted);

    const nlohmann::json summary{
        {"experiment_name", config_->experimentName()},
        {"compton_model", config_->comptonModel()},
        {"source_energy_MeV", config_->sourceEnergyMeV()},
        {"emitted", counters.emitted},
        {"events_with_any_hit", counters.eventsWithAnyHit},
        {"events_with_any_gamma_hit", counters.eventsWithAnyGammaHit},
        {"events_with_primary_gamma_hit", counters.eventsWithPrimaryGammaHit},
        {"selected_truth", counters.selectedTruth},
        {"selected_fraction", selectedFraction},
        {"detector_kinematics_valid", counters.detectorKinematicsValid},
        {"detector_kinematics_invalid", counters.detectorKinematicsInvalid},
        {"rejected_no_primary_gamma_step", counters.rejectedNoPrimaryGammaStep},
        {"rejected_missed_front_chamber", counters.rejectedMissedFrontChamber},
        {"rejected_no_primary_interaction", counters.rejectedNoPrimaryInteraction},
        {"rejected_wrong_first_interaction", counters.rejectedWrongFirstInteraction},
        {"rejected_missing_second_interaction", counters.rejectedMissingSecondInteraction},
        {"rejected_wrong_second_interaction", counters.rejectedWrongSecondInteraction},
        {"rejected_layer_threshold", counters.rejectedLayerThreshold},
        {"rejected_truth_kinematics", counters.rejectedTruthKinematics},
        {"root_file", config_->outputRootFile().string()}
    };

    std::ofstream output{config_->summaryJsonFile()};

    if (!output)
    {
        throw std::runtime_error{
            "Cannot create JSON summary: " + config_->summaryJsonFile().string()
        };
    }

    output << summary.dump(2) << '\n';
}
